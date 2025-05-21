
#analyzer/llm_analysis_start
import json
import logging
import os
import google.generativeai as genai
import asyncio # For to_thread
from dotenv import load_dotenv
from utils.language_support import language_manager
import streamlit as st

language_names = {"en": "English", "tr": "Turkish"}
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Configure Gemini API
# Ensure your GEMINI_API_KEY environment variable is set.
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

async def _call_gemini_api(prompt_text: str) -> str:
    """Helper function to make the blocking Gemini API call in a separate thread."""
    if not model:
        logging.error("Gemini model not initialized. Cannot make API call.")
        return ""
    try:
        # Make the API call non-blocking from the perspective of the async event loop
        response = await asyncio.to_thread(
            model.generate_content,
            prompt_text,
            generation_config={
                "temperature": 0.2, # Lower temperature for more deterministic JSON output
                "response_mime_type": "application/json", # Request JSON output directly
            }
        )
        if response and response.text:
            return response.text
        elif response and response.parts: # Fallback if text is not directly in response.text
             all_text_parts = "".join(part.text for part in response.parts if hasattr(part, 'text'))
             if all_text_parts:
                return all_text_parts
        logging.warning(f"LLM response was empty or did not contain text. Response: {response}")
        return ""
    except Exception as e:
        # Catching google.api_core.exceptions.PermissionDenied or similar specific API errors can be useful
        if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
             logging.error(f"Gemini API Permission Denied or Invalid API Key: {e}")
        else:
            logging.error(f"Error during Gemini API call: {e}", exc_info=True)
        return ""


