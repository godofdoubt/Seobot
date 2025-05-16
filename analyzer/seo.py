import logging
from urllib.parse import urlparse, urljoin
import time
import random
import asyncio
from collections import deque
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
import aiohttp
from typing import Set, Dict, List, Any, Optional
from analyzer.methods import validate_url, extract_text, analyze_headings
from analyzer.seoreportsaver import SEOReportSaver
import analyzer.config as config
from analyzer.sitemap import discover_sitemap_urls, fetch_all_pages_from_sitemaps

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SEOAnalyzer:
    def __init__(self):
        self.saver = SEOReportSaver()
        # Use sets for O(1) lookups
        self.visited_urls = set()
        self.all_discovered_links = set()
    
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        try:
            absolute_url = urljoin(base_url, url)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                return None
            scheme = "https"
            netloc = parsed.netloc.lower().replace('www.', '')
            path = parsed.path.rstrip('/') or '/' 
            query = parsed.query
            normalized = f"{scheme}://{netloc}{path}"
            if query:
                normalized += f"?{query}"
            return normalized
        except Exception as e:
            logging.warning(f"Error normalizing URL '{url}' with base '{base_url}': {e}")
            return None

    async def _extract_internal_links_from_page(self, page: Page, base_domain: str, exclude_patterns: List[str]) -> Set[str]:
        try:
            # Fixed: Pass the JavaScript function and its arguments properly
            links_on_page = await page.evaluate("""
                (params) => {
                    const baseDomain = params.baseDomain;
                    const excludePatterns = params.excludePatterns;
                    const links = new Set();
                    const allowedSchemes = ['http:', 'https:'];
                    Array.from(document.links).forEach(link => {
                        try {
                            const absoluteUrl = new URL(link.href, document.baseURI).href;
                            const linkUrl = new URL(absoluteUrl);
                            if (allowedSchemes.includes(linkUrl.protocol) && 
                                linkUrl.hostname.replace('www.', '') === baseDomain &&
                                !excludePatterns.some(pattern => absoluteUrl.includes(pattern))) {
                                links.add(absoluteUrl.split('#')[0]);
                            }
                        } catch (e) {}
                    });
                    return Array.from(links);
                }
            """, {"baseDomain": base_domain, "excludePatterns": exclude_patterns})
            
            found_links = {
                normalized for link in links_on_page
                if (normalized := self._normalize_url(link, page.url))
            }
            return found_links
            
        except Exception as e:
            logging.warning(f"Could not extract links from {page.url}: {e}")
            return set()

    async def _process_page(self, page: Page, url: str, start_domain: str, exclude_patterns: List[str]) -> Dict[str, Any]:
        """Process a single page: extract content and links simultaneously"""
        result = {
            'url': url,
            'cleaned_text': '',
            'headings': {},
            'new_links': set()
        }
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT)
            
            # Extract text and headings
            text = await page.evaluate('() => document.body ? document.body.innerText : ""')
            result['cleaned_text'] = extract_text(text) if text else ""
            result['headings'] = await analyze_headings(page)
            
            # Extract links in the same page visit
            result['new_links'] = await self._extract_internal_links_from_page(page, start_domain, exclude_patterns)
            
            return result
        except PlaywrightTimeoutError:
            logging.warning(f"Timeout loading page: {url}")
            return result
        except Exception as e:
            logging.error(f"Error processing {url}: {e}")
            return result

    async def analyze_url(self, url: str) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        analysis_url_input = validate_url(url)
        if not analysis_url_input:
            logging.error(f"Invalid start URL provided: {url}")
            return None
        
        normalized_analysis_url = self._normalize_url(analysis_url_input, analysis_url_input)
        if not normalized_analysis_url:
            logging.error(f"Could not normalize the validated start URL: {analysis_url_input}")
            return None
        
        logging.info(f"Analyzing URL: {normalized_analysis_url}")
        parsed_start_url = urlparse(normalized_analysis_url)
        start_domain = parsed_start_url.netloc
        
        # Get URLs from sitemaps first
        sitemap_pages_raw: Set[str] = set()
        sitemap_urls_discovered: List[str] = []

        async with aiohttp.ClientSession(headers={'User-Agent': config.USER_AGENT}) as session:
            sitemap_urls_discovered = await discover_sitemap_urls(normalized_analysis_url, session)
            if sitemap_urls_discovered:
                sitemap_pages_raw = await fetch_all_pages_from_sitemaps(sitemap_urls_discovered, session)
        
        filtered_sitemap_pages = {
            normalized for page_url in sitemap_pages_raw
            if (normalized := self._normalize_url(page_url, normalized_analysis_url)) and 
               not any(exclude in normalized for exclude in config.EXCLUDE_PATTERNS) and
               urlparse(normalized).netloc == start_domain
        }
        logging.info(f"Total unique URLs from sitemaps after filtering: {len(filtered_sitemap_pages)}")
        
        # Initialize analysis result structure
        analysis = {
            'url': normalized_analysis_url,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'crawled_internal_pages_count': 0,
            'crawled_urls': [],
            'page_statistics': {},
            'analysis_duration_seconds': 0,
            'sitemap_found': bool(sitemap_urls_discovered),
            'sitemap_urls_discovered': sitemap_urls_discovered,
            'sitemap_urls_discovered_count': len(sitemap_urls_discovered),
            'sitemap_pages_processed_count': len(filtered_sitemap_pages)
        }

        # Reset tracking sets
        self.visited_urls = {normalized_analysis_url}
        self.all_discovered_links = {normalized_analysis_url}
        
        # Add sitemap URLs to discovered links
        self.all_discovered_links.update(filtered_sitemap_pages)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent=config.USER_AGENT,
                    viewport={'width': config.VIEWPORT_WIDTH, 'height': config.VIEWPORT_HEIGHT},
                )
                
                # Block unnecessary resources for speed
                await context.route("**/*", lambda route: route.abort() if 
                    route.request.resource_type in config.BLOCKED_RESOURCES or 
                    any(domain in route.request.url for domain in config.BLOCKED_DOMAINS) 
                    else route.continue_())
                
                # Process the initial page
                initial_page = await context.new_page()
                try:
                    initial_result = await self._process_page(
                        initial_page, 
                        normalized_analysis_url, 
                        start_domain, 
                        config.EXCLUDE_PATTERNS
                    )
                    
                    # Add initial page to analysis if content was retrieved
                    if initial_result['cleaned_text']:
                        analysis['page_statistics'][normalized_analysis_url] = {
                            'url': normalized_analysis_url,
                            'cleaned_text': initial_result['cleaned_text'],
                            'headings': initial_result['headings'],
                        }
                        analysis['crawled_urls'].append(normalized_analysis_url)
                    
                    # Add discovered links to queue
                    urls_to_visit = deque()
                    for link in initial_result['new_links']:
                        if link not in self.visited_urls:
                            # Only add links from the same domain
                            if urlparse(link).netloc == start_domain and not any(exclude in link for exclude in config.EXCLUDE_PATTERNS):
                                self.all_discovered_links.add(link)
                                urls_to_visit.append(link)
                    
                    # Add sitemap URLs to the queue if not already visited
                    for sitemap_url in filtered_sitemap_pages:
                        if sitemap_url not in self.visited_urls:
                            urls_to_visit.append(sitemap_url)
                            
                except Exception as e:
                    logging.error(f"Error during initial analysis of {normalized_analysis_url}: {e}")
                finally:
                    await initial_page.close()
                
                # Main parallel crawl process
                analyzed_pages_count = len(analysis['crawled_urls'])
                
                async def process_batch(batch_urls):
                    tasks = []
                    pages = []
                    
                    try:
                        # Create pages and tasks for each URL in batch
                        for batch_url in batch_urls:
                            page = await context.new_page()
                            pages.append(page)
                            tasks.append(self._process_page(page, batch_url, start_domain, config.EXCLUDE_PATTERNS))
                        
                        # Process all pages in parallel
                        batch_results = await asyncio.gather(*tasks)
                        return batch_results, pages
                        
                    except Exception as e:
                        logging.error(f"Error in batch processing: {e}")
                        return [], pages
                
                # Process URLs in batches for parallel execution
                batch_size = min(5, config.MAX_PAGES_TO_ANALYZE)  # Adjust based on system resources
                
                while urls_to_visit and len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER and analyzed_pages_count < config.MAX_PAGES_TO_ANALYZE:
                    # Get next batch of URLs to process
                    current_batch = []
                    while urls_to_visit and len(current_batch) < batch_size:
                        url = urls_to_visit.popleft()
                        if url not in self.visited_urls:
                            current_batch.append(url)
                            self.visited_urls.add(url)
                    
                    if not current_batch:
                        continue
                        
                    logging.info(f"Processing batch of {len(current_batch)} pages (Total analyzed: {analyzed_pages_count}/{config.MAX_PAGES_TO_ANALYZE})")
                    
                    # Process batch in parallel
                    batch_results, batch_pages = await process_batch(current_batch)
                    
                    # Close all pages from this batch
                    for page in batch_pages:
                        await page.close()
                    
                    # Process results and add new links to queue
                    for result, url in zip(batch_results, current_batch):
                        # Add page statistics
                        if result['cleaned_text']:
                            analysis['page_statistics'][url] = {
                                'url': url,
                                'cleaned_text': result['cleaned_text'],
                                'headings': result['headings'],
                            }
                            analysis['crawled_urls'].append(url)
                            analyzed_pages_count += 1
                        
                        # Process new links
                        for new_link in result['new_links']:
                            if (new_link not in self.all_discovered_links and 
                                len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER):
                                
                                if urlparse(new_link).netloc == start_domain and not any(exclude in new_link for exclude in config.EXCLUDE_PATTERNS):
                                    self.all_discovered_links.add(new_link)
                                    if new_link not in self.visited_urls:
                                        urls_to_visit.append(new_link)
                    
                    # Check if we've reached limits
                    if analyzed_pages_count >= config.MAX_PAGES_TO_ANALYZE:
                        logging.info(f"Reached maximum pages to analyze: {config.MAX_PAGES_TO_ANALYZE}")
                        break
                    
                    if len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER:
                        logging.info(f"Reached maximum links to discover: {config.MAX_LINKS_TO_DISCOVER}")
                        break
                    
                    # Small delay between batches to be kind to the server
                    await asyncio.sleep(random.uniform(config.CRAWL_DELAY_MIN / 2, config.CRAWL_DELAY_MAX / 2))
                
                # Update final counts
                analysis['crawled_internal_pages_count'] = len(analysis['crawled_urls'])
                analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
                
                logging.info(f"Analysis complete. Discovered {len(self.all_discovered_links)} unique links. Analyzed {analysis['crawled_internal_pages_count']} pages.")
                logging.info(f"Analysis duration: {analysis['analysis_duration_seconds']} seconds")
                
                return analysis
                
            except Exception as e:
                logging.critical(f"Critical error in analysis: {e}", exc_info=True)
                return None
            finally:
                if 'browser' in locals() and browser.is_connected():
                    await browser.close()
                if analysis:
                    try:
                        await self.saver.save_reports(analysis)
                        logging.info(f"Analysis saved successfully for {normalized_analysis_url}.")
                    except Exception as e:
                        logging.error(f"Failed to save analysis for {normalized_analysis_url}: {e}")
                    return analysis
                else:
                    logging.warning("No analysis data to save.")
                    return None