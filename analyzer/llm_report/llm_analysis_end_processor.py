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

# It's good practice to also import any client libraries for Mistral if you use them directly
# e.g., from mistralai.client import MistralClient
# For this example, Mistral calls will be encapsulated in LLMAnalysisProcess, potentially using httpx.


class LLMAnalysisEndProcessor:
    # MODIFIED: Added language_code to __init__ and store it
    def __init__(self, language_code="en"):
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - Line %(lineno)d - %(message)s')
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # MODIFIED: Store language_code
        self.language_code = language_code
        self.logger.info(f"LLMAnalysisEndProcessor initialized with language_code: '{self.language_code}'")


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
        self.model = None # Initialize model to None
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                # Updated model name as per common usage, adjust if needed
                self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
                self.logger.info(f"Gemini model initialized ('{self.model.model_name}').")
            except Exception as e:
                self.logger.error(f"Failed to configure Gemini or initialize model: {e}", exc_info=True)
                self.model = None # Ensure model is None on failure
        else:
            self.logger.warning("GEMINI_API_KEY not set. Gemini functionalities will be unavailable unless Mistral is primary.")

        # Configure Mistral API
        self.mistral_api_key = os.getenv('MISTRAL_API_KEY')
        self.mistral_model_name = os.getenv('MISTRAL_MODEL_NAME', 'mistral-small-latest') # Default if not set

        if self.mistral_api_key:
            self.logger.info(f"Mistral API key found. Mistral model '{self.mistral_model_name}' can be used.")
        else:
            self.logger.warning("MISTRAL_API_KEY not set. Mistral fallback/functionalities will be unavailable.")

        if not self.model and not self.mistral_api_key:
             self.logger.error("Neither Gemini nor Mistral API keys are configured. LLM functionalities will be unavailable.")
             raise ValueError("At least one LLM (Gemini or Mistral) API key must be set.")
        elif not self.model:
             self.logger.warning("Gemini model failed to initialize or key not set. Will rely on Mistral if configured.")

        # Initialize the analysis process handler
        self.analysis_process = LLMAnalysisProcess(
            gemini_model=self.model,
            mistral_api_key=self.mistral_api_key,
            mistral_model_name=self.mistral_model_name,
            logger=self.logger
        )

    def _extract_technical_statistics(self, report_json_blob: dict) -> dict:
        """Extract technical statistics from the report JSON blob."""
        technical_stats = {}

        # Extract technical metrics with safe fallbacks
        technical_stats['robots_txt_found'] = report_json_blob.get('robots_txt_found', False)
        technical_stats['total_images_count'] = report_json_blob.get('total_images_count', 0)
        technical_stats['total_headings_count'] = report_json_blob.get('total_headings_count', 0)
        technical_stats['analysis_duration_seconds'] = report_json_blob.get('analysis_duration_seconds', 0)
        technical_stats['crawled_internal_pages_count'] = report_json_blob.get('crawled_internal_pages_count', 0)
        technical_stats['total_cleaned_content_length'] = report_json_blob.get('total_cleaned_content_length', 0)
        technical_stats['total_missing_alt_tags_count'] = report_json_blob.get('total_missing_alt_tags_count', 0)
        technical_stats['pages_with_mobile_viewport_count'] = report_json_blob.get('pages_with_mobile_viewport_count', 0)
        technical_stats['average_cleaned_content_length_per_page'] = report_json_blob.get('average_cleaned_content_length_per_page', 0)

        # Additional computed metrics
        if technical_stats['total_images_count'] > 0 and technical_stats['total_missing_alt_tags_count'] >= 0:
            # Ensure missing alt tags don't exceed total images
            actual_missing_alt_tags = min(technical_stats['total_missing_alt_tags_count'], technical_stats['total_images_count'])
            alt_text_coverage = ((technical_stats['total_images_count'] - actual_missing_alt_tags) / technical_stats['total_images_count']) * 100
            technical_stats['alt_text_coverage_percentage'] = round(alt_text_coverage, 1)
        else:
            technical_stats['alt_text_coverage_percentage'] = 100 if technical_stats['total_images_count'] == 0 else 0

        if technical_stats['crawled_internal_pages_count'] > 0 and technical_stats['pages_with_mobile_viewport_count'] >= 0:
             # Ensure pages with viewport don't exceed crawled pages
            actual_mobile_pages = min(technical_stats['pages_with_mobile_viewport_count'], technical_stats['crawled_internal_pages_count'])
            mobile_optimization_percentage = (actual_mobile_pages / technical_stats['crawled_internal_pages_count']) * 100
            technical_stats['mobile_optimization_percentage'] = round(mobile_optimization_percentage, 1)
        else:
            technical_stats['mobile_optimization_percentage'] = 100 if technical_stats['crawled_internal_pages_count'] == 0 else 0

        self.logger.info(f"Extracted technical statistics: {technical_stats}")
        return technical_stats

    async def _process_seo_report(self, report_id: int):
        self.logger.info(f"++++ ENTERING _process_seo_report for ID: {report_id} with language_code: '{self.language_code}' ++++")
        try:
            # Use asyncio.to_thread for synchronous Supabase calls
            db_response_task = asyncio.to_thread(
                self.supabase.table('seo_reports')
                .select('id, url, report')
                .eq('id', report_id)
                .single()
                .execute
            )
            db_response = await db_response_task

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

            # Extract technical statistics
            technical_stats = self._extract_technical_statistics(report_json_blob)

            normalized_db_main_url = main_report_url_original.rstrip('/')
            self.logger.info(f"Processing llm_analysis_all for report ID {report_id}, Main Site URL (Original DB): {main_report_url_original}, Normalized: {normalized_db_main_url}")
            page_statistics = report_json_blob.get('page_statistics', {})
            initial_llm_analysis_from_blob = report_json_blob.get('llm_analysis', {}) # This is for the main page only
            llm_analysis_all = {}

            # Add technical statistics to the main structure
            llm_analysis_all['technical_statistics'] = technical_stats

            url_from_llm_blob_original = initial_llm_analysis_from_blob.get('url', "")
            normalized_url_from_llm_blob = url_from_llm_blob_original.rstrip('/')

            # Check if initial_llm_analysis_from_blob is valid and for the correct main URL
            is_valid_and_matches_main_url = (
                initial_llm_analysis_from_blob and # Check it's not empty
                initial_llm_analysis_from_blob.get('keywords') is not None and # Check a key field for structure
                normalized_url_from_llm_blob == normalized_db_main_url # Check URL match
            )

            if is_valid_and_matches_main_url:
                self.logger.info(f"Using pre-existing 'llm_analysis' from report_json_blob for main page: {normalized_db_main_url} (Report ID: {report_id})")
                # Populate 'main_page' with all expected fields from the pre-existing analysis
                llm_analysis_all['main_page'] = {
                    "url": main_report_url_original, # Use the original URL from DB record
                    "keywords": initial_llm_analysis_from_blob.get("keywords", []),
                    "content_summary": initial_llm_analysis_from_blob.get("content_summary", ""),
                    "other_information_and_contacts": initial_llm_analysis_from_blob.get("other_information_and_contacts", []),
                    "suggested_keywords_for_seo": initial_llm_analysis_from_blob.get("suggested_keywords_for_seo", []),
                    "overall_tone": initial_llm_analysis_from_blob.get("overall_tone", ""),
                    "target_audience": initial_llm_analysis_from_blob.get("target_audience", []),
                    "topic_categories": initial_llm_analysis_from_blob.get("topic_categories", []),
                    "header": initial_llm_analysis_from_blob.get("header", []), # Main page specific
                    "footer": initial_llm_analysis_from_blob.get("footer", []), # Main page specific
                    "llm_provider": initial_llm_analysis_from_blob.get("llm_provider", "Pre-computed in crawler") # Track provider
                }
                if initial_llm_analysis_from_blob.get("error"):
                     llm_analysis_all['main_page']['error'] = initial_llm_analysis_from_blob.get("error")
                     self.logger.warning(f"Pre-existing 'llm_analysis' for main page {normalized_db_main_url} contains an error field: {llm_analysis_all['main_page']['error']}")

            else:
                # Determine specific reason for not using pre-existing data
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
                # Create a placeholder error entry for the main page
                llm_analysis_all['main_page'] = {
                    "url": main_report_url_original, "error": error_reason,
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                    "suggested_keywords_for_seo": [], "overall_tone": "", "target_audience": [],
                    "topic_categories": [], "header": [], "footer": [], "llm_provider": "N/A"
                }

            # Process subpages from page_statistics
            pages_to_analyze_data = []
            subpages_llm_analysis = {} # Store subpage results temporarily

            for page_url_key, page_content_item in page_statistics.items():
                normalized_page_url_key = page_url_key.rstrip('/')
                # Skip if this page_statistics entry is for the main URL (already handled or error-marked)
                if normalized_page_url_key == normalized_db_main_url:
                    self.logger.info(f"Skipping page_statistics entry '{page_url_key}' as it matches the main DB URL. (Report ID: {report_id})")
                    continue

                if not page_url_key: # Should ideally not happen if keys are URLs
                    self.logger.warning(f"Skipping page_statistics entry with empty/null URL key (Report ID: {report_id})")
                    continue

                # Ensure page_content_item has necessary data for analysis
                if not page_content_item or not (page_content_item.get('cleaned_text') or page_content_item.get('headings')):
                    self.logger.warning(f"Skipping subpage {page_url_key} due to missing content data. (Report ID: {report_id})")
                    subpages_llm_analysis[page_url_key] = {
                        "url": page_url_key, "error": "Content data missing in page_statistics.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                        "suggested_keywords_for_seo": [], "overall_tone": "", "target_audience": [], "topic_categories": [], "llm_provider": "N/A"
                    }
                    continue

                pages_to_analyze_data.append((page_url_key, page_content_item))

            if not pages_to_analyze_data:
                self.logger.info(f"No additional subpages in page_statistics to analyze for report ID {report_id}.")
            else:
                self.logger.info(f"Found {len(pages_to_analyze_data)} subpages from page_statistics to analyze for report ID {report_id}")
                # Batch processing for subpages
                batch_size = 5; max_retries = 3; delay_between_batches = 2 # Configurable

                for i in range(0, len(pages_to_analyze_data), batch_size):
                    batch = pages_to_analyze_data[i:i+batch_size]
                    batch_tasks = []

                    # Define an async wrapper for retry logic
                    async def analyze_with_retry(p_url, p_data):
                        last_error_result = None
                        for retry_attempt in range(max_retries):
                            # Call analyze_single_page from self.analysis_process
                            # Mark as not main page (is_main_page=False)
                            # If analyze_single_page needs language_code, it should be passed here:
                            # e.g., await self.analysis_process.analyze_single_page(p_url, p_data, is_main_page=False, language_code=self.language_code)
                            analysis_result = await self.analysis_process.analyze_single_page(p_url, p_data, is_main_page=False)
                            last_error_result = analysis_result # Keep track of last result

                            if "error" not in analysis_result or not analysis_result.get("error"):
                                return analysis_result # Success

                            self.logger.warning(f"Error analyzing page {p_url} (attempt {retry_attempt+1}/{max_retries}): {analysis_result.get('error')}")
                            if retry_attempt < max_retries - 1:
                                await asyncio.sleep(1 + retry_attempt) # Exponential backoff-like delay

                        self.logger.error(f"Failed to analyze page {p_url} after {max_retries} attempts. Final error: {last_error_result.get('error') if last_error_result else 'Unknown'}")
                        return last_error_result # Return the result from the last attempt (will contain error)

                    for p_url_item, p_data_item in batch:
                        batch_tasks.append(analyze_with_retry(p_url_item, p_data_item))

                    results_for_batch = await asyncio.gather(*batch_tasks)

                    for result in results_for_batch:
                        if result and result.get("url"): # Ensure result has a URL to use as key
                            subpages_llm_analysis[result["url"]] = result
                        elif result: # Log if result is malformed
                            self.logger.warning(f"Malformed/URL-less analysis result in batch for report {report_id}: {str(result)[:200]}")

                    self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(pages_to_analyze_data) + batch_size - 1)//batch_size} for report {report_id}")
                    if i + batch_size < len(pages_to_analyze_data):
                        await asyncio.sleep(delay_between_batches)

            # Add processed subpages to the main llm_analysis_all dictionary
            llm_analysis_all.update(subpages_llm_analysis)

            self.logger.info(f"Report ID {report_id}: llm_analysis_all contains {len(llm_analysis_all)} entries. Keys: {list(llm_analysis_all.keys())}")

            # Generate comprehensive text report (includes AI recommendations if models available)
            # MODIFIED: Pass self.language_code
            comprehensive_text_report = await self.analysis_process.generate_comprehensive_text_report(
                llm_analysis_all,
                language_code=self.language_code
            )
            self.logger.info(f"Report ID {report_id}: Generated comprehensive text report with language '{self.language_code}'. Length: {len(comprehensive_text_report)} chars.")

            current_timestamp_utc = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            update_data = {
                'llm_analysis_all': llm_analysis_all,
                'llm_analysis_all_completed': True,
                'llm_analysis_all_timestamp': current_timestamp_utc,
                'text_report': comprehensive_text_report,
                'llm_analysis_all_error': None # Clear any previous error if successful
            }

            # Aggregate error messages if any page analysis failed
            error_messages = []
            if llm_analysis_all.get('main_page', {}).get('error'):
                error_messages.append(f"Main page: {llm_analysis_all['main_page']['error'][:150]}")

            for page_url, page_data in subpages_llm_analysis.items(): # Iterate through newly analyzed subpages
                if page_data.get('error'):
                    error_messages.append(f"Subpage ({page_url[:50]}...): {page_data['error'][:100]}")
                    if len(error_messages) > 3: # Limit number of error messages shown
                        error_messages.append("...and more subpage errors.")
                        break

            if error_messages:
                update_data['llm_analysis_all_error'] = "; ".join(error_messages)[:450] # Store truncated error summary
                self.logger.warning(f"Report ID {report_id} has errors in LLM analysis: {update_data['llm_analysis_all_error']}")

            self.logger.info(f"Report ID {report_id}: Preparing to update Supabase.")
            # Update Supabase in a thread
            update_response_task = asyncio.to_thread(
                self.supabase.table('seo_reports').update(update_data).eq('id', report_id).execute
            )
            update_response = await update_response_task

            if hasattr(update_response, 'error') and update_response.error: # Check for Supabase error
                self.logger.error(f"Failed to update report ID {report_id} in Supabase: {update_response.error}")
                # Mark report as error if Supabase update fails, to prevent re-processing a failed DB write
                await self._mark_report_as_error(report_id, f"Supabase update failed: {str(update_response.error)[:400]}")
                return False  # Indicate failure

            self.logger.info(f"Successfully processed and updated report ID {report_id}.")
            return True
        except Exception as e:
            self.logger.error(f"Critical error processing report ID {report_id}: {e}", exc_info=True)
            await self._mark_report_as_error(report_id, f"Processor Critical Error: {str(e)[:450]}")
            return False

    async def _mark_report_as_error(self, report_id: int, error_message: str):
        try:
            error_timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            # Use asyncio.to_thread for synchronous Supabase calls
            await asyncio.to_thread(
                self.supabase.table('seo_reports').update({
                    'llm_analysis_all_completed': False, # Explicitly set to false on error
                    'llm_analysis_all_timestamp': error_timestamp,
                    'llm_analysis_all_error': error_message[:500] # Ensure error message is truncated
                }).eq('id', report_id).execute
            )
            self.logger.info(f"Marked report ID {report_id} with error: {error_message}")
        except Exception as sup_e:
            self.logger.error(f"Failed to update error status for report {report_id} in Supabase: {sup_e}")

    async def _process_pending_reports(self, limit=10):
        try:
            # Use asyncio.to_thread for synchronous Supabase calls
            pending_reports_response_task = asyncio.to_thread(
                self.supabase.table('seo_reports')
                    .select('id, url') # Select only necessary fields
                    .filter('llm_analysis_all_completed', 'not.is', 'true') # Reports not yet completed
                    .is_('llm_analysis_all_error', 'null') # Reports not already marked with an error from this processor
                    .not_('report', 'is', 'null') # Ensure 'report' blob exists
                    .limit(limit)
                    .order('id', desc=False) # Process older reports first
                    .execute
            )
            pending_reports_response = await pending_reports_response_task

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
                report_main_site_url = report_summary.get('url', 'Unknown Site URL') # For logging

                if not report_id:
                    self.logger.warning(f"Found a pending report entry with no ID: {report_summary}")
                    continue

                self.logger.info(f"Starting llm_analysis_all processing for report ID {report_id} (Site: {report_main_site_url}) with language '{self.language_code}'")
                success = await self._process_seo_report(report_id)
                if success:
                    self.logger.info(f"Successfully completed llm_analysis_all for report ID {report_id}")
                else:
                    # Error logging is handled within _process_seo_report and _mark_report_as_error
                    self.logger.error(f"Failed to complete llm_analysis_all for report ID {report_id}. See logs/DB for errors.")

        except Exception as e:
            self.logger.error(f"General error in _process_pending_reports: {e}", exc_info=True)

    # MODIFIED: Pass language_code to _run_async_wrapper (parameter removed from definition)
    def _run_async_wrapper(self, report_ids_str_list):
        # This wrapper allows running the async `run` method in a separate thread's event loop
        try:
            # self.language_code is already set correctly because 'self' is 'processor_for_thread'
            self.logger.info(f"Background thread's event loop started for report IDs: {report_ids_str_list} with language_code: '{self.language_code}'.")
            asyncio.run(self.run(report_ids=report_ids_str_list, process_pending=False)) # self.run() will use self.language_code internally
            self.logger.info(f"Background thread's event loop completed for report IDs: {report_ids_str_list}.")

        except Exception as e:
            # Catch all exceptions to prevent thread from dying silently
            self.logger.error(f"Exception in threaded _run_async_wrapper for report_ids {report_ids_str_list}: {e}", exc_info=True)

    # MODIFIED: Accept language_code and pass it when creating the thread's target's args (args to thread target simplified)
    def schedule_run_in_background(self, report_ids, language_code="en"):
        """Schedules the `run` method to execute in a new background thread."""
        if not isinstance(report_ids, list):
            report_ids_list = [report_ids]
        else:
            report_ids_list = report_ids

        report_ids_str_list = []
        for rid in report_ids_list:
            try:
                report_ids_str_list.append(str(int(rid))) # Validate and convert to string
            except ValueError:
                self.logger.warning(f"Invalid report ID '{rid}' for background scheduling. Skipping.")

        if not report_ids_str_list:
            self.logger.warning("No valid report IDs to schedule for background processing.")
            return

        # Important: Create a new processor instance for THIS thread, initialized with the correct language.
        # The 'self' passed to _run_async_wrapper will be this new instance.
        processor_for_thread = LLMAnalysisEndProcessor(language_code=language_code)
        self.logger.info(f"Scheduling LLMAnalysisEndProcessor.run for report IDs {report_ids_str_list} in a background thread with language_code: '{language_code}'.")

        # Pass the specific processor instance to the thread; _run_async_wrapper uses self.language_code
        thread = threading.Thread(target=processor_for_thread._run_async_wrapper, args=(report_ids_str_list,))
        thread.daemon = True # Daemon threads exit when the main program exits
        thread.start()
        self.logger.info(f"Background thread for report IDs {report_ids_str_list} has been started.")


    async def run(self, report_ids=None, process_pending=False, batch_size=10):
        """
        Main entry point to run the processor.
        Can process specific report IDs or pending reports.
        """
        self.logger.info(f"LLMAnalysisEndProcessor.run called with language_code: '{self.language_code}'")
        if not self.supabase: # Check Supabase client
            self.logger.error("Supabase client not initialized. Aborting run.")
            return
        if not self.model and not self.mistral_api_key: # Check LLM availability
            self.logger.error("Neither Gemini nor Mistral is configured. LLM processing will be unavailable. Aborting run.")
            return

        if report_ids:
            if not isinstance(report_ids, list):
                report_ids = [report_ids] # Ensure it's a list

            valid_ids_to_process = []
            for rid_input in report_ids:
                try:
                    valid_ids_to_process.append(int(rid_input)) # Validate and convert to int
                except ValueError:
                    self.logger.warning(f"Invalid report_id format: '{rid_input}'. Skipping.")

            if not valid_ids_to_process:
                self.logger.info("No valid report IDs provided for specific processing.")
            else:
                self.logger.info(f"Processing specific report IDs: {valid_ids_to_process} with language '{self.language_code}'")
                for pid in valid_ids_to_process:
                    try:
                        await self._process_seo_report(pid) # self.language_code will be used internally
                    except Exception as e: # Catch errors at this level too
                        self.logger.error(f"Error processing report_id '{pid}': {e}", exc_info=True)
                        await self._mark_report_as_error(pid, f"Outer run error: {str(e)[:450]}")

        elif process_pending: # process_pending is True and no specific report_ids given
            self.logger.info(f"Processing pending reports, batch limit: {batch_size} with language '{self.language_code}'")
            await self._process_pending_reports(limit=batch_size) # self.language_code will be used internally

        else: # No specific report_ids and process_pending is False
            self.logger.info(f"LLMAnalysisEndProcessor.run called with no specific actions requested (no report_ids, process_pending=False). Language: '{self.language_code}'")

        self.logger.info(f"LLMAnalysisEndProcessor run method finished operation.")

