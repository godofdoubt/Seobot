
# Seobot/buttons/generate_seo_suggestions.py
import google.generativeai as genai
import json
import logging
import os
import streamlit as st
import requests
#from utils.language_support import language_manager # Removed as lang is from session_state
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
# model = genai.GenerativeModel('gemini-2.0-flash') # Original model

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
            - None: Will use text_report from st.session_state for general report.
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
            # Handle explicit text_report case
            report_data_str = pages_data_for_suggestions.get("content", "No content available")
            
        else:
            # Handle selected pages from llm_analysis_all
            current_url = st.session_state.get("url", "")
            if current_url:
                full_llm_analysis = fetch_llm_analysis_from_db(current_url)
                if full_llm_analysis:
                    enhanced_pages_data = enhance_selected_pages_with_main_context(
                        pages_data_for_suggestions, 
                        full_llm_analysis
                    )
                    report_data_str = json.dumps(enhanced_pages_data, indent=2, ensure_ascii=False)
                else:
                    enhanced_pages_data = pages_data_for_suggestions
                    report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)
            else:
                enhanced_pages_data = pages_data_for_suggestions
                report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)
        
        implementation_priority_title = "Implementation Priority"
        quick_implementation_guide_title = "Quick Implementation Guide"
        if lang == "tr":
            implementation_priority_title = "Uygulama Önceliği"
            quick_implementation_guide_title = "Hızlı Uygulama Rehberi"

        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(
                report_data_str, 
                mistral_api_key, 
                lang, 
                pages_data_for_suggestions,
                enhanced_pages_data,
                implementation_priority_title, 
                quick_implementation_guide_title 
            )
        else:
            # Use Gemini API
            language_instruction = f"Respond in Turkish. " if lang == "tr" else "Respond in English. "
            
            prompt = "" # Initialize prompt string
            if pages_data_for_suggestions and pages_data_for_suggestions.get("_source_type_") == "text_report":
                # UPDATED PROMPT FOR GENERAL TEXT REPORT - FOCUSED ON JSON TASKS
                prompt = f"""{language_instruction}
You are an expert SEO content strategist specializing in creating actionable content tasks.

You have been provided with a comprehensive SEO analysis report. Your primary goal is to deeply analyze this report, infer potential target audience personas and their needs if not explicitly stated, and generate specific, actionable content tasks in JSON format for Article Writer and Product Writer tools.

Based on your thorough analysis of the report, generate the following structured output:

**1. Key Content Opportunities and Implied Personas:**
   * Provide a brief summary (2-3 sentences) of the main content gaps and opportunities.
   * Briefly describe any implied target audience personas you've identified from the report's content, keywords, or themes. This understanding should inform your task generation.

**2. Content Creation Tasks (PRIMARY OUTPUT):**

You MUST provide a JSON object with specific tasks for content creation tools. Format as a markdown code block:

```json
{{
    "article_content_tasks": [
        {{
            "focus_keyword": "string (primary keyword for the article)",
            "content_length": "string (Short/Medium/Long/Very Long)",
            "article_tone": ["string (select one or more appropriate tones from: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive)"],
            "additional_keywords": ["string (supporting keywords)"],
            "suggested_title": "string (SEO-optimized title)",
            "target_page_url": "string (URL where this content will be published)",
            "content_gap_addressed": "string (what gap this fills, considering implied personas)",
            "target_audience": "string (specific audience or implied persona for this content)",
            "content_outline": ["string (3-5 key points/sections this article should cover, tailored to audience needs)"]
        }}
    ],
    "product_content_tasks": [
        {{
            "product_name": "string (product/service name)",
            "product_details": {{
                "features": ["string (list of 2-3 key product features, e.g., 'Durable material', 'Easy to clean')"],
                "benefits": ["string (list of 2-3 key product benefits, e.g., 'Saves time', 'Improves sleep quality')"],
                "target_audience": "string (brief description of the primary target audience for this product, e.g., 'Busy professionals', considering implied personas)",
                "competitive_advantage": "string (brief description of a competitive edge specific to this product's description, e.g., 'Unique patented technology')"
            }},
            "tone": "string (Professional/Casual/Enthusiastic/Technical/Friendly)",
            "description_length": "string (Short/Medium/Long)",
            "target_page_url": "string (product page URL)",
            "seo_keywords": ["string (2-5 SEO keywords)"],
            "competitive_advantage": "string (overall unique selling points of the product/service, broader than the one in product_details)",
            "target_customer": "string (ideal customer profile or implied persona for the product/service)"
        }}
    ]
}}
```

Guidelines for Task Generation:

Generate 3-8 article tasks and 2-5 product tasks based on the report findings and your persona analysis.

For article_tone, select one or more from the allowed list: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive. The choice should align with the content's purpose and target audience.

For product_details object:

features: List key tangible aspects.

benefits: List advantages for the customer.

target_audience: Describe who the product is for, guiding copy, informed by your persona analysis.

competitive_advantage: Note a specific angle for the description.

Focus on high-impact opportunities identified in the analysis.

Ensure each task is specific, actionable, and clearly linked to insights from the report and inferred personas.

Keywords should be based on actual opportunities found in the report.

Target audiences should reflect the site's actual or inferred visitor demographics and needs.

Content outlines should be practical, implementable, and resonate with the target audience.

**3. {implementation_priority_title}:**

List the top 5 tasks from your JSON in order of priority (High/Medium/Low) with brief rationale for each priority level, considering impact on personas and business goals.

Here is the SEO ANALYSIS REPORT:
{report_data_str}
"""
            else:
                # UPDATED PROMPT FOR SELECTED PAGES - FOCUSED ON JSON TASKS
                context_note = ""
                if enhanced_pages_data and "_main_page_context" in enhanced_pages_data:
                    context_note = """
    Important Context: The data includes header and footer information from the main page (marked as '_main_page_context') for site structure reference."""

                prompt = f"""{language_instruction}
You are an expert SEO content strategist specializing in creating actionable content tasks.

You have been provided with detailed page analysis data from a website. Your primary goal is to deeply analyze this data, paying close attention to target_audience fields and other clues to understand user personas, and generate specific, actionable content tasks in JSON format for Article Writer and Product Writer tools.{context_note}

Based on your thorough analysis of the provided page data, generate the following output:

**1. Page Analysis Summary & Persona Insights:**

Provide a brief summary (2-3 sentences) of the key findings and content opportunities for the analyzed pages.

If target_audience is specified in the data, elaborate slightly on how this understanding will shape the generated tasks. If not specified, briefly infer the likely audience based on content and keywords.

**2. Content Creation Tasks (PRIMARY OUTPUT):**

You MUST provide a JSON object with specific tasks for content creation tools. Format as a markdown code block:

```json
{{
    "article_content_tasks": [
        {{
            "focus_keyword": "string (primary keyword for the article from page analysis)",
            "content_length": "string (Short/Medium/Long/Very Long)",
            "article_tone": ["string (select one or more appropriate tones from: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive, based on content and audience)"],
            "additional_keywords": ["string (supporting keywords from page analysis)"],
            "suggested_title": "string (SEO-optimized title, relevant to page data)",
            "target_page_url": "string (URL where content will be published, typically the analyzed page or a new related page)",
            "content_gap_addressed": "string (what specific gap this fills based on page analysis and audience needs)",
            "target_audience": "string (audience based on page data or your persona inference)",
            "content_outline": ["string (3-5 key sections this article should cover, tailored to audience and page content)"],
            "internal_linking_opportunities": ["string (existing pages to link to/from based on data)"]
        }}
    ],
    "product_content_tasks": [
        {{
            "product_name": "string (product/service name from page data)",
            "product_details": {{
                "features": ["string (list of 2-3 key product features based on page data, e.g., 'Eco-friendly material', 'Handmade quality')"],
                "benefits": ["string (list of 2-3 key product benefits based on page data, e.g., 'Supports local artisans', 'Reduces carbon footprint')"],
                "target_audience": "string (description of the target audience for this product, from page data or inferred)",
                "competitive_advantage": "string (description of a competitive edge for this product, from page data if available)"
            }},
            "tone": "string (Professional/Casual/Enthusiastic/Technical/Friendly - chosen based on product and audience)",
            "description_length": "string (Short/Medium/Long)",
            "target_page_url": "string (specific product page URL from analysis)",
            "seo_keywords": ["string (keywords from page analysis)"],
            "competitive_advantage": "string (overall unique selling points identified for the product/service, broader than in product_details, informed by page data)",
            "target_customer": "string (customer profile from page data or inferred for the product/service)",
            "key_features_to_highlight": ["string (specific features to emphasize in marketing, can overlap with product_details.features, derived from page data)"]
        }}
    ]
}}
```

Guidelines for Task Generation:

Generate 2-6 article tasks and 1-4 product tasks based on the specific pages analyzed.

For article_tone, select one or more from the allowed list: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive. The choice must be justified by the page's existing content, style, and the (inferred) target audience.

For product_details object:

features: List key tangible aspects directly from page data or clearly inferred.

benefits: List advantages for the customer as suggested by page data.

target_audience: Describe who the product is for, critically analyzing page data.

competitive_advantage: Note a specific angle for the description evident from page data.

Focus on opportunities directly identified in the page data and tailor them to the specific audience.

Use keywords, topics, and target_audience information already present in the analysis to drive task creation.

Ensure tasks complement the existing page structure and user journey.

Consider internal linking opportunities between pages if data supports this.

Target audiences should match the identified or logically inferred demographics and psychographics from the page data.

**3. {quick_implementation_guide_title}:**

Provide 3-5 bullet points on how to implement these tasks effectively using the Article Writer and Product Writer tools, emphasizing persona alignment.

Here is the page analysis data:
{report_data_str}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text

        return response_text
    
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        error_details = ""
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
            error_details = f" Prompt Feedback: {e.response.prompt_feedback}"
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_details = f" Args: {e.args}"
        return f"Could not generate SEO suggestions: {str(e)}{error_details}"


def generate_with_mistral(report_data_str: str, api_key: str, lang: str = "en",
                          pages_data_for_suggestions: dict = None,
                          enhanced_pages_data: dict = None,
                          implementation_priority_title: str = "Implementation Priority", 
                          quick_implementation_guide_title: str = "Quick Implementation Guide"
                         ) -> str:
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

    user_content = "" # Initialize user_content
    if is_text_report:
        # UPDATED MISTRAL PROMPT FOR GENERAL TEXT REPORT - FOCUSED ON JSON TASKS
        user_content = f"""{mistral_language_instruction}
