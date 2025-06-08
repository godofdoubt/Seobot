import json
import logging
import os
import re # Added for remove_specific_fixed_phrases if it were here, but it's in methods.py
import google.generativeai as genai
import asyncio # For to_thread
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted, PermissionDenied # For specific Gemini errors
from mistralai import Mistral # Import Mistral

# Import the prompt functions from the separate file
from analyzer.llm_analysis_start_prompt import get_gemini_analysis_prompt, get_mistral_analysis_prompt
from analyzer.methods import remove_specific_fixed_phrases # Import the new cleaning function

#from utils.language_support import language_manager # As in your original
#import streamlit as st # As in your original

language_names = {"en": "English", "tr": "Turkish"}
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Gemini Configuration ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
gemini_model_instance = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model_instance = genai.GenerativeModel('gemini-1.5-flash-latest') # Using standard model
        logging.info("Gemini API configured successfully.")
    except Exception as e:
        logging.error(f"Failed to configure Gemini API: {e}")
        gemini_model_instance = None # Ensure it's None if config fails
else:
    logging.warning("GEMINI_API_KEY not found in environment. Gemini LLM will not be available.")

# --- Mistral Configuration ---
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL_NAME = os.getenv('MISTRAL_MODEL_NAME')
mistral_client = None
if MISTRAL_API_KEY and MISTRAL_MODEL_NAME:
    try:
        mistral_client = Mistral(api_key=MISTRAL_API_KEY)
        logging.info(f"Mistral client configured successfully for model: {MISTRAL_MODEL_NAME}")
    except Exception as e:
        logging.error(f"Failed to configure Mistral client: {e}")
        mistral_client = None # Ensure it's None if config fails
elif not MISTRAL_API_KEY:
    logging.warning("MISTRAL_API_KEY not found in environment. Mistral LLM will not be available as a fallback.")
elif not MISTRAL_MODEL_NAME:
    logging.warning("MISTRAL_MODEL_NAME not found in environment. Mistral LLM will not be available as a fallback.")

class GeminiAPIFallbackError(Exception):
    """Custom exception for errors that should trigger a fallback to Mistral."""
    pass

# Define boilerplate phrases to remove from cleaned_text before LLM processing
# These should be the versions of phrases as they appear in `cleaned_text`
# (which might have undergone some initial cleaning like punctuation removal).
BOILERPLATE_PHRASES_TO_REMOVE = [
    "INFORMATION . Başa dön",  # Original form
    "INFORMATION Başa dön",    # Form if '.' is removed/spaced
    "İçeriğe geç -",           # Original form
    "İçeriğe geç"              # Form if '-' is removed/spaced
]

async def _call_gemini_api(prompt_text: str) -> str:
    """Helper function to make the blocking Gemini API call in a separate thread."""
    if not gemini_model_instance:
        logging.error("Gemini model not initialized. Cannot make API call.")
        raise GeminiAPIFallbackError("Gemini model not initialized.")
    try:
        response = await asyncio.to_thread(
            gemini_model_instance.generate_content,
            prompt_text,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }
        )
        if response and response.text:
            return response.text
        elif response and response.parts:
             all_text_parts = "".join(part.text for part in response.parts if hasattr(part, 'text'))
             if all_text_parts:
                return all_text_parts
        logging.warning(f"Gemini LLM response was empty or did not contain text. Response: {response}")
        return "" # Explicitly return empty string for fallback logic
    except PermissionDenied as e:
        logging.error(f"Gemini API Permission Denied or Invalid API Key: {e}")
        raise GeminiAPIFallbackError(f"Gemini API Permission Denied: {e}")
    except ResourceExhausted as e:
        logging.error(f"Gemini API Quota Exceeded: {e}")
        raise GeminiAPIFallbackError(f"Gemini API Quota Exceeded: {e}")
    except Exception as e:
        logging.error(f"Error during Gemini API call: {e}", exc_info=True)
        raise GeminiAPIFallbackError(f"Generic Gemini API error: {e}")

