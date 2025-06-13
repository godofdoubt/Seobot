
import logging
import asyncio # For _wait_for_dynamic_content and type hints
from dotenv import load_dotenv
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError # For helper methods and type hints
from typing import Set, Dict, List, Any, Optional # For type hints
from urllib.parse import urlparse, urljoin, urlunparse # For helper methods

from analyzer.seoreportsaver import SEOReportSaver
# analyzer.config, analyzer.methods, analyzer.sitemap, analyzer.llm_analysis_start (changed to llm_analysis_mainpage.)
# are now primarily used by seomainfunctions.py

from . import seomainfunctions # Import the new module

# Configure logging with reduced verbosity
logging.basicConfig(
    level=logging.INFO, # Changed from WARNING to INFO to see some general flow, DEBUG is too much globally
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' # Added logger name
)

# Set specific loggers to appropriate levels
# --- MODIFICATION FOR MORE LINK DEBUGGING ---
logging.getLogger('analyzer').setLevel(logging.DEBUG) # Set analyzer namespace to DEBUG
# logging.getLogger('analyzer.seo').setLevel(logging.DEBUG) # Or more specifically for seo.py
# --- END MODIFICATION ---
logging.getLogger('analyzer.methods').setLevel(logging.INFO) # MODIFIED: Changed from DEBUG to INFO
logging.getLogger('playwright').setLevel(logging.WARNING) # Playwright can be noisy, WARNING or ERROR
logging.getLogger('asyncio').setLevel(logging.WARNING) # Asyncio can also be noisy

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
                            if (linkDomain.toLowerCase() === baseDomain.toLowerCase()) { // case-insensitive domain check
                                const shouldExclude = excludePatterns.some(pattern => {
                                    return absoluteUrl.toLowerCase().includes(pattern.toLowerCase());
                                });
                                if (!shouldExclude) {
                                    links.add(absoluteUrl);
                                }
                            }
                        } catch (e) {
                            // console.warn('Error processing link:', link.href, e); // Kept commented as per original
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
                                        if (linkDomain.toLowerCase() === baseDomain.toLowerCase()) { // case-insensitive
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
                            // console.warn('Error processing button/element:', e); // Kept commented
                        }
                    });
                    return {
                        links: Array.from(links),
                        anchorsFound: anchors.length,
                        buttonsFound: buttons.length
                    };
                }
            """, {"baseDomain": base_domain_check_part, "excludePatterns": exclude_patterns})

            logging.info(f"Found {links_js_enhanced_result['anchorsFound']} anchor tags and {links_js_enhanced_result['buttonsFound']} interactive elements on {page.url}")
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
            if playwright_urls:
                 logging.info(f"Playwright method found {len(playwright_urls)} potential links on {page.url}")

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
                                            if (linkDomain.toLowerCase() === baseDomain.toLowerCase()) { // case-insensitive
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
                logging.info(f"Navigation-specific extraction found {len(nav_links_from_js)} links on {page.url}")

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
                logging.info(f"Structured data extraction found {len(filtered_structured_links)} internal links on {page.url}")

        except Exception as e:
            logging.warning(f"Structured data link extraction failed for {page.url}: {e}")
            filtered_structured_links = []

        # --- MODIFICATION START: Improved Blog Post Detection ---
        # Strategy 5: Blog and Pagination Link Extraction (runs on all pages)
        blog_specific_links = []
        try:
            # This logic now runs on every page to find blog links from anywhere on the site,
            # such as a "Latest Posts" section on the homepage.
            blog_links_raw = await page.evaluate("""
                () => {
                    const links = new Set();
                    // Selectors for individual blog post links
                    const postSelectors = [
                        'article a[href]', '.post a[href]', '.blog-post a[href]',
                        '.entry-title a[href]', 'h2.entry-title a', '.post-title a',
                        '.post-preview a', '.article-title a', 'a.blog-item-link', '.read-more',
                        '.latest-posts a[href]', '.recent-posts a[href]' // Added selectors for common homepage sections
                    ];
                    // Selectors for blog pagination (next/previous page links)
                    const paginationSelectors = [
                        '.pagination a[href]', '.nav-links a[href]', 'a.next', 'a.page-numbers',
                        '.wp-pagenavi a', '.blog-pagination a'
                    ];
                    const allSelectors = postSelectors.concat(paginationSelectors);

                    allSelectors.forEach(selector => {
                        try { // Inner try-catch for robustness against invalid selectors on some pages
                            document.querySelectorAll(selector).forEach(link => {
                                if (link.href) {
                                    const hrefAttr = link.getAttribute('href');
                                    // Ensure we don't capture empty, anchor, or javascript links
                                    if (hrefAttr && hrefAttr.trim() !== '#' && !hrefAttr.startsWith('javascript:')) {
                                         links.add(new URL(link.href, document.baseURI).href);
                                    }
                                }
                            });
                        } catch (e) {
                           // Silently ignore errors from a single selector failing
                        }
                    });
                    return Array.from(links);
                }
            """)

            # Filter and process the raw links found by the blog-specific strategy
            for link_str in blog_links_raw:
                try:
                    parsed_link = urlparse(link_str)
                    # Check if it's an internal link and not in exclude patterns
                    if parsed_link.netloc.replace('www.', '', 1).lower() == base_domain_check_part.lower():
                        if not any(exclude.lower() in link_str.lower() for exclude in exclude_patterns):
                            blog_specific_links.append(link_str)
                except:
                    # Ignore errors parsing individual URLs from this list
                    continue
            if blog_specific_links:
                logging.info(f"Blog/Pagination-specific extraction found {len(blog_specific_links)} potential links on {page.url}")

        except Exception as e:
            logging.warning(f"Blog/Pagination-specific link extraction failed for {page.url}: {e}")
        # --- MODIFICATION END ---

        all_found_links_raw = set(links_js_enhanced_links + playwright_urls + nav_links_from_js + filtered_structured_links + blog_specific_links)

        normalized_final_links: Set[str] = set()
        for link_str in all_found_links_raw:
            normalized_link = self._normalize_url(link_str, site_canonical_base_url)
            if normalized_link:
                normalized_final_links.add(normalized_link)

        logging.info(f"Total unique internal links found on {page.url}: {len(normalized_final_links)}")
        return normalized_final_links

    async def _wait_for_dynamic_content(self, page: Page, max_wait_seconds: int = 10) -> None:
        """
        Wait for dynamic content to load using a more flexible strategy,
        less prone to timeouts on low-compute environments.
        This version corrects the TypeError from the previous suggestion.
        """
        logging.info(f"Waiting for dynamic content on {page.url} (max {max_wait_seconds}s)...")
        try:
            # 1. Wait for the initial DOM to be ready. 'load' is a good baseline.
            initial_load_timeout = max_wait_seconds * 1000 * 0.5
            await page.wait_for_load_state('load', timeout=initial_load_timeout)
            logging.info(f"Initial 'load' state reached for {page.url}.")

            # 2. Execute a scroll to trigger lazy-loaded content.
            await page.evaluate("""
                () => {
                    window.scrollTo(0, document.body.scrollHeight / 2);
                    return new Promise(resolve => setTimeout(resolve, 500)); // Brief pause after scroll
                }
            """)
            await page.evaluate("() => window.scrollTo(0, 0)") # Scroll back to top

            # 3. Implement a smarter wait that checks for DOM stability, with the timeout handled by asyncio.
            js_stability_check_timeout_seconds = max_wait_seconds * 0.4
        
            js_code_for_stability_check = """
                () => new Promise((resolve) => {
                    let lastBodyHeight = document.body.scrollHeight;
                    let stableChecks = 0;
                    const maxStableChecks = 3; // Require 3 stable checks (1.5 seconds)
                    const checkInterval = 500; // Check every 500ms

                    const intervalId = setInterval(() => {
                        const currentBodyHeight = document.body.scrollHeight;
                        if (currentBodyHeight === lastBodyHeight) {
                            stableChecks++;
                            if (stableChecks >= maxStableChecks) {
                                clearInterval(intervalId);
                                resolve();
                            }
                        } else {
                            stableChecks = 0;
                            lastBodyHeight = currentBodyHeight;
                        }
                    }, checkInterval);

                    // As a fallback, resolve after a max duration slightly less than the python timeout
                    setTimeout(() => {
                        clearInterval(intervalId);
                        resolve();
                    }, (js_stability_check_timeout_seconds * 1000) - 500);
                })
            """.replace('js_stability_check_timeout_seconds', str(js_stability_check_timeout_seconds)) # Inject variable

            await asyncio.wait_for(
                page.evaluate(js_code_for_stability_check),
                timeout=js_stability_check_timeout_seconds
            )

            logging.info(f"Dynamic content wait finished for {page.url}.")

        except PlaywrightTimeoutError:
            logging.warning(
                f"PlaywrightTimeoutError during the initial 'load' state wait for {page.url}. "
                "The page is very slow to load its main resources."
            )
        except asyncio.TimeoutError:
            logging.warning(
                f"asyncio.TimeoutError during JavaScript stability check for {page.url}. "
                "DOM did not stabilize in time, but proceeding with analysis."
            )
        except Exception as e:
            # This will now catch other potential errors without being masked by the incorrect TypeError
            logging.warning(f"Dynamic content wait for {page.url} failed: {type(e).__name__} - {e}")

    async def _extract_links_with_context(self, page: Page, base_domain_check_part: str, site_canonical_base_url: str, exclude_patterns: List[str]) -> Dict[str, Any]:
        """Extract links with additional context information."""
        logging.info(f"Extracting links with context from {page.url}...")
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
                            // console.warn('Error processing link in context extraction:', e); // Kept commented
                        }
                    });
                    return result;
                }
            """, {"baseDomain": base_domain_check_part, "excludePatterns": exclude_patterns})

            normalized_links_set: Set[str] = set()
            if 'links' in links_with_context_data: # Check if 'links' key exists
                for link_info in links_with_context_data.get('links', []):
                    normalized_url = self._normalize_url(link_info['url'], site_canonical_base_url)
                    if normalized_url:
                        normalized_links_set.add(normalized_url)
                        link_info['normalized_url'] = normalized_url # Add normalized_url back to info

            logging.info(f"Links by section on {page.url}: Navigation: {len(links_with_context_data.get('linksBySection', {}).get('navigation', []))}, "
                  f"Content: {len(links_with_context_data.get('linksBySection', {}).get('content', []))}, "
                  f"Footer: {len(links_with_context_data.get('linksBySection', {}).get('footer', []))}")
            logging.info(f"Important links found on {page.url}: {len(links_with_context_data.get('importantLinks', []))}")

            return {
                'links': normalized_links_set,
                'context': links_with_context_data # This now contains link_info objects potentially with 'normalized_url'
            }

        except Exception as e:
            logging.error(f"Link extraction with context failed for {page.url}: {e}")
            return {'links': set(), 'context': {}}

    async def analyze_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Analyzes a given URL for SEO metrics.
        Delegates core processing to seomainfunctions.analyze_url_standalone.
        Ensures 'page_statistics' contains full details for all crawled pages.
        """
        # Delegate to the standalone function, passing 'self' as analyzer_instance
        # This allows analyze_url_standalone to use helper methods from this SEOAnalyzer instance
        # and access/modify its attributes (like self.initial_page_llm_report, self.saver).
        analysis_result = await seomainfunctions.analyze_url_standalone(self, url)

        # THE FOLLOWING POST-PROCESSING BLOCK IS REMOVED:
        # The purpose is to ensure that 'page_statistics' as populated by
        # seomainfunctions.analyze_url_standalone (which should contain full tech stats)
        # is preserved in the final analysis_result.
        #
        # if analysis_result and 'page_statistics' in analysis_result:
        #     for page_url_key in list(analysis_result['page_statistics'].keys()): # Iterate over copy of keys
        #         stats = analysis_result['page_statistics'][page_url_key]
        #         # Reconstruct the entry to only include 'url' and 'cleaned_text'
        #         analysis_result['page_statistics'][page_url_key] = {
        #             'url': stats.get('url'), # Should always be present
        #             'cleaned_text': stats.get('cleaned_text', '') # Ensure cleaned_text is present
        #         }
        #
        # By removing the block above, the 'page_statistics' dictionary within 'analysis_result'
        # will retain all the detailed information collected for each crawled page by
        # 'seomainfunctions.analyze_url_standalone'. This complete 'analysis_result'
        # is then returned and used by 'shared_functions.analyze_website' to populate
        # the 'report' JSONB field in Supabase.

        # Note: The saving of the report might be handled within analyze_url_standalone
        # or by the caller ('shared_functions.analyze_website').
        # The crucial part is that this method now returns the 'analysis_result'
        # with 'page_statistics' intact.

        return analysis_result