# Example usage (for testing purposes)
if __name__ == '__main__':
    async def main_test_runner():
        # Setup enhanced logging for standalone test
        logging.basicConfig(
            level=logging.DEBUG, # More verbose for testing
            format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - Line %(lineno)d - %(message)s',
            handlers=[logging.StreamHandler()] # Log to console
        )
        logger = logging.getLogger("LLMAnalysisEndProcessor_StandaloneTest")
        logger.info("Starting standalone test run...")

        processor = None
        try:
            # Test with a specific language
            test_language = "tr" # or "en"
            logger.info(f"Testing with language_code: '{test_language}'")
            processor = LLMAnalysisEndProcessor(language_code=test_language)

            # Example: Test processing specific report IDs (replace with valid IDs from your DB)
            # Make sure these reports exist and meet criteria (e.g., 'report' blob exists, not completed, no error)
            # await processor.run(report_ids=[123]) # Replace 123 with a valid ID

            # Example: Test processing pending reports
            # This will fetch reports based on criteria defined in _process_pending_reports
            await processor.run(process_pending=True, batch_size=1) # Small batch for testing

            # Example: Test scheduling in background
            # processor.schedule_run_in_background(report_ids=[124], language_code=test_language) # Replace 124
            # logger.info("Scheduled background processing. Main test might exit before completion.")
            # await asyncio.sleep(30) # Give some time for thread to work if testing this

            logger.info("Standalone test run operations initiated/completed.")
        except ValueError as ve_init: # Catch initialization errors specifically
            logger.error(f"LLMAnalysisEndProcessor initialization failed: {ve_init}", exc_info=True)
        except Exception as e:
            logger.error(f"Error during standalone test run: {e}", exc_info=True)
        finally:
             if processor: # Optional: log if processor instance was created
                 logger.info("Processor instance existed during test.")

    # Run the async main_test_runner
    asyncio.run(main_test_runner())