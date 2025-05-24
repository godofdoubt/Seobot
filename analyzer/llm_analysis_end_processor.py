# analyzer/llm_analysis_end_processor.py
import json
import logging
import os
import asyncio
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
import threading
from .llm_analysis_process import LLMAnalysisProcess

class LLMAnalysisEndProcessor:
    def __init__(self):
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - Line %(lineno)d - %(message)s')
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load environment variables
        load_dotenv()

        # Initialize Supabase client
        self.SUPABASE_URL = os.getenv('SUPABASE_URL')
        self.SUPABASE_KEY = os.getenv('SUPABASE_KEY')

        if not self.SUPABASE_URL or not self.SUPABASE_KEY:
            self.logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set.")
        self.supabase: Client = create_client(self.SUPABASE_URL, self.SUPABASE_KEY)

        # Configure Gemini API
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            self.logger.error("GEMINI_API_KEY must be set.")
            raise ValueError("GEMINI_API_KEY must be set.")
        
        self.model = None # Initialize model to None
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        except Exception as e:
            self.logger.error(f"Failed to configure Gemini or initialize model: {e}", exc_info=True)
            # self.model remains None

        if not self.model:
             self.logger.error("Failed to initialize Gemini model. LLM functionalities will be unavailable.")
             # Depending on strictness, could raise RuntimeError here.
             # For now, allow instantiation but log error. API calls will fail gracefully.

        # Initialize the analysis process handler
        self.analysis_process = LLMAnalysisProcess(self.model, self.logger)

    async def _process_seo_report(self, report_id: int):
        self.logger.info(f"++++ ENTERING _process_seo_report for ID: {report_id} ++++")
        try:
            db_response = await asyncio.to_thread(
                self.supabase.table('seo_reports')
                .select('id, url, report')
                .eq('id', report_id)
                .single()
                .execute
            )
            if not db_response.data:
                self.logger.error(f"No report found with ID: {report_id}")
                return False
            main_report_url_original = db_response.data.get('url')
            report_json_blob = db_response.data.get('report', {})
            if not main_report_url_original:
                self.logger.error(f"Report with ID {report_id} has no 'url' (main site URL) in DB record.")
                await self._mark_report_as_error(report_id, "Missing main_report_url in DB record.")
                return False
            if not report_json_blob:
                self.logger.error(f"Report with ID {report_id} has no 'report' JSON data in DB record.")
                await self._mark_report_as_error(report_id, "Missing report_json_blob in DB record.")
                return False
            normalized_db_main_url = main_report_url_original.rstrip('/')
            self.logger.info(f"Processing llm_analysis_all for report ID {report_id}, Main Site URL (Original DB): {main_report_url_original}, Normalized: {normalized_db_main_url}")
            page_statistics = report_json_blob.get('page_statistics', {})
            initial_llm_analysis_from_blob = report_json_blob.get('llm_analysis', {})
            llm_analysis_all = {}
            url_from_llm_blob_original = initial_llm_analysis_from_blob.get('url', "")
            normalized_url_from_llm_blob = url_from_llm_blob_original.rstrip('/')
            is_valid_and_matches_main_url = (
                initial_llm_analysis_from_blob and
                initial_llm_analysis_from_blob.get('keywords') is not None and # Check a key field for structure
                normalized_url_from_llm_blob == normalized_db_main_url
            )
            
            if is_valid_and_matches_main_url:
                self.logger.info(f"Using pre-existing 'llm_analysis' from report_json_blob for main page: {normalized_db_main_url} (Report ID: {report_id})")
                llm_analysis_all['main_page'] = {
                    "url": main_report_url_original,
                    "keywords": initial_llm_analysis_from_blob.get("keywords", []),
                    "content_summary": initial_llm_analysis_from_blob.get("content_summary", ""),
                    "other_information_and_contacts": initial_llm_analysis_from_blob.get("other_information_and_contacts", []),
                    "suggested_keywords_for_seo": initial_llm_analysis_from_blob.get("suggested_keywords_for_seo", []),
                    "overall_tone": initial_llm_analysis_from_blob.get("overall_tone", ""),
                    "target_audience": initial_llm_analysis_from_blob.get("target_audience", []),
                    "topic_categories": initial_llm_analysis_from_blob.get("topic_categories", []),
                    "header": initial_llm_analysis_from_blob.get("header", []),
                    "footer": initial_llm_analysis_from_blob.get("footer", [])
                }
                if initial_llm_analysis_from_blob.get("error"):
                     llm_analysis_all['main_page']['error'] = initial_llm_analysis_from_blob.get("error")
                     self.logger.warning(f"Pre-existing 'llm_analysis' for main page {normalized_db_main_url} contains an error field: {llm_analysis_all['main_page']['error']}")
            else:
                error_reason = "Pre-computed LLM analysis for main page was missing, for a different URL, or structurally inadequate."
                if not initial_llm_analysis_from_blob:
                    error_reason = "Pre-computed LLM analysis (llm_analysis field) was not found in report_json_blob."
                elif normalized_url_from_llm_blob != normalized_db_main_url:
                    error_reason = (f"Pre-computed LLM analysis URL ('{url_from_llm_blob_original}') "
                                    f"does not match main report URL ('{main_report_url_original}').")
                self.logger.warning(
                    f"{error_reason} (Report ID: {report_id}). "
                    "Main page LLM data in 'llm_analysis_all' will be an error placeholder. "
                    "It will NOT be re-processed from page_statistics by this processor."
                )
                llm_analysis_all['main_page'] = {
                    "url": main_report_url_original, "error": error_reason,
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                    "suggested_keywords_for_seo": [], "overall_tone": "", "target_audience": [],
                    "topic_categories": [], "header": [], "footer": []
                }
            
            pages_to_analyze_data = []
            subpages_llm_analysis = {} # Store subpage results temporarily
            for page_url_key, page_content_item in page_statistics.items():
                normalized_page_url_key = page_url_key.rstrip('/')
                if normalized_page_url_key == normalized_db_main_url:
                    self.logger.info(f"Skipping page_statistics entry '{page_url_key}' as it matches the main DB URL. (Report ID: {report_id})")
                    continue
                if not page_url_key:
                    self.logger.warning(f"Skipping page_statistics entry with empty/null URL key (Report ID: {report_id})")
                    continue
                if not page_content_item or not (page_content_item.get('cleaned_text') or page_content_item.get('headings')):
                    self.logger.warning(f"Skipping subpage {page_url_key} due to missing content data. (Report ID: {report_id})")
                    subpages_llm_analysis[page_url_key] = {
                        "url": page_url_key, "error": "Content data missing in page_statistics.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "overall_tone": "", "target_audience": [], "topic_categories": []
                    }
                    continue
                pages_to_analyze_data.append((page_url_key, page_content_item))
            
            if not pages_to_analyze_data:
                self.logger.info(f"No additional subpages in page_statistics to analyze for report ID {report_id}.")
            else:
                self.logger.info(f"Found {len(pages_to_analyze_data)} subpages from page_statistics to analyze for report ID {report_id}")
                batch_size = 5; max_retries = 3; delay_between_batches = 2
                
                for i in range(0, len(pages_to_analyze_data), batch_size):
                    batch = pages_to_analyze_data[i:i+batch_size]
                    batch_tasks = []
                    
                    async def analyze_with_retry(p_url, p_data):
                        last_error_result = None
                        for retry_attempt in range(max_retries):
                            analysis_result = await self.analysis_process.analyze_single_page(p_url, p_data, is_main_page=False)
                            last_error_result = analysis_result # Keep track of last result
                            if "error" not in analysis_result or not analysis_result.get("error"):
                                return analysis_result
                            self.logger.warning(f"Error analyzing page {p_url} (attempt {retry_attempt+1}/{max_retries}): {analysis_result.get('error')}")
                            if retry_attempt < max_retries - 1: await asyncio.sleep(1 + retry_attempt)
                        self.logger.error(f"Failed to analyze page {p_url} after {max_retries} attempts. Final error: {last_error_result.get('error') if last_error_result else 'Unknown'}")
                        return last_error_result # Return the result from the last attempt (will contain error)

                    for p_url_item, p_data_item in batch: batch_tasks.append(analyze_with_retry(p_url_item, p_data_item))
                    results_for_batch = await asyncio.gather(*batch_tasks)

                    for result in results_for_batch:
                        if result and result.get("url"): subpages_llm_analysis[result["url"]] = result
                        elif result: self.logger.warning(f"Malformed/URL-less analysis result in batch for report {report_id}: {str(result)[:200]}")
                    
                    self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(pages_to_analyze_data) + batch_size - 1)//batch_size} for report {report_id}")
                    if i + batch_size < len(pages_to_analyze_data): await asyncio.sleep(delay_between_batches)
            
            llm_analysis_all.update(subpages_llm_analysis) # Add processed subpages to the main dict
                        
            self.logger.info(f"Report ID {report_id}: llm_analysis_all contains {len(llm_analysis_all)} entries. Keys: {list(llm_analysis_all.keys())}")
            
            comprehensive_text_report = await self.analysis_process.generate_comprehensive_text_report(llm_analysis_all)
            self.logger.info(f"Report ID {report_id}: Generated comprehensive text report. Length: {len(comprehensive_text_report)} chars.")
            
            current_timestamp_utc = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            update_data = {
                'llm_analysis_all': llm_analysis_all,
                'llm_analysis_all_completed': True,
                'llm_analysis_all_timestamp': current_timestamp_utc,
                'text_report': comprehensive_text_report,
                'llm_analysis_all_error': None
            }
            
            error_messages = []
            if llm_analysis_all.get('main_page', {}).get('error'):
                error_messages.append(f"Main page: {llm_analysis_all['main_page']['error'][:150]}")
            for page_url, page_data in subpages_llm_analysis.items():
                if page_data.get('error'):
                    error_messages.append(f"Subpage ({page_url[:50]}...): {page_data['error'][:100]}")
                    if len(error_messages) > 3: error_messages.append("...and more subpage errors."); break
            
            if error_messages:
                update_data['llm_analysis_all_error'] = "; ".join(error_messages)[:450]
                self.logger.warning(f"Report ID {report_id} has errors in LLM analysis: {update_data['llm_analysis_all_error']}")
            
            self.logger.info(f"Report ID {report_id}: Preparing to update Supabase.")
            update_response = await asyncio.to_thread(
                self.supabase.table('seo_reports').update(update_data).eq('id', report_id).execute
            )
            if hasattr(update_response, 'error') and update_response.error:
                self.logger.error(f"Failed to update report ID {report_id} in Supabase: {update_response.error}")
                await self._mark_report_as_error(report_id, f"Supabase update failed: {str(update_response.error)[:400]}")
                return False
            if hasattr(update_response, 'error') and update_response.error: # Duplicate check, but safe
                self.logger.error(f"Failed to update report ID {report_id} in Supabase: {update_response.error}")
                await self._mark_report_as_error(report_id, f"Supabase update failed: {str(update_response.error)[:400]}")
                return False  

            self.logger.info(f"Successfully processed and updated report ID {report_id}.")
            return True
        except Exception as e:
            self.logger.error(f"Critical error processing report ID {report_id}: {e}", exc_info=True)
            await self._mark_report_as_error(report_id, f"Processor Critical Error: {str(e)[:450]}")
            return False

    async def _mark_report_as_error(self, report_id: int, error_message: str):
        try:
            error_timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            await asyncio.to_thread(
                self.supabase.table('seo_reports').update({
                    'llm_analysis_all_completed': False,
                    'llm_analysis_all_timestamp': error_timestamp,
                    'llm_analysis_all_error': error_message[:500] 
                }).eq('id', report_id).execute
            )
            self.logger.info(f"Marked report ID {report_id} with error: {error_message}")
        except Exception as sup_e:
            self.logger.error(f"Failed to update error status for report {report_id} in Supabase: {sup_e}")

    async def _process_pending_reports(self, limit=10):
        try:
            pending_reports_response = await asyncio.to_thread(
                self.supabase.table('seo_reports')
                    .select('id, url')
                    .filter('llm_analysis_all_completed', 'not.is', 'true')
                    .is_('llm_analysis_all_error', 'null')
                    .not_('report', 'is', 'null')
                    .limit(limit)
                    .order('id', desc=False) 
                    .execute
            )
            if hasattr(pending_reports_response, 'error') and pending_reports_response.error:
                self.logger.error(f"Error fetching pending reports: {pending_reports_response.error}")
                return
            if not pending_reports_response.data:
                self.logger.info("No pending reports found meeting processing criteria.")
                return
            reports_to_process = pending_reports_response.data
            self.logger.info(f"Found {len(reports_to_process)} pending reports to process.")
            for report_summary in reports_to_process:
                report_id = report_summary.get('id')
                report_main_site_url = report_summary.get('url', 'Unknown Site URL')
                if not report_id:
                    self.logger.warning(f"Found a pending report entry with no ID: {report_summary}")
                    continue
                self.logger.info(f"Starting llm_analysis_all processing for report ID {report_id} (Site: {report_main_site_url})")
                success = await self._process_seo_report(report_id)
                if success:
                    self.logger.info(f"Successfully completed llm_analysis_all for report ID {report_id}")
                else:
                    self.logger.error(f"Failed to complete llm_analysis_all for report ID {report_id}. See logs/DB for errors.")
        except Exception as e:
            self.logger.error(f"General error in _process_pending_reports: {e}", exc_info=True)

    def _run_async_wrapper(self, report_ids_str_list):
        try:
            self.logger.info(f"Background thread's event loop started for report IDs: {report_ids_str_list}.")
            asyncio.run(self.run(report_ids=report_ids_str_list, process_pending=False))
            self.logger.info(f"Background thread's event loop completed for report IDs: {report_ids_str_list}.")
            
        except Exception as e:
            self.logger.error(f"Exception in threaded _run_async_wrapper for report_ids {report_ids_str_list}: {e}", exc_info=True)

    def schedule_run_in_background(self, report_ids):
        if not isinstance(report_ids, list): report_ids_list = [report_ids]
        else: report_ids_list = report_ids
        report_ids_str_list = []
        for rid in report_ids_list:
            try: report_ids_str_list.append(str(int(rid)))
            except ValueError: self.logger.warning(f"Invalid report ID '{rid}' for background scheduling. Skipping.")
        if not report_ids_str_list:
            self.logger.warning("No valid report IDs to schedule for background processing.")
            return

        self.logger.info(f"Scheduling LLMAnalysisEndProcessor.run for report IDs {report_ids_str_list} in a background thread.")
        thread = threading.Thread(target=self._run_async_wrapper, args=(report_ids_str_list,))
        thread.daemon = True
        thread.start()
        self.logger.info(f"Background thread for report IDs {report_ids_str_list} has been started.")

    async def run(self, report_ids=None, process_pending=False, batch_size=10):
        if not self.supabase or not self.model:
            self.logger.error("Processor not fully initialized. Aborting run.")
            return

        if report_ids:
            if not isinstance(report_ids, list): report_ids = [report_ids]
            valid_ids_to_process = []
            for rid_input in report_ids:
                try: valid_ids_to_process.append(int(rid_input))
                except ValueError: self.logger.warning(f"Invalid report_id format: '{rid_input}'. Skipping.")
            
            if not valid_ids_to_process: self.logger.info("No valid report IDs provided.")
            else:
                self.logger.info(f"Processing specific report IDs: {valid_ids_to_process}")
                for pid in valid_ids_to_process:
                    try: await self._process_seo_report(pid)
                    except Exception as e:
                        self.logger.error(f"Error processing report_id '{pid}': {e}", exc_info=True)
                        await self._mark_report_as_error(pid, f"Outer run error: {str(e)[:450]}")
        elif process_pending:
            self.logger.info(f"Processing pending reports, batch limit: {batch_size}")
            await self._process_pending_reports(limit=batch_size)
        else:
            self.logger.info(f"LLMAnalysisEndProcessor.run called with no specific actions requested.")
        
        self.logger.info(f"LLMAnalysisEndProcessor run method finished operation.")

if __name__ == '__main__':
    async def main_test_runner():
        logging.basicConfig(
            level=logging.DEBUG, 
            format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - Line %(lineno)d - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        logger = logging.getLogger("LLMAnalysisEndProcessor_StandaloneTest")
        logger.info("Starting standalone test run...")
        
        processor = None
        try:
            processor = LLMAnalysisEndProcessor()
            
            # Test processing specific report IDs (replace with valid IDs from your DB)
            # await processor.run(report_ids=[278, "invalid_id", 279]) 
            
            # Test processing pending reports
            await processor.run(process_pending=True, batch_size=2)

            # Test scheduling in background (main_test_runner might finish before thread does)
            # processor.schedule_run_in_background(report_ids=[280])
            # logger.info("Scheduled background processing. Main test might exit before completion.")
            # await asyncio.sleep(20) # Give some time for thread to work

            logger.info("Standalone test run operations initiated.")
        except ValueError as ve_init:
            logger.error(f"LLMAnalysisEndProcessor initialization failed: {ve_init}", exc_info=True)
        except Exception as e:
            logger.error(f"Error during standalone test run: {e}", exc_info=True)
        finally:
             if processor:
                 logger.info("Processor instance existed.")
    
    asyncio.run(main_test_runner())