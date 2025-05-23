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
        # Check available models, adjust if 'gemini-2.0-flash' is not right or available
        # For example: model = genai.GenerativeModel('gemini-1.5-flash-latest')
        model = genai.GenerativeModel('gemini-2.0-flash') # Using a potentially more current model
        logging.info("Gemini API configured.")
    else:
        model = None
        logging.warning("GEMINI_API_KEY not found. Gemini model not configured.")
except Exception as e:
    model = None
    logging.error(f"Error configuring Gemini API: {e}")


# This function might be less needed now but kept for potential context
def extract_products_from_keywords(text_report: str) -> str:
    """Extracts a potential product-related focus keyword from the text report."""
    # ... (keep the existing logic for this function if you still want it as fallback/context)
    # For simplicity in the main generation, we'll prioritize user input.
    # You could potentially use this to add context like "Relevant keywords from analysis: ..."
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
        # Consider if this is still useful or generates noise
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', text_report) # Min 4 letters
        if keywords:
            common_words = set(["the", "and", "for", "with", "this", "that", "from", "report", "analysis", "website", "page", "content", "keywords", "search", "engine", "google", "results", "traffic", "recommendations"])
            filtered_keywords = [
                word for word in keywords
                if word.lower() not in common_words and not word.isdigit()
            ]
            if filtered_keywords:
                # Maybe weight keywords appearing multiple times? Simple random choice for now.
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

        # Extract a keyword for context (optional enrichment)
        seo_context_keyword = extract_products_from_keywords(text_report)

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
{text_report[:1500]}  # Provide a snippet for context, not the whole report

Generate the product description now:
"""
        logging.info(f"Generating Gemini description for: {product_name}")
        response = model.generate_content(prompt)
        # Add basic check for response content
        if response.parts:
             return response.text
        else:
             # Log safety feedback if available
             logging.warning(f"Gemini response blocked or empty. Safety feedback: {response.prompt_feedback}")
             return "Error: Could not generate description (response blocked or empty)."


    except Exception as e:
        logging.error(f"Error generating Gemini product description: {e}")
        return f"Error: Could not generate product description via Gemini ({e})."


# *** UPDATED Mistral Function ***
def generate_product_description_with_mistral(text_report: str, product_options: dict, api_key: str) -> str:
    """Generates a product description using Mistral API based on SEO report and user options."""
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json", # Good practice
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
        max_tokens_map = { "Short": 200, "Medium": 350, "Long": 500 } # Adjusted max_tokens estimates
        if length_option == "Short":
            length_guidance = "around 100-150 words"
        elif length_option == "Medium":
            length_guidance = "around 150-250 words"
        elif length_option == "Long":
            length_guidance = "around 250-350 words"
        else:
            length_guidance = "a moderate length"

        # Extract a keyword for context (optional enrichment)
        seo_context_keyword = extract_products_from_keywords(text_report)

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
{text_report[:1500]}
"""

        data = {
            "model": "mistral-large-latest",  # Or choose another suitable model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
             # Adjust max_tokens based on length, add buffer
            "max_tokens": max_tokens_map.get(length_option, 350)
        }

        logging.info(f"Generating Mistral description for: {product_name}")
        response = requests.post(url, headers=headers, json=data, timeout=60) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        response_json = response.json()

        if response_json.get('choices') and response_json['choices'][0].get('message'):
             content = response_json['choices'][0]['message'].get('content')
             if content:
                 return content.strip()
             else:
                 logging.warning("Mistral response missing content.")
                 return "Error: Could not generate description (empty content)."
        else:
             logging.warning(f"Unexpected Mistral response format: {response_json}")
             return "Error: Could not parse Mistral response."


    except requests.exceptions.RequestException as e:
         logging.error(f"Mistral API request error: {e}")
         # Attempt to get more detail from response if available
         error_detail = ""
         if e.response is not None:
             try:
                 error_detail = e.response.json()
             except ValueError: # Handle cases where response is not JSON
                 error_detail = e.response.text
         return f"Error: Could not connect to Mistral API. {error_detail}"
    except Exception as e:
        logging.error(f"Error generating Mistral product description: {e}")
        return f"Error: Could not generate product description via Mistral ({e})."

# *** UPDATED API Choice Function ***
def generate_product_description_with_api_choice(text_report: str, product_options: dict) -> str:
    """Generates product description using either Gemini or Mistral based on availability and user preference."""

    # Retrieve keys securely
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    mistral_api_key = os.getenv('MISTRAL_API_KEY')

    # Determine preferred model (assuming 'use_mistral' might be in session_state, default to True if Mistral key exists)
    # You might want a more explicit model selection UI element
    prefer_mistral = st.session_state.get("use_mistral", True) # Example preference check

    can_use_mistral = mistral_api_key is not None
    can_use_gemini = gemini_api_key is not None and model is not None # Check model is configured

    use_mistral = can_use_mistral and (prefer_mistral or not can_use_gemini)
    use_gemini = can_use_gemini and not use_mistral

    # Basic validation of input options
    if not product_options or not product_options.get("product_name") or not product_options.get("product_details"):
         return "Error: Missing required product information (Name and Details)."

    try:
        if use_mistral:
            logging.info("Using Mistral API for product description.")
            return generate_product_description_with_mistral(text_report, product_options, mistral_api_key)
        elif use_gemini:
            logging.info("Using Gemini API for product description.")
            return generate_product_description(text_report, product_options)
        else:
            logging.error("No suitable API key found or model configured.")
            # Provide specific message based on which keys are missing
            if not can_use_mistral and not can_use_gemini:
                 return "Error: No API key found for Mistral or Gemini."
            elif not can_use_mistral:
                 return "Error: MISTRAL_API_KEY not found."
            elif not can_use_gemini:
                 return "Error: GEMINI_API_KEY not found or Gemini model failed to configure."
            else: # Should not happen with the logic above, but as a safeguard
                 return "Error: Could not determine API to use."

    except Exception as e:
        # Catch any unexpected errors during the choice/call process
        logging.error(f"Error in API choice logic or function call: {e}")
        return f"Error: An unexpected issue occurred during generation ({e})."
