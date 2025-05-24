#SeoTree/generate_seo_suggestions.py
import google.generativeai as genai
import json
import logging
import os
import streamlit as st
import requests
from utils.language_support import language_manager

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# MODIFIED FUNCTION SIGNATURE
def generate_seo_suggestions(pages_data_for_suggestions: dict) -> str: # Changed from 'text_report: str'
    """Generates SEO suggestions and content strategy using Gemini or Mistral based on selected page data from llm_analysis_all.
    Limited to one call per session."""

    # Get current language
    lang = st.session_state.get("language", "en")

    # Check if suggestions have already been generated in this session
    #if "seo_suggestions_generated" in st.session_state and st.session_state.seo_suggestions_generated:
     #   return "SEO suggestions have already been generated in this session. Please refresh the page to generate new suggestions."

    # Get API keys
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    mistral_api_key = os.getenv('MISTRAL_API_KEY')

    # Determine which API to use
    use_mistral = mistral_api_key is not None and (
        gemini_api_key is None or
        st.session_state.get("use_mistral", True)
    )

    try:
        # Convert the structured page data to a JSON string for the prompt
        report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)

        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(report_data_str, mistral_api_key, lang) # Pass stringified data
        else:
            # Use Gemini API
            language_instruction = f"Respond in Turkish. " if lang == "tr" else "Respond in English. "
            
            # GENERALIZED PROMPT FOR GEMINI (UPDATED)
            prompt = f"""{language_instruction}
You are an expert SEO strategist and content analyst.
You have been provided with detailed analysis data for specific page(s) from a website. This data typically includes content summaries, keywords, headers, tone, audience, topics, and existing SEO keyword suggestions for each selected page (e.g., 'main_page' and other specific URLs).

The provided data structure is a dictionary where keys are page identifiers (like 'main_page' or a URL) and values are the detailed analysis for that page.

Your task is to:
1.  Thoroughly analyze ALL sections of the provided data for EACH page.
2.  Based on your deep analysis of this data, generate a NEW and comprehensive set of actionable SEO and content strategy recommendations specifically tailored to improve the visibility and performance of these analyzed pages. Also consider how they contribute to the site's overall SEO if possible from the given data.
3.  Critically evaluate the findings for each page. Identify strengths, weaknesses, and untapped opportunities.
4.  Your recommendations should aim to significantly improve the search engine rankings, organic traffic, user engagement, and overall online presence of these specific pages and, by extension, the site.
5.  **Crucially, if the data for a page contains a section with pre-existing suggestions (like 'suggested_keywords_for_seo'), do not merely rephrase or repeat them.** Instead, you should:
    *   Provide *additional, distinct* recommendations.
    *   Elaborate on existing points if you can offer significant new depth or a different angle.
    *   Identify areas that might have been overlooked or underemphasized for these pages.
    *   Offer alternative strategies.
6.  Organize your suggestions clearly, for example, by categories like:
    *   Overall Strategic Insights (Synthesizing findings from all provided pages)
    *   Page-Specific Recommendations (If multiple pages are provided, you can optionally group recommendations per page or integrate them into the categories below, clearly indicating which page a suggestion pertains to if it's highly specific).
    *   On-Page SEO (Meta tags, Content optimization, Internal linking, Keyword usage specific to these pages)
    *   Technical SEO (Consider if any page-specific technical aspects can be inferred or suggested, e.g., related to structured data for a specific page type)
    *   Content Strategy (Content gaps on these pages, New content ideas related to these pages, Content promotion, E-E-A-T improvement for these pages)
    *   User Experience (UX) related to the content and structure of these pages.
7.  For each suggestion, provide:
    *   A clear, actionable recommendation.
    *   A brief rationale explaining *why* it's important, referencing specific findings or patterns from the provided page data.
    *   Suggested priority (High, Medium, Low).

The goal is to extract maximum value from the analytical data for the selected page(s) and provide fresh, high-quality strategic advice for them.

Here is the detailed analysis data for the selected page(s):
\n\n{report_data_str}
"""
            response = model.generate_content(prompt)
            response_text = response.text

        # Mark that suggestions have been generated in this session
        #st.session_state.seo_suggestions_generated = True

        return response_text
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        return f"Could not generate SEO suggestions: {str(e)}"

# MODIFIED FUNCTION SIGNATURE
def generate_with_mistral(report_data_str: str, api_key: str, lang: str = "en") -> str: # Changed from 'pages_data_for_suggestions: dict' to 'report_data_str: str'
    """Generate SEO suggestions using Mistral API."""
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    language_names = {"en": "English", "tr": "Turkish"}
    mistral_language_instruction = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "

    # GENERALIZED SYSTEM AND USER PROMPTS FOR MISTRAL (UPDATED)
    data = {
        "model": "mistral-large-latest",
        "messages": [
            {
                "role": "system",
                "content": f"You are a world-class SEO strategist and content analyst. Your primary function is to provide expert, actionable, and insightful recommendations based on detailed SEO analysis data for specific web pages. {mistral_language_instruction} You are analyzing detailed data for one or more pages of a website. Your advice should be tailored to the information presented in the data and delivered entirely in the requested language."
            },
            {
                "role": "user",
                "content": f"""{mistral_language_instruction}
Please analyze the following detailed analysis data for specific page(s) from a website. This data includes content summaries, keywords, suggested keywords, tone, audience, topics, etc., for each selected page. The data is structured as a JSON object where keys are page identifiers (like 'main_page' or a URL) and values are the analysis for that page.

Your objective is to go beyond any existing recommendations found within this page-specific data. Based on a thorough examination of ALL the provided information for EACH selected page:

1.  Generate a **new set of strategic SEO and content recommendations specifically for these pages**. These should be distinct from, or significantly build upon/offer alternatives to, any pre-existing suggestions (like 'suggested_keywords_for_seo') within the provided data for these pages.
2.  Identify key opportunities for improvement, potential weaknesses, and areas that require more attention based on the data provided for these pages.
3.  Structure your suggestions into logical categories (e.g., Overall Strategic Insights, Page-Specific Recommendations (optional grouping), On-Page SEO, Technical SEO (if applicable from page data), Content Strategy for these pages, User Experience on these pages).
4.  For each new suggestion, provide:
    *   The recommendation itself (actionable).
    *   The reasoning behind it, linking back to specific data or patterns observed in the page-specific report data.
    *   A suggested priority level (High, Medium, Low).
5.  Focus on delivering high-impact advice that can demonstrably improve the SEO performance and user engagement of these specific pages, based on the details provided. Do not simply summarize or rehash any pre-existing recommendation section in the input. Provide fresh, expert insights for the analyzed pages. Ensure your entire response adheres to the specified language.

Here is the detailed analysis data for the selected page(s):
\n\n{report_data_str}
"""
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000 # Consider increasing if comprehensive reports are very long
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('choices') and len(response_json['choices']) > 0 and response_json['choices'][0].get('message'):
            return response_json['choices'][0]['message']['content']
        else:
            raise Exception(f"Mistral API response format error: 'choices' or 'message' structure not as expected. Response: {response.text}")
    else:
        raise Exception(f"Mistral API error: {response.status_code} - {response.text}")