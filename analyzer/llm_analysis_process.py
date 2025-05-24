# analyzer/llm_analysis_process.py
import json
import asyncio
import time

class LLMAnalysisProcess:
    def __init__(self, model, logger):
        self.model = model
        self.logger = logger

    async def _call_gemini_api(self, prompt_text: str) -> str:
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

    async def analyze_single_page(self, page_url: str, page_data: dict, is_main_page: bool = False) -> dict:
        base_result = {
            "url": page_url,
            "keywords": [],
            "content_summary": "",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "overall_tone": "",
            "target_audience": [],
            "topic_categories": []
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
            "suggested_keywords_for_seo": ["string"],
            "overall_tone": "string",
            "target_audience": ["string"],
            "topic_categories": ["string"]
        }
        if is_main_page:
            json_structure_for_llm.update({
                "header": ["string"],
                "footer": ["string"]
            })

        detailed_instructions_keywords = """1. **"keywords"**:
        * Identify and list the top 7-10 most relevant and frequently occurring keywords or key phrases from the page content and headings.
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
        * If the page mentions specific individuals (e.g., team members, authors), list their names and roles if available. Turkish names and surnames can be longer.
        * Format each piece of information as a descriptive string in a list. Put the relevant information next to each other.
        * Example: ["Email: contact@example.com", "Phone: (555) 123-4567", "Main Office: 123 Innovation Drive, Tech City", "Product: Alpha Suite", "Twitter: https://twitter.com/example"]
        * If no such information is found, return an empty list []."""
        detailed_instructions_seo_keywords = """4. **"suggested_keywords_for_seo"**:
        * Based on the page content and its main topics, suggest 3-5 additional keywords or key phrases that could be targeted for low competitive SEO.
        * Plus to those suggest 3-5 more should be relevant variations, related topics or potential long-tail and alternatives but relevant keywords. Dont use alternative region , city names if its not in the content.
        * Consider user intent (informational, transactional, navigational). Example: ["benefits of data analysis", "best cloud providers for small business", "custom enterprise software development"]
        * If no strong distinct suggestions can be made, return an empty list []."""
        detailed_instructions_overall_tone = """5. **"overall_tone"**:
        * Describe the general tone or style of the content on the page (e.g., formal, informal, professional, casual, authoritative, promotional, educational, humorous, technical).
        * Provide a single, concise descriptive word or short phrase. Example: "professional and informative", "casual and engaging"."""
        detailed_instructions_target_audience = """6. **"target_audience"**:
        * Identify the primary target audience(s) for the content on this page. Consider who the content is intended for (e.g., businesses, consumers, technical professionals, students, specific demographics).
        * List 1-3 distinct groups as strings. Example: ["small business owners", "software developers", "parents"]
        * If not clearly discernible, return an empty list []."""
        detailed_instructions_topic_categories = """7. **"topic_categories"**:
        * Categorize the main topics or themes covered on the page into 2-4 broad categories. Think of general industry or subject areas.
        * Example: ["Software Development", "Digital Marketing", "Financial Services", "Health & Wellness"]
        * If no clear categories, return an empty list []."""
        
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
    {json.dumps(headings_data, indent=2, ensure_ascii=False)}
    ---
    Based on the provided text and headings, generate a JSON object strictly adhering to the following structure.
    Output ONLY the JSON object. Do NOT include any explanatory text, markdown formatting, or anything else outside the JSON object itself.
    {json.dumps(json_structure_for_llm, indent=2)}
    **Detailed Instructions for populating each field in the JSON object:**
    {detailed_instructions_keywords}
    {detailed_instructions_summary}
    {detailed_instructions_contacts}
    {detailed_instructions_seo_keywords}
    {detailed_instructions_overall_tone}
    {detailed_instructions_target_audience}
    {detailed_instructions_topic_categories}
    """
        if is_main_page:
            detailed_instructions_header = """8. **"header"**:
        * From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main header.
        * This typically includes site navigation links (e.g., "Home", "About Us", "Services", "Contact"), site branding text (e.g., company name if prominently in header), or a primary tagline.
        * Provide these as a list of strings. Each string can be a distinct link text or a phrase from the header.
        * If no clear header text is discernible, return an empty list [].
        * Example: ["Home", "Products", "Blog", "Login", "Site Title Example Inc."]"""
            detailed_instructions_footer = """9. **"footer"**:
        * From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main footer.
        * This typically includes copyright notices, links to privacy policy, terms of service, sitemap, contact information repeated in the footer, or social media links.
        * Provide these as a list of strings. Each string can be a distinct link text or a phrase from the footer.
        * If no clear footer text is discernible, return an empty list [].
        * Example: ["© 2024 Company Name", "Privacy Policy", "Terms of Use", "Contact Us", "Follow us on Twitter" , "Bizi Arayın : (555) 123-4567"]"""
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
                "overall_tone": llm_data.get("overall_tone", base_result["overall_tone"]),
                "target_audience": llm_data.get("target_audience", base_result["target_audience"]),
                "topic_categories": llm_data.get("topic_categories", base_result["topic_categories"])
            }
            if is_main_page:
                analysis_result.update({
                    "header": llm_data.get("header", base_result.get("header", [])),
                    "footer": llm_data.get("footer", base_result.get("footer", []))
                })
            self.logger.info(f"Successfully completed LLM analysis for URL: {page_url} (Main page: {is_main_page})")
            return analysis_result
        except Exception as e:
            self.logger.error(f"Unexpected error during LLM analysis processing for URL {page_url}: {e}", exc_info=True)
            return {**base_result, "error": f"An unexpected error occurred: {str(e)}"}

    async def _generate_ai_recommendations(self, llm_analysis_all: dict) -> str:
        """Generate AI-powered recommendations based on the complete website analysis."""
        if not self.model:
            self.logger.error("Gemini model not initialized. Cannot generate AI recommendations.")
            return "AI recommendations could not be generated due to model initialization issues."
        
        try:
            main_page_analysis = llm_analysis_all.get('main_page', {})
            other_pages = {url: data for url, data in llm_analysis_all.items() if url != 'main_page' and data}
            
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
                "total_pages_analyzed": len([p for p_url, p in llm_analysis_all.items() if p and not p.get('error')]),
                "main_page_url": main_page_analysis.get('url', 'Unknown'),
                "all_keywords": list(set(all_keywords)),
                "all_seo_keywords": list(set(all_seo_keywords)),
                "all_topic_categories": list(set(all_topic_categories)),
                "all_target_audiences": list(set(all_target_audiences)),
                "all_content_tones": list(set(all_tones)),
                "content_summaries_sample": all_summaries[:10],
                "main_page_header_elements": main_page_analysis.get('header', []),
                "main_page_footer_elements": main_page_analysis.get('footer', [])
            }
            
            prompt = f"""
