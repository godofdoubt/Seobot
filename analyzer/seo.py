
import logging
import time
import random
import asyncio
import re 
from collections import deque
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
import aiohttp
from typing import Set, Dict, List, Any, Optional
from analyzer.methods import validate_url, extract_text 
from analyzer.seoreportsaver import SEOReportSaver
import analyzer.config as config
from analyzer.sitemap import discover_sitemap_urls, fetch_all_pages_from_sitemaps
from analyzer.llm_analysis_start import llm_analysis_start
from urllib.parse import urlparse, urljoin, urlunparse

# Configure logging with reduced verbosity
logging.basicConfig(
    level=logging.WARNING,  # Changed from DEBUG to WARNING
    format='%(asctime)s - %(levelname)s - %(message)s'  # Simplified format
)

# Set specific loggers to higher levels to reduce noise
logging.getLogger('analyzer.methods').setLevel(logging.ERROR)
logging.getLogger('analyzer').setLevel(logging.WARNING)
logging.getLogger('playwright').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)

load_dotenv()


class SEOAnalyzer:
    def __init__(self):
        self.saver = SEOReportSaver()
        self.visited_urls: Set[str] = set()
        self.all_discovered_links: Set[str] = set()
        self.site_base_for_normalization: Optional[str] = None
        self.start_domain_normal_part: Optional[str] = None
        self.identified_header_texts: List[str] = [] 
        self.identified_footer_texts: List[str] = [] 
        self.initial_page_llm_report: Optional[Dict[str, Any]] = None

    def _normalize_url(self, url: str, site_canonical_base_url: str) -> Optional[str]:
        """
        Normalizes a URL relative to the site's canonical base URL.
        Ensures scheme, www/non-www, trailing slashes, and case are consistent for internal URLs.
        Removes fragments and default ports.
        """
        try:
            absolute_url = urljoin(site_canonical_base_url, url)
            parsed_original_link = urlparse(absolute_url)

            if parsed_original_link.scheme not in ('http', 'https') or not parsed_original_link.netloc:
                return None

            parsed_site_canonical = urlparse(site_canonical_base_url)
            target_scheme = parsed_site_canonical.scheme
            original_link_netloc_lower = parsed_original_link.netloc.lower()
            site_canonical_netloc_lower = parsed_site_canonical.netloc.lower()
            original_link_domain_part = original_link_netloc_lower.split(':')[0].replace('www.', '', 1)
            site_canonical_domain_part = site_canonical_netloc_lower.split(':')[0].replace('www.', '', 1)

            if original_link_domain_part != site_canonical_domain_part:
                return None 

            target_netloc = site_canonical_netloc_lower 

            if (target_scheme == 'http' and target_netloc.endswith(':80')):
                target_netloc = target_netloc.rsplit(':', 1)[0]
            elif (target_scheme == 'https' and target_netloc.endswith(':443')):
                target_netloc = target_netloc.rsplit(':', 1)[0]

            path = parsed_original_link.path
            if not path: 
                path = '/'
            elif not path.endswith('/') and ('.' not in path.split('/')[-1] if path.split('/')[-1] else True):
                path = f"{path}/"

            query = parsed_original_link.query 
            fragment = '' 

            normalized = urlunparse((
                target_scheme,
                target_netloc,
                path,
                parsed_original_link.params,
                query,
                fragment
            ))
            return normalized

        except Exception as e:
            logging.error(f"Error normalizing URL '{url}': {e}")
            return None

    # --- START: NEW METHODS ADDED HERE ---
    async def _extract_internal_links_from_page_enhanced(self, page: Page, base_domain_check_part: str, site_canonical_base_url: str, exclude_patterns: List[str]) -> Set[str]:
        """Enhanced link extraction with multiple strategies and better error handling."""
        
        # Strategy 1: Enhanced JavaScript extraction with better error handling
        try:
            links_js_enhanced_result = await page.evaluate("""
                (params) => {
                    const baseDomain = params.baseDomain;
                    const excludePatterns = params.excludePatterns;
                    const links = new Set();
                    const allowedSchemes = ['http:', 'https:'];
                    
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    const buttons = Array.from(document.querySelectorAll('button[onclick], [data-href], [data-url]'));
                    
                    anchors.forEach(link => {
                        try {
                            if (!link.href) return;
                            const absoluteUrl = new URL(link.href, document.baseURI).href;
                            const linkUrl = new URL(absoluteUrl);
                            if (!allowedSchemes.includes(linkUrl.protocol)) return;
                            const linkDomain = linkUrl.hostname.replace(/^www\\./i, '');
                            if (linkDomain === baseDomain) {
                                const shouldExclude = excludePatterns.some(pattern => {
                                    return absoluteUrl.toLowerCase().includes(pattern.toLowerCase());
                                });
                                if (!shouldExclude) {
                                    links.add(absoluteUrl);
                                }
                            }
                        } catch (e) {
                            console.warn('Error processing link:', link.href, e);
                        }
                    });
                    
                    buttons.forEach(btn => {
                        try {
                            const href = btn.getAttribute('data-href') || 
                                       btn.getAttribute('data-url') ||
                                       btn.getAttribute('onclick');
                            if (href && !href.includes('javascript:')) {
                                let extractedUrl = href;
                                if (href.includes('location.href') || href.includes('window.open')) {
                                    const urlMatch = href.match(/['"`]([^'"`]+)['"`]/);
                                    if (urlMatch) extractedUrl = urlMatch[1];
                                }
                                try {
                                    const absoluteUrl = new URL(extractedUrl, document.baseURI).href;
                                    const linkUrl = new URL(absoluteUrl);
                                    if (allowedSchemes.includes(linkUrl.protocol)) {
                                        const linkDomain = linkUrl.hostname.replace(/^www\\./i, '');
                                        if (linkDomain === baseDomain) {
                                            const shouldExclude = excludePatterns.some(pattern => 
                                                absoluteUrl.toLowerCase().includes(pattern.toLowerCase())
                                            );
                                            if (!shouldExclude) {
                                                links.add(absoluteUrl);
                                            }
                                        }
                                    }
                                } catch (e) {}
                            }
                        } catch (e) {
                            console.warn('Error processing button/element:', e);
                        }
                    });
                    return {
                        links: Array.from(links),
                        anchorsFound: anchors.length,
                        buttonsFound: buttons.length
                    };
                }
            """, {"baseDomain": base_domain_check_part, "excludePatterns": exclude_patterns})
            
            print(f"Found {links_js_enhanced_result['anchorsFound']} anchor tags and {links_js_enhanced_result['buttonsFound']} interactive elements on {page.url}")
            links_js_enhanced_links = links_js_enhanced_result.get('links', [])

        except Exception as e:
            logging.error(f"Enhanced JS link extraction failed for {page.url}: {e}")
            links_js_enhanced_links = []
        
        # Strategy 2: Playwright's built-in link detection as backup
        try:
            playwright_links_locators = await page.locator('a[href]').all()
            playwright_urls = []
            
            for link_element in playwright_links_locators:
                try:
                    href = await link_element.get_attribute('href')
                    if href:
                        absolute_url = urljoin(page.url, href) # Use current page URL as base
                        parsed = urlparse(absolute_url)
                        
                        if (parsed.scheme in ('http', 'https') and 
                            parsed.netloc.replace('www.', '', 1).lower() == base_domain_check_part.lower()):
                            
                            if not any(exclude.lower() in absolute_url.lower() for exclude in exclude_patterns):
                                playwright_urls.append(absolute_url)
                except Exception: # Skip individual link errors
                    continue
            if playwright_urls: # Only print if Playwright method found something not already obvious
                 print(f"Playwright method found {len(playwright_urls)} potential links on {page.url}")
            
        except Exception as e:
            logging.warning(f"Playwright link extraction failed for {page.url}: {e}")
            playwright_urls = []
        
        # Strategy 3: Extract from navigation menus specifically
        try:
            nav_links_from_js = await page.evaluate("""
                (params) => {
                    const baseDomain = params.baseDomain;
                    const excludePatterns = params.excludePatterns;
                    const navLinks = new Set();
                    const navSelectors = [
                        'nav a[href]', '.nav a[href]', '.navigation a[href]', '.menu a[href]',
                        '.navbar a[href]', 'header a[href]', '[role="navigation"] a[href]',
                        '.main-menu a[href]', '.primary-menu a[href]'
                    ];
                    navSelectors.forEach(selector => {
                        try {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(link => {
                                try {
                                    if (link.href) {
                                        const absoluteUrl = new URL(link.href, document.baseURI).href;
                                        const linkUrl = new URL(absoluteUrl);
                                        if (['http:', 'https:'].includes(linkUrl.protocol)) {
                                            const linkDomain = linkUrl.hostname.replace(/^www\\./i, '');
                                            if (linkDomain === baseDomain) {
                                                const shouldExclude = excludePatterns.some(pattern => 
                                                    absoluteUrl.toLowerCase().includes(pattern.toLowerCase())
                                                );
                                                if (!shouldExclude) {
                                                    navLinks.add(absoluteUrl);
                                                }
                                            }
                                        }
                                    }
                                } catch (e) {}
                            });
                        } catch (e) {}
                    });
                    return Array.from(navLinks);
                }
            """, {"baseDomain": base_domain_check_part, "excludePatterns": exclude_patterns})
            if nav_links_from_js:
                print(f"Navigation-specific extraction found {len(nav_links_from_js)} links on {page.url}")
            
        except Exception as e:
            logging.warning(f"Navigation link extraction failed for {page.url}: {e}")
            nav_links_from_js = []
        
        # Strategy 4: Extract from structured data (JSON-LD, microdata)
        try:
            structured_links_raw = await page.evaluate("""
                () => {
                    const links = new Set();
                    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
                    jsonLdScripts.forEach(script => {
                        try {
                            const data = JSON.parse(script.textContent);
                            const extractUrls = (obj) => {
                                if (typeof obj === 'string' && (obj.startsWith('http://') || obj.startsWith('https://'))) {
                                    links.add(obj);
                                } else if (typeof obj === 'object' && obj !== null) {
                                    Object.values(obj).forEach(extractUrls);
                                } else if (Array.isArray(obj)) {
                                    obj.forEach(extractUrls);
                                }
                            };
                            extractUrls(data);
                        } catch (e) {}
                    });
                    const microdataElements = document.querySelectorAll('[itemscope] [itemprop*="url"], [itemscope] [itemprop*="href"]');
                    microdataElements.forEach(el => {
                        const content = el.getAttribute('content') || el.getAttribute('href') || el.textContent;
                        if (content && (content.startsWith('http://') || content.startsWith('https://'))) {
                            links.add(content);
                        }
                    });
                    return Array.from(links);
                }
            """)
            
            filtered_structured_links = []
            for link_str in structured_links_raw:
                try:
                    parsed_link = urlparse(link_str)
                    if parsed_link.netloc.replace('www.', '', 1).lower() == base_domain_check_part.lower():
                        if not any(exclude.lower() in link_str.lower() for exclude in exclude_patterns):
                            filtered_structured_links.append(link_str)
                except:
                    continue
            if filtered_structured_links:
                print(f"Structured data extraction found {len(filtered_structured_links)} internal links on {page.url}")
            
        except Exception as e:
            logging.warning(f"Structured data link extraction failed for {page.url}: {e}")
            filtered_structured_links = []
        
        all_found_links_raw = set(links_js_enhanced_links + playwright_urls + nav_links_from_js + filtered_structured_links)
        
        normalized_final_links: Set[str] = set()
        for link_str in all_found_links_raw:
            normalized_link = self._normalize_url(link_str, site_canonical_base_url)
            if normalized_link:
                normalized_final_links.add(normalized_link)
        
        print(f"Total unique internal links found on {page.url}: {len(normalized_final_links)}")
        return normalized_final_links

    async def _wait_for_dynamic_content(self, page: Page, max_wait_seconds: int = 10) -> None:
        """Wait for dynamic content to load before extracting links."""
        print(f"Waiting for dynamic content on {page.url} (max {max_wait_seconds}s)...")
        try:
            # Timeout for network idle state (in milliseconds for Playwright)
            network_idle_timeout_ms = max_wait_seconds * 1000 * 0.7 
            await page.wait_for_load_state('networkidle', timeout=network_idle_timeout_ms)
            
            # Timeout for the JavaScript stability check (in seconds for asyncio.wait_for)
            js_stability_check_timeout_seconds = max_wait_seconds * 0.3
            
            js_code_for_stability_check = """
                () => new Promise(resolve => {
                    let lastCount = document.querySelectorAll('a[href]').length;
                    let stableCount = 0;
                    let checksDone = 0;
                    const maxChecks = 5; // Check for stability a few times
                    
                    const checkStability = () => {
                        checksDone++;
                        const currentCount = document.querySelectorAll('a[href]').length;
                        if (currentCount === lastCount) {
                            stableCount++;
                            if (stableCount >= 2) {  // Stable for 2 checks (e.g., 1 second if checks are 500ms apart)
                                resolve();
                                return;
                            }
                        } else {
                            stableCount = 0;
                            lastCount = currentCount;
                        }
                        if (checksDone >= maxChecks) {
                            resolve(); // Max checks reached, resolve anyway
                            return;
                        }
                        setTimeout(checkStability, 500); // Check every 500ms
                    };
                    
                    setTimeout(checkStability, 500); // Initial call to start checking
                    
                    // Fallback timeout within JS, should be less than or equal to js_stability_check_timeout_seconds
                    // e.g., maxChecks * 500ms + a small buffer. 5 * 500ms = 2500ms.
                    // A 3000ms (3s) JS fallback is reasonable if js_stability_check_timeout_seconds is also around 3s.
                    setTimeout(resolve, 3000); 
                })
            """
            
            # Use asyncio.wait_for to apply a timeout to the page.evaluate call
            await asyncio.wait_for(
                page.evaluate(js_code_for_stability_check),
                timeout=js_stability_check_timeout_seconds
            )
            
            # Scroll to trigger any lazy loading, with short waits
            await page.evaluate("""
                () => {
                    window.scrollTo(0, document.body.scrollHeight / 2);
                    return new Promise(resolve => setTimeout(resolve, 300)); // Wait for scroll effects
                }
            """)
            await page.evaluate("() => window.scrollTo(0, 0)") # Scroll back to top
            print(f"Dynamic content wait finished for {page.url}.")
            
        except PlaywrightTimeoutError: 
            # This timeout is from page.wait_for_load_state or other Playwright operations that accept a timeout kwarg
            logging.warning(f"PlaywrightTimeoutError during dynamic content wait for {page.url} (e.g., networkidle timed out).")
        except asyncio.TimeoutError: 
            # This timeout is specifically from asyncio.wait_for wrapping the page.evaluate call
            logging.warning(f"asyncio.TimeoutError during JavaScript stability check for {page.url}.")
        except Exception as e:
            # Catch other potential errors from Playwright or JS evaluation
            logging.warning(f"Dynamic content wait for {page.url} failed: {type(e).__name__} - {e}")

    async def _extract_links_with_context(self, page: Page, base_domain_check_part: str, site_canonical_base_url: str, exclude_patterns: List[str]) -> Dict[str, Any]:
        """Extract links with additional context information."""
        print(f"Extracting links with context from {page.url}...")
        try:
            links_with_context_data = await page.evaluate("""
                (params) => {
                    const baseDomain = params.baseDomain;
                    const excludePatterns = params.excludePatterns;
                    const result = {
                        links: [],
                        linksBySection: {},
                        importantLinks: []
                    };
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    
                    anchors.forEach(link => {
                        try {
                            if (!link.href) return;
                            const absoluteUrl = new URL(link.href, document.baseURI).href;
                            const linkUrl = new URL(absoluteUrl);
                            if (!['http:', 'https:'].includes(linkUrl.protocol)) return;
                            const linkDomain = linkUrl.hostname.replace(/^www\\./i, '');
                            if (linkDomain.toLowerCase() === baseDomain.toLowerCase()) { // case-insensitive domain check
                                const shouldExclude = excludePatterns.some(pattern => 
                                    absoluteUrl.toLowerCase().includes(pattern.toLowerCase())
                                );
                                if (!shouldExclude) {
                                    const linkInfo = {
                                        url: absoluteUrl,
                                        text: link.textContent?.trim() || '',
                                        title: link.getAttribute('title') || '',
                                        section: 'other'
                                    };
                                    const nav = link.closest('nav, .nav, .navigation, .menu, header, [role="navigation"]');
                                    const main = link.closest('main, .main, .content, article, section:not(header):not(footer)');
                                    const footer = link.closest('footer, .footer');
                                    
                                    if (nav) linkInfo.section = 'navigation';
                                    else if (main) linkInfo.section = 'content';
                                    else if (footer) linkInfo.section = 'footer';
                                    
                                    if (nav || 
                                        link.classList.contains('cta') ||
                                        link.classList.contains('button') ||
                                        link.matches('[role="button"]') ||
                                        link.textContent?.toLowerCase().includes('learn more') ||
                                        link.textContent?.toLowerCase().includes('read more') ||
                                        link.textContent?.toLowerCase().includes('contact')) {
                                        linkInfo.important = true;
                                        result.importantLinks.push(linkInfo);
                                    }
                                    result.links.push(linkInfo);
                                    if (!result.linksBySection[linkInfo.section]) {
                                        result.linksBySection[linkInfo.section] = [];
                                    }
                                    result.linksBySection[linkInfo.section].push(linkInfo);
                                }
                            }
                        } catch (e) {
                            console.warn('Error processing link in context extraction:', e);
                        }
                    });
                    return result;
                }
            """, {"baseDomain": base_domain_check_part, "excludePatterns": exclude_patterns})
            
            normalized_links_set: Set[str] = set()
            # Normalize URLs within the context data itself if needed, or just the set for discovery
            for link_info in links_with_context_data.get('links', []):
                normalized_url = self._normalize_url(link_info['url'], site_canonical_base_url)
                if normalized_url:
                    normalized_links_set.add(normalized_url)
                    link_info['normalized_url'] = normalized_url # Optionally add normalized URL to context
            
            print(f"Links by section on {page.url}: Navigation: {len(links_with_context_data.get('linksBySection', {}).get('navigation', []))}, "
                  f"Content: {len(links_with_context_data.get('linksBySection', {}).get('content', []))}, "
                  f"Footer: {len(links_with_context_data.get('linksBySection', {}).get('footer', []))}")
            print(f"Important links found on {page.url}: {len(links_with_context_data.get('importantLinks', []))}")
            
            return {
                'links': normalized_links_set, # This set is used for further crawling
                'context': links_with_context_data # This is the raw context data
            }
            
        except Exception as e:
            logging.error(f"Link extraction with context failed for {page.url}: {e}")
            return {'links': set(), 'context': {}}
    # --- END: NEW METHODS ADDED HERE ---

    async def _process_page(self, page: Page, url_to_crawl: str, 
                            start_domain_check_part: str, site_canonical_base_url: str, 
                            exclude_patterns: List[str],
                            header_snippets_to_remove: Optional[List[str]] = None,
                            footer_snippets_to_remove: Optional[List[str]] = None,
                            extract_with_context: bool = False  # New parameter
                            ) -> Dict[str, Any]:
        result = {
            'url': url_to_crawl,
            'cleaned_text': '',
            'new_links': set(),
            'link_context': {}  # Initialize link_context
        }
        
        try:
            await page.goto(url_to_crawl, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT)
            
            if extract_with_context:
                await self._wait_for_dynamic_content(page)
            
            actual_landed_url_str = page.url
            normalized_landed_url = self._normalize_url(actual_landed_url_str, site_canonical_base_url)

            if not normalized_landed_url:
                result['url'] = None # Mark as failed for this URL
                return result
            
            parsed_landed = urlparse(normalized_landed_url)
            # Ensure we haven't been redirected off-domain
            if parsed_landed.netloc.replace('www.','',1).lower() != start_domain_check_part.lower():
                result['url'] = None # Mark as off-domain
                return result

            result['url'] = normalized_landed_url # Update with the actual landed URL

            text_content = await page.evaluate('() => document.body ? document.body.innerText : ""')
            
            if text_content:
                try:
                    result['cleaned_text'] = extract_text(
                        text_content,
                        header_snippets=header_snippets_to_remove,
                        footer_snippets=footer_snippets_to_remove
                    )
                except Exception as extract_error:
                    logging.error(f"extract_text failed for {normalized_landed_url}: {extract_error}")
                    result['cleaned_text'] = text_content
            else:
                result['cleaned_text'] = ""
          
            # Enhanced link extraction logic
            if extract_with_context:
                link_data = await self._extract_links_with_context(
                    page, start_domain_check_part, site_canonical_base_url, exclude_patterns
                )
                result['new_links'] = link_data['links']
                result['link_context'] = link_data['context']
            else:
                result['new_links'] = await self._extract_internal_links_from_page_enhanced(
                    page, start_domain_check_part, site_canonical_base_url, exclude_patterns
                )
            
            return result
        except PlaywrightTimeoutError:
            logging.warning(f"Timeout processing {url_to_crawl}")
            result['url'] = None # Mark as failed due to timeout
            return result
        except Exception as e:
            logging.error(f"Error processing {url_to_crawl}: {e}")
            result['url'] = None # Mark as failed due to other error
            return result

    async def analyze_url(self, url: str) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        
        raw_validated_url = validate_url(url)
        if not raw_validated_url:
            logging.error(f"Invalid start URL provided: {url}")
            return None

        parsed_raw_input = urlparse(raw_validated_url)
        canonical_scheme = parsed_raw_input.scheme if parsed_raw_input.scheme in ('http', 'https') else 'https'
        canonical_netloc = parsed_raw_input.netloc.lower()
        if not canonical_netloc: 
            logging.error(f"Cannot determine netloc from validated URL: {raw_validated_url}")
            return None
        
        self.site_base_for_normalization = urlunparse((canonical_scheme, canonical_netloc, '/', '', '', ''))
        self.start_domain_normal_part = urlparse(self.site_base_for_normalization).netloc.replace('www.', '', 1)
        
        analysis_url_input = self._normalize_url(raw_validated_url, self.site_base_for_normalization)
        if not analysis_url_input:
            logging.error(f"Could not normalize the start URL '{raw_validated_url}'")
            return None

        print(f"Starting analysis of: {analysis_url_input}")
        
        self.identified_header_texts = []
        self.identified_footer_texts = []
        self.visited_urls = set() 
        self.all_discovered_links = set() 
        self.initial_page_llm_report = None
        initial_page_link_context = None # For storing link context from initial page

        sitemap_pages_raw: Set[str] = set()
        sitemap_urls_discovered: List[str] = []

        async with aiohttp.ClientSession(headers={'User-Agent': config.USER_AGENT}) as session:
            sitemap_urls_discovered = await discover_sitemap_urls(analysis_url_input, session) 
            if sitemap_urls_discovered:
                sitemap_pages_raw = await fetch_all_pages_from_sitemaps(sitemap_urls_discovered, session)
        
        sitemap_pages_normalized: Set[str] = set()
        for page_url in sitemap_pages_raw:
            norm_page_url = self._normalize_url(page_url, self.site_base_for_normalization)
            if norm_page_url and not any(exclude in norm_page_url for exclude in config.EXCLUDE_PATTERNS):
                 sitemap_pages_normalized.add(norm_page_url)
        
        print(f"Found {len(sitemap_pages_normalized)} URLs in sitemaps")
        
        analysis = {
            'url': analysis_url_input, 
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'crawled_internal_pages_count': 0,
            'crawled_urls': [],
            'page_statistics': {},
            'analysis_duration_seconds': 0,
            'sitemap_found': bool(sitemap_urls_discovered),
            'sitemap_urls_discovered': sitemap_urls_discovered,
            'sitemap_urls_discovered_count': len(sitemap_urls_discovered),
            'sitemap_pages_processed_count': len(sitemap_pages_normalized)
        }

        self.visited_urls.add(analysis_url_input) 
        self.all_discovered_links.add(analysis_url_input)
        self.all_discovered_links.update(sitemap_pages_normalized)
        
        url_in_report_dict: Dict[str, bool] = {} 
        urls_to_visit = deque()
        for s_url in sitemap_pages_normalized:
            if s_url != analysis_url_input and s_url not in self.visited_urls: # Ensure not already visited
                urls_to_visit.append(s_url)
                self.visited_urls.add(s_url) 

        actual_initial_url = None
        initial_cleaned_text_for_main_url = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent=config.USER_AGENT,
                    viewport={'width': config.VIEWPORT_WIDTH, 'height': config.VIEWPORT_HEIGHT},
                )
                await context.route("**/*", lambda route: route.abort() if 
                    route.request.resource_type in config.BLOCKED_RESOURCES or 
                    any(domain in route.request.url for domain in config.BLOCKED_DOMAINS) 
                    else route.continue_())
                
                initial_page_obj = await context.new_page()
                raw_initial_cleaned_text = "" 
                try:
                    initial_result = await self._process_page(
                        initial_page_obj, 
                        analysis_url_input, 
                        self.start_domain_normal_part,
                        self.site_base_for_normalization,
                        config.EXCLUDE_PATTERNS,
                        header_snippets_to_remove=None, 
                        footer_snippets_to_remove=None,
                        extract_with_context=True  # Enable enhanced extraction for main page
                    )
                    actual_initial_url = initial_result['url'] 

                    if actual_initial_url and initial_result['cleaned_text']:
                        raw_initial_cleaned_text = initial_result['cleaned_text'] 
                        
                        if 'link_context' in initial_result and initial_result['link_context']:
                            initial_page_link_context = initial_result['link_context'] # Store for later
                            lc = initial_page_link_context
                            nav_links_count = len(lc.get('linksBySection', {}).get('navigation', []))
                            content_links_count = len(lc.get('linksBySection', {}).get('content', []))
                            footer_links_count = len(lc.get('linksBySection', {}).get('footer', []))
                            important_links_count = len(lc.get('importantLinks', []))
                            print(f"Initial page link context: Nav: {nav_links_count}, Content: {content_links_count}, Footer: {footer_links_count}, Important: {important_links_count}")
                        
                        print("Analyzing main page content...")
                        initial_page_data_for_llm = {
                            'url': actual_initial_url,
                            'cleaned_text': raw_initial_cleaned_text, 
                            'headings': {} # Placeholder, might be populated by LLM or other analysis
                        }
                        try:
                            self.initial_page_llm_report = await llm_analysis_start(initial_page_data_for_llm)
                            if self.initial_page_llm_report and not self.initial_page_llm_report.get("error"):
                                self.identified_header_texts = self.initial_page_llm_report.get("header", [])
                                self.identified_footer_texts = self.initial_page_llm_report.get("footer", [])
                                if self.identified_header_texts or self.identified_footer_texts:
                                    print(f"Identified {len(self.identified_header_texts)} header and {len(self.identified_footer_texts)} footer elements via LLM")
                                if initial_page_link_context: # Add link context to report
                                    self.initial_page_llm_report['link_context_analysis'] = initial_page_link_context
                            else: # LLM error or no report
                                error_msg = self.initial_page_llm_report.get('error', 'Unknown LLM error') if self.initial_page_llm_report else 'No LLM report'
                                logging.warning(f"LLM analysis for initial page failed: {error_msg}")
                                if not isinstance(self.initial_page_llm_report, dict): 
                                    self.initial_page_llm_report = {}
                                self.initial_page_llm_report.setdefault('url', actual_initial_url)
                                self.initial_page_llm_report.setdefault('error', error_msg)
                                if initial_page_link_context: # Still add link context if available
                                    self.initial_page_llm_report['link_context_analysis'] = initial_page_link_context

                        except Exception as e_llm_init:
                            logging.error(f"Error in LLM analysis for initial page: {e_llm_init}")
                            self.initial_page_llm_report = {
                                "url": actual_initial_url, "error": f"Exception in llm_analysis_start: {str(e_llm_init)}",
                                "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                                "suggested_keywords_for_seo": [], "header": [], "footer": []
                            }
                            if initial_page_link_context: # Add link context even on LLM error
                                self.initial_page_llm_report['link_context_analysis'] = initial_page_link_context
                        
                        final_initial_cleaned_text = raw_initial_cleaned_text 
                        if self.identified_header_texts or self.identified_footer_texts:
                            try:
                                final_initial_cleaned_text = extract_text(
                                    raw_initial_cleaned_text, 
                                    header_snippets=self.identified_header_texts,
                                    footer_snippets=self.identified_footer_texts
                                )
                            except Exception as extract_error_hf:
                                logging.error(f"extract_text failed during header/footer removal for initial page: {extract_error_hf}")
                        
                        initial_cleaned_text_for_main_url = final_initial_cleaned_text
                        analysis['crawled_urls'].append(actual_initial_url)
                        url_in_report_dict[actual_initial_url] = True # Mark main URL as processed for report dict
                        
                        for link in initial_result['new_links']: # Links from initial page
                            if len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                if link not in self.visited_urls and link not in urls_to_visit :
                                    self.all_discovered_links.add(link)
                                    urls_to_visit.append(link)
                                    self.visited_urls.add(link)
                            else: break
                except Exception as e_initial:
                    logging.error(f"Error during initial page analysis for {analysis_url_input}: {e_initial}")
                finally:
                    if initial_page_obj and not initial_page_obj.is_closed():
                        await initial_page_obj.close()
                
                async def process_batch_wrapper(batch_urls_to_crawl):
                    tasks = []
                    pages_for_batch = []
                    try:
                        for batch_url_item in batch_urls_to_crawl:
                            page = await context.new_page()
                            pages_for_batch.append(page)
                            tasks.append(self._process_page( # extract_with_context defaults to False
                                page, batch_url_item, 
                                self.start_domain_normal_part, 
                                self.site_base_for_normalization, 
                                config.EXCLUDE_PATTERNS,
                                header_snippets_to_remove=self.identified_header_texts, 
                                footer_snippets_to_remove=self.identified_footer_texts
                            ))
                        batch_proc_results = await asyncio.gather(*tasks, return_exceptions=True)
                        return batch_proc_results, pages_for_batch
                    except Exception as e_batch_create:
                        logging.error(f"Error creating batch tasks: {e_batch_create}")
                        # Return error for each task and ensure pages are handled
                        return [e_batch_create] * len(batch_urls_to_crawl), pages_for_batch


                batch_size = min(8, config.MAX_PAGES_TO_ANALYZE) # Ensure batch_size is at least 1 if MAX_PAGES_TO_ANALYZE is 1
                if config.MAX_PAGES_TO_ANALYZE == 0: batch_size = 0 # Handle edge case if no pages to analyze

                while urls_to_visit and len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE and \
                      len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER and batch_size > 0:
                    current_batch_urls = []
                    
                    while urls_to_visit and len(current_batch_urls) < batch_size:
                        if len(url_in_report_dict) + len(current_batch_urls) >= config.MAX_PAGES_TO_ANALYZE:
                            break
                        url_from_queue = urls_to_visit.popleft()
                        # Check if already processed or is the main URL (which is handled separately for stats)
                        if url_from_queue not in url_in_report_dict: 
                           current_batch_urls.append(url_from_queue)

                    if not current_batch_urls:
                        break 
                        
                    print(f"Processing batch of {len(current_batch_urls)} pages... ({len(url_in_report_dict)}/{config.MAX_PAGES_TO_ANALYZE} analyzed)")
                    
                    batch_results_data, batch_pages_created = await process_batch_wrapper(current_batch_urls)
                    
                    try: 
                        successful_pages_in_batch = 0
                        for intended_url, page_result_data in zip(current_batch_urls, batch_results_data):
                            if isinstance(page_result_data, Exception):
                                logging.warning(f"Page {intended_url} failed with exception: {page_result_data}")
                                continue 

                            actual_processed_url = page_result_data['url'] 

                            if not actual_processed_url: # Page processing failed (timeout, off-domain, etc.)
                                continue
                            
                            # If page redirected to an already processed URL or itself after normalization
                            if actual_processed_url in url_in_report_dict:
                                for new_link in page_result_data.get('new_links', set()): 
                                    if len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                        if new_link not in self.visited_urls and new_link not in urls_to_visit: 
                                            self.all_discovered_links.add(new_link)
                                            urls_to_visit.append(new_link)
                                            self.visited_urls.add(new_link)
                                    else: break
                                if len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER: break
                                continue

                            # Add to page_statistics if it's not the main URL (main URL stats are in llm_analysis)
                            # and has content, and we haven't reached the page limit
                            if actual_processed_url != analysis_url_input and page_result_data['cleaned_text']: 
                                if len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE :
                                    analysis['page_statistics'][actual_processed_url] = {
                                        'url': actual_processed_url,
                                        'cleaned_text': page_result_data['cleaned_text'], 
                                    }
                                    url_in_report_dict[actual_processed_url] = True
                                    analysis['crawled_urls'].append(actual_processed_url)
                                    successful_pages_in_batch += 1
                            
                            for new_link in page_result_data.get('new_links', set()): 
                                if len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                    if new_link not in self.visited_urls and new_link not in urls_to_visit: 
                                        self.all_discovered_links.add(new_link)
                                        urls_to_visit.append(new_link)
                                        self.visited_urls.add(new_link) 
                                else: break 
                            
                            if len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER or \
                               len(url_in_report_dict) >= config.MAX_PAGES_TO_ANALYZE:
                                break 
                        
                        if successful_pages_in_batch > 0:
                            print(f"Successfully processed {successful_pages_in_batch} pages in this batch.")
                            
                    finally:
                        for p_obj in batch_pages_created:
                             if p_obj and not p_obj.is_closed():
                                await p_obj.close()
                    
                    if len(url_in_report_dict) >= config.MAX_PAGES_TO_ANALYZE or \
                       len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER:
                        print("Reached max pages to analyze or max links to discover.")
                        break 
                    
                    await asyncio.sleep(random.uniform(config.CRAWL_DELAY_MIN / 2, config.CRAWL_DELAY_MAX / 2))

                if self.initial_page_llm_report and initial_cleaned_text_for_main_url:
                    self.initial_page_llm_report['cleaned_text'] = initial_cleaned_text_for_main_url # Store final cleaned text for main Url.

                analysis['crawled_internal_pages_count'] = len(analysis['crawled_urls'])
                analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
                
                print(f"Analysis complete: {analysis['crawled_internal_pages_count']} pages analyzed in {analysis['analysis_duration_seconds']} seconds. Total {len(self.all_discovered_links)} links discovered.")
                
                if self.initial_page_llm_report:
                    analysis['llm_analysis'] = self.initial_page_llm_report
                elif actual_initial_url: # Fallback if LLM report object wasn't created for some reason
                     analysis['llm_analysis'] = {
                        "url": actual_initial_url, "error": "Initial LLM analysis data structure unavailable.",
                        "cleaned_text": initial_cleaned_text_for_main_url, # Still include cleaned text if available
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "header": [], "footer": []
                    }
                     if initial_page_link_context: # Add link context if available
                         analysis['llm_analysis']['link_context_analysis'] = initial_page_link_context
                else: # Absolute fallback
                    analysis['llm_analysis'] = {
                        "url": analysis_url_input, "error": "Initial page processing failed, LLM analysis critically unavailable.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "header": [], "footer": []
                    }
                
                return analysis
                
            except Exception as e_critical:
                logging.critical(f"Critical error in analysis workflow: {e_critical}")
                # Try to salvage some data for the report if possible
                analysis['error'] = f"Critical analysis error: {str(e_critical)}"
                analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
                return analysis # Return partially filled analysis
            finally:
                if 'browser' in locals() and browser.is_connected():
                    await browser.close()
                
                # Ensure analysis object exists for saving
                final_analysis_data_to_save = analysis if 'analysis' in locals() and analysis else {}
                
                # Ensure llm_analysis key exists even if parts failed
                if 'llm_analysis' not in final_analysis_data_to_save:
                    final_url_for_error_report = actual_initial_url if 'actual_initial_url' in locals() and actual_initial_url else analysis_url_input
                    final_analysis_data_to_save['llm_analysis'] = {
                        "url": final_url_for_error_report, 
                        "error": "LLM analysis section incomplete or initial page failed before LLM stage.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "header": [], "footer": []
                    }
                    if 'initial_page_link_context' in locals() and initial_page_link_context:
                         final_analysis_data_to_save['llm_analysis']['link_context_analysis'] = initial_page_link_context


                if final_analysis_data_to_save and (final_analysis_data_to_save.get('crawled_internal_pages_count',0) > 0 or final_analysis_data_to_save.get('url')):
                    try:
                        await self.saver.save_reports(final_analysis_data_to_save) 
                        print("Analysis report saved successfully!")
                    except Exception as e_save_final:
                        logging.error(f"Failed to save final analysis: {e_save_final}")
                else:
                    start_url_for_log = analysis_url_input if 'analysis_url_input' in locals() else url
                    logging.warning(f"No substantial analysis data to save for {start_url_for_log}. Report: {final_analysis_data_to_save}")
                
                return final_analysis_data_to_save if final_analysis_data_to_save.get('url') else None