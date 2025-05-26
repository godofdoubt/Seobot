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
# model = genai.GenerativeModel('gemini-2.0-flash') # Original model
# It's good practice to ensure the model selection here matches any specific model requirements
# For Gemini 1.5 Flash, if it's the intended model:
model = genai.GenerativeModel('gemini-1.5-flash-latest')


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
        st.session_state.get("use_mistral", True) # Assuming True means prefer Mistral if available
    )

    try:
        # Determine data source and prepare report_data_str
        report_data_str = ""
        enhanced_pages_data = None # This will store the data possibly enhanced with main_page context
        
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
                    # Fallback: use provided data as is, without DB enhancement if DB fetch fails
                    enhanced_pages_data = pages_data_for_suggestions # For prompt logic consistency
                    report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)
            else:
                # No URL available, use provided data as-is
                enhanced_pages_data = pages_data_for_suggestions # For prompt logic consistency
                report_data_str = json.dumps(pages_data_for_suggestions, indent=2, ensure_ascii=False)

        if use_mistral:
            # Use Mistral API
            response_text = generate_with_mistral(
                report_data_str, 
                mistral_api_key, 
                lang, 
                pages_data_for_suggestions, # Pass original selection for _source_type_ check
                enhanced_pages_data # Pass enhanced data for context note
            )
        else:
            # Use Gemini API
            language_instruction = f"Respond in Turkish. " if lang == "tr" else "Respond in English. "
            
            if pages_data_for_suggestions and pages_data_for_suggestions.get("_source_type_") == "text_report":
                prompt = f"""{language_instruction}
You are an expert SEO strategist and content analyst.
You have been provided with a general SEO report for a website. Based on this report, generate comprehensive and actionable SEO recommendations.

Your task is to:
1. Analyze the provided report thoroughly.
2. Generate actionable SEO and content strategy recommendations.
3. Organize suggestions into clear categories (On-Page SEO, Technical SEO, Content Strategy, User Experience , Content Suggestions.).
4. For each suggestion, provide:
   - Clear, actionable recommendation.
   - Brief rationale explaining why it's important.
   - Suggested priority (High, Medium, Low).
5. Focus on practical improvements that can be implemented. 

Here is the SEO report:
{report_data_str}

Please provide comprehensive suggestions to improve this website's SEO performance and content strategy.
"""
            else:
                # Enhanced prompt for detailed analysis with context
                context_note = ""
                if enhanced_pages_data and "_main_page_context" in enhanced_pages_data:
                    context_note = """

**Important Context**: The data includes header and footer information from the main page (marked as '_main_page_context') to provide you with the overall site structure and navigation context. Use this information to understand the site's overall theme and structure when making recommendations for the selected pages."""

                prompt = f"""{language_instruction}
You are an expert SEO strategist and content architect.
You have been provided with detailed analysis data for specific page(s) from a website. This data typically includes content summaries, keywords, headers, tone, audience, topics, existing SEO keyword suggestions, and potentially AI-generated strategic insights for each selected page.{context_note}

The provided data structure is a dictionary where keys are page identifiers (like 'main_page', specific URLs, or '_main_page_context' for reference) and values are the detailed analysis for that page.

Your primary task is to act as a strategic advisor, preparing a comprehensive SEO and content *plan* that the user can then take to content generation tools like "Article Writer / Makale Yazarı" or "Product Writer /  Ürün Yazarı"(product content only). Your output should NOT be the full content itself, but the blueprint for it.

Based on your deep analysis of this data, your plan should:

1.  **Thoroughly analyze ALL sections** of the provided data for EACH page.
2.  **If '_main_page_context' is present, use it** to understand the overall site structure, navigation, and theme to ensure your plan is contextually relevant.
3.  **Develop a NEW and actionable SEO and Content Strategy** tailored to improve the visibility, ranking, and user engagement of these analyzed pages. This strategy should aim for quick, impactful wins where possible.
4.  **Critically Evaluate Existing Data**:
    * Identify strengths, weaknesses, and untapped opportunities within the provided page data.
    * If the data contains pre-existing suggestions (e.g., 'suggested_keywords_for_seo', 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS', 'Site-Wide Subpage SEO Suggestions'), do not merely rephrase them. Instead:
        * Provide *additional, distinct, and actionable* strategic recommendations.
        * Elaborate on existing points if you can offer significant new depth, a different angle, or a more concrete implementation plan.
        * Identify overlooked areas or underemphasized strategies.
        * Offer alternative or complementary strategies.
        * Prioritize these existing and new recommendations.
5.  **Strategic Content Development Plan**:
    * **Target Keywords**:
        * Identify relevant **low-competition keywords** with good potential that align with the site's topics and user intent.
        * Suggest a core set of primary and secondary keywords for each targeted piece of content or page.
    * **Content Ideas & Structure**:
        * Propose **new content topics or alternative page ideas** (e.g., supporting articles, cornerstone content, FAQ pages) that could enhance the site's authority, fill content gaps, or target new keyword opportunities. This includes considering pages that can internally link to and power up existing important pages.
        * For key content pieces (new or existing that need enhancement), outline a suggested structure or key talking points.
    * **Tone and Audience Alignment**:
        * Recommend a specific **main tone** for new/updated content that aligns with the target audience identified in the analysis (or suggest refinements if the current tone is suboptimal or inconsistent).
    * **Content Formats**: Suggest appropriate content formats (e.g., blog posts, articles, product descriptions, guides, case studies, listicles) based on the strategic goals and target audience for the selected pages.
6.  **Implementation Guidance**:
    * Outline the **quickest and most effective ways to implement** the proposed strategy, focusing on high-impact actions.
    * Briefly suggest how the user can leverage their "Article Writer" or "Product Writer /  Ürün Yazarı" (product content only.) (e.g., "For the suggested blog post on 'X', use the 'Article Writer' with these keywords, this target audience, this suggested tone, and the outlined structure.").
7.  **Organize your comprehensive plan clearly** by categories like:
    * Overall Strategic Direction (Synthesizing findings and overarching goals for the selected pages based on the analysis)
    * Page-Specific Strategic Plans (If multiple pages are provided, detail the plan for each)
        * Key Objectives for this Page
        * Target Audience & Recommended Tone
        * Core Keywords (including low-competition opportunities and justification)
        * Proposed Content Actions (e.g., create new article on [topic], enhance existing [page] with [details], develop FAQ section) & Structure Outline
        * Key On-Page SEO Focus Points (e.g., title tag refinement, meta description, header optimization, internal linking opportunities specific to this page's new strategy)
    * Site-Level Content Opportunities (e.g., New supporting articles, topic clusters to build authority around core themes identified from the analyzed pages)
    * Quick Wins & Prioritized Action Plan (Top 3-5 actions for immediate impact)
8.  For each strategic element, provide:
    * A clear, actionable recommendation.
    * A brief rationale explaining *why* it's important, referencing specific findings from the provided page data.
    * Suggested priority (High, Medium, Low).

Remember, the output should be a STRATEGY and a PLAN that empowers the user to create effective content, not the content itself. Focus on actionable advice that builds upon or offers alternatives to any existing suggestions in the report.

Here is the detailed analysis data for the selected page(s):
{report_data_str}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text

        return response_text
        
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {e}")
        # Attempt to get more detailed error information if available from Gemini API
        error_details = ""
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
            error_details = f" Prompt Feedback: {e.response.prompt_feedback}"
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_details = f" Args: {e.args}"
        return f"Could not generate SEO suggestions: {str(e)}{error_details}"

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
    has_main_context = enhanced_pages_data and "_main_page_context" in enhanced_pages_data # Check enhanced_pages_data
    
    if is_text_report:
        user_content = f"""{mistral_language_instruction}
