#buttons/generate_product_description.py
import google.generativeai as genai
import re
import random
import logging
import os
import streamlit as st
import requests
# Removed unused import: from utils.language_support import language_manager
# Language is handled via st.session_state

# Configure Logging
logging.basicConfig(level=logging.INFO)

# Configure Gemini API
try:
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        # Aligning model name with other parts of the application
        model = genai.GenerativeModel('gemini-2.0-flash') 
        logging.info("Gemini API configured with gemini-2.0-flash")
    else:
        model = None
        logging.warning("GEMINI_API_KEY not found. Gemini model not configured.")
except Exception as e:
    model = None
    logging.error(f"Error configuring Gemini API: {e}")


def extract_products_from_keywords(text_report: str) -> str:
    """Extracts a potential product-related focus keyword from the text report."""
    if not text_report or not isinstance(text_report, str): # Added check for valid text_report
        logging.warning("extract_products_from_keywords: text_report is None or not a string.")
        return "related products"
        
    try:
        # Prioritize "Top Keywords" section
        match = re.search(r"Top Keywords by Frequency:(.*?)(\n|\Z)", text_report, re.DOTALL | re.IGNORECASE)
        if match:
            keywords_section = match.group(1)
            # Improved regex to handle various list formats (-, *, digits.)
            keywords = re.findall(r"^\s*[-*\d]+\.?\s*(.*?):", keywords_section, re.MULTILINE)
            if keywords:
                return random.choice([k.strip() for k in keywords if k.strip()])

        # Look for product categories if structure exists
        match = re.search(r'"categories":\s*\{(.*?)\}', text_report, re.DOTALL | re.IGNORECASE)
        if match:
            categories_section = match.group(1)
            categories = re.findall(r'"(.*?)"', categories_section)
            if categories:
                 # Filter out generic terms if possible
                 filtered_categories = [cat for cat in categories if len(cat) > 3 and cat.lower() not in ["products", "services", "all"]]
                 if filtered_categories:
                     return random.choice(filtered_categories)
                 elif categories:
                    return random.choice(categories) # Fallback to any category


        # General keyword extraction as fallback (less reliable for products)
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', text_report) # Min 4 letters
        if keywords:
            common_words = set(["the", "and", "for", "with", "this", "that", "from", "report", "analysis", "website", "page", "content", "keywords", "search", "engine", "google", "results", "traffic", "recommendations"])
            filtered_keywords = [
                word for word in keywords
                if word.lower() not in common_words and not word.isdigit()
            ]
            if filtered_keywords:
                return random.choice(filtered_keywords)

        return "related products" # Generic fallback
    except Exception as e:
        logging.error(f"Error extracting keywords: {e}")
        return "related products"


# *** UPDATED Gemini Function ***
def generate_product_description(text_report: str, product_options: dict) -> str:
    """Generates a product description using Gemini based on SEO report and user options."""
    if not model:
        return "Error: Gemini model not configured. Check GEMINI_API_KEY."

    try:
        # Get language from session state
        lang = st.session_state.get("language", "en")
        language_names = {"en": "English", "tr": "Turkish"}
        language_instruction = f"Respond in {language_names.get(lang, 'English')}. "

        # Extract options from the dictionary
        product_name = product_options.get("product_name")
        product_details = product_options.get("product_details", "")
        tone = product_options.get("tone", "Professional")
        length_option = product_options.get("length", "Medium")

        # Basic validation
        if not product_name or not product_details:
            return "Error: Product Name and Product Details are required."

        # Map length option to word count guidance
        length_guidance = ""
        if length_option == "Short":
            length_guidance = "around 100-150 words"
        elif length_option == "Medium":
            length_guidance = "around 150-250 words"
        elif length_option == "Long":
            length_guidance = "around 250-350 words"
        else:
            length_guidance = "a moderate length" # Default if mapping fails

        # Extract a keyword for context (optional enrichment) & prepare report context
        seo_context_keyword = extract_products_from_keywords(text_report) if text_report else "related products"
        report_context_for_prompt = text_report[:1500] if text_report and isinstance(text_report, str) else "No additional site context available."


        # Construct the prompt using the provided options
        prompt = f"""
{language_instruction}
Act as an expert copywriter. Write a compelling product description based on the details provided below.

**Product Information:**
- Product Name: {product_name}
- Key Features/Benefits/Specifications/Target Audience: {product_details}

**Instructions:**
1.  Write the product description for "{product_name}".
2.  Adopt a **{tone}** tone.
3.  The description should be approximately **{length_guidance}** long.
4.  Focus on the product details provided. Highlight the most important features and benefits for the customer.
5.  Make it engaging, persuasive, and easy to read.
6.  **Do not** mention the SEO report explicitly. You can subtly incorporate relevant themes or keywords like '{seo_context_keyword}' if they fit naturally with the product description, but prioritize describing the product based on the provided details.

**[Optional Context from SEO Report Summary - Use subtly if relevant]:**
{report_context_for_prompt}

Generate the product description now:
"""
        logging.info(f"Generating Gemini description for: {product_name}")
        response = model.generate_content(prompt)
        
        if hasattr(response, 'parts') and response.parts: # More robust check for Gemini's response structure
             return response.text
        elif hasattr(response, 'text') and response.text: # Fallback for simpler text responses
             return response.text
        else:
             # Log safety feedback if available
             safety_feedback_message = ""
             if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                 safety_feedback_message = f"Safety feedback: {response.prompt_feedback}"
             logging.warning(f"Gemini response blocked or empty for '{product_name}'. {safety_feedback_message}")
             return f"Error: Could not generate description for '{product_name}' (response blocked or empty). {safety_feedback_message}".strip()


    except Exception as e:
        logging.error(f"Error generating Gemini product description for '{product_name}': {e}", exc_info=True)
        return f"Error: Could not generate product description for '{product_name}' via Gemini ({e})."


