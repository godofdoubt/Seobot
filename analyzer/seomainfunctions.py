import logging
import time
import random
import asyncio
from collections import deque
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
import aiohttp
from typing import Set, Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin, urlunparse

import analyzer.config as config
from analyzer.methods import validate_url, extract_text
from analyzer.sitemap import discover_sitemap_urls, fetch_all_pages_from_sitemaps
from analyzer.llm_analysis_start import llm_analysis_start

# Configure logging for this module if necessary, or rely on root configuration
# For simplicity, we'll assume root configuration is sufficient or use `analyzer_instance.logger` if available.
# Direct logging calls (logging.error, logging.warning) will use the root logger's settings.


async def _process_page_standalone(
    analyzer_instance,  # Instance of SEOAnalyzer
    page: Page,
    url_to_crawl: str,
    start_domain_check_part: str,
    site_canonical_base_url: str,
    exclude_patterns: List[str],
    header_snippets_to_remove: Optional[List[str]] = None,
    footer_snippets_to_remove: Optional[List[str]] = None,
    extract_with_context: bool = False
) -> Dict[str, Any]:
    result = {
        'url': url_to_crawl,
        'cleaned_text': '',
        'new_links': set(),
        'link_context': {},
        'title': '',
        'headings_count': 0,
        'images_count': 0,
        'missing_alt_tags_count': 0,
        'has_mobile_viewport': False,
        'cleaned_content_length': 0,
    }
    
    try:
        await page.goto(url_to_crawl, wait_until='domcontentloaded', timeout=config.PAGE_TIMEOUT)
        
        if extract_with_context: # Typically only for the main page
            await analyzer_instance._wait_for_dynamic_content(page)
        
        actual_landed_url_str = page.url
        normalized_landed_url = analyzer_instance._normalize_url(actual_landed_url_str, site_canonical_base_url)

        if not normalized_landed_url:
            result['url'] = None 
            return result
        
        parsed_landed = urlparse(normalized_landed_url)
        if parsed_landed.netloc.replace('www.','',1).lower() != start_domain_check_part.lower():
            result['url'] = None 
            return result

        result['url'] = normalized_landed_url

        result['title'] = await page.title()
        result['headings_count'] = await page.locator('h1,h2,h3,h4,h5,h6').count()
        
        image_elements = await page.locator('img').all()
        result['images_count'] = len(image_elements)
        missing_alts = 0
        for img_element in image_elements:
            try:
                alt_text = await img_element.get_attribute('alt')
                if alt_text is None or alt_text.strip() == "":
                    missing_alts += 1
            except Exception:
                pass
        result['missing_alt_tags_count'] = missing_alts
        result['has_mobile_viewport'] = await page.locator('meta[name="viewport"]').count() > 0

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
        
        result['cleaned_content_length'] = len(result['cleaned_text'])
      
        if extract_with_context:
            link_data = await analyzer_instance._extract_links_with_context(
                page, start_domain_check_part, site_canonical_base_url, exclude_patterns
            )
            result['new_links'] = link_data['links']
            result['link_context'] = link_data['context']
        else:
            result['new_links'] = await analyzer_instance._extract_internal_links_from_page_enhanced(
                page, start_domain_check_part, site_canonical_base_url, exclude_patterns
            )
        
        return result
    except PlaywrightTimeoutError:
        logging.warning(f"Timeout processing {url_to_crawl}")
        result['url'] = None 
        return result
    except Exception as e:
        logging.error(f"Error processing {url_to_crawl}: {e}")
        result['url'] = None
        return result


