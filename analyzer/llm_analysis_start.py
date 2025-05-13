
#analyzer/llm_analysis_start
import json
import logging
import os
import google.generativeai as genai
import asyncio # For to_thread
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
#load_dotenv()
#GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
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
    Analyzes the report data for a SINGLE page using Google's Gemini LLM and generates a structured JSON report.
    The LLM will extract header and footer content from the cleaned_text.

    Args:
        report_data: A dictionary containing the report data for a single page.
                     Expected structure based on seoreportsaver.py:
                     {
                         'url': 'https://example.com/page', // Main URL of the analysis context
                         'timestamp': '...',
                         'page_statistics': {
                             'https://example.com/page': { // Actual page data for this URL
                                 'url': 'https://example.com/page',
                                 'cleaned_text': 'Full cleaned text of the page...',
                                 'headings': {'h1': ['Main Title'], 'h2': ['Subtitle 1']},
                             }
                         },
                         // ... other top-level analysis fields ...
                     }
                     Alternatively, can accept a flatter structure if `report_data` directly contains
                     'url', 'cleaned_text', 'headings'

    Returns:
        A dictionary formatted according to the specified JSON structure,
        or an empty dictionary if analysis fails or input data is insufficient.
    """
    if not model:
        logging.error("Gemini model not configured. Cannot perform LLM analysis.")
        return {}

    if not report_data or not isinstance(report_data, dict):
        logging.warning("llm_analysis_start received empty or invalid report_data (not a dict).")
        return {}

    # Determine the actual URL and page-specific data
    page_url_from_report = report_data.get('url')
    if not page_url_from_report:
        logging.warning("llm_analysis_start received report_data without a top-level 'url' field.")
        return {}
    
    logging.info(f"Starting LLM analysis for URL: {page_url_from_report}")

    # Extract page-specific statistics
    # Case 1: Data is nested as per seoreportsaver structure
    page_specific_stats = report_data.get('page_statistics', {}).get(page_url_from_report)

    # Case 2: Data is flat (report_data *is* the page_specific_stats)
    if not page_specific_stats and 'cleaned_text' in report_data and 'headings' in report_data:
        page_specific_stats = report_data
    
    if not page_specific_stats:
        logging.warning(f"No 'page_statistics' or direct page data found for URL {page_url_from_report} within the provided report_data.")
        return {
            "url": page_url_from_report,
            "keywords": [],
            "content_summary": "Essential page statistics (cleaned_text, headings) not found for analysis.",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "header": [],
            "footer": []
        }

    cleaned_text = page_specific_stats.get('cleaned_text', '')
    headings_data = page_specific_stats.get('headings', {})
    
    # Note: header_text_from_crawl and footer_text_from_crawl are no longer used directly.
    # The LLM is tasked with extracting this information from cleaned_text.

    if not cleaned_text and not headings_data:
        logging.warning(f"No cleaned_text or headings_data found for URL {page_url_from_report}. LLM analysis might be ineffective.")
        # Even if cleaned_text is minimal, LLM might still find something or return empty as instructed.
        # If truly no text, a more specific message can be given or an empty result with defaults.
        return {
            "url": page_url_from_report,
            "keywords": [],
            "content_summary": "No content (cleaned_text or headings) available for analysis.",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "header": [],
            "footer": []
        }

    max_text_len = 25000 # Characters
    truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')

    prompt = f"""
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

4.  **"suggested_keywords_for_seo"**:
    *   Based on the page content and its main topics, suggest 3-5 additional keywords or key phrases that could be targeted for SEO.
    *   These should be relevant variations, long-tail keywords, or related topics not already dominant but with potential.
    *   Consider user intent (informational, transactional, navigational). Example: ["benefits of data analysis", "best cloud providers for small business", "custom enterprise software development"]
    *   If no strong distinct suggestions can be made, return an empty list [].

5.  **"header"**:
    *   From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main header.
    *   This typically includes site navigation links (e.g., "Home", "About Us", "Services", "Contact"), site branding text (e.g., company name if prominently in header), or a primary tagline.
    *   Provide these as a list of strings. Each string can be a distinct link text or a phrase from the header.
    *   If no clear header text is discernible, return an empty list [].
    *   Example: ["Home", "Products", "Blog", "Login", "Site Title Example Inc."]

6.  **"footer"**:
    *   From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main footer.
    *   This typically includes copyright notices, links to privacy policy, terms of service, sitemap, contact information repeated in the footer, or social media links.
    *   Provide these as a list of strings. Each string can be a distinct link text or a phrase from the footer.
    *   If no clear footer text is discernible, return an empty list [].
    *   Example: ["© 2024 Company Name", "Privacy Policy", "Terms of Use", "Contact Us", "Follow us on Twitter"]

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


