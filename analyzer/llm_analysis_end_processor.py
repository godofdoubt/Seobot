# analyzer/llm_analysis_end_processor.py
import json
import logging
import os
import asyncio
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
import threading # Added import

class LLMAnalysisEndProcessor:
    def __init__(self):
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

    # ... (keep _call_gemini_api, _analyze_single_page, _generate_comprehensive_text_report, _process_seo_report, _mark_report_as_error, _process_pending_reports as they are) ...

    async def _call_gemini_api(self, prompt_text: str) -> str: # Existing method
        if not self.model:
            self.logger.error("Gemini model not initialized. Cannot make API call.")
            return ""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt_text,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                }
            )
            if response and hasattr(response, 'text') and response.text:
                return response.text
            elif response and hasattr(response, 'parts') and response.parts:
                all_text_parts = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                if all_text_parts:
                    return all_text_parts
            if response and hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                self.logger.warning(f"Gemini API call for prompt resulted in feedback: {response.prompt_feedback}")
            self.logger.warning(f"LLM response was empty or did not contain text. Full response object: {response}")
            return ""
        except Exception as e:
            if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
                self.logger.error(f"Gemini API Permission Denied or Invalid API Key: {e}")
            else:
                self.logger.error(f"Error during Gemini API call: {e}", exc_info=True)
            return ""

    async def _analyze_single_page(self, page_url: str, page_data: dict, is_main_page: bool = False) -> dict: # Existing method
        base_result = {
            "url": page_url,
            "keywords": [],
            "content_summary": "",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": []
        }
        if is_main_page:
            base_result.update({"header": [], "footer": []})
        if not page_data:
            self.logger.warning(f"No page data provided for URL: {page_url}")
            return {**base_result, "error": "No page data available for analysis."}
        cleaned_text = page_data.get('cleaned_text', '')
        headings_data = page_data.get('headings', {})
        if not cleaned_text and not headings_data:
            self.logger.warning(f"No cleaned_text or headings_data found for URL {page_url}. LLM analysis might be ineffective.")
            return {**base_result, "error": "No content (cleaned_text or headings) available for analysis."}
        max_text_len = 25000
        truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')
        json_structure_for_llm = {
            "keywords": ["string"],
            "content_summary": "string",
            "other_information_and_contacts": ["string"],
            "suggested_keywords_for_seo": ["string"]
        }
        if is_main_page:
            json_structure_for_llm.update({
                "header": ["string"],
                "footer": ["string"]
            })
        detailed_instructions_keywords = """1. **"keywords"**:
        * Identify and list the top 5-7 most relevant and frequently occurring keywords or key phrases from the page content and headings.
        * These should accurately represent the main topics and themes of the page.
        * Prioritize multi-word phrases if they are more descriptive. Example: ["data analysis solutions", "cloud computing services", "enterprise software"]
        * Return as a list of strings. If no distinct keywords are found, return an empty list []."""
        detailed_instructions_summary = """2. **"content_summary"**:
        * Provide a concise summary of the page content in 2-4 sentences (target 100-150 words).
        * The summary must capture the main purpose, key offerings, or core information presented on the page.
        * It should be informative and engaging.
        * If the content is too sparse for a meaningful summary, provide a brief note like "Page content is minimal." """
        detailed_instructions_contacts = """3. **"other_information_and_contacts"**:
        * Extract any explicit contact information: email addresses, phone numbers, physical addresses.
        * Identify specific company names, key product names and prices, or important service names mentioned.
        * List social media profile URLs if clearly present.
        * If the page mentions specific individuals (e.g., team members, authors), list their names and roles if available. 
        * Format each piece of information as a descriptive string in a list.
        * Example: ["Email: contact@example.com", "Phone: (555) 123-4567", "Main Office: 123 Innovation Drive, Tech City", "Product: Alpha Suite", "Twitter: https://twitter.com/example"]
        * If no such information is found, return an empty list []."""
        detailed_instructions_seo_keywords = """4. **"suggested_keywords_for_seo"**:
        * Based on the page content and its main topics, suggest 5-7 additional keywords or key phrases that could be targeted for low competitive SEO. Make sure these some long-tail and alternative but relevant keywords.
        * These should be relevant variations, long-tail keywords, or related topics not already dominant but with potential.
        * Consider user intent (informational, transactional, navigational). Example: ["benefits of data analysis", "best cloud providers for small business", "custom enterprise software development"]
        * If no strong distinct suggestions can be made, return an empty list []."""
        prompt = f"""If content is Turkish make your analysis in Turkish, Otherwise make it in English.
    --
    Analyze the following web page content for the URL: {page_url}
    ---
    **Page Content (Cleaned Text Snippet):**
    ---
    {truncated_cleaned_text}
    ---
    **Page Headings (JSON format):**
    ---
    {json.dumps(headings_data, indent=2)}
    ---
    Based on the provided text and headings, generate a JSON object strictly adhering to the following structure.
    Output ONLY the JSON object. Do NOT include any explanatory text, markdown formatting, or anything else outside the JSON object itself.
    {json.dumps(json_structure_for_llm, indent=2)}
    **Detailed Instructions for populating each field in the JSON object:**
    {detailed_instructions_keywords}
    {detailed_instructions_summary}
    {detailed_instructions_contacts}
    {detailed_instructions_seo_keywords}
    """
        if is_main_page:
            detailed_instructions_header = """5. **"header"**:
        * From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main header.
        * This typically includes site navigation links (e.g., "Home", "About Us", "Services", "Contact"), site branding text (e.g., company name if prominently in header), or a primary tagline.
        * Provide these as a list of strings. Each string can be a distinct link text or a phrase from the header.
        * If no clear header text is discernible, return an empty list [].
        * Example: ["Home", "Products", "Blog", "Login", "Site Title Example Inc."]"""
            detailed_instructions_footer = """6. **"footer"**:
        * From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main footer.
        * This typically includes copyright notices, links to privacy policy, terms of service, sitemap, contact information repeated in the footer, or social media links.
        * Provide these as a list of strings. Each string can be a distinct link text or a phrase from the footer.
        * If no clear footer text is discernible, return an empty list [].
        * Example: ["© 2024 Company Name", "Privacy Policy", "Terms of Use", "Contact Us", "Follow us on Twitter"]"""
            prompt += f"""
    {detailed_instructions_header}
    {detailed_instructions_footer}"""
        prompt += """
    Ensure your entire response is ONLY a valid JSON object.
    """
        try:
            self.logger.debug(f"Sending prompt to Gemini for URL: {page_url} (Main page: {is_main_page})")
            llm_response_str = await self._call_gemini_api(prompt)
            if not llm_response_str:
                self.logger.error(f"LLM returned empty or no-text response for URL: {page_url}")
                return {**base_result, "error": "LLM returned an empty response."}
            try:
                cleaned_llm_response_str = llm_response_str.strip()
                if cleaned_llm_response_str.startswith("```json"):
                    cleaned_llm_response_str = cleaned_llm_response_str[7:]
                if cleaned_llm_response_str.endswith("```"):
                    cleaned_llm_response_str = cleaned_llm_response_str[:-3]
                cleaned_llm_response_str = cleaned_llm_response_str.strip()
                llm_data = json.loads(cleaned_llm_response_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON response from LLM for {page_url}: {e}. Raw Response: '{llm_response_str[:500]}'")
                return {**base_result, "error": "Failed to parse LLM response as JSON.", "llm_response_raw": llm_response_str[:500]}
            analysis_result = {
                "url": page_url,
                "keywords": llm_data.get("keywords", base_result["keywords"]),
                "content_summary": llm_data.get("content_summary", base_result["content_summary"]),
                "other_information_and_contacts": llm_data.get("other_information_and_contacts", base_result["other_information_and_contacts"]),
                "suggested_keywords_for_seo": llm_data.get("suggested_keywords_for_seo", base_result["suggested_keywords_for_seo"]),
            }
            if is_main_page:
                analysis_result.update({
                    "header": llm_data.get("header", base_result["header"]),
                    "footer": llm_data.get("footer", base_result["footer"])
                })
            self.logger.info(f"Successfully completed LLM analysis for URL: {page_url} (Main page: {is_main_page})")
            return analysis_result
        except Exception as e:
            self.logger.error(f"Unexpected error during LLM analysis processing for URL {page_url}: {e}", exc_info=True)
            return {**base_result, "error": f"An unexpected error occurred: {str(e)}"}

    async def _generate_comprehensive_text_report(self, llm_analysis_all: dict) -> str: # Existing method
        main_page_analysis = llm_analysis_all.get('main_page', {})
        other_pages = {url: data for url, data in llm_analysis_all.items() if url != 'main_page'}
        report_sections = []
        report_sections.append("# COMPREHENSIVE SEO ANALYSIS REPORT")
        report_sections.append("Generated: " + time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
        report_sections.append("")
        if main_page_analysis:
            main_url_display = main_page_analysis.get('url', 'Main Page Analysis (URL not found in analysis data)')
            report_sections.append(f"## Main Page Analysis: {main_url_display}")
            if main_page_analysis.get("error"):
                 report_sections.append(f"**Note:** Main page analysis encountered an error: {main_page_analysis['error']}")
            content_summary = main_page_analysis.get('content_summary', '')
            if content_summary:
                report_sections.append(f"### Content Summary")
                report_sections.append(content_summary)
                report_sections.append("")
            keywords = main_page_analysis.get('keywords', [])
            if keywords:
                report_sections.append(f"### Primary Keywords")
                report_sections.append(", ".join(k for k in keywords if k))
                report_sections.append("")
            seo_keywords = main_page_analysis.get('suggested_keywords_for_seo', [])
            if seo_keywords:
                report_sections.append(f"### Suggested SEO Keywords")
                report_sections.append(", ".join(sk for sk in seo_keywords if sk))
                report_sections.append("")
            contacts = main_page_analysis.get('other_information_and_contacts', [])
            if contacts:
                report_sections.append(f"### Contact Information & Key Mentions")
                for contact in contacts:
                    if contact: report_sections.append(f"- {contact}")
                report_sections.append("")
            header = main_page_analysis.get('header', [])
            if header:
                report_sections.append(f"### Header Elements")
                report_sections.append(", ".join(h for h in header if h) if any(h for h in header) else "No distinct header elements identified.")
                report_sections.append("")
            footer = main_page_analysis.get('footer', [])
            if footer:
                report_sections.append(f"### Footer Elements")
                report_sections.append(", ".join(f for f in footer if f) if any(f for f in footer) else "No distinct footer elements identified.")
                report_sections.append("")
        else:
            report_sections.append("## Main Page Analysis")
            report_sections.append("Main page analysis data was not available or incomplete in llm_analysis_all.")
            report_sections.append("")
        if other_pages:
            report_sections.append("## Subpage Analysis")
            report_sections.append(f"Number of additional pages analyzed: {len(other_pages)}")
            report_sections.append("")
            all_subpage_keywords = []
            all_subpage_seo_keywords = []
            for page_key, page_analysis_item in other_pages.items():
                page_url_display = page_analysis_item.get('url', page_key)
                report_sections.append(f"### {page_url_display}")
                if page_analysis_item.get("error"):
                    report_sections.append(f"**Note:** Analysis for this page encountered an error: {page_analysis_item['error']}")
                content_summary = page_analysis_item.get('content_summary', '')
                if content_summary:
                    report_sections.append(content_summary)
                    report_sections.append("")
                keywords = page_analysis_item.get('keywords', [])
                if keywords:
                    report_sections.append(f"**Keywords**: {', '.join(k for k in keywords if k)}")
                    all_subpage_keywords.extend(k for k in keywords if k)
                seo_keywords = page_analysis_item.get('suggested_keywords_for_seo', [])
                if seo_keywords:
                    report_sections.append(f"**SEO Suggestions**: {', '.join(sk for sk in seo_keywords if sk)}")
                    all_subpage_seo_keywords.extend(sk for sk in seo_keywords if sk)
                report_sections.append("")
            if all_subpage_keywords:
                keyword_count = {}
                for keyword_item in all_subpage_keywords:
                    keyword_count[keyword_item] = keyword_count.get(keyword_item, 0) + 1
                sorted_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)
                report_sections.append("## Site-Wide Subpage Keyword Analysis")
                report_sections.append("Most common keywords across analyzed subpages (top 15):")
                for kw, count in sorted_keywords[:15]:
                    report_sections.append(f"- {kw} (found in {count} subpages)")
                report_sections.append("")
            if all_subpage_seo_keywords:
                seo_keyword_count = {}
                for keyword_item in all_subpage_seo_keywords:
                    seo_keyword_count[keyword_item] = seo_keyword_count.get(keyword_item, 0) + 1
                sorted_seo_keywords = sorted(seo_keyword_count.items(), key=lambda x: x[1], reverse=True)
                report_sections.append("## Site-Wide Subpage SEO Suggestions")
                report_sections.append("Most frequently suggested SEO keywords for subpages (top 10):")
                for kw, count in sorted_seo_keywords[:10]:
                    report_sections.append(f"- {kw} (suggested for {count} subpages)")
                report_sections.append("")
        report_sections.append("## General Recommendations")
        report_sections.append("1. Focus on creating high-quality, relevant content aligned with your primary and suggested SEO keywords identified for both main and subpages.")
        report_sections.append("2. Ensure consistent branding and navigation (header/footer elements) across the site, as identified in the main page analysis. Verify these elements are user-friendly and effective on all page types.")
        report_sections.append("3. Optimize on-page SEO elements (title tags, meta descriptions, heading structure) for all important pages, incorporating identified keywords naturally and contextually.")
        report_sections.append("4. Strengthen internal linking between relevant pages to distribute link equity and improve site navigation for users and search engines. Link from authoritative pages to those needing a boost.")
        report_sections.append("5. Regularly review and update content to maintain accuracy and relevance. Consider creating new content clusters or cornerstone pieces targeting high-potential suggested SEO keywords.")
        report_sections.append("6. Monitor key SEO metrics (rankings, organic traffic, user engagement, conversion rates for target keywords) to assess the impact of optimizations and identify further opportunities for growth.")
        return "\n".join(report_sections)

    async def _process_seo_report(self, report_id: int): # Existing method
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
                    "header": initial_llm_analysis_from_blob.get("header", []),
                    "footer": initial_llm_analysis_from_blob.get("footer", [])
                }
                if initial_llm_analysis_from_blob.get("error"):
                     llm_analysis_all['main_page']['error'] = initial_llm_analysis_from_blob.get("error")
                     self.logger.warning(f"Pre-existing 'llm_analysis' for main page {normalized_db_main_url} contains an error field: {llm_analysis_all['main_page']['error']}")
                if not llm_analysis_all['main_page'].get('header') and not llm_analysis_all['main_page'].get('footer') and not llm_analysis_all['main_page'].get('error'):
                    self.logger.warning(f"Pre-existing 'llm_analysis' for main page {normalized_db_main_url} is valid but missing header/footer snippets.")
            else:
                error_reason = "Pre-computed LLM analysis for main page was missing, for a different URL, or structurally absent."
                if not initial_llm_analysis_from_blob:
                    error_reason = "Pre-computed LLM analysis (llm_analysis field) was not found in report_json_blob."
                elif normalized_url_from_llm_blob != normalized_db_main_url:
                    error_reason = (f"Pre-computed LLM analysis URL ('{url_from_llm_blob_original}') "
                                    f"does not match main report URL ('{main_report_url_original}').")
                self.logger.error(
                    f"{error_reason} (Report ID: {report_id}). "
                    "Main page LLM data in 'llm_analysis_all' will be an error placeholder. "
                    "It will NOT be re-processed from page_statistics by this processor."
                )
                llm_analysis_all['main_page'] = {
                    "url": main_report_url_original,
                    "error": error_reason,
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [],
                    "suggested_keywords_for_seo": [], "header": [], "footer": []
                }
            pages_to_analyze_data = []
            for page_url_key, page_content_item in page_statistics.items():
                normalized_page_url_key = page_url_key.rstrip('/')
                if normalized_page_url_key == normalized_db_main_url:
                    self.logger.info(f"Skipping page_statistics entry '{page_url_key}' (normalized to '{normalized_page_url_key}') as it matches the normalized main DB URL '{normalized_db_main_url}'. (Report ID: {report_id})")
                    continue
                if not page_url_key:
                    self.logger.warning(f"Skipping page_statistics entry with empty/null URL key (Report ID: {report_id})")
                    continue
                if not page_content_item or not (page_content_item.get('cleaned_text') or page_content_item.get('headings')):
                    self.logger.warning(f"Skipping subpage {page_url_key} due to missing cleaned_text or headings. (Report ID: {report_id})")
                    llm_analysis_all[page_url_key] = {
                        "url": page_url_key, "error": "Content data (cleaned_text/headings) missing in page_statistics.",
                        "keywords": [], "content_summary": "", "other_information_and_contacts": [], "suggested_keywords_for_seo": []
                    }
                    continue
                pages_to_analyze_data.append((page_url_key, page_content_item))
            if not pages_to_analyze_data:
                self.logger.info(f"No additional subpages found in page_statistics to analyze for report ID {report_id} (after potentially skipping main page).")
            else:
                self.logger.info(f"Found {len(pages_to_analyze_data)} subpages from page_statistics to analyze for report ID {report_id}")
                batch_size = 5; max_retries = 3; delay_between_batches = 2
                for i in range(0, len(pages_to_analyze_data), batch_size):
                    batch = pages_to_analyze_data[i:i+batch_size]
                    batch_tasks = []
                    async def analyze_with_retry(p_url, p_data):
                        for retry_attempt in range(max_retries):
                            analysis_result = await self._analyze_single_page(p_url, p_data, is_main_page=False)
                            if "error" not in analysis_result or not analysis_result["error"]:
                                return analysis_result
                            self.logger.warning(f"Error analyzing page {p_url} (attempt {retry_attempt+1}/{max_retries}): {analysis_result.get('error')}")
                            if retry_attempt < max_retries - 1:
                                await asyncio.sleep(1 + retry_attempt)
                            else:
                                self.logger.error(f"Failed to analyze page {p_url} after {max_retries} attempts. Final error: {analysis_result.get('error')}")
                                return analysis_result
                        return None
                    for p_url_item, p_data_item in batch:
                        batch_tasks.append(analyze_with_retry(p_url_item, p_data_item))
                    results_for_batch = await asyncio.gather(*batch_tasks)
                    for result in results_for_batch:
                        if result and result.get("url"):
                            llm_analysis_all[result["url"]] = result
                        elif result:
                            self.logger.warning(f"Malformed or URL-less analysis result in batch for report {report_id}: {str(result)[:200]}")
                    self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(pages_to_analyze_data) + batch_size - 1)//batch_size} for report {report_id}")
                    if i + batch_size < len(pages_to_analyze_data): await asyncio.sleep(delay_between_batches)
            self.logger.info(f"Report ID {report_id}: After all page analyses, llm_analysis_all contains {len(llm_analysis_all)} entries. Keys: {list(llm_analysis_all.keys())}")
            self.logger.debug(f"Report ID {report_id}: llm_analysis_all content preview: {json.dumps({k: (v.get('error') if v.get('error') else 'OK') for k, v in llm_analysis_all.items()}, indent=2)}")
            comprehensive_text_report = await self._generate_comprehensive_text_report(llm_analysis_all)
            self.logger.info(f"Report ID {report_id}: Generated comprehensive text report. Length: {len(comprehensive_text_report)} chars.")
            current_timestamp_utc = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            update_data = {
                'llm_analysis_all': llm_analysis_all,
                'llm_analysis_all_completed': True,
                'llm_analysis_all_timestamp': current_timestamp_utc,
                'text_report': comprehensive_text_report,
                'llm_analysis_all_error': None
            }
            if llm_analysis_all.get('main_page', {}).get('error'):
                update_data['llm_analysis_all_error'] = f"Main page LLM data error: {llm_analysis_all['main_page']['error'][:350]}"
            self.logger.info(f"Report ID {report_id}: Preparing to update Supabase. update_data keys: {list(update_data.keys())}")
            update_response = await asyncio.to_thread(
                self.supabase.table('seo_reports').update(update_data).eq('id', report_id).execute
            )
            if hasattr(update_response, 'error') and update_response.error:
                self.logger.error(f"Failed to update report ID {report_id} in Supabase: {update_response.error}")
                await self._mark_report_as_error(report_id, f"Supabase update failed: {str(update_response.error)[:400]}")
                return False
            self.logger.info(f"Successfully processed and updated report ID {report_id} with all page analyses and comprehensive text_report.")
            return True
        except Exception as e:
            self.logger.error(f"Critical error processing report ID {report_id}: {e}", exc_info=True)
            await self._mark_report_as_error(report_id, f"Processor Critical Error: {str(e)[:450]}")
            return False

    async def _mark_report_as_error(self, report_id: int, error_message: str): # Existing method
        try:
            error_timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            await asyncio.to_thread(
                self.supabase.table('seo_reports').update({
                    'llm_analysis_all_completed': False,
                    'llm_analysis_all_timestamp': error_timestamp,
                    'llm_analysis_all_error': error_message
                }).eq('id', report_id).execute
            )
            self.logger.info(f"Marked report ID {report_id} with error: {error_message}")
        except Exception as sup_e:
            self.logger.error(f"Failed to update error status for report {report_id} in Supabase: {sup_e}")

    async def _process_pending_reports(self, limit=10): # Existing method
        try:
            pending_reports_response = await asyncio.to_thread(
                self.supabase.table('seo_reports')
                    .select('id, url')
                    .filter('llm_analysis_all_completed', 'not.is', 'true')
                    .is_('llm_analysis_all_error', 'null')
                    .not_('report', 'is', 'null')
                    .limit(limit)
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
                    self.logger.error(f"Failed to complete llm_analysis_all for report ID {report_id}. Check previous logs and DB for error details.")
        except Exception as e:
            self.logger.error(f"General error in _process_pending_reports scheduler: {e}", exc_info=True)

    def _run_async_wrapper(self, report_ids_str_list): # New method
        """Internal wrapper to run the async 'run' method in a new event loop."""
        try:
            self.logger.info(f"Background thread's event loop started for report IDs: {report_ids_str_list}.")
            asyncio.run(self.run(report_ids=report_ids_str_list, process_pending=False)) # Explicitly call 'run'
            self.logger.info(f"Background thread's event loop completed for report IDs: {report_ids_str_list}.")
        except Exception as e:
            self.logger.error(f"Exception in threaded _run_async_wrapper for report_ids {report_ids_str_list}: {e}", exc_info=True)
            # If critical, consider updating DB error status for these reports, if self.run() didn't do it.
            # For example, iterate report_ids_str_list and call self._mark_report_as_error if appropriate.
            # This depends on how self.run() and its sub-methods handle their own errors.
            # Given self._process_seo_report calls _mark_report_as_error, this might be redundant here
            # unless _run_async_wrapper itself fails before or after calling self.run.

    def schedule_run_in_background(self, report_ids): # New method
        """Schedules the .run() method to execute in a new background thread
           with its own asyncio event loop."""
        if not isinstance(report_ids, list):
            report_ids_list = [report_ids]
        else:
            report_ids_list = report_ids

        report_ids_str_list = [str(rid) for rid in report_ids_list]

        self.logger.info(f"Scheduling LLMAnalysisEndProcessor.run for report IDs {report_ids_str_list} in a background thread.")
        thread = threading.Thread(target=self._run_async_wrapper, args=(report_ids_str_list,))
        thread.daemon = True  # Allows main program to exit even if thread is running
        thread.start()
        self.logger.info(f"Background thread for report IDs {report_ids_str_list} has been started.")


    async def run(self, report_ids=None, process_pending=False, batch_size=10): # Existing method - minor adjustment for clarity if called by wrapper
        """Main entry point for the processor's operations."""
        if not self.supabase or not self.model:
            self.logger.error("Processor not fully initialized (Supabase client or Gemini model missing). Aborting run.")
            return

        if report_ids:
            if not isinstance(report_ids, list):
                report_ids = [report_ids]
            self.logger.info(f"Processing specific report IDs: {report_ids}")
            for report_id_input in report_ids:
                try:
                    parsed_id = int(report_id_input)
                    await self._process_seo_report(parsed_id) # This already logs its own success/failure
                except ValueError:
                    self.logger.warning(f"Invalid report_id format: '{report_id_input}'. Must be an integer. Skipping.")
                except Exception as e:
                    self.logger.error(f"Unexpected error processing report_id '{report_id_input}': {e}", exc_info=True)
                    # Optionally mark this specific ID as error if _process_seo_report didn't catch it.
                    try:
                        await self._mark_report_as_error(int(report_id_input), f"Outer run error: {str(e)[:450]}")
                    except ValueError: # if report_id_input wasn't even an int
                        pass


        elif process_pending: # This branch will be used by the scheduler, not direct calls with report_ids from main.py
            self.logger.info(f"Processing pending reports, batch limit: {batch_size}")
            await self._process_pending_reports(limit=batch_size)
        else:
            # Default behavior if called with no args from scheduler, but our wrapper specifies report_ids.
            # If run is called with process_pending=False and no report_ids, it does nothing.
            # This is fine as schedule_run_in_background always provides report_ids.
            self.logger.info(f"LLMAnalysisEndProcessor.run called with no specific report IDs and process_pending=False. No action taken by default.")
        
        self.logger.info(f"LLMAnalysisEndProcessor run method finished for report_ids: {report_ids if report_ids else 'pending processing'}.")

# ... (keep if __name__ == '__main__': block as is for testing) ...
if __name__ == '__main__':
    async def main_test_runner():
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - Line %(lineno)d - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        logger = logging.getLogger("LLMAnalysisEndProcessor_StandaloneTest")
        logger.info("Starting standalone test run...")
        
        processor = None
        try:
            processor = LLMAnalysisEndProcessor()
            # To test the new threading approach from a sync context (similar to how Streamlit would call it):
            # processor.schedule_run_in_background(report_ids=[278])
            # logger.info("Scheduled job in background. Main thread will wait a bit for demo purposes.")
            # time.sleep(60) # Wait for the background thread to do some work

            # Or test the async run directly (as before)
            await processor.run(report_ids=[278])

            logger.info("Standalone test run finished successfully.")
        except ValueError as ve_init:
            logger.error(f"LLMAnalysisEndProcessor initialization failed: {ve_init}", exc_info=True)
        except Exception as e:
            logger.error(f"Error during standalone test run: {e}", exc_info=True)
        finally:
             if processor:
                 pass
    # If testing schedule_run_in_background, you don't need asyncio.run here for the main_test_runner itself.
    # asyncio.run(main_test_runner())
    # For testing schedule_run_in_background:
    # main_test_runner_sync():
    #    ...
    #    processor.schedule_run_in_background(report_ids=[278])
    #    time.sleep(X) # wait for thread
    # main_test_runner_sync()
    # For testing await processor.run():
    asyncio.run(main_test_runner())