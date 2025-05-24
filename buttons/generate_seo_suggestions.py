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

def generate_seo_suggestions(pages_data_for_suggestions: dict = None) -> str:
    """Generates SEO suggestions and content strategy using Gemini or Mistral based on selected page data from llm_analysis_all.
    
    Args:
        pages_data_for_suggestions: Dict containing either:
            - Selected pages from llm_analysis_all: {"page_key": {...}, ...}
            - Text report fallback: {"_source_type_": "text_report", "content": "..."}
            - None: Will use all llm_analysis_all data
    """
    
    # Get current language
    lang = st.session_state.get("language", "en")

    # Get API keys
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    mistral_api_key = os.getenv('MISTRAL_API_KEY')

    # Determine which API to use
    use_mistral = mistral_api_key is not None and (
        gemini_api_key is None or
        st.session_state.get("use_mistral", True)
    )

    try:
        # Determine data source and prepare report_data_str
        if pages_data_for_suggestions is None:
            # Use all llm_analysis_all if no specific data provided
            if st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                report_data_str = json.dumps(st.session_state.full_report["llm_analysis_all"], indent=2, ensure_ascii=False)
            else:
                return "No detailed analysis data available. Please analyze a URL first to generate suggestions."
        
        elif pages_data_for_suggestions.get("_source_type_") == "text_report":
            # Handle text_report fallback
            report_data_str = pages_data_for_suggestions.get("content", "No content available")
            
        else:
            # Handle selected pages from llm_analysis_all
            report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)

        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(report_data_str, mistral_api_key, lang)
        else:
            # Use Gemini API
            language_instruction = f"Respond in Turkish. " if lang == "tr" else "Respond in English. "
            
            # Handle different data types in prompt
            if pages_data_for_suggestions and pages_data_for_suggestions.get("_source_type_") == "text_report":
                prompt = f"""{language_instruction}
You are an expert SEO strategist and content analyst.
You have been provided with a general SEO report for a website. Based on this report, generate comprehensive and actionable SEO recommendations.

Your task is to:
1. Analyze the provided report thoroughly
2. Generate NEW actionable SEO and content strategy recommendations
3. Organize suggestions into clear categories (On-Page SEO, Technical SEO, Content Strategy, User Experience)
4. For each suggestion, provide:
   - Clear, actionable recommendation
   - Brief rationale explaining why it's important
   - Suggested priority (High, Medium, Low)

Here is the SEO report:
{report_data_str}
"""
            else:
                prompt = f"""{language_instruction}
You are an expert SEO strategist and content analyst.
You have been provided with detailed analysis data for specific page(s) from a website. This data typically includes content summaries, keywords, headers, tone, audience, topics, and existing SEO keyword suggestions for each selected page (e.g., 'main_page' and other specific URLs).

The provided data structure is a dictionary where keys are page identifiers (like 'main_page' or a URL) and values are the detailed analysis for that page.

Your task is to:
1. Thoroughly analyze ALL sections of the provided data for EACH page.
2. Based on your deep analysis of this data, generate a NEW and comprehensive set of actionable SEO and content strategy recommendations specifically tailored to improve the visibility and performance of these analyzed pages.
3. Critically evaluate the findings for each page. Identify strengths, weaknesses, and untapped opportunities.
4. Your recommendations should aim to significantly improve the search engine rankings, organic traffic, user engagement, and overall online presence of these specific pages.
5. **Crucially, if the data for a page contains a section with pre-existing suggestions (like 'suggested_keywords_for_seo'), do not merely rephrase or repeat them.** Instead, you should:
   - Provide *additional, distinct* recommendations.
   - Elaborate on existing points if you can offer significant new depth or a different angle.
   - Identify areas that might have been overlooked or underemphasized for these pages.
   - Offer alternative strategies.
6. Organize your suggestions clearly by categories like:
   - Overall Strategic Insights (Synthesizing findings from all provided pages)
   - Page-Specific Recommendations (If multiple pages are provided)
   - On-Page SEO (Meta tags, Content optimization, Internal linking, Keyword usage specific to these pages)
   - Technical SEO (Consider if any page-specific technical aspects can be inferred)
   - Content Strategy (Content gaps on these pages, New content ideas, Content promotion, E-E-A-T improvement)
   - User Experience (UX) related to the content and structure of these pages.
7. For each suggestion, provide:
   - A clear, actionable recommendation.
   - A brief rationale explaining *why* it's important, referencing specific findings from the provided page data.
   - Suggested priority (High, Medium, Low).

Here is the detailed analysis data for the selected page(s):
{report_data_str}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text

        return response_text
        
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        return f"Could not generate SEO suggestions: {str(e)}"

def generate_with_mistral(report_data_str: str, api_key: str, lang: str = "en") -> str:
    """Generate SEO suggestions using Mistral API."""
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    language_names = {"en": "English", "tr": "Turkish"}
    mistral_language_instruction = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "

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
Please analyze the following detailed analysis data for specific page(s) from a website. This data includes content summaries, keywords, suggested keywords, tone, audience, topics, etc., for each selected page.

Your objective is to go beyond any existing recommendations found within this page-specific data. Based on a thorough examination of ALL the provided information:

1. Generate a **new set of strategic SEO and content recommendations specifically for these pages**. These should be distinct from, or significantly build upon/offer alternatives to, any pre-existing suggestions within the provided data.
2. Identify key opportunities for improvement, potential weaknesses, and areas that require more attention based on the data provided.
3. Structure your suggestions into logical categories (e.g., Overall Strategic Insights, On-Page SEO, Technical SEO, Content Strategy, User Experience).
4. For each new suggestion, provide:
   - The recommendation itself (actionable).
   - The reasoning behind it, linking back to specific data or patterns observed in the report data.
   - A suggested priority level (High, Medium, Low).
5. Focus on delivering high-impact advice that can demonstrably improve the SEO performance and user engagement of these specific pages.

Here is the detailed analysis data:
{report_data_str}
"""
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
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