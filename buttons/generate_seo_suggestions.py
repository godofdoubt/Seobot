#SeoTree/buttons/generate_seo_suggestions.py
import google.generativeai as genai
import json
import logging
import os
import streamlit as st
import requests
from utils.language_support import language_manager
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_supabase_client():
    """Initialize and return Supabase client."""
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        return None

def fetch_llm_analysis_from_db(url: str) -> dict:
    """Fetch llm_analysis_all data from Supabase database for the given URL."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return {}
        
        response = supabase.table('seo_reports').select('llm_analysis_all').eq('url', url).execute()
        
        if response.data and len(response.data) > 0:
            llm_analysis_all = response.data[0].get('llm_analysis_all')
            if llm_analysis_all and isinstance(llm_analysis_all, dict):
                return llm_analysis_all
        
        return {}
    except Exception as e:
        logging.error(f"Error fetching llm_analysis_all from database for URL {url}: {e}")
        return {}

def enhance_selected_pages_with_main_context(selected_pages_data: dict, full_llm_analysis: dict) -> dict:
    """
    Enhance selected pages data with header and footer from main_page if main_page is not included.
    
    Args:
        selected_pages_data: Dictionary of selected pages data
        full_llm_analysis: Full llm_analysis_all data from database
    
    Returns:
        Enhanced selected pages data with main_page context
    """
    try:
        # Check if main_page is already included in selected pages
        if "main_page" in selected_pages_data:
            return selected_pages_data
        
        # Get main_page data from full analysis
        main_page_data = full_llm_analysis.get("main_page", {})
        if not main_page_data:
            return selected_pages_data
        
        # Extract header and footer from main_page
        main_header = main_page_data.get("header", [])
        main_footer = main_page_data.get("footer", [])
        main_url = main_page_data.get("url", "")
        
        # Create enhanced data with main_page context
        enhanced_data = {}
        
        # Add main_page context as a separate entry
        enhanced_data["_main_page_context"] = {
            "url": main_url,
            "header": main_header,
            "footer": main_footer,
            "note": "Header and footer context from main page for reference"
        }
        
        # Add all selected pages
        enhanced_data.update(selected_pages_data)
        
        return enhanced_data
        
    except Exception as e:
        logging.error(f"Error enhancing selected pages with main context: {e}")
        return selected_pages_data

def generate_seo_suggestions(pages_data_for_suggestions: dict = None) -> str:
    """Generates SEO suggestions and content strategy using Gemini or Mistral based on selected page data from llm_analysis_all.
    
    Args:
        pages_data_for_suggestions: Dict containing either:
            - Selected pages from llm_analysis_all: {"page_key": {...}, ...}
            - Text report fallback: {"_source_type_": "text_report", "content": "..."}
            - None: Will use text_report as fallback if llm_analysis_all not available
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
        report_data_str = ""
        enhanced_pages_data = None
        
        if pages_data_for_suggestions is None:
            # Default to text_report when no specific data provided
            if st.session_state.get("text_report"):
                pages_data_for_suggestions = {
                    "_source_type_": "text_report",
                    "content": st.session_state.text_report
                }
                report_data_str = st.session_state.text_report
            else:
                return "No analysis data available. Please analyze a URL first to generate suggestions."
        
        elif pages_data_for_suggestions.get("_source_type_") == "text_report":
            # Handle text_report case
            report_data_str = pages_data_for_suggestions.get("content", "No content available")
            
        else:
            # Handle selected pages from llm_analysis_all
            # First, try to get full analysis from database
            current_url = st.session_state.get("url", "")
            if current_url:
                full_llm_analysis = fetch_llm_analysis_from_db(current_url)
                if full_llm_analysis:
                    # Enhance selected pages with main_page context if needed
                    enhanced_pages_data = enhance_selected_pages_with_main_context(
                        pages_data_for_suggestions, 
                        full_llm_analysis
                    )
                    report_data_str = json.dumps(enhanced_pages_data, indent=2, ensure_ascii=False)
                else:
                    # Fallback to session state data
                    report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)
            else:
                # No URL available, use provided data as-is
                report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)

        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(
                report_data_str, 
                mistral_api_key, 
                lang, 
                pages_data_for_suggestions,
                enhanced_pages_data
            )
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
2. Generate actionable SEO and content strategy recommendations
3. Organize suggestions into clear categories (On-Page SEO, Technical SEO, Content Strategy, User Experience)
4. For each suggestion, provide:
   - Clear, actionable recommendation
   - Brief rationale explaining why it's important
   - Suggested priority (High, Medium, Low)
5. Focus on practical improvements that can be implemented

Here is the SEO report:
{report_data_str}

Please provide comprehensive suggestions to improve this website's SEO performance.
"""
            else:
                # Enhanced prompt for detailed analysis with context
                context_note = ""
                if enhanced_pages_data and "_main_page_context" in enhanced_pages_data:
                    context_note = """

