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

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SEOAnalyzer:
    def __init__(self):
        self.saver = SEOReportSaver()
        self.visited_urls: Set[str] = set()
        self.all_discovered_links: Set[str] = set()
        self.site_base_for_normalization: Optional[str] = None
        self.start_domain_normal_part: Optional[str] = None
        self.identified_header_texts: List[str] = [] 
        self.identified_footer_texts: List[str] = [] 
        self.initial_page_llm_report: Optional[Dict[str, Any]] = None # To store the first LLM report

    # ... ( _normalize_url and _extract_internal_links_from_page methods remain unchanged) ...
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
                logging.debug(f"URL '{url}' has invalid scheme or netloc after making absolute: {absolute_url}")
                return None

            parsed_site_canonical = urlparse(site_canonical_base_url)
            target_scheme = parsed_site_canonical.scheme
            original_link_netloc_lower = parsed_original_link.netloc.lower()
            site_canonical_netloc_lower = parsed_site_canonical.netloc.lower()
            original_link_domain_part = original_link_netloc_lower.split(':')[0].replace('www.', '', 1)
            site_canonical_domain_part = site_canonical_netloc_lower.split(':')[0].replace('www.', '', 1)

            if original_link_domain_part != site_canonical_domain_part:
                logging.debug(f"URL '{url}' (domain: {original_link_domain_part}) is not on the canonical site domain ({site_canonical_domain_part}). Not an internal link for this crawl.")
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
            logging.warning(f"Error normalizing URL '{url}' with site_canonical_base_url '{site_canonical_base_url}': {e}")
            return None

    async def _extract_internal_links_from_page(self, page: Page, base_domain_check_part: str, site_canonical_base_url: str, exclude_patterns: List[str]) -> Set[str]:
        try:
            links_on_page_js = await page.evaluate("""
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
                                linkUrl.hostname.replace(/^www\\./i, '') === baseDomain && 
                                !excludePatterns.some(pattern => absoluteUrl.includes(pattern))) {
                                links.add(absoluteUrl); 
                            }
                        } catch (e) {}
                    });
                    return Array.from(links);
                }
            """, {"baseDomain": base_domain_check_part, "excludePatterns": exclude_patterns})
            
            normalized_found_links: Set[str] = set()
            for link_str in links_on_page_js:
                normalized_link = self._normalize_url(link_str, site_canonical_base_url)
                if normalized_link:
                    normalized_found_links.add(normalized_link)
            
            return normalized_found_links
            
        except Exception as e:
            logging.warning(f"Could not extract links from {page.url}: {e}")
            return set()

    async def _process_page(self, page: Page, url_to_crawl: str, 
                            start_domain_check_part: str, site_canonical_base_url: str, 
                            exclude_patterns: List[str],
                            header_snippets_to_remove: Optional[List[str]] = None,
                            footer_snippets_to_remove: Optional[List[str]] = None
                            ) -> Dict[str, Any]:
        result = {
            'url': url_to_crawl,
            'cleaned_text': '',
            'new_links': set()
        }
        
        try:
            await page.goto(url_to_crawl, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT)
            
            actual_landed_url_str = page.url
            normalized_landed_url = self._normalize_url(actual_landed_url_str, site_canonical_base_url)

            if not normalized_landed_url:
                logging.warning(f"Crawled {url_to_crawl}, but landed on unnormalizable URL: {actual_landed_url_str}. Skipping.")
                result['url'] = None
                return result
            
            parsed_landed = urlparse(normalized_landed_url)
            if parsed_landed.netloc.replace('www.','',1) != start_domain_check_part:
                logging.warning(f"Crawled {url_to_crawl}, but redirected to external domain: {normalized_landed_url}. Skipping.")
                result['url'] = None
                return result

            result['url'] = normalized_landed_url 

            text_content = await page.evaluate('() => document.body ? document.body.innerText : ""')
            
            if text_content:
                result['cleaned_text'] = extract_text(
                    text_content,
                    header_snippets=header_snippets_to_remove,
                    footer_snippets=footer_snippets_to_remove
                )
                if header_snippets_to_remove or footer_snippets_to_remove:
                    logging.debug(f"Called extract_text for {normalized_landed_url} with H/F snippet removal.")
            else:
                result['cleaned_text'] = ""
          
            result['new_links'] = await self._extract_internal_links_from_page(
                page, start_domain_check_part, site_canonical_base_url, exclude_patterns
            )
            
            return result
        except PlaywrightTimeoutError:
            logging.warning(f"Timeout loading page: {url_to_crawl} (intended), landed on {page.url if 'page' in locals() else 'N/A'}")
            result['url'] = None
            return result
        except Exception as e:
            logging.error(f"Error processing {url_to_crawl} (intended), landed on {page.url if 'page' in locals() else 'N/A'}: {e}")
            result['url'] = None
            return result

    async def analyze_url(self, url: str) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        # ... (URL validation and normalization setup remains the same) ...
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
            logging.error(f"Could not normalize the start URL '{raw_validated_url}' using base '{self.site_base_for_normalization}'")
            return None

        logging.info(f"Site base for normalization: {self.site_base_for_normalization}")
        logging.info(f"Analyzing normalized URL: {analysis_url_input}")
        
        self.identified_header_texts = []
        self.identified_footer_texts = []
        self.visited_urls = set() 
        self.all_discovered_links = set() 
        self.initial_page_llm_report = None # Reset for new analysis

        # ... (sitemap discovery remains the same) ...
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
        
        logging.info(f"Total unique URLs from sitemaps after filtering and normalization: {len(sitemap_pages_normalized)}")
        
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
            # 'llm_analysis' will be added later before saving
        }

        self.visited_urls.add(analysis_url_input) 
        self.all_discovered_links.add(analysis_url_input)
        self.all_discovered_links.update(sitemap_pages_normalized)
        
        url_in_report_dict: Dict[str, bool] = {} 
        urls_to_visit = deque()
        for s_url in sitemap_pages_normalized:
            if s_url != analysis_url_input and s_url not in self.visited_urls:
                urls_to_visit.append(s_url)
                self.visited_urls.add(s_url) 

        actual_initial_url = None # Define for broader scope, in case of errors before assignment
        initial_cleaned_text_for_main_url = "" # Store this for LLM analysis only

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
                        footer_snippets_to_remove=None  
                    )
                    actual_initial_url = initial_result['url'] 

                    if actual_initial_url and initial_result['cleaned_text']:
                        raw_initial_cleaned_text = initial_result['cleaned_text'] 
                        
                        logging.info(f"Requesting LLM analysis for main page: {actual_initial_url} to identify header/footer.")
                        initial_page_data_for_llm = {
                            'url': actual_initial_url,
                            'cleaned_text': raw_initial_cleaned_text, 
                            'headings': {} 
                        }
                        try:
                            # This is the FIRST and CRITICAL LLM call for H/F identification
                            self.initial_page_llm_report = await llm_analysis_start(initial_page_data_for_llm)
                            if self.initial_page_llm_report and not self.initial_page_llm_report.get("error"):
                                self.identified_header_texts = self.initial_page_llm_report.get("header", [])
                                self.identified_footer_texts = self.initial_page_llm_report.get("footer", [])
                                logging.info(f"LLM identified header snippets ({len(self.identified_header_texts)}): {self.identified_header_texts if self.identified_header_texts else 'None'}")
                                logging.info(f"LLM identified footer snippets ({len(self.identified_footer_texts)}): {self.identified_footer_texts if self.identified_footer_texts else 'None'}")
                            else:
                                error_msg = self.initial_page_llm_report.get('error', 'Unknown LLM error') if self.initial_page_llm_report else 'No LLM report'
                                logging.warning(f"LLM analysis for main page header/footer identification ({actual_initial_url}) failed or returned error: {error_msg}")
                                # Ensure initial_page_llm_report is a dict even on error for later assignment
                                if not isinstance(self.initial_page_llm_report, dict): self.initial_page_llm_report = {}
                                self.initial_page_llm_report.setdefault('url', actual_initial_url)
                                self.initial_page_llm_report.setdefault('error', error_msg)
                        except Exception as e_llm_init:
                            logging.error(f"Error calling llm_analysis_start for initial page {actual_initial_url}: {e_llm_init}", exc_info=True)
                            self.initial_page_llm_report = {
                                "url": actual_initial_url, "error": f"Exception in llm_analysis_start: {str(e_llm_init)}",
                                "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                                "suggested_keywords_for_seo": [], "header": [], "footer": []
                            }
                        
                        final_initial_cleaned_text = raw_initial_cleaned_text 
                        if self.identified_header_texts or self.identified_footer_texts:
                            logging.info(f"Re-processing initial page text for {actual_initial_url} with identified H/F snippets.")
                            final_initial_cleaned_text = extract_text(
                                raw_initial_cleaned_text, 
                                header_snippets=self.identified_header_texts,
                                footer_snippets=self.identified_footer_texts
                            )
                            logging.debug(f"Initial page text length after H/F removal: {len(final_initial_cleaned_text)} (Original: {len(raw_initial_cleaned_text)})")
                        
                        # Store the cleaned text but DON'T add to page_statistics
                        initial_cleaned_text_for_main_url = final_initial_cleaned_text
                        analysis['crawled_urls'].append(actual_initial_url)
                        
                        for link in initial_result['new_links']:
                            if link not in self.visited_urls and link not in urls_to_visit :
                                self.all_discovered_links.add(link)
                                urls_to_visit.append(link)
                                self.visited_urls.add(link) 
                except Exception as e:
                    logging.error(f"Error during initial page analysis of {analysis_url_input}: {e}")
                finally:
                    if initial_page_obj and not initial_page_obj.is_closed():
                        await initial_page_obj.close()
                
                # --- Main parallel crawl process (remains largely the same) ---
                async def process_batch_wrapper(batch_urls_to_crawl):
                    # ... (no changes needed inside process_batch_wrapper)
                    tasks = []
                    pages_for_batch = []
                    try:
                        for batch_url_item in batch_urls_to_crawl:
                            page = await context.new_page()
                            pages_for_batch.append(page)
                            tasks.append(self._process_page(
                                page, batch_url_item, 
                                self.start_domain_normal_part, 
                                self.site_base_for_normalization, 
                                config.EXCLUDE_PATTERNS,
                                header_snippets_to_remove=self.identified_header_texts, 
                                footer_snippets_to_remove=self.identified_footer_texts
                            ))
                        batch_proc_results = await asyncio.gather(*tasks, return_exceptions=True)
                        return batch_proc_results, pages_for_batch
                    except Exception as e_batch:
                        logging.error(f"Error in batch processing setup: {e_batch}")
                        return [e_batch] * len(batch_urls_to_crawl), pages_for_batch

                batch_size = min(8, config.MAX_PAGES_TO_ANALYZE)
                
                while urls_to_visit and len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE and len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER :
                    # ... (batch processing loop remains the same logic) ...
                    current_batch_urls = []
                    processed_in_batch_count = 0 
                    
                    while urls_to_visit and len(current_batch_urls) < batch_size:
                        if len(url_in_report_dict) + processed_in_batch_count >= config.MAX_PAGES_TO_ANALYZE:
                            break
                        url_from_queue = urls_to_visit.popleft()
                        if url_from_queue not in url_in_report_dict:
                           current_batch_urls.append(url_from_queue)
                           processed_in_batch_count +=1 

                    if not current_batch_urls:
                        if not urls_to_visit and len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE:
                            logging.info("No more URLs in queue to process, but MAX_PAGES_TO_ANALYZE not reached.")
                        break 
                        
                    logging.info(f"Processing batch of {len(current_batch_urls)} pages (Total unique pages in report: {len(url_in_report_dict)}/{config.MAX_PAGES_TO_ANALYZE})")
                    
                    batch_results_data, batch_pages_created = await process_batch_wrapper(current_batch_urls)
                    
                    try: 
                        for intended_url, page_result_data in zip(current_batch_urls, batch_results_data):
                            if isinstance(page_result_data, Exception):
                                logging.error(f"Task for {intended_url} failed with exception: {page_result_data}")
                                continue 

                            actual_processed_url = page_result_data['url'] 

                            if not actual_processed_url: 
                                logging.debug(f"Skipping result for intended URL {intended_url} as actual processed URL is invalid.")
                                continue
                            
                            if actual_processed_url in url_in_report_dict:
                                logging.debug(f"URL {actual_processed_url} (from intended {intended_url}) already in report. Skipping storage.")
                                for new_link in page_result_data['new_links']: 
                                    if len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                        if new_link not in self.visited_urls and new_link not in urls_to_visit: 
                                            self.all_discovered_links.add(new_link)
                                            urls_to_visit.append(new_link)
                                            self.visited_urls.add(new_link)
                                    else: break
                                if len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER: break
                                continue

                            # Skip adding to page_statistics if it's the main URL
                            if actual_processed_url == analysis_url_input:
                                continue

                            if page_result_data['cleaned_text']: 
                                if len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE :
                                    analysis['page_statistics'][actual_processed_url] = {
                                        'url': actual_processed_url,
                                        'cleaned_text': page_result_data['cleaned_text'], 
                                    }
                                    url_in_report_dict[actual_processed_url] = True
                                    analysis['crawled_urls'].append(actual_processed_url)
                                    if self.identified_header_texts or self.identified_footer_texts:
                                        logging.info(f"Stored cleaned_text for {actual_processed_url} (H/F removal applied by extract_text).")
                                else:
                                    logging.info(f"Max pages limit ({config.MAX_PAGES_TO_ANALYZE}) reached, not adding {actual_processed_url} to report.")
                            
                            for new_link in page_result_data['new_links']: 
                                if len(self.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                    if new_link not in self.visited_urls and new_link not in urls_to_visit: 
                                        self.all_discovered_links.add(new_link)
                                        urls_to_visit.append(new_link)
                                        self.visited_urls.add(new_link) 
                                else:
                                    logging.info(f"Reached maximum links to discover: {config.MAX_LINKS_TO_DISCOVER}")
                                    break 
                            if len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER or \
                               len(url_in_report_dict) >= config.MAX_PAGES_TO_ANALYZE:
                                break 
                    finally:
                        for p_obj in batch_pages_created:
                             if p_obj and not p_obj.is_closed():
                                await p_obj.close()
                    
                    if len(url_in_report_dict) >= config.MAX_PAGES_TO_ANALYZE or \
                       len(self.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER:
                        logging.info("Max pages or max discovered links limit reached. Ending crawl.")
                        break 
                    
                    await asyncio.sleep(random.uniform(config.CRAWL_DELAY_MIN / 2, config.CRAWL_DELAY_MAX / 2))

                # Add the cleaned text to the LLM report if it exists
                if self.initial_page_llm_report and initial_cleaned_text_for_main_url:
                    self.initial_page_llm_report['cleaned_text'] = initial_cleaned_text_for_main_url

                analysis['crawled_internal_pages_count'] = len(analysis['crawled_urls'])
                analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
                
                if len(set(analysis['crawled_urls'])) != len(analysis['crawled_urls']):
                    logging.warning(f"DUPLICATE CHECK: crawled_urls list contains duplicates. Unique count: {len(set(analysis['crawled_urls']))}, List length: {len(analysis['crawled_urls'])}")

                logging.info(f"Analysis complete. Discovered {len(self.all_discovered_links)} unique links. Analyzed {analysis['crawled_internal_pages_count']} unique pages in report.")
                logging.info(f"Total visited_urls (includes queue): {len(self.visited_urls)}")
                logging.info(f"Analysis duration: {analysis['analysis_duration_seconds']} seconds")
                
                # Add the stored initial LLM report to the main analysis object
                if self.initial_page_llm_report:
                    analysis['llm_analysis'] = self.initial_page_llm_report
                elif actual_initial_url: # Fallback if initial_page_llm_report wasn't set but we know the URL
                     analysis['llm_analysis'] = {
                        "url": actual_initial_url, "error": "Initial LLM analysis data unavailable.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "header": [], "footer": []
                    }
                else: # Ultimate fallback
                    analysis['llm_analysis'] = {
                        "url": analysis_url_input, "error": "Initial LLM analysis data critically unavailable.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "header": [], "footer": []
                    }
                
                return analysis
                
            except Exception as e:
                logging.critical(f"Critical error in analysis: {e}", exc_info=True)
                analysis = None 
                return None
            finally:
                if 'browser' in locals() and browser.is_connected():
                    await browser.close()
                
                current_analysis_data = analysis if 'analysis' in locals() and analysis else None
                final_analysis_data = current_analysis_data if current_analysis_data and current_analysis_data.get('crawled_internal_pages_count',0) > 0 else None

                if final_analysis_data:
                    # Ensure llm_analysis is part of final_analysis_data from the stored initial report
                    # This step is slightly redundant if 'analysis' object was correctly populated above, but acts as a safeguard.
                    if self.initial_page_llm_report and 'llm_analysis' not in final_analysis_data:
                        final_analysis_data['llm_analysis'] = self.initial_page_llm_report
                    elif 'llm_analysis' not in final_analysis_data: # If still not present, add a default error
                        final_url_for_llm_error = actual_initial_url if actual_initial_url else analysis_url_input
                        final_analysis_data['llm_analysis'] = {
                            "url": final_url_for_llm_error, "error": "LLM analysis for initial page missing before save.",
                            "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                            "suggested_keywords_for_seo": [], "header": [], "footer": []
                        }
                        
                    try:
                        await self.saver.save_reports(final_analysis_data) 
                        logging.info(f"Analysis saved successfully for {final_analysis_data['url']}.")
                    except Exception as e_save:
                        logging.error(f"Failed to save analysis for {final_analysis_data.get('url', 'N/A')}: {e_save}")
                else:
                    start_url_for_log = analysis_url_input if 'analysis_url_input' in locals() else url
                    logging.warning(f"No substantial analysis data to save for {start_url_for_log}.")
                
                return final_analysis_data