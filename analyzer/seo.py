import logging
from urllib.parse import urlparse, urljoin
import time
import random
import asyncio
from collections import deque, Counter
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
import aiohttp # Keep aiohttp for the sitemap module's session
from typing import Set, List
from analyzer.methods import validate_url, extract_keywords, analyze_headings
from analyzer.seoreportsaver import SEOReportSaver
import analyzer.config as config
# Import the new sitemap functions
from analyzer.sitemap import discover_sitemap_urls, fetch_all_pages_from_sitemaps

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SEOAnalyzer:
    def __init__(self):
        self.saver = SEOReportSaver()
    
    # _get_robots_txt, _extract_sitemaps_from_robots, _fetch_sitemap are now moved. inside sitemap.py
    # analyze headings inside methods.py

    def _normalize_url(self, url: str, base_url: str) -> str | None:
        # ... (no changes to this method)
        try:
            absolute_url = urljoin(base_url, url)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                return None
            scheme = "https"
            netloc = parsed.netloc.lower().replace('www.', '')
            path = parsed.path.rstrip('/') or '/' # Ensure path ends without slash, or is '/'
            query = parsed.query
            # Consider sorting query params for stricter normalization if necessary
            normalized = f"{scheme}://{netloc}{path}"
            if query:
                normalized += f"?{query}"
            return normalized
        except Exception as e:
            logging.warning(f"Error normalizing URL '{url}' with base '{base_url}': {e}")
            return None


    async def analyze_links(self, page: Page, base_url: str):
        # ... (no changes to this method)
        try:
            base_domain = urlparse(base_url).netloc.replace('www.', '')
            links_data = await page.evaluate("""
                ([baseDomain, pageUrl]) => {
                    const internal = new Set();
                    const external = new Set();
                    const allowedSchemes = ['http:', 'https:'];
                    try {
                        Array.from(document.links).forEach(link => {
                            try {
                                const absoluteUrl = new URL(link.href, pageUrl).href;
                                const linkUrl = new URL(absoluteUrl);
                                if (!allowedSchemes.includes(linkUrl.protocol)) return;
                                const linkDomain = linkUrl.hostname.replace('www.', '');
                                const normalizedUrl = absoluteUrl.split('#')[0];
                                if (linkDomain === baseDomain) {
                                    internal.add(normalizedUrl);
                                } else {
                                    external.add(normalizedUrl);
                                }
                            } catch (e) { /* ignore invalid URLs */ }
                        });
                    } catch (e) { console.error('Error extracting links:', e); }
                    return { internal_links: Array.from(internal), external_links: Array.from(external) };
                }
            """, [base_domain, page.url])
            return {
                'internal_links': links_data.get('internal_links', []),
                'external_links': links_data.get('external_links', []),
                'internal_count': len(links_data.get('internal_links', [])),
                'external_count': len(links_data.get('external_links', []))
            }
        except Exception as e:
            logging.error(f"Error in analyze_links for {base_url}: {e}")
            return {'internal_links': [], 'external_links': [], 'internal_count': 0, 'external_count': 0}

    async def _extract_internal_links_from_page(self, page: Page, base_domain: str, exclude_patterns: list[str]) -> set[str]:
        # ... (no changes to this method)
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
        # Ensure start_domain is derived after normalization for consistency
        start_domain = parsed_start_url.netloc 

        sitemap_pages_raw: Set[str] = set()
        sitemap_urls_discovered: List[str] = []

        async with aiohttp.ClientSession(headers={'User-Agent': config.USER_AGENT}) as session: # Use configured user-agent
            sitemap_urls_discovered = await discover_sitemap_urls(normalized_analysis_url, session)
            if sitemap_urls_discovered:
                sitemap_pages_raw = await fetch_all_pages_from_sitemaps(sitemap_urls_discovered, session)
        
        filtered_sitemap_pages = {
            normalized for page_url in sitemap_pages_raw
            if (normalized := self._normalize_url(page_url, normalized_analysis_url)) and 
               not any(exclude in normalized for exclude in config.EXCLUDE_PATTERNS) and
               urlparse(normalized).netloc == start_domain # Critical: ensure sitemap pages are for the same domain
        }
        logging.info(f"Total unique URLs from sitemaps after domain filtering & normalization: {len(filtered_sitemap_pages)}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) # Consider adding args e.g. ['--no-sandbox'] if in restricted env
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
                initial_keywords_list = []
                initial_cleaned_text = ""
                initial_filtered_words = ""
                initial_extracted_info = {}  # Added to store extracted information
                initial_page_general_links = {'internal_links': [], 'external_links': [], 'internal_count': 0, 'external_count': 0}
                links_from_start_page_for_queue = set()

                try:
                    logging.info(f"Performing initial analysis of {normalized_analysis_url}")
                    await page_for_initial_analysis.goto(normalized_analysis_url, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT * 1.5)
                    initial_text_content = await page_for_initial_analysis.evaluate('() => document.body ? document.body.innerText : ""')
                    initial_headings = await analyze_headings(page_for_initial_analysis)
                    # Capture all four return values from extract_keywords
                    initial_keywords_list, initial_cleaned_text, initial_filtered_words, initial_extracted_info = extract_keywords(initial_text_content) if initial_text_content else ([], "", "", {})
                    initial_page_general_links = await self.analyze_links(page_for_initial_analysis, normalized_analysis_url)
                    links_from_start_page_for_queue = await self._extract_internal_links_from_page(page_for_initial_analysis, start_domain, config.EXCLUDE_PATTERNS)
                except PlaywrightTimeoutError:
                    logging.warning(f"Timeout loading initial page: {normalized_analysis_url}")
                    # Allow to continue with empty initial data, or handle as critical error
                except Exception as e:
                    logging.error(f"Error during initial analysis of {normalized_analysis_url}: {e}", exc_info=True) # Log stack trace
                    await browser.close() # Ensure browser is closed
                    return None 
                finally:
                    await page_for_initial_analysis.close()
                
                analysis = {
                    'url': normalized_analysis_url,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'links': initial_page_general_links,
                    'content_length': len(initial_text_content) if initial_text_content else 0,
                    'word_count': len(initial_text_content.split()) if initial_text_content else 0,
                    'crawled_internal_pages_count': 0, # Updated after loop
                    'crawled_urls': [normalized_analysis_url] if initial_text_content else [], # Add only if successfully analyzed
                    'page_statistics': {}, # Populated below
                    'content_length_stats': {},
                    'word_count_stats': {},
                    'aggregated_keywords': {},
                    'analysis_duration_seconds': 0,
                    'sitemap_found': bool(sitemap_urls_discovered), # If any sitemap URLs were listed (even if they 404'd later)
                    'sitemap_urls_discovered': sitemap_urls_discovered, # Actual URLs attempted from robots/common
                    'sitemap_urls_discovered_count': len(sitemap_urls_discovered),
                    'sitemap_pages_processed_count': len(filtered_sitemap_pages) # Pages from sitemap after filtering
                }   
                # Add initial page stats if content was fetched
                if initial_text_content or not analysis['crawled_urls']: # if crawled_urls is empty, means initial failed hard
                     analysis['page_statistics'][normalized_analysis_url] = {
                        'url': normalized_analysis_url,
                        'content_length': len(initial_text_content) if initial_text_content else 0,
                        'word_count': len(initial_text_content.split()) if initial_text_content else 0,
                        'keywords': initial_keywords_list,
                        'cleaned_text': initial_cleaned_text,
                        'filtered_words': initial_filtered_words,
                        'extracted_info': initial_extracted_info,  # Store extracted information
                        'headings': initial_headings,
                    }
                
                content_lengths_list = [analysis['content_length']] if initial_text_content else []
                word_counts_list = [analysis['word_count']] if initial_text_content else []
                
                visited_urls = {normalized_analysis_url} # All URLs we attempt to goto
                all_discovered_links = set(visited_urls) # Master set of all unique internal links
                all_discovered_links.update(links_from_start_page_for_queue)
                all_discovered_links.update(filtered_sitemap_pages)

                # Initialize queue with links from sitemap and initial page, excluding already visited
                urls_to_visit_list_intermediate = [
                    link for link in (filtered_sitemap_pages | links_from_start_page_for_queue) 
                    if link not in visited_urls and link # Ensure link is not None
                ]
                urls_to_visit = deque(urls_to_visit_list_intermediate)

                logging.info(f"Initial analysis of {normalized_analysis_url} complete.")
                logging.info(f"Unique internal links from start page for queue: {len(links_from_start_page_for_queue)}")
                logging.info(f"Unique internal links from sitemaps for queue: {len(filtered_sitemap_pages)}")
                logging.info(f"Combined unique URLs to start crawl queue (after filtering visited): {len(urls_to_visit)}")
                logging.info(f"Total discovered links before loop (master set): {len(all_discovered_links)}")

                analyzed_pages_count_in_loop = 0 # Pages analyzed *in the loop* (initial page is separate)

                # Main crawl loop
                while urls_to_visit and \
                      len(all_discovered_links) < config.MAX_LINKS_TO_DISCOVER and \
                      (analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)) < config.MAX_PAGES_TO_ANALYZE:

                    current_url_to_crawl = urls_to_visit.popleft()

                    if current_url_to_crawl in visited_urls: # Should be rare due to pre-filtering
                        logging.debug(f"Skipping {current_url_to_crawl} as it's already in visited_urls.")
                        continue
                    
                    # Final check for domain consistency before costly page load
                    if urlparse(current_url_to_crawl).netloc != start_domain:
                        logging.warning(f"Skipping {current_url_to_crawl} due to domain mismatch with {start_domain}. Adding to visited to prevent re-queue.")
                        visited_urls.add(current_url_to_crawl)
                        continue
                        
                    logging.info(f"Processing page [{analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)}/{config.MAX_PAGES_TO_ANALYZE}]: {current_url_to_crawl} (Queue: {len(urls_to_visit)}, Discovered: {len(all_discovered_links)})")
                    page_for_crawling = await context.new_page()
                    
                    try:
                        await page_for_crawling.goto(current_url_to_crawl, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT)
                        visited_urls.add(current_url_to_crawl) # Mark as visited after successful/attempted goto

                        # Extract links from this page
                        newly_found_links_on_page = await self._extract_internal_links_from_page(page_for_crawling, start_domain, config.EXCLUDE_PATTERNS)
                        for new_link in newly_found_links_on_page:
                            if new_link not in all_discovered_links: # Check against master set
                                if len(all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                    all_discovered_links.add(new_link)
                                    if new_link not in visited_urls: # Not yet visited (or failed)
                                        urls_to_visit.append(new_link)
                                else:
                                    logging.info(f"MAX_LINKS_TO_DISCOVER ({config.MAX_LINKS_TO_DISCOVER}) reached while adding new links.")
                                    break # from new_link loop
                        
                        # Analyze content if within limits
                        if (analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)) < config.MAX_PAGES_TO_ANALYZE:
                            logging.info(f"Analyzing content of: {current_url_to_crawl}")
                            text = await page_for_crawling.evaluate('() => document.body ? document.body.innerText : ""')
                            # Capture all four return values from extract_keywords
                            page_keywords_list, page_cleaned_text, page_filtered_words, page_extracted_info = extract_keywords(text) if text else ([], "", "", {})
                            page_headings = await analyze_headings(page_for_crawling)

                            analysis['page_statistics'][current_url_to_crawl] = {
                                'url': current_url_to_crawl,
                                'content_length': len(text) if text else 0,
                                'word_count': len(text.split()) if text else 0,
                                'keywords': page_keywords_list,
                                'cleaned_text': page_cleaned_text,
                                'filtered_words': page_filtered_words,
                                'extracted_info': page_extracted_info,  # Store extracted information
                                'headings': page_headings,
                            }
                            content_lengths_list.append(len(text) if text else 0)
                            word_counts_list.append(len(text.split()) if text else 0)
                            analysis['crawled_urls'].append(current_url_to_crawl)
                            analyzed_pages_count_in_loop += 1
                        else:
                            logging.info(f"MAX_PAGES_TO_ANALYZE limit reached. Skipping content analysis for {current_url_to_crawl}. Links (if any) were still extracted.")
                            
                    except PlaywrightTimeoutError:
                        logging.warning(f"Timeout loading page for link extraction/analysis: {current_url_to_crawl}")
                        visited_urls.add(current_url_to_crawl) # Mark as visited to prevent re-queue
                    except Exception as e:
                        logging.error(f"Error processing {current_url_to_crawl} for links/analysis: {e}", exc_info=True)
                        visited_urls.add(current_url_to_crawl) # Mark as visited
                    finally:
                        await page_for_crawling.close()

                    # Check limits again to break outer while loop if necessary
                    if len(all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER or \
                       (analyzed_pages_count_in_loop + (1 if analysis['crawled_urls'] else 0)) >= config.MAX_PAGES_TO_ANALYZE:
                        logging.info("Loop termination condition met (MAX_LINKS or MAX_PAGES).")
                        break
                    
                    await asyncio.sleep(random.uniform(config.CRAWL_DELAY_MIN, config.CRAWL_DELAY_MAX)) # Use config values

                # Update final counts based on what was actually analyzed
                analysis['crawled_internal_pages_count'] = len(analysis['crawled_urls']) 
                logging.info(f"Crawl finished. Discovered {len(all_discovered_links)} unique links. Analyzed content of {analysis['crawled_internal_pages_count']} pages.")

                # Calculate stats only if lists are not empty
                if content_lengths_list:
                    sorted_lengths = sorted(content_lengths_list)
                    analysis['content_length_stats'] = {
                        'total': sum(content_lengths_list),
                        'average': round(sum(content_lengths_list) / len(content_lengths_list), 2),
                        'min': min(content_lengths_list),
                        'max': max(content_lengths_list),
                        'median': sorted_lengths[len(sorted_lengths) // 2] if sorted_lengths else 0,
                        'pages_analyzed': len(content_lengths_list)
                    }
                if word_counts_list:
                    sorted_counts = sorted(word_counts_list)
                    analysis['word_count_stats'] = {
                        'total': sum(word_counts_list),
                        'average': round(sum(word_counts_list) / len(word_counts_list), 2),
                        'min': min(word_counts_list),
                        'max': max(word_counts_list),
                        'median': sorted_counts[len(sorted_counts) // 2] if sorted_counts else 0,
                        'pages_analyzed': len(word_counts_list)
                    }
                
                all_keywords_from_analyzed_pages = []
                for page_url_key in analysis['crawled_urls']: # Iterate over successfully crawled URLs
                    page_data = analysis['page_statistics'].get(page_url_key)
                    if page_data and 'keywords' in page_data:
                        all_keywords_from_analyzed_pages.extend(page_data['keywords'])
                analysis['aggregated_keywords'] = dict(Counter(all_keywords_from_analyzed_pages).most_common(config.TOP_N_KEYWORDS)) # Use config
                
                analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
                
                await self.saver.save_reports(analysis)
                logging.info(f"Analysis saved. Duration: {analysis['analysis_duration_seconds']}s")
                return analysis
            
            except Exception as e: # Catch broad errors in Playwright setup
                logging.critical(f"A critical error occurred in Playwright setup or main analysis structure: {e}", exc_info=True)
                return None # Indicate overall failure
            finally:
                if 'browser' in locals() and browser.is_connected(): # Ensure browser is defined and connected
                    await browser.close()
                    logging.info("Playwright browser closed.")