You are an expert SEO content strategist specializing in creating actionable content tasks.

You have been provided with a comprehensive SEO analysis report. Your primary goal is to deeply analyze this report, infer potential target audience personas and their needs if not explicitly stated, and generate specific, actionable content tasks in JSON format for Article Writer and Product Writer tools.

Based on your thorough analysis of the report, generate the following structured output:

**1. Key Content Opportunities and Implied Personas:**

Provide a brief summary (2-3 sentences) of the main content gaps and opportunities.

Briefly describe any implied target audience personas you've identified from the report's content, keywords, or themes. This understanding should inform your task generation.

**2. Content Creation Tasks (PRIMARY OUTPUT):**

You MUST provide a JSON object with specific tasks for content creation tools. Format as a markdown code block:

```json
{{
    "article_content_tasks": [
        {{
            "focus_keyword": "string (primary keyword for the article)",
            "content_length": "string (Short/Medium/Long/Very Long)",
            "article_tone": ["string (select one or more appropriate tones from: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive)"],
            "additional_keywords": ["string (supporting keywords)"],
            "suggested_title": "string (SEO-optimized title)",
            "target_page_url": "string (URL where this content will be published)",
            "content_gap_addressed": "string (what gap this fills, considering implied personas)",
            "target_audience": "string (specific audience or implied persona for this content)",
            "content_outline": ["string (3-5 key points/sections this article should cover, tailored to audience needs)"]
        }}
    ],
    "product_content_tasks": [
        {{
            "product_name": "string (product/service name)",
            "product_details": {{
                "features": ["string (list of 2-3 key product features, e.g., 'Durable material', 'Easy to clean')"],
                "benefits": ["string (list of 2-3 key product benefits, e.g., 'Saves time', 'Improves sleep quality')"],
                "target_audience": "string (brief description of the primary target audience for this product, e.g., 'Busy professionals', considering implied personas)",
                "competitive_advantage": "string (brief description of a competitive edge specific to this product's description, e.g., 'Unique patented technology')"
            }},
            "tone": "string (Professional/Casual/Enthusiastic/Technical/Friendly)",
            "description_length": "string (Short/Medium/Long)",
            "target_page_url": "string (product page URL)",
            "seo_keywords": ["string (2-5 SEO keywords)"],
            "competitive_advantage": "string (overall unique selling points of the product/service, broader than the one in product_details)",
            "target_customer": "string (ideal customer profile or implied persona for the product/service)"
        }}
    ]
}}
```