Based on the comprehensive SEO and content analysis of this website, provide strategic recommendations and actionable SEO optimization suggestions.
Language: Turkish if the content is primarily in Turkish, otherwise English.
The analysis includes:
WEBSITE ANALYSIS DATA:
{json.dumps(website_data_summary, indent=2, ensure_ascii=False)}

Generate recommendations in the following JSON structure:
{{
    "strategic_recommendations": [
        {{
            "category": "string (e.g., 'SEO Optimization', 'Content Strategy', 'Technical SEO', 'User Experience')",
            "title": "string (brief title for the recommendation)",
            "description": "string (detailed explanation and actionable steps)",
            "priority": "string (High/Medium/Low)",
            "implementation_difficulty": "string (Easy/Medium/Hard)"
        }}
    ],
    "seo_content_optimization": [
        {{
            "focus_area": "string (e.g., 'Keyword Strategy', 'Content Gaps', 'Internal Linking', 'Meta Optimization')",
            "recommendation": "string (specific actionable recommendation)",
            "expected_impact": "string (what improvement to expect)"
        }}
    ],
    "content_strategy_insights": [
        {{
            "insight": "string (key insight about content strategy)",
            "action_items": ["string", "string"] 
        }}
    ]
}}

REQUIREMENTS:
1. Provide 3-5 strategic recommendations covering different aspects (SEO, content, technical, UX).
2. Include 4-6 specific SEO & content optimization suggestions.
3. Give 2-4 content strategy insights with actionable items.
4. Base all recommendations on the actual website data provided. Be specific and actionable, not generic.
5. Consider the identified target audiences, topic categories, and content tones.
6. Address any content gaps or opportunities you identify from the summaries and keyword data.
7. If the website content (keywords, summaries) appears to be primarily in Turkish, respond entirely in Turkish.


