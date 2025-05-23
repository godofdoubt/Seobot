#SeoTree/generate_seo_suggestions.py
import google.generativeai as genai
import json # Keep for now, might be useful if text_report needs parsing later, or remove if definitely not needed.
import logging
import os
import streamlit as st
import requests
from utils.language_support import language_manager

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-pro-002') # As per original file

# MODIFIED FUNCTION SIGNATURE
def generate_seo_suggestions(text_report: str) -> str: # Changed from 'report: dict'
    """Generates SEO suggestions and content strategy using Gemini or Mistral based on the full text report.
    Limited to one call per session."""

    # Get current language
    lang = st.session_state.get("language", "en")

    # Check if suggestions have already been generated in this session
    if "seo_suggestions_generated" in st.session_state and st.session_state.seo_suggestions_generated:
        return "SEO suggestions have already been generated in this session. Please refresh the page to generate new suggestions."

    # Get API keys
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    mistral_api_key = os.getenv('MISTRAL_API_KEY')

    # Determine which API to use
    use_mistral = mistral_api_key is not None and (
        gemini_api_key is None or
        st.session_state.get("use_mistral", True)
    )

    try:
        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(text_report, mistral_api_key, lang)
        else:
            # Use Gemini API
            language_instruction = f"Respond in Turkish. " if lang == "tr" else "Respond in English. "
            
            # GENERALIZED PROMPT FOR GEMINI
            prompt = f"""{language_instruction}
You are an expert SEO strategist and content analyst. You have been provided with a comprehensive SEO analysis report for a website.

The report typically includes:
- Main Page Analysis (Content Summary, Keywords, Headers, etc.)
- Detailed Subpage Analysis (Summary, Tone, Audience, Topics, Keywords, SEO Keyword Suggestions for multiple pages)
- Site-Wide Aggregations (Common Keywords, Suggested SEO Keywords, Topics, Audiences, Tones)
- Potentially a section with pre-existing suggestions (e.g., 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS').

Your task is to:
1.  Thoroughly analyze ALL sections of the provided report.
2.  Based on your deep analysis of the *entire* report (especially the content summaries, keyword lists, site-wide data, and individual page details), generate a NEW and comprehensive set of actionable SEO and content strategy recommendations.
3.  Critically evaluate the findings. Identify strengths, weaknesses, and untapped opportunities.
4.  Your recommendations should aim to significantly improve the website's search engine rankings, organic traffic, user engagement, and overall online presence.
5.  **Crucially, if the report contains a section with pre-existing suggestions, do not merely rephrase or repeat them.** Instead, you should:
    *   Provide *additional, distinct* recommendations.
    *   Elaborate on existing points if you can offer significant new depth or a different angle.
    *   Identify areas that might have been overlooked or underemphasized.
    *   Offer alternative strategies.
6.  Organize your suggestions clearly, for example, by categories like:
    *   On-Page SEO (Meta tags, Content optimization, Internal linking, Keyword usage)
    *   Technical SEO (Site speed, Mobile-friendliness, Crawlability, Schema markup)
    *   Content Strategy (Content gaps, New content ideas, Content promotion, E-E-A-T improvement)
    *   Off-Page SEO (Link building, Local SEO if applicable based on report data)
    *   User Experience (UX)
7.  For each suggestion, provide:
    *   A clear, actionable recommendation.
    *   A brief rationale explaining *why* it's important, referencing specific findings or patterns from the report.
    *   Suggested priority (High, Medium, Low).

The goal is to extract maximum value from the raw analytical data in the report and provide fresh, high-quality strategic advice.

Here is the report:
\n\n{text_report}
"""
            response = model.generate_content(prompt)
            response_text = response.text

        # Mark that suggestions have been generated in this session
        st.session_state.seo_suggestions_generated = True

        return response_text
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        return f"Could not generate SEO suggestions: {str(e)}"

# MODIFIED FUNCTION SIGNATURE
def generate_with_mistral(text_report: str, api_key: str, lang: str = "en") -> str: # Changed from 'report: dict'
    """Generate SEO suggestions using Mistral API."""
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    language_names = {"en": "English", "tr": "Turkish"}
    mistral_language_instruction = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "

    # GENERALIZED SYSTEM AND USER PROMPTS FOR MISTRAL
    data = {
        "model": "mistral-large-latest",
        "messages": [
            {
                "role": "system",
                "content": f"You are a world-class SEO strategist and content analyst. Your primary function is to provide expert, actionable, and insightful recommendations based on detailed SEO reports. {mistral_language_instruction} You are analyzing a detailed SEO report for a website. Your advice should be tailored to the information presented in the report and delivered entirely in the requested language."
            },
            {
                "role": "user",
                "content": f"""{mistral_language_instruction}
Please analyze the following comprehensive SEO report for a website.

The report typically contains:
- Main Page Analysis
- Detailed Subpage Analysis (summaries, keywords, current SEO suggestions, etc.)
- Site-Wide Analyses (keywords, topics, audience, tone)
- Potentially an existing section with suggestions (e.g., 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS').

Your objective is to go beyond any existing recommendations. Based on a thorough examination of ALL the data within the report (especially the raw analysis of content, keywords, and site structure):

1.  Generate a **new set of strategic SEO and content recommendations**. These should be distinct from, or significantly build upon/offer alternatives to, those already present in the report, if any.
2.  Identify key opportunities for improvement, potential weaknesses, and areas that require more attention based on the data provided.
3.  Structure your suggestions into logical categories (e.g., On-Page SEO, Technical SEO, Content Strategy, Off-Page SEO/Local SEO if relevant, User Experience).
4.  For each new suggestion, provide:
    *   The recommendation itself (actionable).
    *   The reasoning behind it, linking back to specific data or patterns observed in the report.
    *   A suggested priority level (High, Medium, Low).
5.  Focus on delivering high-impact advice that can demonstrably improve the website's SEO performance and user engagement, based on the specifics of the provided report. Do not simply summarize or rehash any pre-existing recommendation section in the input. Provide fresh, expert insights. Ensure your entire response adheres to the specified language.

Here is the SEO report:
\n\n{text_report}
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