Guidelines for Task Generation:

Generate 3-8 article tasks and 2-5 product tasks based on the report findings and your persona analysis.

For article_tone, select one or more from the allowed list: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive. The choice should align with the content's purpose and target audience.

For product_details object:

features: List key tangible aspects.

benefits: List advantages for the customer.

target_audience: Describe who the product is for, guiding copy, informed by your persona analysis.

competitive_advantage: Note a specific angle for the description.

Focus on high-impact opportunities identified in the analysis.

Ensure each task is specific, actionable, and clearly linked to insights from the report and inferred personas.

Keywords should be based on actual opportunities found in the report.

Target audiences should reflect the site's actual or inferred visitor demographics and needs.

Content outlines should be practical, implementable, and resonate with the target audience.

**3. {implementation_priority_title}:**

List the top 5 tasks from your JSON in order of priority (High/Medium/Low) with brief rationale for each priority level, considering impact on personas and business goals.

Here is the SEO ANALYSIS REPORT:
{report_data_str}
"""
    else:
        # UPDATED MISTRAL PROMPT FOR SELECTED PAGES - FOCUSED ON JSON TASKS
        context_instruction = ""
        if has_main_context:
            context_instruction = """
Important Context: The data includes header and footer information from the main page (marked as '_main_page_context') for site structure reference."""

        user_content = f"""{mistral_language_instruction}