Please analyze the following general SEO report for a website and provide comprehensive, actionable SEO recommendations.

Your objective is to:
1. Thoroughly analyze the provided SEO report.
2. Generate strategic SEO and content recommendations based on the findings.
3. Identify key opportunities for improvement and potential weaknesses.
4. Structure your suggestions into logical categories (e.g., On-Page SEO, Technical SEO, Content Strategy, User Experience).
5. For each suggestion, provide:
   - The recommendation itself (actionable and specific).
   - The reasoning behind it, linking back to findings in the report.
   - A suggested priority level (High, Medium, Low).
6. Focus on delivering high-impact advice that can demonstrably improve SEO performance.

Here is the SEO report:
{report_data_str}
"""
    else:
        context_instruction = ""
        if has_main_context: # Use has_main_context
            context_instruction = """

**Important Context**: The data includes header and footer information from the main page (marked as '_main_page_context') to provide you with the overall site structure and navigation context. Use this information to understand the site's overall theme and structure when making recommendations for the selected pages."""

        user_content = f"""{mistral_language_instruction}
You are an expert SEO strategist and content architect.
You have been provided with detailed analysis data for specific page(s) from a website. This data includes content summaries, keywords, suggested keywords, tone, audience, topics, and potentially AI-generated strategic insights for each selected page.{context_instruction}

Your primary task is to act as a strategic advisor, preparing a comprehensive SEO and content *plan* that the user can then take to content generation tools like "Article Writer / Makale Yazarı " or "Product Writer /  Ürün Yazarı" (product content only). Your output should NOT be the full content itself, but the blueprint for it.

Based on your deep analysis of this data, your plan should:

1.  **Thoroughly analyze ALL sections** of the provided data for EACH page.
2.  **If '_main_page_context' is present, use it** to understand the overall site structure and theme to ensure your plan is contextually relevant.
3.  **Develop a NEW and actionable SEO and Content Strategy** tailored to improve the visibility, ranking, and user engagement of these analyzed pages. This strategy should aim for quick, impactful wins where possible.
4.  **Critically Evaluate Existing Data**:
    * Identify strengths, weaknesses, and untapped opportunities within the provided page data.
    * If the data contains pre-existing suggestions (e.g., 'suggested_keywords_for_seo', 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS', 'Site-Wide Subpage SEO Suggestions'), do not merely rephrase them. Instead:
        * Provide *additional, distinct, and actionable* strategic recommendations.
        * Elaborate on existing points if you can offer significant new depth, a different angle, or a more concrete implementation plan.
        * Identify overlooked areas or underemphasized strategies.
        * Offer alternative or complementary strategies.
        * Prioritize these existing and new recommendations.
5.  **Strategic Content Development Plan**:
    * **Target Keywords**:
        * Identify relevant **low-competition keywords** with good potential that align with the site's topics and user intent.
        * Suggest a core set of primary and secondary keywords for each targeted piece of content or page.
    * **Content Ideas & Structure**:
        * Propose **new content topics or alternative page ideas** (e.g., supporting articles, cornerstone content, FAQ pages, pillar pages, topic clusters) that could enhance the site's authority, fill content gaps, or target new keyword opportunities. Consider pages that can internally link to and power up existing important pages.
        * For key content pieces (new or existing that need enhancement), outline a suggested structure or key talking points.
    * **Tone and Audience Alignment**:
        * Recommend a specific **main tone** for new/updated content that aligns with the target audience identified in the analysis (or suggest refinements if the current tone is suboptimal or inconsistent).
    * **Content Formats**: Suggest appropriate content formats (e.g., blog posts, articles, product descriptions, guides, case studies, listicles, pillar pages) based on the strategic goals and target audience for the selected pages.
6.  **Implementation Guidance**:
    * Outline the **quickest and most effective ways to implement** the proposed strategy, focusing on high-impact actions.
    * Briefly suggest how the user can leverage their "Article Writer / Makale Yazarı" or "Product Writer /  Ürün Yazarı" (product content only.) tools with your strategic plan (e.g., "For the proposed blog post on 'X', utilize the 'Article Writer' with the identified keywords, target audience, recommended tone, and the outlined structure.").
7.  **Organize your comprehensive plan clearly** by categories such as:
    * Overall Strategic Direction (Synthesizing findings, overarching goals for the selected pages based on the analysis)
    * Page-Specific Strategic Plans (If multiple pages are analyzed, detail the plan for each)
        * Key Objectives for this Page
        * Target Audience & Recommended Tone
        * Core Keywords (including low-competition options and justification)
        * Proposed Content Actions (e.g., create new article on [topic], enhance existing [page] with [details], develop FAQ section) & Structure Outline
        * Key On-Page SEO Focus Points (e.g., title tag refinement, meta description, header optimization, internal linking opportunities specific to this page's new strategy)
    * Site-Level Content Opportunities (e.g., New supporting articles, topic clusters to build authority around core themes identified from the analyzed pages)
    * Quick Wins & Prioritized Action Plan (Top 3-5 actions for immediate impact)
8.  For each strategic element, provide:
    * A clear, actionable recommendation.
    * A brief rationale explaining *why* it's important, referencing specific findings from the provided page data.
    * Suggested priority (High, Medium, Low).

Remember, the output should be a STRATEGY and a PLAN that empowers the user to create effective content. Focus on providing actionable advice that goes beyond merely summarizing the input data or repeating existing suggestions.

Here is the detailed analysis data for the selected page(s):
{report_data_str}
"""

    data = {
        "model": "mistral-large-latest", # Consider using a specific version if needed, e.g., "mistral-large-2402"
        "messages": [
            {
                "role": "system",
                "content": f"You are a world-class SEO strategist and content architect. Your primary function is to provide expert, actionable, and insightful strategic plans based on SEO analysis data. {mistral_language_instruction} Your advice should be tailored to the information presented in the data and delivered entirely in the requested language. You excel at understanding site context, identifying strategic opportunities, and providing recommendations that align with overall site strategy, guiding users on how to plan content effectively before generation."
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "temperature": 0.7, # Adjust as needed; lower for more deterministic, higher for more creative
        "max_tokens": 3500 # Increased to allow for more comprehensive strategic plans
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('choices') and len(response_json['choices']) > 0 and response_json['choices'][0].get('message'):
            return response_json['choices'][0]['message']['content']
        else:
            logging.error(f"Mistral API response format error: 'choices' or 'message' structure not as expected. Response: {response.text}")
            raise Exception(f"Mistral API response format error. Check logs.")
    else:
        logging.error(f"Mistral API error: {response.status_code} - {response.text}")
        raise Exception(f"Mistral API error: {response.status_code}. Check logs.")