Output ONLY the JSON object with no additional text or formatting.
"""
            
            self.logger.info(f"Generating AI-powered recommendations for main URL: {website_data_summary['main_page_url']}")
            ai_response_str = await self._call_gemini_api(prompt)
            
            if not ai_response_str:
                self.logger.error("AI recommendations generation failed - empty response from LLM")
                return "AI recommendations could not be generated due to API response issues."
            
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
                        
                        formatted_recommendations.append(f"#### {i}. {title} ({category})")
                        formatted_recommendations.append(f"**Priority**: {priority} | **Implementation**: {difficulty}")
                        formatted_recommendations.append(description)
                        formatted_recommendations.append("")
                
                seo_recs = recommendations_data.get('seo_content_optimization', [])
                if seo_recs:
                    formatted_recommendations.append("### SEO & Content Optimization")
                    for rec in seo_recs:
                        focus_area = rec.get('focus_area', 'SEO Suggestion')
                        recommendation = rec.get('recommendation', '')
                        expected_impact = rec.get('expected_impact', '')
                        
                        formatted_recommendations.append(f"#### {focus_area}")
                        formatted_recommendations.append(f"**Recommendation**: {recommendation}")
                        if expected_impact:
                            formatted_recommendations.append(f"**Expected Impact**: {expected_impact}")
                        formatted_recommendations.append("")
                
                content_insights = recommendations_data.get('content_strategy_insights', [])
                if content_insights:
                    formatted_recommendations.append("### Content Strategy Insights")
                    for i, insight_data in enumerate(content_insights, 1):
                        insight = insight_data.get('insight', '')
                        action_items = insight_data.get('action_items', [])
                        
                        formatted_recommendations.append(f"#### Insight {i}: {insight}")
                        if action_items:
                            formatted_recommendations.append("**Action Items:**")
                            for item in action_items:
                                formatted_recommendations.append(f"- {item}")
                        formatted_recommendations.append("")
                
                if not formatted_recommendations:
                    self.logger.warning("AI generated data, but no specific recommendation sections were populated.")
                    return "AI generated data, but it was not in the expected format or was empty."

                self.logger.info("Successfully generated and formatted AI-powered recommendations.")
                return "\n".join(formatted_recommendations)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse AI recommendations JSON: {e}. Raw response: '{ai_response_str[:500]}'")
                return f"AI recommendations were generated but could not be parsed properly. Raw response (first 500 chars): {ai_response_str[:500]}..."
                
        except Exception as e:
            self.logger.error(f"Error generating AI recommendations: {e}", exc_info=True)
            return f"An error occurred while generating AI recommendations: {str(e)}"

    async def generate_comprehensive_text_report(self, llm_analysis_all: dict) -> str:
        main_page_analysis = llm_analysis_all.get('main_page', {})
        other_pages = {url: data for url, data in llm_analysis_all.items() if url != 'main_page' and data}
        report_sections = []
        report_sections.append("# COMPREHENSIVE SEO ANALYSIS REPORT")
        report_sections.append("Generated: " + time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
        report_sections.append("")
        
        if main_page_analysis:
            main_url_display = main_page_analysis.get('url', 'Main Page Analysis (URL not found in analysis data)')
            report_sections.append(f"## Main Page Analysis: {main_url_display}")
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
                report_sections.append(f"#### Page: {page_url_display}")
                
                if page_analysis_item.get("error"):
                    report_sections.append(f"  **Note:** Analysis for this page encountered an error: {page_analysis_item['error']}")
                
                content_summary_sub = page_analysis_item.get('content_summary', '')
                if content_summary_sub: report_sections.append(f"  **Summary**: {content_summary_sub}")
                
                subpage_overall_tone = page_analysis_item.get('overall_tone', '')
                if subpage_overall_tone:
                    report_sections.append(f"  **Overall Tone**: {subpage_overall_tone}")
                    all_subpage_tones.append(subpage_overall_tone)
                
                subpage_target_audience = page_analysis_item.get('target_audience', [])
                if subpage_target_audience:
                    audiences_str_sub = ", ".join(ta for ta in subpage_target_audience if ta)
                    if audiences_str_sub: report_sections.append(f"  **Target Audience**: {audiences_str_sub}")
                    all_subpage_target_audiences.extend(ta for ta in subpage_target_audience if ta)

                subpage_topic_categories = page_analysis_item.get('topic_categories', [])
                if subpage_topic_categories:
                    categories_str_sub = ", ".join(tc for tc in subpage_topic_categories if tc)
                    if categories_str_sub: report_sections.append(f"  **Topic Categories**: {categories_str_sub}")
                    all_subpage_topic_categories.extend(tc for tc in subpage_topic_categories if tc)
                
                keywords_sub = page_analysis_item.get('keywords', [])
                if keywords_sub:
                    keywords_str_sub = ", ".join(k for k in keywords_sub if k)
                    if keywords_str_sub: report_sections.append(f"  **Keywords**: {keywords_str_sub}")
                    all_subpage_keywords.extend(k for k in keywords_sub if k)
                    
                seo_keywords_sub = page_analysis_item.get('suggested_keywords_for_seo', [])
                if seo_keywords_sub:
                    seo_keywords_str_sub = ", ".join(sk for sk in seo_keywords_sub if sk)
                    if seo_keywords_str_sub: report_sections.append(f"  **SEO Keyword Suggestions**: {seo_keywords_str_sub}")
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
                    for kw, count in sorted_keywords[:15]: report_sections.append(f"- {kw} (found in {count} subpages)")
                    report_sections.append("")
                
            if all_subpage_seo_keywords:
                seo_keyword_count = {k: all_subpage_seo_keywords.count(k) for k in set(all_subpage_seo_keywords) if k}
                sorted_seo_keywords = sorted(seo_keyword_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_seo_keywords:
                    report_sections.append("## Site-Wide Subpage SEO Suggestions")
                    report_sections.append("Most frequently suggested SEO keywords for subpages (top 10):")
                    for kw, count in sorted_seo_keywords[:10]: report_sections.append(f"- {kw} (suggested for {count} subpages)")
                    report_sections.append("")
            
            if all_subpage_topic_categories:
                topic_category_count = {k: all_subpage_topic_categories.count(k) for k in set(all_subpage_topic_categories) if k}
                sorted_topic_categories = sorted(topic_category_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_topic_categories:
                    report_sections.append("## Site-Wide Topic Categories Analysis (Subpages)")
                    report_sections.append("Most common topic categories across analyzed subpages (top 10):")
                    for tc, count in sorted_topic_categories[:10]: report_sections.append(f"- {tc} (found in {count} subpages)")
                    report_sections.append("")

            if all_subpage_target_audiences:
                target_audience_count = {k: all_subpage_target_audiences.count(k) for k in set(all_subpage_target_audiences) if k}
                sorted_target_audiences = sorted(target_audience_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_target_audiences:
                    report_sections.append("## Site-Wide Target Audience Analysis (Subpages)")
                    report_sections.append("Most common target audiences across analyzed subpages (top 8):")
                    for ta, count in sorted_target_audiences[:8]: report_sections.append(f"- {ta} (identified in {count} subpages)")
                    report_sections.append("")

            if all_subpage_tones:
                tone_count = {k: all_subpage_tones.count(k) for k in set(all_subpage_tones) if k}
                sorted_tones = sorted(tone_count.items(), key=lambda x: x[1], reverse=True)
                if sorted_tones:
                    report_sections.append("## Site-Wide Content Tone Analysis (Subpages)")
                    report_sections.append("Most common content tones across analyzed subpages:")
                    for tone, count in sorted_tones: report_sections.append(f"- {tone} (found in {count} subpages)")
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