You are an expert SEO content strategist specializing in creating actionable content tasks.

You have been provided with detailed page analysis data from a website. Your primary goal is to deeply analyze this data, paying close attention to target_audience fields and other clues to understand user personas, and generate specific, actionable content tasks in JSON format for Article Writer and Product Writer tools.{context_instruction}

Based on your thorough analysis of the provided page data, generate the following output:

**1. Page Analysis Summary & Persona Insights:**

Provide a brief summary (2-3 sentences) of the key findings and content opportunities for the analyzed pages.

If target_audience is specified in the data, elaborate slightly on how this understanding will shape the generated tasks. If not specified, briefly infer the likely audience based on content and keywords.

**2. Content Creation Tasks (PRIMARY OUTPUT):**

You MUST provide a JSON object with specific tasks for content creation tools. Format as a markdown code block:

```json
{{
    "article_content_tasks": [
        {{
            "focus_keyword": "string (primary keyword for the article from page analysis)",
            "content_length": "string (Short/Medium/Long/Very Long)",
            "article_tone": ["string (select one or more appropriate tones from: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive, based on content and audience)"],
            "additional_keywords": ["string (supporting keywords from page analysis)"],
            "suggested_title": "string (SEO-optimized title, relevant to page data)",
            "target_page_url": "string (URL where content will be published, typically the analyzed page or a new related page)",
            "content_gap_addressed": "string (what specific gap this fills based on page analysis and audience needs)",
            "target_audience": "string (audience based on page data or your persona inference)",
            "content_outline": ["string (3-5 key sections this article should cover, tailored to audience and page content)"],
            "internal_linking_opportunities": ["string (existing pages to link to/from based on data)"]
        }}
    ],
    "product_content_tasks": [
        {{
            "product_name": "string (product/service name from page data)",
            "product_details": {{
                "features": ["string (list of 2-3 key product features based on page data, e.g., 'Eco-friendly material', 'Handmade quality')"],
                "benefits": ["string (list of 2-3 key product benefits based on page data, e.g., 'Supports local artisans', 'Reduces carbon footprint')"],
                "target_audience": "string (description of the target audience for this product, from page data or inferred)",
                "competitive_advantage": "string (description of a competitive edge for this product, from page data if available)"
            }},
            "tone": "string (Professional/Casual/Enthusiastic/Technical/Friendly - chosen based on product and audience)",
            "description_length": "string (Short/Medium/Long)",
            "target_page_url": "string (specific product page URL from analysis)",
            "seo_keywords": ["string (keywords from page analysis)"],
            "competitive_advantage": "string (overall unique selling points identified for the product/service, broader than in product_details, informed by page data)",
            "target_customer": "string (customer profile from page data or inferred for the product/service)",
            "key_features_to_highlight": ["string (specific features to emphasize in marketing, can overlap with product_details.features, derived from page data)"]
        }}
    ]
}}
```