**Important Context**: The data includes header and footer information from the main page (marked as '_main_page_context') to provide you with the overall site structure and navigation context. Use this information to understand the site's overall theme and structure when making recommendations for the selected pages."""

                prompt = f"""{language_instruction}
You are an expert SEO strategist and content analyst.
You have been provided with detailed analysis data for specific page(s) from a website. This data typically includes content summaries, keywords, headers, tone, audience, topics, and existing SEO keyword suggestions for each selected page.{context_note}

The provided data structure is a dictionary where keys are page identifiers (like 'main_page', specific URLs, or '_main_page_context' for reference) and values are the detailed analysis for that page.

Your task is to:
1. Thoroughly analyze ALL sections of the provided data for EACH page.
2. **If '_main_page_context' is present, use it to understand the overall site structure, navigation, and theme** to provide more contextually relevant recommendations for the selected pages.
3. Based on your deep analysis of this data, generate a NEW and comprehensive set of actionable SEO and content strategy recommendations specifically tailored to improve the visibility and performance of these analyzed pages.
4. Critically evaluate the findings for each page. Identify strengths, weaknesses, and untapped opportunities.
5. Consider how the selected pages fit within the overall site structure (using main page context if available).
6. Your recommendations should aim to significantly improve the search engine rankings, organic traffic, user engagement, and overall online presence of these specific pages.
7. **Crucially, if the data for a page contains a section with pre-existing suggestions (like 'suggested_keywords_for_seo'), do not merely rephrase or repeat them.** Instead, you should:
   - Provide *additional, distinct* recommendations.
   - Elaborate on existing points if you can offer significant new depth or a different angle.
   - Identify areas that might have been overlooked or underemphasized for these pages.
   - Offer alternative strategies.
8. Organize your suggestions clearly by categories like:
   - Overall Strategic Insights (Synthesizing findings from all provided pages and main page context)
   - Page-Specific Recommendations (If multiple pages are provided)
   - On-Page SEO (Content optimization, Internal linking, Keyword usage specific to these pages)
   - Technical SEO (Consider if any page-specific technical aspects can be inferred)
   - Content Strategy (Content gaps on these pages, New content ideas, Content promotion, E-E-A-T improvement)
   - User Experience (UX) related to the content and structure of these pages.
9. For each suggestion, provide:
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

def generate_with_mistral(report_data_str: str, api_key: str, lang: str = "en", pages_data_for_suggestions: dict = None, enhanced_pages_data: dict = None) -> str:
    """Generate SEO suggestions using Mistral API."""
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    language_names = {"en": "English", "tr": "Turkish"}
    mistral_language_instruction = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "

    # Determine the type of data we're working with
    is_text_report = pages_data_for_suggestions and pages_data_for_suggestions.get("_source_type_") == "text_report"
    has_main_context = enhanced_pages_data and "_main_page_context" in enhanced_pages_data
    
    if is_text_report:
        user_content = f"""{mistral_language_instruction}
Please analyze the following general SEO report for a website and provide comprehensive, actionable SEO recommendations.

Your objective is to:
1. Thoroughly analyze the provided SEO report
2. Generate strategic SEO and content recommendations based on the findings
3. Identify key opportunities for improvement and potential weaknesses
4. Structure your suggestions into logical categories (e.g., On-Page SEO, Technical SEO, Content Strategy, User Experience)
5. For each suggestion, provide:
   - The recommendation itself (actionable and specific)
   - The reasoning behind it, linking back to findings in the report
   - A suggested priority level (High, Medium, Low)
6. Focus on delivering high-impact advice that can demonstrably improve SEO performance

Here is the SEO report:
{report_data_str}
"""
    else:
        context_instruction = ""
        if has_main_context:
            context_instruction = """
**Important**: The analysis data includes '_main_page_context' which contains header and footer information from the main page. Use this context to understand the overall site structure and navigation when making recommendations for the selected pages. This will help you provide more contextually relevant suggestions that align with the site's overall theme and user journey."""

        user_content = f"""{mistral_language_instruction}
Please analyze the following detailed analysis data for specific page(s) from a website. This data includes content summaries, keywords, suggested keywords, tone, audience, topics, etc., for each selected page.{context_instruction}

Your objective is to go beyond any existing recommendations found within this page-specific data. Based on a thorough examination of ALL the provided information:

1. **If '_main_page_context' is present, use it to understand the overall site structure and theme** to provide more contextually relevant recommendations.
2. Generate a **new set of strategic SEO and content recommendations specifically for these pages**. These should be distinct from, or significantly build upon/offer alternatives to, any pre-existing suggestions within the provided data.
3. Consider how the selected pages fit within the overall site ecosystem (using main page context if available).
4. Identify key opportunities for improvement, potential weaknesses, and areas that require more attention based on the data provided.
5. Structure your suggestions into logical categories (e.g., Overall Strategic Insights, Page-Specific Recommendations, On-Page SEO, Technical SEO, Content Strategy, User Experience).
6. For each new suggestion, provide:
   - The recommendation itself (actionable).
   - The reasoning behind it, linking back to specific data or patterns observed in the report data.
   - A suggested priority level (High, Medium, Low).
7. Focus on delivering high-impact advice that can demonstrably improve the SEO performance and user engagement of these specific pages within the context of the overall site.

Here is the detailed analysis data:
{report_data_str}
"""

    data = {
        "model": "mistral-large-latest",
        "messages": [
            {
                "role": "system",
                "content": f"You are a world-class SEO strategist and content analyst. Your primary function is to provide expert, actionable, and insightful recommendations based on SEO analysis data. {mistral_language_instruction} Your advice should be tailored to the information presented in the data and delivered entirely in the requested language. You excel at understanding site context and providing recommendations that align with overall site strategy."
            },
            {
                "role": "user",
                "content": user_content
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