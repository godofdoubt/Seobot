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

    async def _analyze_single_page(self, page_url: str, page_data: dict, is_main_page: bool = False) -> dict:
        base_result = {
            "url": page_url,
            "keywords": [],
            "content_summary": "",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "overall_tone": "",  # New field
            "target_audience": [], # New field
            "topic_categories": []  # New field
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
            "overall_tone": "string", # New field
            "target_audience": ["string"], # New field
            "topic_categories": ["string"]  # New field
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
                    "header": llm_data.get("header", base_result["header"]),
                    "footer": llm_data.get("footer", base_result["footer"])
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
            # Prepare comprehensive data summary for AI analysis
            main_page_analysis = llm_analysis_all.get('main_page', {})
            other_pages = {url: data for url, data in llm_analysis_all.items() if url != 'main_page' and data} # Ensure data exists
            
            # Collect all data for analysis
            all_keywords = []
            all_seo_keywords = []
            all_topic_categories = []
            all_target_audiences = []
            all_tones = []
            all_summaries = []
            
            # Main page data
            if main_page_analysis and not main_page_analysis.get('error'):
                all_keywords.extend(k for k in main_page_analysis.get('keywords', []) if k)
                all_seo_keywords.extend(sk for sk in main_page_analysis.get('suggested_keywords_for_seo', []) if sk)
                all_topic_categories.extend(tc for tc in main_page_analysis.get('topic_categories', []) if tc)
                all_target_audiences.extend(ta for ta in main_page_analysis.get('target_audience', []) if ta)
                if main_page_analysis.get('overall_tone'):
                    all_tones.append(main_page_analysis.get('overall_tone'))
                if main_page_analysis.get('content_summary'):
                    all_summaries.append(f"Main Page ({main_page_analysis.get('url', 'N/A')}): {main_page_analysis.get('content_summary')}")
            
            # Subpage data
            for page_url, page_data in other_pages.items():
                if page_data and not page_data.get('error'): # Check if page_data exists
                    all_keywords.extend(k for k in page_data.get('keywords', []) if k)
                    all_seo_keywords.extend(sk for sk in page_data.get('suggested_keywords_for_seo', []) if sk)
                    all_topic_categories.extend(tc for tc in page_data.get('topic_categories', []) if tc)
                    all_target_audiences.extend(ta for ta in page_data.get('target_audience', []) if ta)
                    if page_data.get('overall_tone'):
                        all_tones.append(page_data.get('overall_tone'))
                    if page_data.get('content_summary'):
                        all_summaries.append(f"{page_url}: {page_data.get('content_summary')}")
            
            # Create data summary for AI
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

    async def _generate_comprehensive_text_report(self, llm_analysis_all: dict) -> str:
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
                for contact_item in contacts: # Renamed variable to avoid conflict
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
                footer_str = ", ".join(f_item for f_item in footer if f_item) # Renamed variable
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
                
                content_summary_sub = page_analysis_item.get('content_summary', '') # Renamed variable
                if content_summary_sub: report_sections.append(f"  **Summary**: {content_summary_sub}")
                
                subpage_overall_tone = page_analysis_item.get('overall_tone', '')
                if subpage_overall_tone:
                    report_sections.append(f"  **Overall Tone**: {subpage_overall_tone}")
                    all_subpage_tones.append(subpage_overall_tone)
                
                subpage_target_audience = page_analysis_item.get('target_audience', [])
                if subpage_target_audience:
                    audiences_str_sub = ", ".join(ta for ta in subpage_target_audience if ta) # Renamed
                    if audiences_str_sub: report_sections.append(f"  **Target Audience**: {audiences_str_sub}")
                    all_subpage_target_audiences.extend(ta for ta in subpage_target_audience if ta)

                subpage_topic_categories = page_analysis_item.get('topic_categories', [])
                if subpage_topic_categories:
                    categories_str_sub = ", ".join(tc for tc in subpage_topic_categories if tc) # Renamed
                    if categories_str_sub: report_sections.append(f"  **Topic Categories**: {categories_str_sub}")
                    all_subpage_topic_categories.extend(tc for tc in subpage_topic_categories if tc)
                
                keywords_sub = page_analysis_item.get('keywords', []) # Renamed
                if keywords_sub:
                    keywords_str_sub = ", ".join(k for k in keywords_sub if k) # Renamed
                    if keywords_str_sub: report_sections.append(f"  **Keywords**: {keywords_str_sub}")
                    all_subpage_keywords.extend(k for k in keywords_sub if k)
                    
                seo_keywords_sub = page_analysis_item.get('suggested_keywords_for_seo', []) # Renamed
                if seo_keywords_sub:
                    seo_keywords_str_sub = ", ".join(sk for sk in seo_keywords_sub if sk) # Renamed
                    if seo_keywords_str_sub: report_sections.append(f"  **SEO Keyword Suggestions**: {seo_keywords_str_sub}")
                    all_subpage_seo_keywords.extend(sk for sk in seo_keywords_sub if sk)

                # MODIFICATION: Add 'other_information_and_contacts' for subpages
                contacts_sub = page_analysis_item.get('other_information_and_contacts', []) # Renamed
                if contacts_sub:
                    report_sections.append(f"  **Contact Information & Key Mentions**:")
                    has_sub_contacts = False
                    for contact_item_sub in contacts_sub: # Renamed
                        if contact_item_sub:
                            report_sections.append(f"    - {contact_item_sub}")
                            has_sub_contacts = True
                    if not has_sub_contacts:
                         report_sections.append("    No specific contact information or key mentions identified on this subpage.")
                # END MODIFICATION
                report_sections.append("") # Add a blank line for separation between subpage entries
            
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
                            analysis_result = await self._analyze_single_page(p_url, p_data, is_main_page=False)
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
            #if not (200 <= update_response.status_code < 300):
             #    self.logger.error(f"Failed to update report ID {report_id} in Supabase. Status: {update_response.status_code}, Response: {update_response.data}")
            #     await self._mark_report_as_error(report_id, f"Supabase update failed. Status: {update_response.status_code}, Details: {str(update_response.data)[:350]}")
              #   return False
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