Guidelines for Task Generation:

Generate 2-6 article tasks and 1-4 product tasks based on the specific pages analyzed.

For article_tone, select one or more from the allowed list: Professional, Casual, Enthusiastic, Technical, Friendly, Informative, Creative, Descriptive. The choice must be justified by the page's existing content, style, and the (inferred) target audience.

For product_details object:

features: List key tangible aspects directly from page data or clearly inferred.

benefits: List advantages for the customer as suggested by page data.

target_audience: Describe who the product is for, critically analyzing page data.

competitive_advantage: Note a specific angle for the description evident from page data.

Focus on opportunities directly identified in the page data and tailor them to the specific audience.

Use keywords, topics, and target_audience information already present in the analysis to drive task creation.

Ensure tasks complement the existing page structure and user journey.

Consider internal linking opportunities between pages if data supports this.

Target audiences should match the identified or logically inferred demographics and psychographics from the page data.

**3. {quick_implementation_guide_title}:**

Provide 3-5 bullet points on how to implement these tasks effectively using the Article Writer and Product Writer tools, emphasizing persona alignment.

Here is the page analysis data:
{report_data_str}
"""

    data = {
        "model": "mistral-large-latest",
        "messages": [
            {
                "role": "system",
                "content": f"You are an expert SEO content strategist specializing in creating actionable, JSON-formatted content tasks for Article Writer and Product Writer tools. {mistral_language_instruction} Your primary function is to analyze SEO data and generate specific, implementable content tasks that teams can immediately use for content creation."
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "temperature": 0.7,
        "max_tokens": 3500 
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('choices') and len(response_json['choices']) > 0 and response_json['choices'][0].get('message'):
            return response_json['choices'][0]['message']['content']
        else:
            logging.error(f"Mistral API response format error: {response.text}")
            raise Exception(f"Mistral API response format error. Check logs.")
    else:
        logging.error(f"Mistral API error: {response.status_code} - {response.text}")
        raise Exception(f"Mistral API error: {response.status_code}. Check logs.")
