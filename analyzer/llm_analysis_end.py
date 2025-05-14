#analayzer/llm_analysis_end.py
#This will be a loop to making same analysis like llm_analysis_start.py updates llm_analysis field in supabase with crawled urls except main page . 



#analyzer/llm_analysis_end.py
import json
import logging
import os
import asyncio
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure Gemini API
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
                "temperature": 0.2,  # Lower temperature for more deterministic JSON output
                "response_mime_type": "application/json",  # Request JSON output directly
            }
        )
        if response and response.text:
            return response.text
        elif response and response.parts:  # Fallback if text is not directly in response.text
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


async def analyze_single_page(page_url: str, page_data: dict) -> dict:
    """
    Analyzes a single page using Google's Gemini LLM and generates a structured JSON report.
    
    Args:
        page_url: URL of the page to analyze
        page_data: Data for the page including cleaned_text and headings
        
    Returns:
        A dictionary containing the LLM analysis results
    """
    if not page_data:
        logging.warning(f"No page data provided for URL: {page_url}")
        return {
            "url": page_url,
            "keywords": [],
            "content_summary": "No page data available for analysis.",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "header": [],
            "footer": []
        }
    
    cleaned_text = page_data.get('cleaned_text', '')
    headings_data = page_data.get('headings', {})
    
    if not cleaned_text and not headings_data:
        logging.warning(f"No cleaned_text or headings_data found for URL {page_url}. LLM analysis might be ineffective.")
        return {
            "url": page_url,
            "keywords": [],
            "content_summary": "No content (cleaned_text or headings) available for analysis.",
            "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [],
            "header": [],
            "footer": []
        }

    max_text_len = 25000  # Characters
    truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')

    prompt = f"""
Analyze the following web page content for the URL: {page_url}

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
        logging.debug(f"Sending prompt to Gemini for URL: {page_url}")
        llm_response_str = await _call_gemini_api(prompt)

        if not llm_response_str:
            logging.error(f"LLM returned empty or no-text response for URL: {page_url}")
            return {
                "url": page_url,
                "error": "LLM returned an empty response.",
                "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
                "suggested_keywords_for_seo": [], "header": [], "footer": []
            }
        
        try:
            llm_data = json.loads(llm_response_str.strip())
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response from LLM for {page_url}: {e}. Raw Response: '{llm_response_str[:500]}'")
            return {
                "url": page_url,
                "error": "Failed to parse LLM response as JSON.",
                "llm_response_raw": llm_response_str[:500],
                "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
                "suggested_keywords_for_seo": [], "header": [], "footer": []
            }

        analysis_result = {
            "url": page_url,
            "keywords": llm_data.get("keywords", []),
            "content_summary": llm_data.get("content_summary", "Summary not generated by LLM."),
            "other_information_and_contacts": llm_data.get("other_information_and_contacts", []),
            "suggested_keywords_for_seo": llm_data.get("suggested_keywords_for_seo", []),
            "header": llm_data.get("header", []), 
            "footer": llm_data.get("footer", [])
        }

        logging.info(f"Successfully completed LLM analysis for URL: {page_url}")
        return analysis_result

    except Exception as e:
        logging.error(f"Unexpected error during LLM analysis processing for URL {page_url}: {e}", exc_info=True)
        return {
            "url": page_url,
            "error": f"An unexpected error occurred: {str(e)}",
            "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
            "suggested_keywords_for_seo": [], "header": [], "footer": []
        }


async def process_seo_report(report_id):
    """
    Process a single SEO report, analyzing all pages except the main page.
    
    Args:
        report_id: The ID of the report in Supabase to process
    """
    try:
        # Fetch the report from Supabase
        response = await asyncio.to_thread(
            supabase.table('seo_reports').select('*').eq('id', report_id).single().execute
        )
        
        if not response.data:
            logging.error(f"No report found with ID: {report_id}")
            return False
        
        report_data = response.data.get('report', {})
        main_url = report_data.get('url')
        
        if not main_url or not report_data:
            logging.error(f"Report with ID {report_id} has no URL or data")
            return False
            
        logging.info(f"Processing report ID {report_id} for URL: {main_url}")
        
        # Get the page statistics for all pages except the main page
        page_statistics = report_data.get('page_statistics', {})
        pages_to_analyze = [(url, data) for url, data in page_statistics.items() if url != main_url]
        
        if not pages_to_analyze:
            logging.info(f"No additional pages to analyze for report ID {report_id}")
            return True
            
        logging.info(f"Found {len(pages_to_analyze)} additional pages to analyze for report ID {report_id}")
        
        # Initialize llm_analysis_all to store all page analyses
        llm_analysis_all = {
            "main_page": report_data.get('llm_analysis', {})
        }
        
        # Process pages in batches to avoid overwhelming the LLM service
        batch_size = 5
        max_retries = 3
        delay_between_batches = 2  # seconds
        
        for i in range(0, len(pages_to_analyze), batch_size):
            batch = pages_to_analyze[i:i+batch_size]
            batch_results = {}
            
            for page_url, page_data in batch:
                for retry in range(max_retries):
                    try:
                        analysis_result = await analyze_single_page(page_url, page_data)
                        batch_results[page_url] = analysis_result
                        break
                    except Exception as e:
                        if retry < max_retries - 1:
                            logging.warning(f"Error analyzing page {page_url} (attempt {retry+1}/{max_retries}): {e}")
                            await asyncio.sleep(1)  # Short delay before retry
                        else:
                            logging.error(f"Failed to analyze page {page_url} after {max_retries} attempts: {e}")
                            batch_results[page_url] = {
                                "url": page_url,
                                "error": f"Failed after {max_retries} attempts: {str(e)}",
                                "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
                                "suggested_keywords_for_seo": [], "header": [], "footer": []
                            }
            
            # Add batch results to the overall analysis
            llm_analysis_all.update(batch_results)
            
            # Log progress
            logging.info(f"Processed batch {i//batch_size + 1}/{(len(pages_to_analyze)-1)//batch_size + 1} " +
                         f"({min(i+batch_size, len(pages_to_analyze))}/{len(pages_to_analyze)} pages)")
            
            # Wait between batches to avoid rate limiting
            if i + batch_size < len(pages_to_analyze):
                await asyncio.sleep(delay_between_batches)
        
        # Update the report in Supabase with the analysis results
        update_data = {
            'llm_analysis_all': llm_analysis_all,
            'llm_analysis_all_completed': True,
            'llm_analysis_all_timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        }
        
        update_response = await asyncio.to_thread(
            supabase.table('seo_reports').update(update_data).eq('id', report_id).execute
        )
        
        if hasattr(update_response, 'error') and update_response.error:
            logging.error(f"Failed to update report in Supabase: {update_response.error}")
            return False
        
        logging.info(f"Successfully processed and updated report ID {report_id} with {len(pages_to_analyze)} page analyses")
        return True
        
    except Exception as e:
        logging.error(f"Error processing report ID {report_id}: {e}", exc_info=True)
        return False


async def process_pending_reports(limit=10):
    """
    Process pending reports that don't have llm_analysis_all_completed set.
    
    Args:
        limit: Maximum number of reports to process in one run
    """
    try:
        # Get reports that have llm_analysis but not llm_analysis_all_completed
        response = await asyncio.to_thread(
            supabase.table('seo_reports')
                .select('id,url')
                .not_('llm_analysis_all_completed', 'is', 'true')
                .not_('llm_analysis', 'is', 'null')
                .limit(limit)
                .execute
        )
        
        if not response.data:
            logging.info("No pending reports found for processing")
            return
            
        reports = response.data
        logging.info(f"Found {len(reports)} pending reports to process")
        
        for report in reports:
            report_id = report.get('id')
            report_url = report.get('url')
            logging.info(f"Starting processing for report ID {report_id} ({report_url})")
            
            success = await process_seo_report(report_id)
            
            if success:
                logging.info(f"Successfully processed report ID {report_id}")
            else:
                logging.error(f"Failed to process report ID {report_id}")
    
    except Exception as e:
        logging.error(f"Error in process_pending_reports: {e}", exc_info=True)


async def main():
    """Main entry point for the script."""
    # Process reports specified by ID
    if len(os.sys.argv) > 1:
        report_ids = os.sys.argv[1:]
        logging.info(f"Processing specific report IDs: {report_ids}")
        for report_id in report_ids:
            await process_seo_report(report_id)
    # Or process pending reports if no IDs specified
    else:
        batch_size = int(os.getenv('PROCESS_BATCH_SIZE', '10'))
        logging.info(f"Processing pending reports, batch size: {batch_size}")
        await process_pending_reports(limit=batch_size)
    
    logging.info("Finished processing reports")


if __name__ == "__main__":
    asyncio.run(main())
