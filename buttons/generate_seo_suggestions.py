#Seobot/buttons/generate_seo_suggestions.py
import google.generativeai as genai
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
        # Extract key sections from the report based on actual structure
        url = report.get("url", "")
        links = report.get("links", {})
        images = report.get("images", [])
        headings = report.get("headings", {})
        keywords = report.get("keywords", {})
        meta_tags = report.get("meta_tags", {})
        content_types = report.get("content_types", {})
        content_length = report.get("content_length", 0)
        word_count = report.get("word_count", 0)
        
        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(report, api_key=mistral_api_key, lang=lang, 
                                                url=url, links=links, images=images, 
                                                headings=headings, keywords=keywords, 
                                                meta_tags=meta_tags, content_types=content_types,
                                                content_length=content_length, word_count=word_count)
        else:
            # Use Gemini API
            response_text = generate_with_gemini(report, lang=lang, 
                                               url=url, links=links, images=images, 
                                               headings=headings, keywords=keywords, 
                                               meta_tags=meta_tags, content_types=content_types,
                                               content_length=content_length, word_count=word_count)
        
        # Mark that suggestions have been generated in this session
        st.session_state.seo_suggestions_generated = True
        
        return response_text
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        return f"Could not generate SEO suggestions: {str(e)}"

def generate_with_gemini(report: dict, lang: str, url: str, links: dict, images: list, 
                        headings: dict, keywords: dict, meta_tags: dict, 
                        content_types: dict, content_length: int, word_count: int) -> str:
    """Generate SEO suggestions using Gemini API with structured prompt based on actual report structure."""
    
    language_instruction = f"Respond in Turkish. " if lang == "tr" else ""
    
    # Create a structured prompt highlighting key sections from your actual report structure
    prompt = f"""{language_instruction}
You are an SEO expert. Provide detailed SEO suggestions based on this website report for {url}:

SITE OVERVIEW:
URL: {url}
Content Length: {content_length} characters
Word Count: {word_count} words

META INFORMATION:
Title: {meta_tags.get('title', 'Not specified')}
Meta Description: {meta_tags.get('description', 'Missing - this is a critical SEO issue!')}
Meta Keywords: {meta_tags.get('keywords', 'Missing')}

HEADINGS STRUCTURE:
H1: {headings.get('h1', [])}
H2: {headings.get('h2', [])}
H3: {headings.get('h3', [])}
H4: {headings.get('h4', [])}

TOP KEYWORDS ON PAGE:
{keywords}

LINKS ANALYSIS:
External Links: {links.get('external_count', 0)} links
Internal Links: {links.get('internal_count', 0)} links

IMAGES ANALYSIS:
Total Images: {len(images)}
Images Missing Alt Text: {sum(1 for img in images if not img.get('has_alt', False))}

CONTENT TYPES:
{content_types}

FULL REPORT:
{report}

Please provide actionable SEO suggestions in these key areas:
1. Meta tag improvements (title, description)
2. Content optimization for keywords
3. Heading structure recommendations
4. Image optimization (especially alt text)
5. Internal linking strategy
6. Content development suggestions
"""
    
    response = model.generate_content(prompt)
    return response.text

def generate_with_mistral(report: dict, api_key: str, lang: str, url: str, links: dict, 
                         images: list, headings: dict, keywords: dict, meta_tags: dict, 
                         content_types: dict, content_length: int, word_count: int) -> str:
    """Generate SEO suggestions using Mistral API with structured prompt."""
    url_endpoint = "https://api.mistral.ai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Language mapping for Mistral API
    language_names = {"en": "English", "tr": "Turkish"}
    language_instruction = f"Please respond in {language_names.get(lang, 'English')}. " if lang != "en" else ""
    
    # Create a structured prompt highlighting key sections from your actual report structure
    structured_prompt = f"""{language_instruction}
Analyze this SEO report and provide comprehensive suggestions for improving the website's SEO:

SITE OVERVIEW:
URL: {url}
Content Length: {content_length} characters
Word Count: {word_count} words

META INFORMATION:
Title: {meta_tags.get('title', 'Not specified')}
Meta Description: {meta_tags.get('description', 'Missing - this is a critical SEO issue!')}
Meta Keywords: {meta_tags.get('keywords', 'Missing')}

HEADINGS STRUCTURE:
H1: {headings.get('h1', [])}
H2: {headings.get('h2', [])}
H3: {headings.get('h3', [])}
H4: {headings.get('h4', [])}

TOP KEYWORDS ON PAGE:
{keywords}

LINKS ANALYSIS:
External Links: {links.get('external_count', 0)} links
Internal Links: {links.get('internal_count', 0)} links

IMAGES ANALYSIS:
Total Images: {len(images)}
Images Missing Alt Text: {sum(1 for img in images if not img.get('has_alt', False))}

CONTENT TYPES:
{content_types}

FULL REPORT:
{report}

Please provide actionable SEO suggestions in these key areas:
1. Meta tag improvements (title, description)
2. Content optimization for keywords
3. Heading structure recommendations
4. Image optimization (especially alt text)
5. Internal linking strategy
6. Content development suggestions
"""
    
    data = {
        "model": "mistral-large-latest",
        "messages": [
            {
                "role": "system",
                "content": f"You are an SEO expert assistant. {language_instruction}Provide helpful SEO suggestions based on the website analysis report."
            },
            {
                "role": "user",
                "content": structured_prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    
    response = requests.post(url_endpoint, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        response_json = response.json()
        return response_json['choices'][0]['message']['content']
    else:
        raise Exception(f"Mistral API error: {response.status_code} - {response.text}")