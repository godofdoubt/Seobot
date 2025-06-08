# analyzer/llm_analysis_process.py
import json
import asyncio
import time
import httpx # For Mistral API calls
#import streamlit as st # For language selection (though direct use in background thread is problematic)
from .llm_analysis_process_prompts import LLMAnalysisPrompts # Import the prompts class for single page
from .generate_ai_recommendations import generate_ai_recommendations_content # Import the new function

# Assuming Seobot is the root package and utils is a sibling directory to analyzer
# Adjust the import path according to your project structure.
# Example: from ..utils.language_support import language_manager
# If analyzer and utils are top-level under Seobot: from Seobot.utils.language_support import language_manager
# For this example, assuming a structure like:
# project_root/
#   Seobot/
#     analyzer/
#       llm_analysis_process.py
#     utils/
#       language_support.py
#       keys_en.py
#       keys_tr.py
from utils.language_support import language_manager

class LLMAnalysisProcess:
    def __init__(self, gemini_model, logger, mistral_api_key=None, mistral_model_name=None):
        self.gemini_model = gemini_model
        self.logger = logger
        self.mistral_api_key = mistral_api_key
        self.mistral_model_name = mistral_model_name

    def _get_localized_titles(self, language_code: str) -> dict:
        self.logger.info(f"LLMAnalysisProcess._get_localized_titles: Requested language_code: '{language_code}'")
        
        # These are the internal keys used by this class's methods when accessing the 'titles' dictionary.
        # They correspond to the keys in the original titles_en/titles_tr dictionaries.
        internal_report_keys = [
            "main_title", "generated_at", "technical_overview", "website_analysis_summary",
            "total_pages_crawled", "analysis_duration", "minutes_label", "seconds_label",
            "content_metrics", "total_content_analyzed", "characters_label",
            "average_content_per_page", "total_headings_found", "image_optimization",
            "total_images_found", "images_missing_alt_text", "alt_text_coverage", "status",
            "excellent", "good", "needs_improvement", "critical", "no_images_found",
            "mobile_friendliness", "pages_with_mobile_viewport", "mobile_optimization_coverage",
            "basic_technical_setup", "robots_txt_file", "found", "not_found", "recommendation",
            "robots_txt_recommendation", "main_page_analysis", "url_not_found_in_data",
            "via_llm_provider", "note", "main_page_analysis_error", "overall_content_tone",
            "identified_target_audience", "main_topic_categories", "content_summary",
            "primary_keywords_identified", "suggested_seo_keywords", "contact_info_key_mentions",
            "no_contacts_identified", "key_header_elements", "no_header_elements_identified",
            "key_footer_elements", "no_footer_elements_identified", "main_page_data_missing",
            "subpage_analysis_overview", "num_additional_pages_analyzed",
            "highlights_individual_subpages", "page", "subpage_analysis_error", "summary_prefix",
            "tone_prefix", "audience_prefix", "topics_prefix",
            "common_keywords_subpages_title_format", "mentioned_in_subpages_format",
            "frequently_suggested_seo_keywords_subpages_title_format",
            "common_topic_categories_subpages_title_format",
            "common_target_audiences_subpages_title_format",
            "common_content_tones_subpages_title_format", "ai_powered_strategic_insights",
            "no_ai_recommendations", "error_generating_ai_recommendations",
            "no_ai_recommendations_configured", "performance_monitoring_next_steps",
            "next_steps_1", "next_steps_2", "next_steps_3", "next_steps_4", "next_steps_5",
            "end_of_report", 
            "raw_report_data_label", # This key was in the original titles_en
            "raw_report_help"      # This key was in the original titles_en
        ]

        localized_titles = {}
        for internal_key in internal_report_keys:
            # Determine the global translation key name
            # Most will be prefixed with "report_", but some existing keys are used directly.
            if internal_key == "raw_report_data_label":
                global_key = "raw_report_data_label" # Uses existing key from keys_en.py
            elif internal_key == "raw_report_help":
                global_key = "raw_report_help"       # Uses existing key from keys_en.py
            elif internal_key == "found":
                global_key = "report_found"          # Use "report_found" for clarity
            elif internal_key == "not_found":
                global_key = "report_not_found"      # Use "report_not_found"
            else:
                global_key = f"report_{internal_key}"
            
            localized_titles[internal_key] = language_manager.get_text(global_key, lang=language_code)
        
        self.logger.info(f"LLMAnalysisProcess._get_localized_titles: Loaded titles for language_code '{language_code}'. Example for 'main_title': {localized_titles.get('main_title', 'NOT_FOUND')}")
        return localized_titles

    # ... _call_gemini_api, _call_mistral_api, analyze_single_page ...
    # (These methods remain unchanged unless they directly used the old titles_en/tr dicts,
    # which they didn't. They use the `titles` dict returned by `_get_localized_titles`
    # or direct string literals that are not part of this refactoring.)

    async def _call_gemini_api(self, prompt_text: str) -> str:
        if not self.gemini_model:
            self.logger.error("Gemini model not initialized. Cannot make API call.")
            return ""
        try:
            # Use asyncio.to_thread for the blocking SDK call
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt_text,
                generation_config={ # Ensure this matches your model's capabilities
                    "temperature": 0.2, # Adjust as needed
                    "response_mime_type": "application/json",
                }
            )
            # Process response: Gemini API might return response in 'text' or 'parts'
            if response and hasattr(response, 'text') and response.text:
                return response.text
            elif response and hasattr(response, 'parts') and response.parts:
                # Concatenate text from all parts if content is chunked
                all_text_parts = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                if all_text_parts:
                    return all_text_parts

            # Log if prompt feedback indicates issues (e.g., safety blocks)
            if response and hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                self.logger.warning(f"Gemini API call for prompt resulted in feedback: {response.prompt_feedback}")

            self.logger.warning(f"LLM response (Gemini) was empty or did not contain text. Full response object: {response}")
            return ""
        except Exception as e:
            # Specific error handling for API key issues
            if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
                self.logger.error(f"Gemini API Permission Denied or Invalid API Key: {e}")
            else:
                self.logger.error(f"Error during Gemini API call: {e}", exc_info=True)
            return ""

    async def _call_mistral_api(self, prompt_text: str, purpose: str) -> tuple[str | None, str | None]:
        """
        Calls the Mistral API using httpx.
        Returns (response_text, error_message string or None if success).
        'purpose' is for logging.
        """
        if not self.mistral_api_key:
            return None, "Mistral API key not configured."
        if not self.mistral_model_name:
            return None, "Mistral model name not configured."

        self.logger.debug(f"Attempting Mistral API call ({self.mistral_model_name}) for {purpose} (prompt {len(prompt_text)} chars)")
        api_url = "https://api.mistral.ai/v1/chat/completions" # Standard endpoint
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json", # Important for ensuring JSON response
        }
        # Payload structure for Mistral chat completions
        payload = {
            "model": self.mistral_model_name,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.7, # Adjust as desired
            # "response_format": {"type": "json_object"}, # Enable if Mistral model supports constrained JSON output
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client: # Increased timeout
                api_response = await client.post(api_url, headers=headers, json=payload)
                api_response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

            data = api_response.json()
            # Check response structure for Mistral
            if data.get("choices") and data["choices"][0].get("message") and data["choices"][0]["message"].get("content"):
                response_text = data["choices"][0]["message"]["content"]
                if not response_text.strip(): # Check if content is just whitespace
                    self.logger.warning(f"Mistral API for {purpose} returned blank content after stripping.")
                    return None, "Mistral LLM returned blank content."
                self.logger.debug(f"Mistral API call for {purpose} successful.")
                return response_text, None
            else:
                self.logger.warning(f"Mistral API call for {purpose} returned unexpected JSON structure or no content: {data}")
                return None, "Mistral LLM returned malformed/empty response."
        except httpx.HTTPStatusError as e:
            err_text = e.response.text[:200] if e.response else "No response body"
            self.logger.error(f"HTTP Error calling Mistral API for {purpose}: {e.response.status_code if e.response else 'N/A'} - {err_text}")
            return None, f"Mistral API HTTP error {e.response.status_code if e.response else 'N/A'}: {err_text}"
        except Exception as e:
            self.logger.error(f"Error calling Mistral API for {purpose}: {e}", exc_info=True)
            return None, f"Mistral API error: {str(e)}"

    async def analyze_single_page(self, page_url: str, page_data: dict, is_main_page: bool = False) -> dict:
        # Initialize base result dictionary
        base_result = {
            "url": page_url,
            "keywords": [],
            "content_summary": "",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "overall_tone": "",
            "target_audience": [],
            "topic_categories": [],
            "llm_provider": "N/A" # Track which LLM provided the data
        }
        if is_main_page: # Add header/footer fields for main page
            base_result.update({"header": [], "footer": []})

        # Validate input page_data
        if not page_data:
            self.logger.warning(f"No page data provided for URL: {page_url}")
            return {**base_result, "error": "No page data available for analysis."}

        cleaned_text = page_data.get('cleaned_text', '')
        headings_data = page_data.get('headings', {})

        if not cleaned_text and not headings_data: # Check if there's any content to analyze
            self.logger.warning(f"No cleaned_text or headings_data found for URL {page_url}. LLM analysis might be ineffective.")
            return {**base_result, "error": "No content (cleaned_text or headings) available for analysis."}

        # Truncate cleaned_text to manage prompt size (adjust limit as needed)
        max_text_len = 22000 # Example limit, ensure it's reasonable for your LLM
        truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')

        # Use LLMAnalysisPrompts to build the prompt for single page analysis
        prompt = LLMAnalysisPrompts.build_single_page_analysis_prompt(
            page_url=page_url,
            truncated_cleaned_text=truncated_cleaned_text,
            headings_data=headings_data,
            is_main_page=is_main_page
        )

        llm_response_str = None
        llm_provider = "N/A" # Default
        error_message_for_return = "LLM analysis failed for both primary and fallback providers."

        try:
            # Attempt 1: Gemini (if available)
            if self.gemini_model:
                self.logger.debug(f"Attempting LLM analysis with Gemini for URL: {page_url} (Main page: {is_main_page})")
                llm_response_str = await self._call_gemini_api(prompt)
                llm_provider = "Gemini"

            # Attempt 2: Mistral (if Gemini failed or not available, and Mistral is configured)
            if not llm_response_str: # If Gemini call failed or returned empty
                if self.gemini_model: # Log Gemini failure before trying Mistral
                    self.logger.warning(f"Gemini returned empty or no-text response for URL: {page_url}. Attempting Mistral fallback.")
                else: # Gemini was not even configured
                    self.logger.info(f"Gemini not configured. Attempting analysis with Mistral for URL: {page_url}.")

                if self.mistral_api_key and self.mistral_model_name:
                    mistral_response, mistral_error = await self._call_mistral_api(prompt, purpose=f"analyze_single_page_fallback_for_{page_url}")
                    if mistral_error:
                        self.logger.error(f"Mistral fallback for {page_url} also failed: {mistral_error}")
                        error_message_for_return = f"Gemini primary failed/not configured; Mistral fallback failed: {mistral_error}"
                    elif mistral_response:
                        llm_response_str = mistral_response
                        llm_provider = "Mistral (fallback)"
                        self.logger.info(f"Successfully used Mistral as fallback for LLM analysis for URL: {page_url}")
                    else: # Mistral returned empty response without explicit error
                        self.logger.error(f"Mistral fallback for {page_url} returned empty response without explicit error.")
                        error_message_for_return = "Gemini primary failed/not configured; Mistral fallback returned empty."
                else:
                    # Mistral not configured, and primary (Gemini) already failed or wasn't configured
                    self.logger.warning(f"LLM (Gemini) failed or not configured, and Mistral is not configured. Cannot analyze URL: {page_url}")
                    error_message_for_return = "Primary LLM (Gemini) failed or not configured; Mistral fallback not configured."

            # If after all attempts, llm_response_str is still None or empty
            if not llm_response_str:
                self.logger.error(f"All LLM attempts failed for URL: {page_url}. Final error state: {error_message_for_return}")
                return {**base_result, "error": error_message_for_return, "llm_provider": llm_provider}

            # Process the successful LLM response
            try:
                # Clean the response string (remove markdown code blocks if present)
                cleaned_llm_response_str = llm_response_str.strip()
                if cleaned_llm_response_str.startswith("```json"):
                    cleaned_llm_response_str = cleaned_llm_response_str[7:]
                if cleaned_llm_response_str.endswith("```"):
                    cleaned_llm_response_str = cleaned_llm_response_str[:-3]
                cleaned_llm_response_str = cleaned_llm_response_str.strip()

                llm_data = json.loads(cleaned_llm_response_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON response from {llm_provider} for {page_url}: {e}. Raw Response: '{llm_response_str[:500]}'")
                return {**base_result, "error": f"Failed to parse {llm_provider} response as JSON.", "llm_response_raw": llm_response_str[:500], "llm_provider": llm_provider}

            # Populate result dictionary from parsed LLM data, using defaults from base_result
            analysis_result = {
                "url": page_url,
                "keywords": llm_data.get("keywords", base_result["keywords"]),
                "content_summary": llm_data.get("content_summary", base_result["content_summary"]),
                "other_information_and_contacts": llm_data.get("other_information_and_contacts", base_result["other_information_and_contacts"]),
                "suggested_keywords_for_seo": llm_data.get("suggested_keywords_for_seo", base_result["suggested_keywords_for_seo"]),
                "overall_tone": llm_data.get("overall_tone", base_result["overall_tone"]),
                "target_audience": llm_data.get("target_audience", base_result["target_audience"]),
                "topic_categories": llm_data.get("topic_categories", base_result["topic_categories"]),
                "llm_provider": llm_provider
            }
            if is_main_page: # Add header/footer for main page
                analysis_result.update({
                    "header": llm_data.get("header", base_result.get("header", [])),
                    "footer": llm_data.get("footer", base_result.get("footer", []))
                })

            self.logger.info(f"Successfully completed LLM analysis via {llm_provider} for URL: {page_url} (Main page: {is_main_page})")
            return analysis_result

        except Exception as e: # Catch-all for unexpected errors during the process
            self.logger.error(f"Unexpected error during LLM analysis processing for URL {page_url}: {e}", exc_info=True)
            return {**base_result, "error": f"An unexpected error occurred: {str(e)}", "llm_provider": llm_provider}

    def _format_technical_statistics_section(self, tech_stats: dict, language_code: str) -> list:
        """Helper to format technical statistics into markdown report sections."""
        titles = self._get_localized_titles(language_code=language_code)
        if not tech_stats:
            return [f"## {titles['technical_overview']}", "Technical statistics data not available.", ""]

        tech_sections = []
        tech_sections.append(f"## {titles['technical_overview']}")

        # Website Analysis Summary
        crawled_pages = tech_stats.get('crawled_internal_pages_count', 0)
        analysis_duration = tech_stats.get('analysis_duration_seconds', 0)
        tech_sections.append(f"**{titles['website_analysis_summary']}:**")
        tech_sections.append(f"- {titles['total_pages_crawled']}: {crawled_pages}")
        if analysis_duration > 0:
            minutes = int(analysis_duration // 60)
            seconds = int(analysis_duration % 60)
            duration_str = ""
            if minutes > 0: duration_str += f"{minutes} {titles.get('minutes_label', 'minutes')} "
            duration_str += f"{seconds} {titles.get('seconds_label', 'seconds')}"
            tech_sections.append(f"- {titles['analysis_duration']}: {duration_str.strip()}")
        tech_sections.append("")

        # Content Analysis
        total_content_length = tech_stats.get('total_cleaned_content_length', 0)
        avg_content_length = tech_stats.get('average_cleaned_content_length_per_page', 0)
        total_headings = tech_stats.get('total_headings_count', 0)

        tech_sections.append(f"**{titles['content_metrics']}:**")
        if total_content_length > 0:
            tech_sections.append(f"- {titles['total_content_analyzed']}: {total_content_length:,} {titles.get('characters_label', 'characters')}")
        if avg_content_length > 0 and crawled_pages > 0 :
            tech_sections.append(f"- {titles['average_content_per_page']}: {avg_content_length:,} {titles.get('characters_label', 'characters')}")
        if total_headings > 0:
            tech_sections.append(f"- {titles['total_headings_found']}: {total_headings}")
        tech_sections.append("")

        # Image Optimization Analysis
        total_images = tech_stats.get('total_images_count', 0)
        missing_alt_tags = tech_stats.get('total_missing_alt_tags_count', 0)
        alt_text_coverage = tech_stats.get('alt_text_coverage_percentage', 0)

        if total_images > 0:
            tech_sections.append(f"**{titles['image_optimization']}:**")
            tech_sections.append(f"- {titles['total_images_found']}: {total_images}")
            tech_sections.append(f"- {titles['images_missing_alt_text']}: {missing_alt_tags}")
            tech_sections.append(f"- {titles['alt_text_coverage']}: {alt_text_coverage:.2f}%")

            if alt_text_coverage >= 90:
                tech_sections.append(f"- ✅ **{titles['status']}**: {titles['excellent']} alt text coverage.")
            elif alt_text_coverage >= 70:
                tech_sections.append(f"- ⚠️ **{titles['status']}**: {titles['good']}, but some images lack alt text.")
            elif alt_text_coverage >= 50:
                tech_sections.append(f"- ❗ **{titles['status']}**: {titles['needs_improvement']}. Many images are missing alt text.")
            else:
                tech_sections.append(f"- ❌ **{titles['status']}**: {titles['critical']}. Most images lack alt text, impacting SEO and accessibility.")
            tech_sections.append("")
        elif crawled_pages > 0:
             tech_sections.append(f"**{titles['image_optimization']}:**")
             tech_sections.append(f"- {titles['no_images_found']}")
             tech_sections.append("")

        # Mobile Optimization
        mobile_pages = tech_stats.get('pages_with_mobile_viewport_count', 0)
        mobile_optimization = tech_stats.get('mobile_optimization_percentage', 0)

        if crawled_pages > 0:
            tech_sections.append(f"**{titles['mobile_friendliness']}:**")
            tech_sections.append(f"- {titles['pages_with_mobile_viewport']}: {mobile_pages} out of {crawled_pages}")
            tech_sections.append(f"- {titles['mobile_optimization_coverage']}: {mobile_optimization:.2f}%")

            if mobile_optimization >= 95:
                tech_sections.append(f"- ✅ **{titles['status']}**: {titles['excellent']} mobile optimization.")
            elif mobile_optimization >= 80:
                tech_sections.append(f"- ⚠️ **{titles['status']}**: {titles['good']} mobile optimization, minor improvements possible.")
            elif mobile_optimization >= 50:
                tech_sections.append(f"- ❗ **{titles['status']}**: {titles['needs_improvement']}. A significant number of pages may not be mobile-friendly.")
            else:
                tech_sections.append(f"- ❌ **{titles['status']}**: {titles['critical']}. Website appears largely unoptimized for mobile devices.")
            tech_sections.append("")

        # Technical Configuration
        robots_found = tech_stats.get('robots_txt_found', False)
        tech_sections.append(f"**{titles['basic_technical_setup']}:**")
        status_text = f"✅ {titles['found']}" if robots_found else f"❌ {titles['not_found']}" # Uses localized 'found'/'not_found'
        tech_sections.append(f"- {titles['robots_txt_file']}: {status_text}")
        if not robots_found:
            tech_sections.append(f"  - {titles['recommendation']}: {titles['robots_txt_recommendation']}")
        tech_sections.append("")

        return tech_sections

    async def generate_comprehensive_text_report(self, llm_analysis_all: dict, language_code: str = "en") -> str:
        self.logger.info(f"LLMAnalysisProcess.generate_comprehensive_text_report: Generating report with language_code: '{language_code}'")
        titles = self._get_localized_titles(language_code=language_code)    
        
        # Extract different parts of the analysis
        main_page_analysis = llm_analysis_all.get('main_page', {})
        technical_stats = llm_analysis_all.get('technical_statistics', {})
        other_pages = {url: data for url, data in llm_analysis_all.items()
                      if url not in ['main_page', 'technical_statistics'] and data}

        report_sections = []
        report_sections.append(f"# {titles['main_title']}")
        report_sections.append(f"{titles['generated_at']}: " + time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
        report_sections.append("---")

        tech_sections = self._format_technical_statistics_section(technical_stats, language_code=language_code)
        report_sections.extend(tech_sections)
        report_sections.append("---")

        # Main Page Analysis Section
        if main_page_analysis:
            main_url_display = main_page_analysis.get('url', titles['url_not_found_in_data'])
            llm_provider_main = main_page_analysis.get('llm_provider', 'N/A')
            report_sections.append(f"## {titles['main_page_analysis']}: {main_url_display} ({titles['via_llm_provider']} {llm_provider_main})")
            if main_page_analysis.get("error"):
                 report_sections.append(f"  **{titles['note']}:** {titles['main_page_analysis_error']}: {main_page_analysis['error']}")

            if main_page_analysis.get('overall_tone'):
                report_sections.append(f"### {titles['overall_content_tone']}")
                report_sections.append(f"- {main_page_analysis['overall_tone']}")
                report_sections.append("")

            if main_page_analysis.get('target_audience'):
                audiences_str = ", ".join(ta for ta in main_page_analysis['target_audience'] if ta)
                if audiences_str:
                    report_sections.append(f"### {titles['identified_target_audience']}")
                    report_sections.append(f"- {audiences_str}")
                    report_sections.append("")

            if main_page_analysis.get('topic_categories'):
                categories_str = ", ".join(tc for tc in main_page_analysis['topic_categories'] if tc)
                if categories_str:
                    report_sections.append(f"### {titles['main_topic_categories']}")
                    report_sections.append(f"- {categories_str}")
                    report_sections.append("")

            if main_page_analysis.get('content_summary'):
                report_sections.append(f"### {titles['content_summary']}")
                report_sections.append(main_page_analysis['content_summary'])
                report_sections.append("")

            if main_page_analysis.get('keywords'):
                keywords_str = ", ".join(k for k in main_page_analysis['keywords'] if k)
                if keywords_str:
                    report_sections.append(f"### {titles['primary_keywords_identified']}")
                    report_sections.append(f"- {keywords_str}")
                    report_sections.append("")

            if main_page_analysis.get('suggested_keywords_for_seo'):
                seo_keywords_str = ", ".join(sk for sk in main_page_analysis['suggested_keywords_for_seo'] if sk)
                if seo_keywords_str:
                    report_sections.append(f"### {titles['suggested_seo_keywords']}")
                    report_sections.append(f"- {seo_keywords_str}")
                    report_sections.append("")

            if main_page_analysis.get('other_information_and_contacts'):
                report_sections.append(f"### {titles['contact_info_key_mentions']}")
                contacts_list = [c for c in main_page_analysis['other_information_and_contacts'] if c]
                if contacts_list:
                    for contact_item in contacts_list: report_sections.append(f"- {contact_item}")
                else:
                    report_sections.append(f"- {titles['no_contacts_identified']}")
                report_sections.append("")

            if main_page_analysis.get('header'):
                header_str = ", ".join(h for h in main_page_analysis['header'] if h)
                report_sections.append(f"### {titles['key_header_elements']}")
                report_sections.append(f"- {header_str}" if header_str else f"- {titles['no_header_elements_identified']}")
                report_sections.append("")

            if main_page_analysis.get('footer'):
                footer_str = ", ".join(f_item for f_item in main_page_analysis['footer'] if f_item)
                report_sections.append(f"### {titles['key_footer_elements']}")
                report_sections.append(f"- {footer_str}" if footer_str else f"- {titles['no_footer_elements_identified']}")
                report_sections.append("")
        else:
            report_sections.append(f"## {titles['main_page_analysis']}")
            report_sections.append(titles['main_page_data_missing'])
            report_sections.append("")
        report_sections.append("---")

        # Subpage Analysis Overview Section
        if other_pages:
            report_sections.append(f"## {titles['subpage_analysis_overview']}")
            report_sections.append(f"{titles['num_additional_pages_analyzed']}: {len(other_pages)}")
            report_sections.append("")

            all_subpage_keywords, all_subpage_seo_keywords, all_subpage_topic_categories = [], [], []
            all_subpage_target_audiences, all_subpage_tones = [], []

            report_sections.append(f"### {titles['highlights_individual_subpages']}")
            for page_key, page_analysis_item in other_pages.items():
                page_url_display = page_analysis_item.get('url', page_key)
                llm_provider_sub = page_analysis_item.get('llm_provider', 'N/A')
                report_sections.append(f"#### {titles['page']}: {page_url_display} ({titles['via_llm_provider']} {llm_provider_sub})")

                if page_analysis_item.get("error"):
                    report_sections.append(f"  **{titles['note']}:** {titles['subpage_analysis_error']}: {page_analysis_item['error']}")

                if page_analysis_item.get('content_summary'):
                    summary_text = page_analysis_item['content_summary']
                    truncated_summary = (summary_text[:200] + '...') if len(summary_text) > 200 else summary_text
                    report_sections.append(f"  - **{titles['summary_prefix']}**: {truncated_summary}")
                if page_analysis_item.get('overall_tone'):
                    report_sections.append(f"  - **{titles['tone_prefix']}**: {page_analysis_item['overall_tone']}")
                    all_subpage_tones.extend(t for t in [page_analysis_item['overall_tone']] if t)
                if page_analysis_item.get('target_audience'):
                    audiences_str_sub = ", ".join(ta for ta in page_analysis_item['target_audience'] if ta)
                    if audiences_str_sub: report_sections.append(f"  - **{titles['audience_prefix']}**: {audiences_str_sub}")
                    all_subpage_target_audiences.extend(ta for ta in page_analysis_item['target_audience'] if ta)
                if page_analysis_item.get('topic_categories'):
                    categories_str_sub = ", ".join(tc for tc in page_analysis_item['topic_categories'] if tc)
                    if categories_str_sub: report_sections.append(f"  - **{titles['topics_prefix']}**: {categories_str_sub}")
                    all_subpage_topic_categories.extend(tc for tc in page_analysis_item['topic_categories'] if tc)
                if page_analysis_item.get('keywords'):
                    all_subpage_keywords.extend(k for k in page_analysis_item['keywords'] if k)
                if page_analysis_item.get('suggested_keywords_for_seo'):
                    all_subpage_seo_keywords.extend(sk for sk in page_analysis_item['suggested_keywords_for_seo'] if sk)
                report_sections.append("")

            def get_top_items_md(items_list, title_format_key_internal, item_mention_format_key_internal, top_n=10):
                if not items_list: return []
                from collections import Counter
                counts = Counter(k for k in items_list if k)
                if not counts: return []
                sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)

                # Use the already localized format string from the titles dictionary
                localized_title_format = titles[title_format_key_internal] 
                localized_title = localized_title_format.format(count=min(top_n, len(sorted_items)))
                
                md_list = [f"### {localized_title}"]
                mention_format_string = titles[item_mention_format_key_internal]
                for item, count in sorted_items[:top_n]:
                    mention_text = mention_format_string.format(count=count)
                    md_list.append(f"- {item} ({mention_text})")
                md_list.append("")
                return md_list

            report_sections.extend(get_top_items_md(all_subpage_keywords, "common_keywords_subpages_title_format", "mentioned_in_subpages_format"))
            report_sections.extend(get_top_items_md(all_subpage_seo_keywords, "frequently_suggested_seo_keywords_subpages_title_format", "mentioned_in_subpages_format"))
            report_sections.extend(get_top_items_md(all_subpage_topic_categories, "common_topic_categories_subpages_title_format", "mentioned_in_subpages_format"))
            report_sections.extend(get_top_items_md(all_subpage_target_audiences, "common_target_audiences_subpages_title_format", "mentioned_in_subpages_format", top_n=5))
            report_sections.extend(get_top_items_md(all_subpage_tones, "common_content_tones_subpages_title_format", "mentioned_in_subpages_format", top_n=5))
        
        
        report_sections.append("---")

        report_sections.append(f"## {titles['ai_powered_strategic_insights']}")
        ai_recommendations_text = titles.get('no_ai_recommendations', "AI recommendations were not generated.") # Default
        gemini_available_for_recs = bool(self.gemini_model)
        mistral_available_for_recs = bool(self.mistral_api_key and self.mistral_model_name)
        
        if gemini_available_for_recs or mistral_available_for_recs:
            try:
                self.logger.info(f"Attempting to generate AI recommendations content with language_code: {language_code}")
                ai_recommendations_text = await generate_ai_recommendations_content(
                    llm_analysis_all=llm_analysis_all,
                    logger=self.logger,
                    call_gemini_api_func=self._call_gemini_api, 
                    call_mistral_api_func=self._call_mistral_api, 
                    gemini_model_available=gemini_available_for_recs,
                    mistral_configured=mistral_available_for_recs,
                    language_code=language_code 
                )
                self.logger.info(f"AI recommendations content generated successfully with language_code: {language_code}.")
            except Exception as e:
                self.logger.error(f"Error during generate_ai_recommendations_content call: {e}", exc_info=True)
                ai_recommendations_text = titles.get('error_generating_ai_recommendations', f"An error occurred while generating AI-powered recommendations.") + f" (Details: {str(e)[:100]})"
        else:
            ai_recommendations_text = titles.get('no_ai_recommendations_configured', "AI recommendations cannot be generated as no LLM is configured for this task.")
            self.logger.warning(ai_recommendations_text)
                
        report_sections.append(ai_recommendations_text)
        report_sections.append("") 
        report_sections.append("---")
        
        
        report_sections.append(f"## {titles['performance_monitoring_next_steps']}")
        report_sections.append(titles['next_steps_1'])
        report_sections.append(titles['next_steps_2'])
        report_sections.append(titles['next_steps_3'])
        report_sections.append(titles['next_steps_4'])
        report_sections.append(titles['next_steps_5'])
        report_sections.append("---")
        report_sections.append(titles['end_of_report'])
        
        return "\n".join(report_sections)