import logging
from urllib.parse import urlparse, urljoin
import time
import random
import asyncio
from collections import deque
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
import aiohttp
from typing import Set
from analyzer.methods import validate_url, extract_text, analyze_headings
from analyzer.seoreportsaver import SEOReportSaver
import analyzer.config as config
from analyzer.sitemap import discover_sitemap_urls, fetch_all_pages_from_sitemaps

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SEOAnalyzer:
    def __init__(self):
        self.saver = SEOReportSaver()
    
    def _normalize_url(self, url: str, base_url: str) -> str | None:
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

    async def _extract_internal_links_from_page(self, page: Page, base_domain: str, exclude_patterns: list[str]) -> set[str]:
        found_links = set()
        try:
            links_on_page = await page.evaluate("""
                (baseDomain) => {
                    const links = new Set();
                    const allowedSchemes = ['http:', 'https:'];
                    Array.from(document.links).forEach(link => {
                        try {
                            const absoluteUrl = new URL(link.href, document.baseURI).href;
                            const linkUrl = new URL(absoluteUrl);
                            if (allowedSchemes.includes(linkUrl.protocol) && 
                                linkUrl.hostname.replace('www.', '') === baseDomain) {
                                links.add(absoluteUrl.split('#')[0]);
                            }
                        } catch (e) {}
                    });
                    return Array.from(links);
                }
            """, base_domain)

            for link in links_on_page:
                normalized = self._normalize_url(link, page.url)
                if normalized and not any(exclude in normalized for exclude in exclude_patterns):
                    found_links.add(normalized)
        except Exception as e:
            logging.warning(f"Could not extract links from {page.url}: {e}")
        return found_links

    async def analyze_url(self, url):
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

        sitemap_pages_raw: Set[str] = set()
        sitemap_urls_discovered: list[str] = []

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
        logging.info(f"Total unique URLs from sitemaps after domain filtering & normalization: {len(filtered_sitemap_pages)}")

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

                page_for_initial_analysis = await context.new_page()
                initial_text_content = ""
                initial_headings = {}
                initial_cleaned_text = ""
                links_from_start_page_for_queue = set()

                try:
                    logging.info(f"Performing initial analysis of {normalized_analysis_url}")
                    await page_for_initial_analysis.goto(normalized_analysis_url, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT * 1.5)
                    initial_text_content = await page_for_initial_analysis.evaluate('() => document.body ? document.body.innerText : ""')
                    initial_headings = await analyze_headings(page_for_initial_analysis)
                    initial_cleaned_text = extract_text(initial_text_content) if initial_text_content else ""
                    links_from_start_page_for_queue = await self._extract_internal_links_from_page(page_for_initial_analysis, start_domain, config.EXCLUDE_PATTERNS)
                except PlaywrightTimeoutError:
                    logging.warning(f"Timeout loading initial page: {normalized_analysis_url}")
                except Exception as e:
                    logging.error(f"Error during initial analysis of {normalized_analysis_url}: {e}", exc_info=True)
                    await browser.close()
                    return None 
                finally:
                    await page_for_initial_analysis.close()
                
                analysis = {
                    'url': normalized_analysis_url,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'crawled_internal_pages_count': 0,
                    'crawled_urls': [normalized_analysis_url] if initial_text_content else [],
                    'page_statistics': {},
                    'analysis_duration_seconds': 0,
                    'sitemap_found': bool(sitemap_urls_discovered),
                    'sitemap_urls_discovered': sitemap_urls_discovered,
                    'sitemap_urls_discovered_count': len(sitemap_urls_discovered),
                    'sitemap_pages_processed_count': len(filtered_sitemap_pages)
                }   

                # Add initial page stats
                if initial_text_content:
                    analysis['page_statistics'][normalized_analysis_url] = {
                        'url': normalized_analysis_url,
                        'cleaned_text': initial_cleaned_text,
                        'headings': initial_headings,
                    }
                
                visited_urls = {normalized_analysis_url}
                all_discovered_links = set(visited_urls)
                all_discovered_links.update(links_from_start_page_for_queue)
                all_discovered_links.update(filtered_sitemap_pages)

                # Initialize queue with links from sitemap and initial page
                urls_to_visit_list_intermediate = [
                    link for link in (filtered_sitemap_pages | links_from_start_page_for_queue) 
                    if link not in visited_urls and link
                ]
                urls_to_visit = deque(urls_to_visit_list_intermediate)

                logging.info(f"Initial analysis of {normalized_analysis_url} complete.")
                logging.info(f"Unique internal links from start page for queue: {len(links_from_start_page_for_queue)}")
                logging.info(f"Unique internal links from sitemaps for queue: {len(filtered_sitemap_pages)}")
                logging.info(f"Combined unique URLs to start crawl queue (after filtering visited): {len(urls_to_visit)}")
                logging.info(f"Total discovered links before loop (master set): {len(all_discovered_links)}")

                analyzed_pages_count_in_loop = 0

                # Main crawl loop
                while urls_to_visit and len(all_discovered_links) < config.MAX_LINKS_TO_DISCOVER and \
                      (analyzed_pages_count_in_loop + 1) < config.MAX_PAGES_TO_ANALYZE:
                
                    current_url_to_crawl = urls_to_visit.popleft()
                
                    # Domain Consistency Check
                    if urlparse(current_url_to_crawl).netloc != start_domain:
                        logging.warning(f"Skipping {current_url_to_crawl} due to domain mismatch with {start_domain}")
                        visited_urls.add(current_url_to_crawl)
                        continue
                
                    # Exclude Patterns Check
                    if any(exclude in current_url_to_crawl for exclude in config.EXCLUDE_PATTERNS):
                        logging.info(f"Skipping {current_url_to_crawl} due to exclude patterns")
                        visited_urls.add(current_url_to_crawl)
                        continue
                
                    logging.info(f"Processing page [{analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)}/{config.MAX_PAGES_TO_ANALYZE}]: {current_url_to_crawl} (Queue: {len(urls_to_visit)}, Discovered: {len(all_discovered_links)})")
                    page_for_crawling = await context.new_page()
                    
                    try:
                        await page_for_crawling.goto(current_url_to_crawl, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT)
                        visited_urls.add(current_url_to_crawl)

                        # Extract links from this page
                        newly_found_links_on_page = await self._extract_internal_links_from_page(page_for_crawling, start_domain, config.EXCLUDE_PATTERNS)
                        for new_link in newly_found_links_on_page:
                            if new_link not in all_discovered_links:
                                if len(all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                    all_discovered_links.add(new_link)
                                    if new_link not in visited_urls:
                                        urls_to_visit.append(new_link)
                                else:
                                    logging.info(f"MAX_LINKS_TO_DISCOVER ({config.MAX_LINKS_TO_DISCOVER}) reached while adding new links.")
                                    break
                        
                        # Analyze content if within limits
                        if (analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)) < config.MAX_PAGES_TO_ANALYZE:
                            logging.info(f"Analyzing content of: {current_url_to_crawl}")
                            text = await page_for_crawling.evaluate('() => document.body ? document.body.innerText : ""')
                            page_cleaned_text = extract_text(text) if text else ""
                            page_headings = await analyze_headings(page_for_crawling)

                            analysis['page_statistics'][current_url_to_crawl] = {
                                'url': current_url_to_crawl,
                                'cleaned_text': page_cleaned_text,
                                'headings': page_headings,
                            }
                            analysis['crawled_urls'].append(current_url_to_crawl)
                            analyzed_pages_count_in_loop += 1
                        else:
                            logging.info(f"MAX_PAGES_TO_ANALYZE limit reached. Skipping content analysis for {current_url_to_crawl}. Links (if any) were still extracted.")
                            
                    except PlaywrightTimeoutError:
                        logging.warning(f"Timeout loading page for link extraction/analysis: {current_url_to_crawl}")
                        visited_urls.add(current_url_to_crawl)
                    except Exception as e:
                        logging.error(f"Error processing {current_url_to_crawl} for links/analysis: {e}", exc_info=True)
                        visited_urls.add(current_url_to_crawl)
                    finally:
                        await page_for_crawling.close()

                    # Break loop if limits are reached
                    if len(all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER or \
                       (analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)) >= config.MAX_PAGES_TO_ANALYZE:
                        logging.info("Loop termination condition met (MAX_LINKS or MAX_PAGES).")
                        break
                    
                    await asyncio.sleep(random.uniform(config.CRAWL_DELAY_MIN, config.CRAWL_DELAY_MAX))

                # Update final counts
                analysis['crawled_internal_pages_count'] = len(analysis['crawled_urls']) 
                logging.info(f"Crawl finished. Discovered {len(all_discovered_links)} unique links. Analyzed content of {analysis['crawled_internal_pages_count']} pages.")
                
            except Exception as e:
                logging.critical(f"A critical error occurred in Playwright setup or main analysis structure: {e}", exc_info=True)
                return None
            finally:
                if 'browser' in locals() and browser.is_connected():
                    await browser.close()
                    logging.info("Playwright browser closed.")
                if analysis:
                    logging.info(f"Analysis data before saving: {analysis}")
                    try:
                        await self.saver.save_reports(analysis)
                        logging.info(f"Analysis saved successfully for {normalized_analysis_url}. Duration: {analysis['analysis_duration_seconds']}s")
                    except Exception as e:
                        logging.error(f"Failed to save analysis for {normalized_analysis_url}: {e}", exc_info=True)
                    return analysis
                else:
                    logging.warning("No analysis data to save.")
                    return None