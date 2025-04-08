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
model = genai.GenerativeModel('gemini-1.5-pro-002')

def generate_seo_suggestions(report: dict) -> str:
    """Generates SEO suggestions using Gemini or Mistral based on the full report.
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
            response_text = generate_with_mistral(report, mistral_api_key, lang)
        else:
            # Use Gemini API
            language_instruction = f"Respond in Turkish. " if lang == "tr" else ""
            prompt = f"{language_instruction}Provide SEO suggestions based on this report:\n\n{json.dumps(report, indent=2)}"
            response = model.generate_content(prompt)
            response_text = response.text
        
        # Mark that suggestions have been generated in this session
        st.session_state.seo_suggestions_generated = True
        
        return response_text
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        return f"Could not generate SEO suggestions: {str(e)}"

def generate_with_mistral(report: dict, api_key: str, lang: str = "en") -> str:
    """Generate SEO suggestions using Mistral API."""
    url = "https://api.mistral.ai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Language mapping for Mistral API
    language_names = {"en": "English", "tr": "Turkish"}
    language_instruction = f"Please respond in {language_names.get(lang, 'English')}. " if lang != "en" else ""
    
    data = {
        "model": "mistral-large-latest",  # You can change this to your preferred Mistral model
        "messages": [
            {
                "role": "system",
                "content": f"You are an SEO expert assistant. {language_instruction}Provide helpful SEO suggestions based on the website analysis report."
            },
            {
                "role": "user",
                "content": f"{language_instruction} , Please analyze this SEO report and provide comprehensive suggestions for improving the website's SEO:\n\n{json.dumps(report, indent=2)}"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        response_json = response.json()
        return response_json['choices'][0]['message']['content']
    else:
        raise Exception(f"Mistral API error: {response.status_code} - {response.text}")