# Example Usage (for testing the function independently)
if __name__ == '__main__':
    async def main():
        # Simulate report data for a single page as it would be passed from seoreportsaver
        # Note: 'header_text' and 'footer_text' in this test data are for the crawler's output.
        # The LLM will attempt to derive header/footer from 'cleaned_text'.
        test_single_page_report_data_from_saver = {
            'url': 'https://www.example.com/test-page', 
            'timestamp': '2023-10-27 10:00:00',
            'page_statistics': { 
                'https://www.example.com/test-page': { 
                    'url': 'https://www.example.com/test-page', 
                    'cleaned_text': 'HEADER START Site Logo | Home | Products | Services | Contact - Example.com Official HEADER END This is extensive cleaned text content for the example page. It discusses our amazing products and comprehensive services. We offer cutting-edge solutions for data analysis and robust cloud computing. For inquiries, please contact us at info@example.com or call our dedicated line at (555) 987-6543. Our main corporate office is located at 123 Example Street, Example City, EX 54321. Follow our updates on Twitter @example_inc and on LinkedIn at linkedin.com/company/exampleinc. Our flagship services include the "Innovate Suite Pro" and the "DataMaster Pro AI" platform. We also highlight our commitment to customer success. FOOTER START © 2024 Example Corp | Privacy Policy | Terms of Service | Sitemap FOOTER END',
                    'headings': {
                        'stats': {'h1_count': 1, 'h2_count': 3},
                        'h1': ['Example Page Title: Showcasing Amazing Products & Services'],
                        'h2': ['About Our Innovative Products', 'Comprehensive Service Offerings', 'Contact Us Today for a Demo']
                    },
                    # These fields from crawler output might be present in input data,
                    # but llm_analysis_start will now rely on LLM to extract from cleaned_text.
                    'header_text': 'Site Logo | Home | Products | Services | Contact - Example.com Official', 
                    'footer_text': '© 2024 Example Corp | Privacy Policy | Terms of Service | Sitemap'
                }
            },
            'sitemap_found': True,
        }

        test_flat_single_page_data = {
            'url': 'https://www.example.com/another-page',
            'cleaned_text': 'Global Site Header - Another Example. Welcome to another interesting page. This page dives deep into advanced SEO strategies and effective content marketing techniques. For personalized consultations, reach out to our expert team at seo_expert_team@example.com. We also provide a suite of powerful keyword research tools and analytics platforms. Global Site Footer © 2024 - All Rights Reserved',
            'headings': {
                'h1': ['Mastering Advanced SEO Techniques for 2024'],
                'h2': ['Content is Still King: A Deep Dive', 'Strategic Keyword Research and Implementation']
            },
            # These fields from crawler output might be present in input data.
            'header_text': 'Global Site Header - Another Example',
            'footer_text': 'Global Site Footer © 2024 - All Rights Reserved'
        }

        if not os.getenv('GEMINI_API_KEY'):
            print("GEMINI_API_KEY not set. Skipping live API call test.")
            print("To run this test, set the GEMINI_API_KEY environment variable.")
            
            # Simulate what the LLM might output for header/footer
            simulated_output = {
                "url": test_single_page_report_data_from_saver['url'],
                "keywords": ["simulated products", "simulated services", "data analysis (simulated)"],
                "content_summary": "This is a simulated summary of the page about products and services, generated because GEMINI_API_KEY is not set.",
                "other_information_and_contacts": ["simulated contact: info@example.com", "simulated office: 123 Example St"],
                "suggested_keywords_for_seo": ["advanced data solutions", "cloud service providers", "simulated SEO term"],
                "header": ["Simulated LLM: Home", "Simulated LLM: Products"], # Placeholder for LLM extracted header
                "footer": ["Simulated LLM: © 2024 Example", "Simulated LLM: Privacy"] # Placeholder for LLM extracted footer
            }
            print("\nSimulated LLM Analysis Output (due to missing API key):")
            print(json.dumps(simulated_output, indent=2))
            return

        print("--- Testing with data structure from seoreportsaver ---")
        # Added some markers to cleaned_text to help LLM identify header/footer for test
        analysis_result_1 = await llm_analysis_start(test_single_page_report_data_from_saver)
        print("LLM Analysis Output (from seoreportsaver structure):")
        print(json.dumps(analysis_result_1, indent=2))

        print("\n--- Testing with flat single page data structure ---")
        analysis_result_2 = await llm_analysis_start(test_flat_single_page_data)
        print("LLM Analysis Output (from flat structure):")
        print(json.dumps(analysis_result_2, indent=2))

    asyncio.run(main())
