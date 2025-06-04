
# analyzer/llm_analysis_process.py
import json
import asyncio
import time
import httpx # For Mistral API calls
from .llm_analysis_process_prompts import LLMAnalysisPrompts # Import the prompts class for single page
from .generate_ai_recommendations import generate_ai_recommendations_content # Import the new function

class LLMAnalysisProcess:
    def __init__(self, gemini_model, logger, mistral_api_key=None, mistral_model_name=None):
        self.gemini_model = gemini_model  # This is the initialized genai.GenerativeModel
        self.logger = logger
        self.mistral_api_key = mistral_api_key
        self.mistral_model_name = mistral_model_name

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

    def _format_technical_statistics_section(self, tech_stats: dict) -> list:
        """Helper to format technical statistics into markdown report sections."""
        if not tech_stats: # Handle case where tech_stats might be empty or None
            return ["## Technical SEO Overview", "Technical statistics data not available.", ""]
        
        tech_sections = []
        tech_sections.append("## Technical SEO Overview")
        
        # Website Analysis Summary
        crawled_pages = tech_stats.get('crawled_internal_pages_count', 0)
        analysis_duration = tech_stats.get('analysis_duration_seconds', 0)
        tech_sections.append(f"**Website Analysis Summary:**")
        tech_sections.append(f"- Total pages crawled and analyzed: {crawled_pages}")
        if analysis_duration > 0:
            minutes = analysis_duration // 60
            seconds = analysis_duration % 60
            duration_str = ""
            if minutes > 0: duration_str += f"{minutes} minutes "
            duration_str += f"{seconds} seconds"
            tech_sections.append(f"- Analysis duration: {duration_str.strip()}")
        tech_sections.append("")
        
        # Content Analysis
        total_content_length = tech_stats.get('total_cleaned_content_length', 0)
        avg_content_length = tech_stats.get('average_cleaned_content_length_per_page', 0)
        total_headings = tech_stats.get('total_headings_count', 0)
        
        tech_sections.append(f"**Content Metrics:**")
        if total_content_length > 0:
            tech_sections.append(f"- Total content analyzed (all pages): {total_content_length:,} characters")
        if avg_content_length > 0 and crawled_pages > 0 : # Makes sense only if pages were crawled
            tech_sections.append(f"- Average content per page: {avg_content_length:,} characters")
        if total_headings > 0:
            tech_sections.append(f"- Total headings found (all pages): {total_headings}")
        tech_sections.append("")
        
        # Image Optimization Analysis
        total_images = tech_stats.get('total_images_count', 0)
        missing_alt_tags = tech_stats.get('total_missing_alt_tags_count', 0)
        alt_text_coverage = tech_stats.get('alt_text_coverage_percentage', 0) # This is already a percentage
        
        if total_images > 0: # Only show if images exist
            tech_sections.append(f"**Image Optimization:**")
            tech_sections.append(f"- Total images found: {total_images}")
            tech_sections.append(f"- Images missing alt text: {missing_alt_tags}")
            tech_sections.append(f"- Alt text coverage: {alt_text_coverage}%") # Display as percentage
            
            # Add qualitative feedback based on coverage
            if alt_text_coverage >= 90:
                tech_sections.append("- ✅ **Status**: Excellent alt text coverage.")
            elif alt_text_coverage >= 70:
                tech_sections.append("- ⚠️ **Status**: Good, but some images lack alt text.")
            elif alt_text_coverage >= 50:
                tech_sections.append("- ❗ **Status**: Needs Improvement. Many images are missing alt text.")
            else:
                tech_sections.append("- ❌ **Status**: Critical. Most images lack alt text, impacting SEO and accessibility.")
            tech_sections.append("")
        elif crawled_pages > 0: # If pages crawled but no images found.
             tech_sections.append(f"**Image Optimization:**")
             tech_sections.append(f"- No images found across analyzed pages, or image counting was not performed.")
             tech_sections.append("")

        # Mobile Optimization
        mobile_pages = tech_stats.get('pages_with_mobile_viewport_count', 0)
        mobile_optimization = tech_stats.get('mobile_optimization_percentage', 0) # Already a percentage
        
        if crawled_pages > 0: # Only show if pages were crawled
            tech_sections.append(f"**Mobile Friendliness:**")
            tech_sections.append(f"- Pages confirmed with mobile viewport: {mobile_pages} out of {crawled_pages}")
            tech_sections.append(f"- Mobile optimization coverage: {mobile_optimization}%")
            
            if mobile_optimization >= 95:
                tech_sections.append("- ✅ **Status**: Excellent mobile optimization.")
            elif mobile_optimization >= 80:
                tech_sections.append("- ⚠️ **Status**: Good mobile optimization, minor improvements possible.")
            elif mobile_optimization >= 50:
                tech_sections.append("- ❗ **Status**: Needs Improvement. A significant number of pages may not be mobile-friendly.")
            else:
                tech_sections.append("- ❌ **Status**: Critical. Website appears largely unoptimized for mobile devices.")
            tech_sections.append("")
        
        # Technical Configuration (e.g., robots.txt)
        robots_found = tech_stats.get('robots_txt_found', False)
        tech_sections.append(f"**Basic Technical Setup:**")
        tech_sections.append(f"- Robots.txt file: {'✅ Found' if robots_found else '❌ Not found'}")
        if not robots_found:
            tech_sections.append("  - Recommendation: Add a `robots.txt` file to guide search engine crawlers. If one exists but was not detected, ensure it's accessible at the root.")
        tech_sections.append("")
        
        return tech_sections

    async def generate_comprehensive_text_report(self, llm_analysis_all: dict) -> str:
        # Extract different parts of the analysis
        main_page_analysis = llm_analysis_all.get('main_page', {})
        technical_stats = llm_analysis_all.get('technical_statistics', {})
        # Filter out main_page and technical_statistics to get other_pages
        other_pages = {url: data for url, data in llm_analysis_all.items() 
                      if url not in ['main_page', 'technical_statistics'] and data} # Ensure data is not None
        
        report_sections = []
        # Report Header
        report_sections.append("# COMPREHENSIVE SEO & CONTENT ANALYSIS REPORT")
        report_sections.append("Generated: " + time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
        report_sections.append("---") # Separator
        
        # Technical Statistics Section
        tech_sections = self._format_technical_statistics_section(technical_stats)
        report_sections.extend(tech_sections) 
        report_sections.append("---")
        
        # Main Page Analysis Section
        if main_page_analysis:
            main_url_display = main_page_analysis.get('url', 'Main Page Analysis (URL not found in analysis data)')
            llm_provider_main = main_page_analysis.get('llm_provider', 'N/A')
            report_sections.append(f"## Main Page Analysis: {main_url_display} (via {llm_provider_main})")
            if main_page_analysis.get("error"): # Display error if any
                 report_sections.append(f"  **Note:** Main page analysis encountered an error: {main_page_analysis['error']}")
            
            # Iterate through key fields for main page and add them if present
            if main_page_analysis.get('overall_tone'):
                report_sections.append(f"### Overall Content Tone")
                report_sections.append(f"- {main_page_analysis['overall_tone']}")
                report_sections.append("")

            if main_page_analysis.get('target_audience'):
                audiences_str = ", ".join(ta for ta in main_page_analysis['target_audience'] if ta)
                if audiences_str: 
                    report_sections.append(f"### Identified Target Audience(s)")
                    report_sections.append(f"- {audiences_str}")
                    report_sections.append("")

            if main_page_analysis.get('topic_categories'):
                categories_str = ", ".join(tc for tc in main_page_analysis['topic_categories'] if tc)
                if categories_str:
                    report_sections.append(f"### Main Topic Categories")
                    report_sections.append(f"- {categories_str}")
                    report_sections.append("")
            
            if main_page_analysis.get('content_summary'):
                report_sections.append(f"### Content Summary")
                report_sections.append(main_page_analysis['content_summary']) # Summary can be multi-line
                report_sections.append("")
                
            if main_page_analysis.get('keywords'):
                keywords_str = ", ".join(k for k in main_page_analysis['keywords'] if k)
                if keywords_str:
                    report_sections.append(f"### Primary Keywords Identified")
                    report_sections.append(f"- {keywords_str}")
                    report_sections.append("")
                
            if main_page_analysis.get('suggested_keywords_for_seo'):
                seo_keywords_str = ", ".join(sk for sk in main_page_analysis['suggested_keywords_for_seo'] if sk)
                if seo_keywords_str:
                    report_sections.append(f"### Suggested SEO Keywords (Low Competition / Long-Tail)")
                    report_sections.append(f"- {seo_keywords_str}")
                    report_sections.append("")
                
            if main_page_analysis.get('other_information_and_contacts'):
                report_sections.append(f"### Contact Info & Key Mentions")
                contacts_list = [c for c in main_page_analysis['other_information_and_contacts'] if c]
                if contacts_list:
                    for contact_item in contacts_list: report_sections.append(f"- {contact_item}")
                else:
                    report_sections.append("- No specific contact information or key brand/product mentions identified.")
                report_sections.append("")
                
            if main_page_analysis.get('header'): # Main page specific
                header_str = ", ".join(h for h in main_page_analysis['header'] if h)
                report_sections.append(f"### Key Header Elements")
                report_sections.append(f"- {header_str}" if header_str else "- No distinct header elements identified.")
                report_sections.append("")
                
            if main_page_analysis.get('footer'): # Main page specific
                footer_str = ", ".join(f_item for f_item in main_page_analysis['footer'] if f_item)
                report_sections.append(f"### Key Footer Elements")
                report_sections.append(f"- {footer_str}" if footer_str else "- No distinct footer elements identified.")
                report_sections.append("")
        else: # Case where main_page_analysis data is missing
            report_sections.append("## Main Page Analysis")
            report_sections.append("Main page analysis data was not available or was incomplete in `llm_analysis_all`.")
            report_sections.append("")
        report_sections.append("---")
            
        # Subpage Analysis Overview Section
        if other_pages:
            report_sections.append("## Subpage Analysis Overview")
            report_sections.append(f"Number of additional pages analyzed: {len(other_pages)}")
            report_sections.append("")
            
            # Aggregated insights from subpages
            all_subpage_keywords, all_subpage_seo_keywords, all_subpage_topic_categories = [], [], []
            all_subpage_target_audiences, all_subpage_tones = [], []
            
            report_sections.append("### Highlights from Individual Subpages:")
            for page_key, page_analysis_item in other_pages.items():
                page_url_display = page_analysis_item.get('url', page_key) # Use actual URL from item if available
                llm_provider_sub = page_analysis_item.get('llm_provider', 'N/A')
                report_sections.append(f"#### Page: {page_url_display} (via {llm_provider_sub})")
                
                if page_analysis_item.get("error"): # Display error if any for this subpage
                    report_sections.append(f"  **Note:** Analysis for this page encountered an error: {page_analysis_item['error']}")
                
                # Display key findings for each subpage
                if page_analysis_item.get('content_summary'): 
                    report_sections.append(f"  - **Summary**: {page_analysis_item['content_summary'][:200]}..." if len(page_analysis_item['content_summary']) > 200 else page_analysis_item['content_summary']) # Truncate long summaries
                if page_analysis_item.get('overall_tone'):
                    report_sections.append(f"  - **Tone**: {page_analysis_item['overall_tone']}")
                    all_subpage_tones.extend(t for t in [page_analysis_item['overall_tone']] if t)
                if page_analysis_item.get('target_audience'):
                    audiences_str_sub = ", ".join(ta for ta in page_analysis_item['target_audience'] if ta)
                    if audiences_str_sub: report_sections.append(f"  - **Audience**: {audiences_str_sub}")
                    all_subpage_target_audiences.extend(ta for ta in page_analysis_item['target_audience'] if ta)
                if page_analysis_item.get('topic_categories'):
                    categories_str_sub = ", ".join(tc for tc in page_analysis_item['topic_categories'] if tc)
                    if categories_str_sub: report_sections.append(f"  - **Topics**: {categories_str_sub}")
                    all_subpage_topic_categories.extend(tc for tc in page_analysis_item['topic_categories'] if tc)
                if page_analysis_item.get('keywords'):
                    all_subpage_keywords.extend(k for k in page_analysis_item['keywords'] if k)
                if page_analysis_item.get('suggested_keywords_for_seo'):
                    all_subpage_seo_keywords.extend(sk for sk in page_analysis_item['suggested_keywords_for_seo'] if sk)
                report_sections.append("") # Blank line after each subpage summary
            
            # Helper for creating frequency lists for aggregated data
            def get_top_items_md(items_list, title, top_n=10):
                if not items_list: return []
                from collections import Counter
                counts = Counter(k for k in items_list if k) # Filter out empty strings/None
                if not counts: return []
                sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
                md_list = [f"### {title} (Top {min(top_n, len(sorted_items))}):"]
                for item, count in sorted_items[:top_n]:
                    md_list.append(f"- {item} (mentioned in {count} subpages)")
                md_list.append("")
                return md_list

            report_sections.extend(get_top_items_md(all_subpage_keywords, "Common Keywords Across Subpages"))
            report_sections.extend(get_top_items_md(all_subpage_seo_keywords, "Frequently Suggested SEO Keywords (Subpages)"))
            report_sections.extend(get_top_items_md(all_subpage_topic_categories, "Common Topic Categories (Subpages)"))
            report_sections.extend(get_top_items_md(all_subpage_target_audiences, "Common Target Audiences (Subpages)", top_n=5))
            report_sections.extend(get_top_items_md(all_subpage_tones, "Common Content Tones (Subpages)", top_n=5))
        report_sections.append("---")

        # AI-Powered Strategic Insights & Recommendations Section
        report_sections.append("## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS")
        try:
            # Call the dedicated function to generate AI recommendations
            ai_recommendations_text = await generate_ai_recommendations_content(
                llm_analysis_all=llm_analysis_all,
                logger=self.logger,
                call_gemini_api_func=self._call_gemini_api, # Pass the API call methods
                call_mistral_api_func=self._call_mistral_api,
                gemini_model_available=bool(self.gemini_model),
                mistral_configured=bool(self.mistral_api_key and self.mistral_model_name)
            )
            report_sections.append(ai_recommendations_text if ai_recommendations_text else "No AI recommendations were generated or an issue occurred.")
        except Exception as ai_exc:
            self.logger.error(f"Failed to generate or append AI recommendations: {ai_exc}", exc_info=True)
            report_sections.append("An error occurred while generating AI-powered recommendations. Please check application logs for details.")
        report_sections.append("") # Ensure spacing after recommendations
        report_sections.append("---")
        
        # Performance Monitoring & Next Steps Section
        report_sections.append("## Performance Monitoring & Next Steps")
        report_sections.append("1. **Implement Recommendations**: Prioritize and implement the strategic, SEO, and content recommendations. Focus on high-impact, low-difficulty items first.")
        report_sections.append("2. **Track Key Metrics**: Monitor organic traffic, keyword rankings (especially for targeted and suggested keywords), user engagement (e.g., bounce rate, time on page, pages per session), and conversion rates using tools like Google Analytics and Google Search Console.")
        report_sections.append("3. **Content Performance Review**: Assess if new/updated content aligns with identified target personas and topic categories. Monitor shares, comments, and direct feedback to gauge resonance.")
        report_sections.append("4. **Technical Health**: Regularly check for technical SEO issues (e.g., crawl errors, mobile usability, site speed) via Search Console and re-audits.")
        report_sections.append("5. **Iterate and Adapt**: SEO and content marketing are ongoing processes. Continuously analyze performance data, adapt strategies based on results, and stay informed about search engine algorithm updates and industry best practices.")
        report_sections.append("---")
        report_sections.append("End of Report.")
        
        return "\n".join(report_sections)
