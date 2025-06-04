# analyzer/llm_analysis_process.py
import json
import asyncio
import time
import httpx # For Mistral API calls
from .llm_analysis_process_prompts import LLMAnalysisPrompts # Import the new prompts class

class LLMAnalysisProcess:
    def __init__(self, gemini_model, logger, mistral_api_key=None, mistral_model_name=None):
        self.gemini_model = gemini_model  # This is the initialized genai.GenerativeModel
        self.logger = logger
        self.mistral_api_key = mistral_api_key
        self.mistral_model_name = mistral_model_name

    async def _call_gemini_api(self, prompt_text: str) -> str:
        if not self.gemini_model: # Corrected: was self.model
            self.logger.error("Gemini model not initialized. Cannot make API call.")
            return ""
        try:
            response = await asyncio.to_thread(
                self.gemini_model.generate_content, # Corrected: was self.model
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
            self.logger.warning(f"LLM response (Gemini) was empty or did not contain text. Full response object: {response}")
            return ""
        except Exception as e:
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
        api_url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.mistral_model_name,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.7, 
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client: 
                api_response = await client.post(api_url, headers=headers, json=payload)
                api_response.raise_for_status() 
            
            data = api_response.json()
            if data.get("choices") and data["choices"][0].get("message") and data["choices"][0]["message"].get("content"):
                response_text = data["choices"][0]["message"]["content"]
                if not response_text.strip():
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
        base_result = {
            "url": page_url,
            "keywords": [],
            "content_summary": "",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "overall_tone": "",
            "target_audience": [],
            "topic_categories": [],
            "llm_provider": "N/A"
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
        
        max_text_len = 22000
        truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')
        
        # Use LLMAnalysisPrompts to build the prompt
        prompt = LLMAnalysisPrompts.build_single_page_analysis_prompt(
            page_url=page_url,
            truncated_cleaned_text=truncated_cleaned_text,
            headings_data=headings_data,
            is_main_page=is_main_page
        )
        
        llm_response_str = None
        llm_provider = "N/A"
        error_message_for_return = "LLM analysis failed for both primary and fallback providers."

        try:
            if self.gemini_model:
                self.logger.debug(f"Attempting LLM analysis with Gemini for URL: {page_url} (Main page: {is_main_page})")
                llm_response_str = await self._call_gemini_api(prompt)
                llm_provider = "Gemini"
            
            if not llm_response_str:
                if self.gemini_model: 
                    self.logger.warning(f"Gemini returned empty or no-text response for URL: {page_url}. Attempting Mistral fallback.")
                else: 
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
                    else: 
                        self.logger.error(f"Mistral fallback for {page_url} returned empty response without explicit error.")
                        error_message_for_return = "Gemini primary failed/not configured; Mistral fallback returned empty."
                else:
                    self.logger.warning(f"LLM (Gemini) failed or not configured, and Mistral is not configured. Cannot analyze URL: {page_url}")
                    error_message_for_return = "Primary LLM (Gemini) failed or not configured; Mistral fallback not configured."
            
            if not llm_response_str: 
                self.logger.error(f"All LLM attempts failed for URL: {page_url}. Final error state: {error_message_for_return}")
                return {**base_result, "error": error_message_for_return, "llm_provider": llm_provider}

            try:
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
            if is_main_page:
                analysis_result.update({
                    "header": llm_data.get("header", base_result.get("header", [])),
                    "footer": llm_data.get("footer", base_result.get("footer", []))
                })
            self.logger.info(f"Successfully completed LLM analysis via {llm_provider} for URL: {page_url} (Main page: {is_main_page})")
            return analysis_result
        except Exception as e:
            self.logger.error(f"Unexpected error during LLM analysis processing for URL {page_url}: {e}", exc_info=True)
            return {**base_result, "error": f"An unexpected error occurred: {str(e)}", "llm_provider": llm_provider}

    def _format_technical_statistics_section(self, tech_stats: dict) -> list:
        """Format technical statistics into report sections."""
        if not tech_stats:
            return ["## Technical SEO Overview", "Technical statistics data not available.", ""]
        
        tech_sections = []
        tech_sections.append("## Technical SEO Overview")
        
        crawled_pages = tech_stats.get('crawled_internal_pages_count', 0)
        analysis_duration = tech_stats.get('analysis_duration_seconds', 0)
        tech_sections.append(f"**Website Analysis Summary:**")
        tech_sections.append(f"- Total pages crawled and analyzed: {crawled_pages}")
        if analysis_duration > 0:
            minutes = analysis_duration // 60
            seconds = analysis_duration % 60
            if minutes > 0:
                tech_sections.append(f"- Analysis duration: {minutes} minutes {seconds} seconds")
            else:
                tech_sections.append(f"- Analysis duration: {seconds} seconds")
        tech_sections.append("")
        
        total_content_length = tech_stats.get('total_cleaned_content_length', 0)
        avg_content_length = tech_stats.get('average_cleaned_content_length_per_page', 0)
        total_headings = tech_stats.get('total_headings_count', 0)
        
        tech_sections.append(f"**Content Analysis:**")
        if total_content_length > 0:
            tech_sections.append(f"- Total content analyzed: {total_content_length:,} characters")
        if avg_content_length > 0:
            tech_sections.append(f"- Average content per page: {avg_content_length:,} characters")
        if total_headings > 0:
            tech_sections.append(f"- Total headings found: {total_headings}")
        tech_sections.append("")
        
        total_images = tech_stats.get('total_images_count', 0)
        missing_alt_tags = tech_stats.get('total_missing_alt_tags_count', 0)
        alt_text_coverage = tech_stats.get('alt_text_coverage_percentage', 0)
        
        if total_images > 0:
            tech_sections.append(f"**Image Optimization Analysis:**")
            tech_sections.append(f"- Total images found: {total_images}")
            tech_sections.append(f"- Images missing alt text: {missing_alt_tags}")
            tech_sections.append(f"- Alt text coverage: {alt_text_coverage}%")
            
            if alt_text_coverage >= 90:
                tech_sections.append("- ✅ **Excellent**: Alt text coverage is very good")
            elif alt_text_coverage >= 70:
                tech_sections.append("- ⚠️ **Good**: Alt text coverage is decent but could be improved")
            elif alt_text_coverage >= 50:
                tech_sections.append("- ⚠️ **Needs Improvement**: Many images lack alt text")
            else:
                tech_sections.append("- ❌ **Critical Issue**: Most images are missing alt text")
            tech_sections.append("")
        
        mobile_pages = tech_stats.get('pages_with_mobile_viewport_count', 0)
        mobile_optimization = tech_stats.get('mobile_optimization_percentage', 0)
        
        if crawled_pages > 0:
            tech_sections.append(f"**Mobile Optimization:**")
            tech_sections.append(f"- Pages with mobile viewport: {mobile_pages} out of {crawled_pages}")
            tech_sections.append(f"- Mobile optimization coverage: {mobile_optimization}%")
            
            if mobile_optimization >= 95:
                tech_sections.append("- ✅ **Excellent**: Nearly all pages are mobile-optimized")
            elif mobile_optimization >= 80:
                tech_sections.append("- ⚠️ **Good**: Most pages are mobile-optimized")
            elif mobile_optimization >= 50:
                tech_sections.append("- ⚠️ **Needs Improvement**: Some pages lack mobile optimization")
            else:
                tech_sections.append("- ❌ **Critical Issue**: Many pages are not mobile-optimized")
            tech_sections.append("")
        
        robots_found = tech_stats.get('robots_txt_found', False)
        tech_sections.append(f"**Technical Configuration:**")
        tech_sections.append(f"- Robots.txt file: {'✅ Found' if robots_found else '❌ Not found'}")
        if not robots_found:
            tech_sections.append("  - Consider adding a robots.txt file to guide search engine crawlers")
        tech_sections.append("")
        
        return tech_sections

    async def _generate_ai_recommendations(self, llm_analysis_all: dict) -> str:
        primary_llm_available = bool(self.gemini_model)
        fallback_llm_available = bool(self.mistral_api_key and self.mistral_model_name)

        if not primary_llm_available and not fallback_llm_available:
            self.logger.error("Neither Gemini nor Mistral is configured. Cannot generate AI recommendations.")
            return "AI recommendations could not be generated due to model initialization/configuration issues."
            
        main_page_analysis = llm_analysis_all.get('main_page', {})
        technical_stats = llm_analysis_all.get('technical_statistics', {})
        other_pages = {url: data for url, data in llm_analysis_all.items() 
                        if url not in ['main_page', 'technical_statistics'] and data}
        
        all_keywords = []
        all_seo_keywords = []
        all_topic_categories = []
        all_target_audiences = []
        all_tones = []
        all_summaries = []
        
        if main_page_analysis and not main_page_analysis.get('error'):
            all_keywords.extend(k for k in main_page_analysis.get('keywords', []) if k)
            all_seo_keywords.extend(sk for sk in main_page_analysis.get('suggested_keywords_for_seo', []) if sk)
            all_topic_categories.extend(tc for tc in main_page_analysis.get('topic_categories', []) if tc)
            all_target_audiences.extend(ta for ta in main_page_analysis.get('target_audience', []) if ta)
            if main_page_analysis.get('overall_tone'):
                all_tones.append(main_page_analysis.get('overall_tone'))
            if main_page_analysis.get('content_summary'):
                all_summaries.append(f"Main Page ({main_page_analysis.get('url', 'N/A')}): {main_page_analysis.get('content_summary')}")
        
        for page_url, page_data in other_pages.items():
            if page_data and not page_data.get('error'):
                all_keywords.extend(k for k in page_data.get('keywords', []) if k)
                all_seo_keywords.extend(sk for sk in page_data.get('suggested_keywords_for_seo', []) if sk)
                all_topic_categories.extend(tc for tc in page_data.get('topic_categories', []) if tc)
                all_target_audiences.extend(ta for ta in page_data.get('target_audience', []) if ta)
                if page_data.get('overall_tone'):
                    all_tones.append(page_data.get('overall_tone'))
                if page_data.get('content_summary'):
                    all_summaries.append(f"{page_url}: {page_data.get('content_summary')}")
        
        website_data_summary = {
            "total_pages_analyzed": len([p for p_url, p in llm_analysis_all.items() 
                                        if p and not p.get('error') and p_url not in ['technical_statistics']]),
            "main_page_url": main_page_analysis.get('url', 'Unknown'),
            "all_keywords": list(set(all_keywords)),
            "all_seo_keywords": list(set(all_seo_keywords)),
            "all_topic_categories": list(set(all_topic_categories)),
            "all_target_audiences": list(set(all_target_audiences)),
            "all_content_tones": list(set(all_tones)),
            "content_summaries_sample": all_summaries[:15],
            "main_page_header_elements": main_page_analysis.get('header', []),
            "main_page_footer_elements": main_page_analysis.get('footer', []),
            "technical_statistics": technical_stats
        }
        
        # Use LLMAnalysisPrompts to build the AI recommendations prompt
        prompt = LLMAnalysisPrompts.build_ai_recommendations_prompt(website_data_summary)
        
        ai_response_str = None
        llm_provider_recs = "N/A"
        error_message_for_recs = "AI recommendations failed for both primary and fallback LLMs."

        try:
            if primary_llm_available:
                self.logger.info(f"Generating AI-powered recommendations (Gemini attempt) for main URL: {website_data_summary['main_page_url']}")
                ai_response_str = await self._call_gemini_api(prompt)
                llm_provider_recs = "Gemini"

            if not ai_response_str:
                if primary_llm_available:
                     self.logger.warning("Gemini returned empty response for AI recommendations. Attempting Mistral fallback.")
                else: 
                     self.logger.info("Gemini not available. Attempting AI recommendations with Mistral.")

                if fallback_llm_available:
                    mistral_response, mistral_error = await self._call_mistral_api(prompt, purpose="ai_recommendations_fallback")
                    if mistral_error:
                        self.logger.error(f"Mistral fallback for AI recommendations also failed: {mistral_error}")
                        error_message_for_recs = f"Primary LLM (Gemini) failed/not configured; Mistral fallback for recommendations failed: {mistral_error}"
                    elif mistral_response:
                        ai_response_str = mistral_response
                        llm_provider_recs = "Mistral (fallback)"
                        self.logger.info("Successfully used Mistral as fallback for AI recommendations.")
                    else:
                        self.logger.error("Mistral fallback for AI recommendations returned empty response without explicit error.")
                        error_message_for_recs = "Primary LLM (Gemini) failed/not configured; Mistral fallback for recommendations returned empty."
                else:
                    self.logger.warning("Primary LLM failed/not configured for recommendations, and Mistral is not configured.")
                    error_message_for_recs = "Primary LLM (Gemini) failed/not configured for recommendations; Mistral fallback not configured."
            
            if not ai_response_str:
                self.logger.error(f"All LLM attempts for AI recommendations failed. Final error state: {error_message_for_recs}")
                return f"AI recommendations could not be generated. {error_message_for_recs}"
            
            try:
                cleaned_response = ai_response_str.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                recommendations_data = json.loads(cleaned_response)
                
                formatted_recommendations = []
                
                strategic_recs = recommendations_data.get('strategic_recommendations', [])
                if strategic_recs:
                    formatted_recommendations.append("### Strategic Recommendations")
                    for i, rec in enumerate(strategic_recs, 1):
                        category = rec.get('category', 'General')
                        title = rec.get('title', 'Recommendation')
                        description = rec.get('description', '')
                        priority = rec.get('priority', 'Medium')
                        difficulty = rec.get('implementation_difficulty', 'Medium')
                        based_on_data = rec.get('based_on_data', '')
                        
                        formatted_recommendations.append(f"#### {i}. {title} ({category})")
                        formatted_recommendations.append(f"**Priority**: {priority} | **Implementation**: {difficulty}")
                        if based_on_data:
                            formatted_recommendations.append(f"**Data Source**: {based_on_data}")
                        formatted_recommendations.append(description)
                        formatted_recommendations.append("")
                
                seo_recs = recommendations_data.get('seo_content_optimization', [])
                if seo_recs:
                    formatted_recommendations.append("### SEO & Content Optimization")
                    for rec in seo_recs:
                        focus_area = rec.get('focus_area', 'SEO Suggestion')
                        current_issue = rec.get('current_issue', '')
                        recommendation = rec.get('recommendation', '')
                        expected_impact = rec.get('expected_impact', '')
                        pages_affected = rec.get('pages_affected', [])
                        
                        formatted_recommendations.append(f"#### {focus_area}")
                        if current_issue:
                            formatted_recommendations.append(f"**Current Issue**: {current_issue}")
                        formatted_recommendations.append(f"**Recommendation**: {recommendation}")
                        if expected_impact:
                            formatted_recommendations.append(f"**Expected Impact**: {expected_impact}")
                        if pages_affected:
                            formatted_recommendations.append(f"**Pages Affected**: {', '.join(pages_affected)}")
                        formatted_recommendations.append("")
                
                content_insights = recommendations_data.get('content_strategy_insights', [])
                if content_insights:
                    formatted_recommendations.append("### Content Strategy Insights")
                    for i, insight_data in enumerate(content_insights, 1):
                        insight = insight_data.get('insight', '')
                        supporting_data = insight_data.get('supporting_data', '')
                        action_items = insight_data.get('action_items', [])
                        
                        formatted_recommendations.append(f"#### Insight {i}: {insight}")
                        if supporting_data:
                            formatted_recommendations.append(f"**Supporting Data**: {supporting_data}")
                        if action_items:
                            formatted_recommendations.append("**Action Items:**")
                            for item in action_items:
                                action_type = item.get('action_type', 'Action')
                                page_url = item.get('page_url', 'N/A')
                                title = item.get('title', 'N/A')
                                description = item.get('description', '')
                                priority = item.get('priority', 'Medium')
                                
                                formatted_recommendations.append(f"- **{action_type}** ({priority} Priority)")
                                formatted_recommendations.append(f"  - **Page**: {page_url}")
                                formatted_recommendations.append(f"  - **Title**: {title}")
                                formatted_recommendations.append(f"  - **Description**: {description}")
                                
                                if item.get('social_media_opportunity'):
                                    formatted_recommendations.append(f"  - **Social Media**: {item.get('social_media_opportunity')}")
                                if item.get('media_suggestions'):
                                    formatted_recommendations.append(f"  - **Media**: {item.get('media_suggestions')}")
                                if item.get('headings_structure'):
                                    formatted_recommendations.append(f"  - **Suggested Headings**: {', '.join(item.get('headings_structure'))}")
                        formatted_recommendations.append("")

                article_tasks = recommendations_data.get('article_content_tasks', [])
                if article_tasks:
                    formatted_recommendations.append("### Article Content Tasks")
                    for i, task in enumerate(article_tasks, 1):
                        formatted_recommendations.append(f"#### Article Task {i}")
                        formatted_recommendations.append(f"**Focus Keyword**: {task.get('focus_keyword', 'N/A')}")
                        formatted_recommendations.append(f"**Content Length**: {task.get('content_length', 'Medium')}")
                        formatted_recommendations.append(f"**Tone**: {task.get('article_tone', 'Professional')}")
                        formatted_recommendations.append(f"**Suggested Title**: {task.get('suggested_title', 'N/A')}")
                        formatted_recommendations.append(f"**Target Page**: {task.get('target_page_url', 'New page')}")
                        formatted_recommendations.append(f"**Content Gap Addressed**: {task.get('content_gap_addressed', 'N/A')}")
                        formatted_recommendations.append(f"**Target Audience**: {task.get('target_audience', 'General')}")
                        
                        additional_keywords = task.get('additional_keywords', [])
                        if additional_keywords:
                            formatted_recommendations.append(f"**Additional Keywords**: {', '.join(additional_keywords)}")
                        formatted_recommendations.append("")

                product_tasks = recommendations_data.get('product_content_tasks', [])
                if product_tasks:
                    formatted_recommendations.append("### Product Content Tasks")
                    for i, task in enumerate(product_tasks, 1):
                        formatted_recommendations.append(f"#### Product Task {i}")
                        formatted_recommendations.append(f"**Product Name**: {task.get('product_name', 'N/A')}")
                        formatted_recommendations.append(f"**Tone**: {task.get('tone', 'Professional')}")
                        formatted_recommendations.append(f"**Description Length**: {task.get('description_length', 'Medium')}")
                        formatted_recommendations.append(f"**Target Page**: {task.get('target_page_url', 'N/A')}")
                        formatted_recommendations.append(f"**Competitive Advantage**: {task.get('competitive_advantage', 'N/A')}")
                        
                        product_details = task.get('product_details', {})
                        if product_details.get('features'):
                            formatted_recommendations.append(f"**Features**: {', '.join(product_details.get('features'))}")
                        if product_details.get('benefits'):
                            formatted_recommendations.append(f"**Benefits**: {', '.join(product_details.get('benefits'))}")
                        if product_details.get('target_audience'):
                            formatted_recommendations.append(f"**Target Audience**: {product_details.get('target_audience')}")
                        
                        seo_keywords = task.get('seo_keywords', [])
                        if seo_keywords:
                            formatted_recommendations.append(f"**SEO Keywords**: {', '.join(seo_keywords)}")
                        formatted_recommendations.append("")
                
                if not formatted_recommendations:
                    self.logger.warning(f"AI ({llm_provider_recs}) generated data for recommendations, but no specific sections were populated.")
                    return f"AI ({llm_provider_recs}) generated data, but it was not in the expected format or was empty."

                self.logger.info(f"Successfully generated and formatted AI-powered recommendations using {llm_provider_recs}.")
                return "\n".join(formatted_recommendations)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse AI recommendations JSON from {llm_provider_recs}: {e}. Raw response: '{ai_response_str[:500]}'")
                return f"AI recommendations were generated by {llm_provider_recs} but could not be parsed properly. Raw response (first 500 chars): {ai_response_str[:500]}..."
                
        except Exception as e:
            self.logger.error(f"Error generating AI recommendations: {e}", exc_info=True)
            return f"An error occurred while generating AI recommendations: {str(e)}"


    async def generate_comprehensive_text_report(self, llm_analysis_all: dict) -> str:
        main_page_analysis = llm_analysis_all.get('main_page', {})
        technical_stats = llm_analysis_all.get('technical_statistics', {})
        other_pages = {url: data for url, data in llm_analysis_all.items() 
                      if url not in ['main_page', 'technical_statistics'] and data}
        
        report_sections = []
        report_sections.append("# COMPREHENSIVE SEO ANALYSIS REPORT")
        report_sections.append("Generated: " + time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
        report_sections.append("")
        
        tech_sections = self._format_technical_statistics_section(technical_stats)
        report_sections.extend(tech_sections) 
        report_sections.append("")
        
        if main_page_analysis:
            main_url_display = main_page_analysis.get('url', 'Main Page Analysis (URL not found in analysis data)')
            llm_provider_main = main_page_analysis.get('llm_provider', 'N/A')
            report_sections.append(f"## Main Page Analysis: {main_url_display} (via {llm_provider_main})")
            if main_page_analysis.get("error"):
                 report_sections.append(f"**Note:** Main page analysis encountered an error: {main_page_analysis['error']}")
            
            overall_tone = main_page_analysis.get('overall_tone', '')
            if overall_tone:
                report_sections.append(f"### Overall Content Tone")
                report_sections.append(overall_tone)
                report_sections.append("")

            target_audience = main_page_analysis.get('target_audience', [])
            if target_audience: 
                audiences_str = ", ".join(ta for ta in target_audience if ta)
                if audiences_str: 
                    report_sections.append(f"### Identified Target Audience")
                    report_sections.append(audiences_str)
                    report_sections.append("")

            topic_categories = main_page_analysis.get('topic_categories', [])
            if topic_categories:
                categories_str = ", ".join(tc for tc in topic_categories if tc)
                if categories_str:
                    report_sections.append(f"### Main Topic Categories")
                    report_sections.append(categories_str)
                    report_sections.append("")
            
            content_summary = main_page_analysis.get('content_summary', '')
            if content_summary:
                report_sections.append(f"### Content Summary")
                report_sections.append(content_summary)
                report_sections.append("")
                
            keywords = main_page_analysis.get('keywords', [])
            if keywords:
                keywords_str = ", ".join(k for k in keywords if k)
                if keywords_str:
                    report_sections.append(f"### Primary Keywords")
                    report_sections.append(keywords_str)
                    report_sections.append("")
                
            seo_keywords = main_page_analysis.get('suggested_keywords_for_seo', [])
            if seo_keywords:
                seo_keywords_str = ", ".join(sk for sk in seo_keywords if sk)
                if seo_keywords_str:
                    report_sections.append(f"### Suggested SEO Keywords")
                    report_sections.append(seo_keywords_str)
                    report_sections.append("")
                
            contacts = main_page_analysis.get('other_information_and_contacts', [])
            if contacts:
                report_sections.append(f"### Contact Information & Key Mentions")
                has_contacts = False
                for contact_item in contacts:
                    if contact_item: 
                        report_sections.append(f"- {contact_item}")
                        has_contacts = True
                if not has_contacts:
                    report_sections.append("No specific contact information or key mentions identified.")
                report_sections.append("")
                
            header = main_page_analysis.get('header', [])
            if header:
                header_str = ", ".join(h for h in header if h)
                report_sections.append(f"### Header Elements")
                report_sections.append(header_str if header_str else "No distinct header elements identified.")
                report_sections.append("")
                
            footer = main_page_analysis.get('footer', [])
            if footer:
                footer_str = ", ".join(f_item for f_item in footer if f_item)
                report_sections.append(f"### Footer Elements")
                report_sections.append(footer_str if footer_str else "No distinct footer elements identified.")
                report_sections.append("")
        else:
            report_sections.append("## Main Page Analysis")
            report_sections.append("Main page analysis data was not available or incomplete in llm_analysis_all.")
            report_sections.append("")
            
        if other_pages:
            report_sections.append("## Subpage Analysis Overview")
            report_sections.append(f"Number of additional pages analyzed: {len(other_pages)}")
            report_sections.append("")
            
            all_subpage_keywords = []
            all_subpage_seo_keywords = []
            all_subpage_topic_categories = []
            all_subpage_target_audiences = []
            all_subpage_tones = []
            
            report_sections.append("### Individual Subpage Highlights")
            for page_key, page_analysis_item in other_pages.items():
                page_url_display = page_analysis_item.get('url', page_key)
                llm_provider_sub = page_analysis_item.get('llm_provider', 'N/A')
                report_sections.append(f"#### Page: {page_url_display} (via {llm_provider_sub})")
                
                if page_analysis_item.get("error"):
                    report_sections.append(f"  **Note:** Analysis for this page encountered an error: {page_analysis_item['error']}")
                
                content_summary_sub = page_analysis_item.get('content_summary', '')
                if content_summary_sub: 
                    report_sections.append(f"  **Summary**: {content_summary_sub}")
                
                subpage_overall_tone = page_analysis_item.get('overall_tone', '')
                if subpage_overall_tone:
                    report_sections.append(f"  **Overall Tone**: {subpage_overall_tone}")
                    all_subpage_tones.append(subpage_overall_tone)
                
                subpage_target_audience = page_analysis_item.get('target_audience', [])
                if subpage_target_audience:
                    audiences_str_sub = ", ".join(ta for ta in subpage_target_audience if ta)
                    if audiences_str_sub: 
                        report_sections.append(f"  **Target Audience**: {audiences_str_sub}")
                    all_subpage_target_audiences.extend(ta for ta in subpage_target_audience if ta)

                subpage_topic_categories = page_analysis_item.get('topic_categories', [])
                if subpage_topic_categories:
                    categories_str_sub = ", ".join(tc for tc in subpage_topic_categories if tc)
                    if categories_str_sub: 
                        report_sections.append(f"  **Topic Categories**: {categories_str_sub}")
                    all_subpage_topic_categories.extend(tc for tc in subpage_topic_categories if tc)
                
                keywords_sub = page_analysis_item.get('keywords', [])
                if keywords_sub:
                    keywords_str_sub = ", ".join(k for k in keywords_sub if k)
                    if keywords_str_sub: 
                        report_sections.append(f"  **Keywords**: {keywords_str_sub}")
                    all_subpage_keywords.extend(k for k in keywords_sub if k)
                    
                seo_keywords_sub = page_analysis_item.get('suggested_keywords_for_seo', [])
                if seo_keywords_sub:
                    seo_keywords_str_sub = ", ".join(sk for sk in seo_keywords_sub if sk)
                    if seo_keywords_str_sub: 
                        report_sections.append(f"  **SEO Keyword Suggestions**: {seo_keywords_str_sub}")
                    all_subpage_seo_keywords.extend(sk for sk in seo_keywords_sub if sk)

                contacts_sub = page_analysis_item.get('other_information_and_contacts', [])
                if contacts_sub:
                    report_sections.append(f"  **Contact Information & Key Mentions**:")
                    has_sub_contacts = False
                    for contact_item_sub in contacts_sub:
                        if contact_item_sub:
                            report_sections.append(f"    - {contact_item_sub}")
                            has_sub_contacts = True
                    if not has_sub_contacts:
                         report_sections.append("    No specific contact information or key mentions identified on this subpage.")
                report_sections.append("")
            
            if all_subpage_keywords:
                keyword_count = {k: all_subpage_keywords.count(k) for k in set(all_subpage_keywords) if k}
                sorted_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_keywords:
                    report_sections.append("## Site-Wide Subpage Keyword Analysis")
                    report_sections.append("Most common keywords across analyzed subpages (top 15):")
                    for kw, count in sorted_keywords[:15]: 
                        report_sections.append(f"- {kw} (found in {count} subpages)")
                    report_sections.append("")
                
            if all_subpage_seo_keywords:
                seo_keyword_count = {k: all_subpage_seo_keywords.count(k) for k in set(all_subpage_seo_keywords) if k}
                sorted_seo_keywords = sorted(seo_keyword_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_seo_keywords:
                    report_sections.append("## Site-Wide Subpage SEO Suggestions")
                    report_sections.append("Most frequently suggested SEO keywords for subpages (top 10):")
                    for kw, count in sorted_seo_keywords[:10]: 
                        report_sections.append(f"- {kw} (suggested for {count} subpages)")
                    report_sections.append("")
            
            if all_subpage_topic_categories:
                topic_category_count = {k: all_subpage_topic_categories.count(k) for k in set(all_subpage_topic_categories) if k}
                sorted_topic_categories = sorted(topic_category_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_topic_categories:
                    report_sections.append("## Site-Wide Topic Categories Analysis (Subpages)")
                    report_sections.append("Most common topic categories across analyzed subpages (top 10):")
                    for tc, count in sorted_topic_categories[:10]: 
                        report_sections.append(f"- {tc} (found in {count} subpages)")
                    report_sections.append("")

            if all_subpage_target_audiences:
                target_audience_count = {k: all_subpage_target_audiences.count(k) for k in set(all_subpage_target_audiences) if k}
                sorted_target_audiences = sorted(target_audience_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_target_audiences:
                    report_sections.append("## Site-Wide Target Audience Analysis (Subpages)")
                    report_sections.append("Most common target audiences across analyzed subpages (top 8):")
                    for ta, count in sorted_target_audiences[:8]: 
                        report_sections.append(f"- {ta} (identified in {count} subpages)")
                    report_sections.append("")

            if all_subpage_tones:
                tone_count = {k: all_subpage_tones.count(k) for k in set(all_subpage_tones) if k}
                sorted_tones = sorted(tone_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_tones:
                    report_sections.append("## Site-Wide Content Tone Analysis (Subpages)")
                    report_sections.append("Most common content tones across analyzed subpages:")
                    for tone, count in sorted_tones: 
                        report_sections.append(f"- {tone} (found in {count} subpages)")
                    report_sections.append("")

        report_sections.append("## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS")
        try:
            ai_recommendations_text = await self._generate_ai_recommendations(llm_analysis_all)
            report_sections.append(ai_recommendations_text)
        except Exception as ai_exc:
            self.logger.error(f"Failed to generate or append AI recommendations: {ai_exc}", exc_info=True)
            report_sections.append("An error occurred while generating AI-powered recommendations. Please check logs.")
        report_sections.append("")
        
        report_sections.append("## Performance Monitoring & Next Steps")
        report_sections.append("1. **Implement Recommendations**: Prioritize and implement the strategic and SEO recommendations provided. Start with high-priority, easy-to-implement items for quick wins.")
        report_sections.append("2. **Monitor Key Metrics**: Track rankings for target keywords, organic traffic, user engagement (bounce rate, time on page), and conversion rates. Use tools like Google Analytics and Google Search Console.")
        report_sections.append("3. **Audience Engagement**: Validate that content resonates with identified target audiences. Monitor social shares, comments, and feedback. Adjust content strategy based on performance data.")
        report_sections.append("4. **Regular Audits**: Conduct periodic SEO and content audits (e.g., quarterly or bi-annually) to identify new opportunities and ensure the site remains optimized.")
        report_sections.append("5. **Stay Updated**: SEO is dynamic. Keep abreast of search engine algorithm updates and industry best practices.")
        
        return "\n".join(report_sections)