async def analyze_url_standalone(analyzer_instance, url: str) -> Optional[Dict[str, Any]]:
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
    
    analyzer_instance.site_base_for_normalization = urlunparse((canonical_scheme, canonical_netloc, '/', '', '', ''))
    analyzer_instance.start_domain_normal_part = urlparse(analyzer_instance.site_base_for_normalization).netloc.replace('www.', '', 1)
    
    analysis_url_input = analyzer_instance._normalize_url(raw_validated_url, analyzer_instance.site_base_for_normalization)
    if not analysis_url_input:
        logging.error(f"Could not normalize the start URL '{raw_validated_url}'")
        return None

    print(f"Starting analysis of: {analysis_url_input}")
    
    analyzer_instance.identified_header_texts = []
    analyzer_instance.identified_footer_texts = []
    analyzer_instance.visited_urls = set() 
    analyzer_instance.all_discovered_links = set() 
    analyzer_instance.initial_page_llm_report = {"tech_stats": {}}
    initial_page_link_context = None

    sitemap_pages_raw: Set[str] = set()
    sitemap_urls_discovered: List[str] = []
    robots_txt_found_status = False

    async with aiohttp.ClientSession(headers={'User-Agent': config.USER_AGENT}) as session:
        sitemap_urls_discovered = await discover_sitemap_urls(analysis_url_input, session) 
        if sitemap_urls_discovered:
            sitemap_pages_raw = await fetch_all_pages_from_sitemaps(sitemap_urls_discovered, session)
        
        robots_url = urljoin(analysis_url_input, '/robots.txt')
        try:
            async with session.get(robots_url, timeout=10) as response:
                robots_txt_found_status = response.status == 200
        except Exception as e_robots:
            logging.warning(f"Could not fetch robots.txt from {robots_url}: {e_robots}")
            robots_txt_found_status = False
    
    sitemap_pages_normalized: Set[str] = set()
    for page_url in sitemap_pages_raw:
        norm_page_url = analyzer_instance._normalize_url(page_url, analyzer_instance.site_base_for_normalization)
        if norm_page_url and not any(exclude in norm_page_url for exclude in config.EXCLUDE_PATTERNS):
             sitemap_pages_normalized.add(norm_page_url)
    
    print(f"Found {len(sitemap_pages_normalized)} URLs in sitemaps. Robots.txt found: {robots_txt_found_status}")
    
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
        'sitemap_pages_processed_count': len(sitemap_pages_normalized),
        'robots_txt_found': robots_txt_found_status,
        'total_cleaned_content_length': 0,
        'average_cleaned_content_length_per_page': 0.0,
        'total_headings_count': 0,
        'total_images_count': 0,
        'total_missing_alt_tags_count': 0,
        'pages_with_mobile_viewport_count': 0,
    }

    analyzer_instance.visited_urls.add(analysis_url_input) 
    analyzer_instance.all_discovered_links.add(analysis_url_input)
    analyzer_instance.all_discovered_links.update(sitemap_pages_normalized)
    
    url_in_report_dict: Dict[str, bool] = {} 
    urls_to_visit = deque()
    for s_url in sitemap_pages_normalized:
        if s_url != analysis_url_input and s_url not in analyzer_instance.visited_urls:
            urls_to_visit.append(s_url)
            analyzer_instance.visited_urls.add(s_url) 

    actual_initial_url = None
    initial_cleaned_text_for_main_url = ""
    current_total_cleaned_content_length = 0
    current_total_headings_count = 0
    current_total_images_count = 0
    current_total_missing_alt_tags_count = 0
    current_pages_with_mobile_viewport_count = 0

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
            initial_page_tech_stats = {}
            try:
                initial_result = await _process_page_standalone(
                    analyzer_instance,
                    initial_page_obj, 
                    analysis_url_input, 
                    analyzer_instance.start_domain_normal_part,
                    analyzer_instance.site_base_for_normalization,
                    config.EXCLUDE_PATTERNS,
                    header_snippets_to_remove=None, 
                    footer_snippets_to_remove=None,
                    extract_with_context=True
                )
                actual_initial_url = initial_result['url'] 

                if actual_initial_url:
                    initial_page_tech_stats = {
                        'title': initial_result['title'],
                        'headings_count': initial_result['headings_count'],
                        'images_count': initial_result['images_count'],
                        'missing_alt_tags_count': initial_result['missing_alt_tags_count'],
                        'has_mobile_viewport': initial_result['has_mobile_viewport'],
                        'cleaned_content_length': initial_result['cleaned_content_length']
                    }
                    current_total_cleaned_content_length += initial_page_tech_stats['cleaned_content_length']
                    current_total_headings_count += initial_page_tech_stats['headings_count']
                    current_total_images_count += initial_page_tech_stats['images_count']
                    current_total_missing_alt_tags_count += initial_page_tech_stats['missing_alt_tags_count']
                    if initial_page_tech_stats['has_mobile_viewport']:
                        current_pages_with_mobile_viewport_count +=1

                    if initial_result['cleaned_text']:
                        raw_initial_cleaned_text = initial_result['cleaned_text'] 
                    
                        # Store link context for internal use but don't add to report
                        if 'link_context' in initial_result and initial_result['link_context']:
                            initial_page_link_context = initial_result['link_context']
                    
                        print("Analyzing main page content...")
                        initial_page_data_for_llm = {
                            'url': actual_initial_url,
                            'cleaned_text': raw_initial_cleaned_text, 
                            'headings': {} 
                        }
                        try:
                            analyzer_instance.initial_page_llm_report = await llm_analysis_start(initial_page_data_for_llm)
                            if analyzer_instance.initial_page_llm_report and not analyzer_instance.initial_page_llm_report.get("error"):
                                analyzer_instance.identified_header_texts = analyzer_instance.initial_page_llm_report.get("header", [])
                                analyzer_instance.identified_footer_texts = analyzer_instance.initial_page_llm_report.get("footer", [])
                                if analyzer_instance.identified_header_texts or analyzer_instance.identified_footer_texts:
                                    print(f"Identified {len(analyzer_instance.identified_header_texts)} header and {len(analyzer_instance.identified_footer_texts)} footer elements via LLM")
                                # Note: link_context is available internally but not added to report
                            else: 
                                error_msg = analyzer_instance.initial_page_llm_report.get('error', 'Unknown LLM error') if analyzer_instance.initial_page_llm_report else 'No LLM report'
                                logging.warning(f"LLM analysis for initial page failed: {error_msg}")
                                if not isinstance(analyzer_instance.initial_page_llm_report, dict): 
                                    analyzer_instance.initial_page_llm_report = {}
                                analyzer_instance.initial_page_llm_report.setdefault('url', actual_initial_url)
                                analyzer_instance.initial_page_llm_report.setdefault('error', error_msg)

                        except Exception as e_llm_init:
                            logging.error(f"Error in LLM analysis for initial page: {e_llm_init}")
                            analyzer_instance.initial_page_llm_report = {
                                "url": actual_initial_url, "error": f"Exception in llm_analysis_start: {str(e_llm_init)}",
                                "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                                "suggested_keywords_for_seo": [], "header": [], "footer": []
                            }
                        
                        if isinstance(analyzer_instance.initial_page_llm_report, dict):
                            analyzer_instance.initial_page_llm_report['tech_stats'] = initial_page_tech_stats
                        else: 
                            analyzer_instance.initial_page_llm_report = {'tech_stats': initial_page_tech_stats}

                        final_initial_cleaned_text = raw_initial_cleaned_text 
                        if analyzer_instance.identified_header_texts or analyzer_instance.identified_footer_texts:
                            try:
                                final_initial_cleaned_text = extract_text(
                                    raw_initial_cleaned_text, 
                                    header_snippets=analyzer_instance.identified_header_texts,
                                    footer_snippets=analyzer_instance.identified_footer_texts
                                )
                                new_length = len(final_initial_cleaned_text)
                                if new_length != initial_page_tech_stats['cleaned_content_length']:
                                    current_total_cleaned_content_length -= initial_page_tech_stats['cleaned_content_length']
                                    current_total_cleaned_content_length += new_length
                                    initial_page_tech_stats['cleaned_content_length'] = new_length
                                    if isinstance(analyzer_instance.initial_page_llm_report, dict) and 'tech_stats' in analyzer_instance.initial_page_llm_report:
                                        analyzer_instance.initial_page_llm_report['tech_stats']['cleaned_content_length'] = new_length
                            except Exception as extract_error_hf:
                                logging.error(f"extract_text failed during header/footer removal for initial page: {extract_error_hf}")
                        
                        initial_cleaned_text_for_main_url = final_initial_cleaned_text
                        analysis['crawled_urls'].append(actual_initial_url)
                        url_in_report_dict[actual_initial_url] = True 
                        
                        for link in initial_result['new_links']: 
                            if len(analyzer_instance.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                if link not in analyzer_instance.visited_urls and link not in urls_to_visit :
                                    analyzer_instance.all_discovered_links.add(link)
                                    urls_to_visit.append(link)
                                    analyzer_instance.visited_urls.add(link)
                            else: break
                    else: 
                         if isinstance(analyzer_instance.initial_page_llm_report, dict):
                            analyzer_instance.initial_page_llm_report['tech_stats'] = initial_page_tech_stats
                         analysis['crawled_urls'].append(actual_initial_url) 
                         url_in_report_dict[actual_initial_url] = True
                else: 
                    logging.error(f"Initial page processing failed for {analysis_url_input}. Cannot proceed with LLM or content analysis for it.")
                    analyzer_instance.initial_page_llm_report = {
                        "url": analysis_url_input, 
                        "error": "Initial page processing failed (e.g. timeout, navigation error)",
                        "tech_stats": initial_page_tech_stats 
                    }

            except Exception as e_initial:
                logging.error(f"Error during initial page analysis for {analysis_url_input}: {e_initial}")
                analyzer_instance.initial_page_llm_report = {
                    "url": analysis_url_input, "error": f"Outer error during initial page processing: {e_initial}",
                    "tech_stats": {}
                }
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
                        tasks.append(_process_page_standalone(
                            analyzer_instance,
                            page, batch_url_item, 
                            analyzer_instance.start_domain_normal_part, 
                            analyzer_instance.site_base_for_normalization, 
                            config.EXCLUDE_PATTERNS,
                            header_snippets_to_remove=analyzer_instance.identified_header_texts, 
                            footer_snippets_to_remove=analyzer_instance.identified_footer_texts
                        ))
                    batch_proc_results = await asyncio.gather(*tasks, return_exceptions=True)
                    return batch_proc_results, pages_for_batch
                except Exception as e_batch_create:
                    logging.error(f"Error creating batch tasks: {e_batch_create}")
                    return [e_batch_create] * len(batch_urls_to_crawl), pages_for_batch

            batch_size = min(8, config.MAX_PAGES_TO_ANALYZE if config.MAX_PAGES_TO_ANALYZE > 0 else 1)
            if config.MAX_PAGES_TO_ANALYZE == 0: batch_size = 0

            while urls_to_visit and len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE and \
                  len(analyzer_instance.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER and batch_size > 0:
                current_batch_urls = []
                
                while urls_to_visit and len(current_batch_urls) < batch_size:
                    if len(url_in_report_dict) + len(current_batch_urls) >= config.MAX_PAGES_TO_ANALYZE:
                        break
                    url_from_queue = urls_to_visit.popleft()
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

                        if not actual_processed_url: 
                            continue
                        
                        if actual_processed_url in url_in_report_dict:
                            for new_link in page_result_data.get('new_links', set()): 
                                if len(analyzer_instance.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                    if new_link not in analyzer_instance.visited_urls and new_link not in urls_to_visit: 
                                        analyzer_instance.all_discovered_links.add(new_link)
                                        urls_to_visit.append(new_link)
                                        analyzer_instance.visited_urls.add(new_link)
                                else: break
                            if len(analyzer_instance.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER: break
                            continue

                        if actual_processed_url != analysis_url_input: 
                            if len(url_in_report_dict) < config.MAX_PAGES_TO_ANALYZE :
                                page_stats_data = {
                                    'url': actual_processed_url,
                                    'cleaned_text': page_result_data['cleaned_text'],
                                    'title': page_result_data['title'],
                                    'headings_count': page_result_data['headings_count'],
                                    'images_count': page_result_data['images_count'],
                                    'missing_alt_tags_count': page_result_data['missing_alt_tags_count'],
                                    'has_mobile_viewport': page_result_data['has_mobile_viewport'],
                                    'cleaned_content_length': page_result_data['cleaned_content_length']
                                }
                                analysis['page_statistics'][actual_processed_url] = page_stats_data
                                
                                current_total_cleaned_content_length += page_stats_data['cleaned_content_length']
                                current_total_headings_count += page_stats_data['headings_count']
                                current_total_images_count += page_stats_data['images_count']
                                current_total_missing_alt_tags_count += page_stats_data['missing_alt_tags_count']
                                if page_stats_data['has_mobile_viewport']:
                                    current_pages_with_mobile_viewport_count +=1
                                
                                url_in_report_dict[actual_processed_url] = True
                                analysis['crawled_urls'].append(actual_processed_url)
                                successful_pages_in_batch += 1
                        
                        for new_link in page_result_data.get('new_links', set()): 
                            if len(analyzer_instance.all_discovered_links) < config.MAX_LINKS_TO_DISCOVER:
                                if new_link not in analyzer_instance.visited_urls and new_link not in urls_to_visit: 
                                    analyzer_instance.all_discovered_links.add(new_link)
                                    urls_to_visit.append(new_link)
                                    analyzer_instance.visited_urls.add(new_link) 
                            else: break 
                        
                        if len(analyzer_instance.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER or \
                           len(url_in_report_dict) >= config.MAX_PAGES_TO_ANALYZE:
                            break 
                    
                    if successful_pages_in_batch > 0:
                        print(f"Successfully processed {successful_pages_in_batch} pages in this batch.")
                        
                finally:
                    for p_obj in batch_pages_created:
                         if p_obj and not p_obj.is_closed():
                            await p_obj.close()
                
                if len(url_in_report_dict) >= config.MAX_PAGES_TO_ANALYZE or \
                   len(analyzer_instance.all_discovered_links) >= config.MAX_LINKS_TO_DISCOVER:
                    print("Reached max pages to analyze or max links to discover.")
                    break 
                
                await asyncio.sleep(random.uniform(config.CRAWL_DELAY_MIN / 2, config.CRAWL_DELAY_MAX / 2))

            if analyzer_instance.initial_page_llm_report and initial_cleaned_text_for_main_url:
                 if isinstance(analyzer_instance.initial_page_llm_report, dict):
                    analyzer_instance.initial_page_llm_report['cleaned_text'] = initial_cleaned_text_for_main_url

            analysis['crawled_internal_pages_count'] = len(analysis['crawled_urls'])
            analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
            
            analysis['total_cleaned_content_length'] = current_total_cleaned_content_length
            analysis['total_headings_count'] = current_total_headings_count
            analysis['total_images_count'] = current_total_images_count
            analysis['total_missing_alt_tags_count'] = current_total_missing_alt_tags_count
            analysis['pages_with_mobile_viewport_count'] = current_pages_with_mobile_viewport_count
            if analysis['crawled_internal_pages_count'] > 0:
                analysis['average_cleaned_content_length_per_page'] = round(
                    current_total_cleaned_content_length / analysis['crawled_internal_pages_count'], 2
                )
            else:
                analysis['average_cleaned_content_length_per_page'] = 0.0

            print(f"Analysis complete: {analysis['crawled_internal_pages_count']} pages analyzed in {analysis['analysis_duration_seconds']} seconds. Total {len(analyzer_instance.all_discovered_links)} links discovered.")
            
            if analyzer_instance.initial_page_llm_report:
                analysis['llm_analysis'] = analyzer_instance.initial_page_llm_report
            elif actual_initial_url: 
                 analysis['llm_analysis'] = {
                    "url": actual_initial_url, "error": "Initial LLM analysis data structure unavailable.",
                    "cleaned_text": initial_cleaned_text_for_main_url,
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                    "suggested_keywords_for_seo": [], "header": [], "footer": [],
                    "tech_stats": initial_page_tech_stats if initial_page_tech_stats else {}
                }
            else: 
                analysis['llm_analysis'] = {
                    "url": analysis_url_input, "error": "Initial page processing failed, LLM analysis critically unavailable.",
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                    "suggested_keywords_for_seo": [], "header": [], "footer": [],
                    "tech_stats": {}
                }
            
            return analysis
            
        except Exception as e_critical:
            logging.critical(f"Critical error in analysis workflow: {e_critical}", exc_info=True)
            analysis['error'] = f"Critical analysis error: {str(e_critical)}"
            analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
            if 'llm_analysis' not in analysis: analysis['llm_analysis'] = {}
            if 'tech_stats' not in analysis['llm_analysis']: analysis['llm_analysis']['tech_stats'] = {}
            return analysis
        finally:
            if 'browser' in locals() and browser.is_connected():
                await browser.close()
            
            final_analysis_data_to_save = analysis if 'analysis' in locals() and analysis else {}
            
            if 'llm_analysis' not in final_analysis_data_to_save:
                final_url_for_error_report = actual_initial_url if 'actual_initial_url' in locals() and actual_initial_url else analysis_url_input
                final_analysis_data_to_save['llm_analysis'] = {
                    "url": final_url_for_error_report, 
                    "error": "LLM analysis section incomplete or initial page failed before LLM stage.",
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                    "suggested_keywords_for_seo": [], "header": [], "footer": [],
                    "tech_stats": {} 
                }
            elif 'tech_stats' not in final_analysis_data_to_save.get('llm_analysis', {}):
                 if isinstance(final_analysis_data_to_save.get('llm_analysis'), dict):
                    final_analysis_data_to_save['llm_analysis']['tech_stats'] = {}

            if final_analysis_data_to_save and (final_analysis_data_to_save.get('crawled_internal_pages_count',0) > 0 or final_analysis_data_to_save.get('url')):
                try:
                    await analyzer_instance.saver.save_reports(final_analysis_data_to_save) 
                    print("Analysis report saved successfully!")
                except Exception as e_save_final:
                    logging.error(f"Failed to save final analysis: {e_save_final}")
            else:
                start_url_for_log = analysis_url_input if 'analysis_url_input' in locals() else url
                logging.warning(f"No substantial analysis data to save for {start_url_for_log}. Report: {final_analysis_data_to_save}")
            
            return final_analysis_data_to_save if final_analysis_data_to_save.get('url') else None