async def llm_analysis_start(report_data: dict) -> dict:
    """
    Analyzes report data for a SINGLE page using Google's Gemini LLM.
    Primarily used to extract header/footer content from cleaned_text for an initial page analysis,
    but can also perform broader content analysis.

    Args:
        report_data: A dictionary containing data for a single page.
                     It expects 'url', 'cleaned_text', and 'headings' keys directly.
                     Example for initial page analysis (e.g., from seo.py):
                     {
                         'url': 'https://example.com/page',
                         'cleaned_text': 'Full cleaned text of the page...',
                         'headings': {} // Or populated headings if available
                     }
                     Alternatively, for compatibility or other use cases, it can extract
                     'cleaned_text' and 'headings' from a nested 'page_statistics' entry
                     if `report_data.get('page_statistics', {}).get(report_data.get('url'))` exists.

    Returns:
        A dictionary formatted according to the specified JSON structure,
        or an error dictionary if analysis fails or input data is insufficient.
    """
    if not model:
        logging.error("Gemini model not configured. Cannot perform LLM analysis.")
        return {"error": "Gemini model not configured."} # Ensure a dict is returned

    if not report_data or not isinstance(report_data, dict):
        logging.warning("llm_analysis_start received empty or invalid report_data (not a dict).")
        return {"error": "Invalid report_data: must be a dictionary."}

    page_url_from_report = report_data.get('url')
    if not page_url_from_report:
        logging.warning("llm_analysis_start received report_data without a top-level 'url' field.")
        return {"error": "Missing 'url' in report_data."}
    
    logging.info(f"Starting LLM analysis for URL: {page_url_from_report}")

    cleaned_text = None
    headings_data = None

    # Priority 1: Direct flat structure (common for initial page analysis from seo.py)
    if 'cleaned_text' in report_data and 'headings' in report_data:
        cleaned_text = report_data.get('cleaned_text', '')
        headings_data = report_data.get('headings', {})
        logging.debug(f"Using direct cleaned_text and headings from report_data for {page_url_from_report}")
    # Priority 2: Nested structure (fallback or alternative use cases)
    elif 'page_statistics' in report_data and page_url_from_report in report_data.get('page_statistics', {}):
        page_data_from_stats = report_data['page_statistics'][page_url_from_report]
        cleaned_text = page_data_from_stats.get('cleaned_text', '')
        headings_data = page_data_from_stats.get('headings', {})
        logging.debug(f"Using cleaned_text and headings from page_statistics for {page_url_from_report}")
    
    # Check if data was successfully extracted by either method
    if cleaned_text is None or headings_data is None:
        logging.warning(f"Could not extract 'cleaned_text' and 'headings' for URL {page_url_from_report} from report_data using available methods.")
        return {
            "url": page_url_from_report,
            "error": "Essential page data (cleaned_text, headings) not found for analysis.",
            "keywords": [], "content_summary": "", "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [], "header": [], "footer": []
        }

    # Note: header_text_from_crawl and footer_text_from_crawl are no longer used directly.
    # The LLM is tasked with extracting this information from cleaned_text.

    if not cleaned_text and not headings_data: # e.g. cleaned_text is "" and headings_data is {}
        logging.warning(f"No cleaned_text or headings_data found for URL {page_url_from_report}. LLM analysis might be ineffective.")
        return {
            "url": page_url_from_report,
            "error": "No content (cleaned_text or headings) available for analysis.",
            "keywords": [],
            "content_summary": "No content (cleaned_text or headings) available for analysis.",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "header": [],
            "footer": []
        }

    max_text_len = 30000 # Characters
    truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')
    language_instruction = f"Please respond in {language_names.get(st.session_state.language, 'English')}." if st.session_state.language != "en" else ""
    lang = st.session_state.get("language", "en")
    prompt = f"""{language_instruction} If content is Turkish make your analysis in Turkish , Otherwise make it in English.
Analyze the following web page content for the URL: {page_url_from_report}

**Page Content (Cleaned Text Snippet):**
---
{truncated_cleaned_text}
---

**Page Headings (JSON format):**
---
{json.dumps(headings_data, indent=2)}
---

Based on the provided text and headings, generate a JSON object strictly adhering to the following structure.
Output ONLY the JSON object. Do NOT include any explanatory text, markdown formatting (like ```json), or anything else outside the JSON object itself.

{{
    "keywords": ["string"],
    "content_summary": "string",
    "other_information_and_contacts": ["string"],
    "suggested_keywords_for_seo": ["string"],
    "header": ["string"],
    "footer": ["string"]
}}

**Detailed Instructions for populating each field in the JSON object:**

1.  **"keywords"**:
    *   Identify and list the top 5-7 most relevant and frequently occurring keywords or key phrases from the page content and headings.
    *   These should accurately represent the main topics and themes of the page.
    *   Prioritize multi-word phrases if they are more descriptive. Example: ["data analysis solutions", "cloud computing services", "enterprise software"]
    *   Return as a list of strings. If no distinct keywords are found, return an empty list [].

2.  **"content_summary"**:
    *   Provide a concise summary of the page content in 2-4 sentences (target 50-100 words).
    *   The summary must capture the main purpose, key offerings, or core information presented on the page.
    *   It should be informative and engaging.
    *   If the content is too sparse for a meaningful summary, provide a brief note like "Page content is minimal."

3.  **"other_information_and_contacts"**:
    *   Extract any explicit contact information: email addresses, phone numbers, physical addresses.
    *   Identify specific company names, key product names, or important service names mentioned.
    *   List social media profile URLs if clearly present.
    *   If the page mentions specific individuals (e.g., team members, authors), list their names and roles if available.
    *   Format each piece of information as a descriptive string in a list.
    *   Example: ["Email: contact@example.com", "Phone: (555) 123-4567", "Main Office: 123 Innovation Drive, Tech City", "Product: Alpha Suite", "Twitter: https://twitter.com/example"]
    *   If no such information is found, return an empty list [].
    *   Avoid generic phrases that do not provide specific information. Example: "Contact us" or "Follow us on social media" is too vague.


4.  **"suggested_keywords_for_seo"**:
    *   Based on the page content and its main topics, suggest 3-5 additional keywords or key phrases that could be targeted for SEO.
    *   These should be relevant variations, long-tail keywords, or related topics not already dominant but with potential.
    *   Consider user intent (informational, transactional, navigational). Example: ["benefits of data analysis", "best cloud providers for small business", "custom enterprise software development"]
    *   If no strong distinct suggestions can be made, return an empty list [].

5.  **"header"**:
    *   From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main header.
    *   This typically includes site navigation links (e.g., "Home", "About Us", "Services", "Contact" , Certificates), site branding text (e.g., company name if prominently in header), or a primary tagline.
    *   Provide these as a list of strings. Each string can be a distinct link text or a phrase from the header.
    *   May contain menu items, site title, or catagory and product name.
    *   If no clear header text is discernible, return an empty list [].
    *   Example: ["Home", "Products", "Blog", "Login", "Site Title Example Inc." , "About Us", "Contact Us"]

6.  **"footer"**:
    *   From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main footer.
    *   This typically includes copyright notices, links to privacy policy, terms of service, sitemap, contact information repeated in the footer, or social media links.
    *   Provide these as a list of strings. Each string can be a distinct link text or a phrase from the footer.
    *   If no clear footer text is discernible, return an empty list [].
    *   Example: ["© 2024 Company Name", "Privacy Policy", "Terms of Use", "Contact Us", "Follow us on Twitter" , © 2025 Company name. Tüm Hakları Saklıdır",]

Ensure your entire response is ONLY a valid JSON object.
"""

    try:
        logging.debug(f"Sending prompt to Gemini for URL: {page_url_from_report}")
        llm_response_str = await _call_gemini_api(prompt)

        if not llm_response_str:
            logging.error(f"LLM returned empty or no-text response for URL: {page_url_from_report}")
            return {
                "url": page_url_from_report,
                "error": "LLM returned an empty response.",
                "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
                "suggested_keywords_for_seo": [], "header": [], "footer": []
            }
        
        try:
            llm_data = json.loads(llm_response_str.strip())
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response from LLM for {page_url_from_report}: {e}. Raw Response: '{llm_response_str[:500]}'")
            return {
                "url": page_url_from_report,
                "error": "Failed to parse LLM response as JSON.",
                "llm_response_raw": llm_response_str[:500],
                "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
                "suggested_keywords_for_seo": [], "header": [], "footer": []
            }

        analysis_result = {
            "url": page_url_from_report,
            "keywords": llm_data.get("keywords", []),
            "content_summary": llm_data.get("content_summary", "Summary not generated by LLM."),
            "other_information_and_contacts": llm_data.get("other_information_and_contacts", []),
            "suggested_keywords_for_seo": llm_data.get("suggested_keywords_for_seo", []),
            "header": llm_data.get("header", []), 
            "footer": llm_data.get("footer", [])
        }

        logging.info(f"Successfully completed LLM analysis for URL: {page_url_from_report}")
        return analysis_result

    except Exception as e:
        logging.error(f"Unexpected error during LLM analysis processing for URL {page_url_from_report}: {e}", exc_info=True)
        return {
            "url": page_url_from_report,
            "error": f"An unexpected error occurred: {str(e)}",
            "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
            "suggested_keywords_for_seo": [], "header": [], "footer": []
        }