# *** UPDATED Mistral Function ***
def generate_product_description_with_mistral(text_report: str, product_options: dict, api_key: str) -> str:
    """Generates a product description using Mistral API based on SEO report and user options."""
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json", 
        "Authorization": f"Bearer {api_key}"
    }

    try:
        # Get language from session state
        lang = st.session_state.get("language", "en")
        language_names = {"en": "English", "tr": "Turkish"}
        language_instruction = f"Please respond in {language_names.get(lang, 'English')}. "

        # Extract options from the dictionary
        product_name = product_options.get("product_name")
        product_details = product_options.get("product_details", "")
        tone = product_options.get("tone", "Professional")
        length_option = product_options.get("length", "Medium")

        # Basic validation
        if not product_name or not product_details:
            return "Error: Product Name and Product Details are required."

        # Map length option to word count guidance
        length_guidance = ""
        max_tokens_map = { "Short": 200, "Medium": 350, "Long": 500 } 
        if length_option == "Short":
            length_guidance = "around 100-150 words"
        elif length_option == "Medium":
            length_guidance = "around 150-250 words"
        elif length_option == "Long":
            length_guidance = "around 250-350 words"
        else:
            length_guidance = "a moderate length"

        # Extract a keyword for context (optional enrichment) & prepare report context
        seo_context_keyword = extract_products_from_keywords(text_report) if text_report else "related products"
        report_context_for_prompt = text_report[:1500] if text_report and isinstance(text_report, str) else "No additional site context available."

        # System Prompt
        system_prompt = f"""You are an expert copywriter. Your task is to write a compelling product description.
- Adopt a **{tone}** tone.
- The description should be approximately **{length_guidance}** long.
- Focus on the product details provided by the user.
- Make it engaging, persuasive, and easy to read.
- {language_instruction}
- Do not mention SEO reports. You can subtly use relevant themes or keywords like '{seo_context_keyword}' from the context if they fit naturally.
"""

        # User Prompt with Product Info and Context
        user_prompt = f"""Write a product description for:

**Product Name:** {product_name}

**Product Details:**
{product_details}

**[Optional Context from SEO Report Summary]:**
{report_context_for_prompt}
"""

        data = {
            "model": "mistral-large-latest", 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens_map.get(length_option, 350)
        }

        logging.info(f"Generating Mistral description for: {product_name}")
        response = requests.post(url, headers=headers, json=data, timeout=60) 
        response.raise_for_status() 

        response_json = response.json()

        if response_json.get('choices') and response_json['choices'][0].get('message'):
             content = response_json['choices'][0]['message'].get('content')
             if content:
                 return content.strip()
             else:
                 logging.warning(f"Mistral response missing content for '{product_name}'.")
                 return f"Error: Could not generate description for '{product_name}' (empty content from Mistral)."
        else:
             logging.warning(f"Unexpected Mistral response format for '{product_name}': {response_json}")
             return f"Error: Could not parse Mistral response for '{product_name}'."


    except requests.exceptions.RequestException as e:
         logging.error(f"Mistral API request error for '{product_name}': {e}", exc_info=True)
         error_detail = ""
         if e.response is not None:
             try:
                 error_detail = e.response.json()
             except ValueError: 
                 error_detail = e.response.text
         return f"Error: Could not connect to Mistral API for '{product_name}'. Details: {error_detail}"
    except Exception as e:
        logging.error(f"Error generating Mistral product description for '{product_name}': {e}", exc_info=True)
        return f"Error: Could not generate product description for '{product_name}' via Mistral ({e})."

# *** UPDATED API Choice Function ***
def generate_product_description_with_api_choice(text_report: str, product_options: dict) -> str:
    """Generates product description using either Gemini or Mistral based on availability and user preference."""

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    mistral_api_key = os.getenv('MISTRAL_API_KEY')

    # Check product_options upfront for required keys
    product_name = product_options.get("product_name")
    product_details = product_options.get("product_details")

    if not product_name or not product_details:
         logging.error(f"generate_product_description_with_api_choice: Missing product_name ('{product_name}') or product_details.")
         return "Error: Missing required product information (Name and Details)."
    
    # Determine preferred model
    prefer_mistral = st.session_state.get("use_mistral", True) 

    can_use_mistral = mistral_api_key is not None
    can_use_gemini = gemini_api_key is not None and model is not None 

    use_mistral_flag = can_use_mistral and (prefer_mistral or not can_use_gemini)
    use_gemini_flag = can_use_gemini and not use_mistral_flag


    try:
        if use_mistral_flag:
            logging.info(f"Using Mistral API for product description: {product_name}")
            return generate_product_description_with_mistral(text_report, product_options, mistral_api_key)
        elif use_gemini_flag:
            logging.info(f"Using Gemini API for product description: {product_name}")
            return generate_product_description(text_report, product_options)
        else:
            error_messages = []
            if not can_use_mistral: error_messages.append("MISTRAL_API_KEY not found or invalid.")
            if not can_use_gemini: error_messages.append("GEMINI_API_KEY not found or Gemini model failed to configure.")
            
            final_error_msg = "Error: No suitable API available for product generation. " + " ".join(error_messages)
            logging.error(final_error_msg + f" (Product: {product_name})")
            return final_error_msg

    except Exception as e:
        logging.error(f"Error in API choice logic or function call for '{product_name}': {e}", exc_info=True)
        return f"Error: An unexpected issue occurred during generation for '{product_name}' ({e})."