async def _call_mistral_api(prompt_text: str) -> str:
    """Helper function to make the Mistral API call."""
    if not mistral_client or not MISTRAL_MODEL_NAME:
        logging.error("Mistral client or model name not configured. Cannot make API call.")
        return "" # Return empty string for consistent error handling
    
    logging.info(f"Attempting API call to Mistral model: {MISTRAL_MODEL_NAME}")
    try:
        chat_response = await mistral_client.chat.complete_async(
            model=MISTRAL_MODEL_NAME,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        if chat_response and chat_response.choices and chat_response.choices[0].message.content:
            return chat_response.choices[0].message.content
        logging.warning(f"Mistral LLM response was empty or did not contain content. Response: {chat_response}")
        return ""
    except Exception as e:
        # Log specific Mistral errors if identifiable, otherwise generic
        if "API key" in str(e) or "authentication" in str(e).lower():
             logging.error(f"Mistral API Key/Authentication Error: {e}")
        elif "quota" in str(e).lower(): # Example for quota, adjust if Mistral has specific exceptions
            logging.error(f"Mistral API Quota Error: {e}")
        else:
            logging.error(f"Error during Mistral API call: {e}", exc_info=True)
        return "" # Return empty string on error

async def llm_analysis_start(report_data: dict) -> dict:
    page_url_from_report = report_data.get('url') # Keep this for _error_response

    def _error_response(message, url=None, raw_resp=""):
        # Consistent error response structure including needless_info
        err_dict = {
            "url": url if url else page_url_from_report,
            "error": message,
            "keywords": [], "content_summary": "", "other_information_and_contacts": [],
            "suggested_keywords_for_seo": [], "header": [], "footer": [], "needless_info": []
        }
        if raw_resp:
            err_dict["llm_response_raw"] = raw_resp[:500] # Include raw response snippet if available
        return err_dict

    if not gemini_model_instance and not (mistral_client and MISTRAL_MODEL_NAME):
        logging.error("No LLM configured (neither Gemini nor Mistral). Cannot perform LLM analysis.")
        return _error_response("No LLM configured.", url=page_url_from_report)

    if not report_data or not isinstance(report_data, dict):
        logging.warning("llm_analysis_start received empty or invalid report_data (not a dict).")
        return _error_response("Invalid report_data: must be a dictionary.", url=page_url_from_report)

    # page_url_from_report already defined above
    if not page_url_from_report:
        logging.warning("llm_analysis_start received report_data without a top-level 'url' field.")
        # Since page_url_from_report would be None here, explicitly pass None or handle differently
        return _error_response("Missing 'url' in report_data.", url=None) 
    
    logging.info(f"Starting LLM analysis for URL: {page_url_from_report}")

    cleaned_text = None
    headings_data = None

    if 'cleaned_text' in report_data and 'headings' in report_data:
        cleaned_text = report_data.get('cleaned_text', '')
        headings_data = report_data.get('headings', {})
        logging.debug(f"Using direct cleaned_text and headings from report_data for {page_url_from_report}")
    elif 'page_statistics' in report_data and page_url_from_report in report_data.get('page_statistics', {}):
        page_data_from_stats = report_data['page_statistics'][page_url_from_report]
        cleaned_text = page_data_from_stats.get('cleaned_text', '')
        headings_data = page_data_from_stats.get('headings', {})
        logging.debug(f"Using cleaned_text and headings from page_statistics for {page_url_from_report}")
    
    if cleaned_text is None or headings_data is None:
        # Check if cleaned_text is in report_data directly even if headings_data might be missing for some reason
        if 'cleaned_text' in report_data:
             cleaned_text = report_data.get('cleaned_text', '')
             headings_data = report_data.get('headings', {}) # Will default to empty if not present
             logging.debug(f"Using direct cleaned_text (headings might be missing/default) from report_data for {page_url_from_report}")
        else:
            logging.warning(f"Could not extract 'cleaned_text' and 'headings' for URL {page_url_from_report} from report_data.")
            return _error_response("Essential page data (cleaned_text, headings) not found for analysis.", url=page_url_from_report)

    # Pre-clean the cleaned_text to remove defined boilerplate phrases before sending to LLM
    if cleaned_text:
        original_len_for_debug = len(cleaned_text)
        cleaned_text_after_boilerplate_removal = remove_specific_fixed_phrases(cleaned_text, BOILERPLATE_PHRASES_TO_REMOVE)
        if len(cleaned_text_after_boilerplate_removal) != original_len_for_debug:
            logging.debug(f"Applied boilerplate phrase removal to 'cleaned_text' for LLM input. "
                          f"Original length: {original_len_for_debug}, "
                          f"New length: {len(cleaned_text_after_boilerplate_removal)}. "
                          f"Sample of cleaned: '{cleaned_text_after_boilerplate_removal[:200]}'")
        cleaned_text = cleaned_text_after_boilerplate_removal # Use the cleaned version

    if not cleaned_text and not (headings_data and any(headings_data.values())): # Check if headings_data has any actual headings
        logging.warning(f"No cleaned_text or substantive headings_data found for URL {page_url_from_report} (after potential boilerplate removal). LLM analysis might be ineffective.")
        return _error_response("No content (cleaned_text or substantive headings) available for analysis.", url=page_url_from_report)

    # Language instruction
    language_instruction = f"If content is Turkish make your analysis in Turkish , Otherwise make it in English."
    #lang = st.session_state.get("language", "en") # As in your original
    
    llm_response_str = ""
    service_used = ""

    # Attempt Gemini first if configured
    if gemini_model_instance:
        logging.debug(f"Attempting LLM analysis with Gemini for URL: {page_url_from_report}")
        try:
            # Get Gemini-specific prompt
            prompt = get_gemini_analysis_prompt(page_url_from_report, cleaned_text, headings_data, language_instruction)
            llm_response_str = await _call_gemini_api(prompt)
            if llm_response_str:
                service_used = "Gemini"
            # If llm_response_str is empty here, it means Gemini returned empty, will proceed to Mistral if configured
        except GeminiAPIFallbackError as e:
            logging.warning(f"Gemini API call failed with an error warranting fallback: {e}. Will attempt Mistral.")
        # No other `except Exception` here, as _call_gemini_api handles logging and raises specific error for fallback

    # Attempt Mistral if Gemini was not used, failed, or returned empty, and Mistral is configured
    if not llm_response_str and mistral_client and MISTRAL_MODEL_NAME:
        if service_used == "Gemini": # Implies Gemini was tried and returned empty
            logging.warning(f"Gemini returned an empty response for {page_url_from_report}. Attempting fallback to Mistral.")
        else: # Gemini was not configured, or an error occurred before calling it that triggers Mistral
             logging.info(f"Attempting LLM analysis with Mistral for URL: {page_url_from_report} (Gemini not used or failed).")
        
        try:
            # Get Mistral-specific prompt
            prompt = get_mistral_analysis_prompt(page_url_from_report, cleaned_text, headings_data, language_instruction)
            llm_response_str = await _call_mistral_api(prompt)
            if llm_response_str:
                 service_used = "Mistral"
            # If llm_response_str is empty here, Mistral also returned empty
        except Exception as e: # Catching general exceptions from _call_mistral_api if it doesn't handle all
            logging.error(f"Error during Mistral API call (potentially after Gemini attempt): {e}", exc_info=True)
            # Error message should reflect that Mistral was the one failing here
            return _error_response(f"LLM analysis failed. Mistral error: {str(e)}", url=page_url_from_report)

    if not llm_response_str:
        # This means either only one LLM was configured and it failed/returned empty, or both did.
        tried_services = []
        if gemini_model_instance: tried_services.append("Gemini")
        if mistral_client and MISTRAL_MODEL_NAME: tried_services.append("Mistral")
        service_msg = " and ".join(tried_services) if tried_services else "Configured LLM(s)"
        
        logging.error(f"LLM ({service_msg}) returned empty or no-text response for URL: {page_url_from_report}")
        return _error_response(f"LLM ({service_msg}) returned an empty response.", url=page_url_from_report)
    
    logging.info(f"LLM response received using {service_used} for URL: {page_url_from_report}")

    try:
        # Clean up potential markdown code block fences if LLM doesn't strictly adhere
        cleaned_llm_response_str = llm_response_str.strip()
        if cleaned_llm_response_str.startswith("```json"):
            cleaned_llm_response_str = cleaned_llm_response_str[7:]
        if cleaned_llm_response_str.endswith("```"):
            cleaned_llm_response_str = cleaned_llm_response_str[:-3]
        
        llm_data = json.loads(cleaned_llm_response_str.strip())

    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response from {service_used} for {page_url_from_report}: {e}. Raw Response: '{llm_response_str[:500]}'")
        return _error_response(f"Failed to parse {service_used} response as JSON.", url=page_url_from_report, raw_resp=llm_response_str)
    except Exception as e: # Catch any other unexpected error during parsing
        logging.error(f"Unexpected error parsing LLM response from {service_used} for {page_url_from_report}: {e}", exc_info=True)
        return _error_response(f"Unexpected error parsing {service_used} response.", url=page_url_from_report, raw_resp=llm_response_str)

    analysis_result = {
        "url": page_url_from_report,
        # "llm_service_used": service_used, # You can uncomment this if you want to track it internally
        "keywords": llm_data.get("keywords", []),
        "content_summary": llm_data.get("content_summary", "Summary not generated by LLM."),
        "other_information_and_contacts": llm_data.get("other_information_and_contacts", []),
        "suggested_keywords_for_seo": llm_data.get("suggested_keywords_for_seo", []),
        "header": llm_data.get("header", []), 
        "footer": llm_data.get("footer", []),
        "needless_info": llm_data.get("needless_info", []) # Added needless_info
    }

    logging.info(f"Successfully completed LLM analysis using {service_used} for URL: {page_url_from_report}")
    return analysis_result

# --- Example Usage (Uncomment to test) ---
# async def main():
#     # Create a .env file in the same directory with your API keys:
#     # GEMINI_API_KEY=your_gemini_key
#     # MISTRAL_API_KEY=your_mistral_key
#     # MISTRAL_MODEL_NAME=mistral-small-latest (or your preferred model)
#     load_dotenv()
#
#     sample_report_data_1 = {
#         "url": "http://example.com/test1",
#         "cleaned_text": "İçeriğe geç - Welcome to ExampleCom. Our services include web design and SEO. Contact us at contact@example.com or call 123-456-7890. Follow us on Twitter: https://twitter.com/example. This is some header text: Home, About, Services. This is footer text: © 2024 ExampleCom, Privacy Policy. Needless info: My Cart 0.00 My Cart 0.00. INFORMATION . Başa dön",
#         "headings": {"h1": ["Main Title Example"], "h2": ["Our Services", "Contact Information"]}
#     }
#     sample_report_data_2 = {
#         "url": "http://example.com/test2",
#         "page_statistics": {
#             "http://example.com/test2": {
#                 "cleaned_text": "İçeriğe geç - Turkish example: Bu bir Türkçe web sayfasıdır. Anahtar kelimeler ve SEO hakkında bilgiler içerir. İletişim için e-posta@ornek.com. Başlık: Ana Sayfa, Hakkımızda. Altbilgi: © 2024 Örnek A.Ş. Gereksiz Bilgi: Sepetim 0.00 TL. INFORMATION . Başa dön",
#                 "headings": {"h1": ["Türkçe Başlık"], "h2": ["Hizmetlerimiz"]}
#             }
#         }
#     }
#
#     print("--- Analysis 1 (Direct data) ---")
#     result1 = await llm_analysis_start(sample_report_data_1)
#     print(json.dumps(result1, indent=2, ensure_ascii=False))
#
#     print("\n--- Analysis 2 (Nested page_statistics, Turkish example) ---")
#     result2 = await llm_analysis_start(sample_report_data_2)
#     print(json.dumps(result2, indent=2, ensure_ascii=False))
#
# if __name__ == "__main__":
#    logging.basicConfig(level=logging.DEBUG) # Enable debug for testing
#    asyncio.run(main())