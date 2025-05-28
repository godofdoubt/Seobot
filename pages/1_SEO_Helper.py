#SeoTree/pages/1_SEO_Helper.py
import streamlit as st

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="SEO Helper",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)
hide_pages_nav = """
<style>
  div[data-testid="stSidebarNav"] { 
    display: none !important; 
  }
</style>
"""
st.markdown(hide_pages_nav, unsafe_allow_html=True)

import asyncio
import os
import logging
import json 
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history
from utils.language_support import language_manager
# Import new utility functions
from utils.seo_data_parser import parse_auto_suggestions, load_auto_suggestions_from_supabase, save_auto_suggestions_to_supabase
from helpers.seo_main_helper8 import process_chat_input
from buttons.generate_seo_suggestions import generate_seo_suggestions
import re
# --- Import process_url from main.py ---
try:
    from main import process_url as main_process_url
except ImportError:
    st.error("Failed to import process_url from main.py. Ensure main.py is in the correct path.")
    main_process_url = None

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_supabase_client():
    """Get Supabase client instance."""
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

def check_auth():
    """Check if user is authenticated and redirect if not."""
    if not st.session_state.get("authenticated", False):
        lang = st.session_state.get("language", "en")
        st.warning(language_manager.get_text("authentication_required", lang))
        if st.button(language_manager.get_text("go_to_login", lang)):
            st.switch_page("main.py")
        st.stop()

def validate_supabase_data():
    """Validate the structure of data retrieved from Supabase."""
    if not st.session_state.get("full_report"):
        return False
    
    if not isinstance(st.session_state.full_report, dict):
        logging.warning("full_report is not a dictionary")
        return False
    
    llm_analysis = st.session_state.full_report.get("llm_analysis_all")
    if llm_analysis and not isinstance(llm_analysis, dict):
        logging.warning("llm_analysis_all is not a dictionary")
        return False
    
    return True

def get_available_pages():
    """Get available pages from llm_analysis_all with proper error handling."""
    try:
        if not validate_supabase_data():
            return []
        
        llm_data = st.session_state.full_report.get("llm_analysis_all", {})
        if not llm_data:
            return []
        
        available_page_keys = list(llm_data.keys())
        
        # Sort pages with main_page first
        sorted_page_keys = []
        if "main_page" in available_page_keys:
            sorted_page_keys.append("main_page")
            sorted_page_keys.extend([key for key in available_page_keys if key != "main_page"])
        else:
            sorted_page_keys = available_page_keys
        
        return sorted_page_keys
    except Exception as e:
        logging.error(f"Error getting available pages: {str(e)}")
        return []

# parse_auto_suggestions, load_auto_suggestions_from_supabase, save_auto_suggestions_to_supabase
# are now imported from utils.seo_data_parser

def generate_seo_suggestions_with_fallback(pages_data_for_suggestions, primary_service="gemini"):
    """
    Generate SEO suggestions with fallback mechanism.
    
    Args:
        pages_data_for_suggestions: Data to generate suggestions from
        primary_service: Primary AI service to use ("gemini" or "mistral")
    
    Returns:
        Generated suggestions or None if both services fail
    """
    lang = st.session_state.get("language", "en")
    
    has_mistral = bool(st.session_state.get("MISTRAL_API_KEY"))
    has_gemini = bool(st.session_state.get("GEMINI_API_KEY"))
    
    if not has_mistral and not has_gemini:
        logging.error("No AI API keys available for suggestions generation")
        return None
    
    if primary_service == "mistral" and has_mistral:
        primary = "mistral"
        fallback = "gemini" if has_gemini else None
    else:
        primary = "gemini" if has_gemini else "mistral" # Default to gemini if available, else mistral
        fallback = "mistral" if has_mistral and primary != "mistral" else None
        if not has_gemini and not has_mistral: # Should be caught above, but for safety
             primary = None 

    if not primary: # No primary service determined (e.g. Gemini preferred but no key, Mistral also no key)
        logging.error("No primary AI service could be determined based on available keys.")
        return None

    original_mistral_key = st.session_state.get("MISTRAL_API_KEY")
    original_gemini_key = st.session_state.get("GEMINI_API_KEY")
    
    # Try primary service
    try:
        logging.info(f"Attempting to generate suggestions using {primary}")
        if primary == "gemini": st.session_state["MISTRAL_API_KEY"] = None
        else: st.session_state["GEMINI_API_KEY"] = None
        
        suggestions = generate_seo_suggestions(pages_data_for_suggestions=pages_data_for_suggestions)
        
        st.session_state["MISTRAL_API_KEY"] = original_mistral_key
        st.session_state["GEMINI_API_KEY"] = original_gemini_key
        
        if suggestions and suggestions.strip():
            logging.info(f"Successfully generated suggestions using {primary}")
            return suggestions
        else:
            logging.warning(f"Empty or invalid response from {primary}")
            
    except Exception as e:
        logging.error(f"Error generating suggestions with {primary}: {str(e)}")
        st.session_state["MISTRAL_API_KEY"] = original_mistral_key
        st.session_state["GEMINI_API_KEY"] = original_gemini_key
    
    # Try fallback service if available
    if fallback:
        try:
            logging.info(f"Falling back to {fallback} for suggestions generation")
            st.info(language_manager.get_text("fallback_ai_service", lang, fallback.title(), fallback=f"Primary AI service unavailable. Using {fallback.title()} as fallback..."))
            
            if fallback == "gemini": st.session_state["MISTRAL_API_KEY"] = None
            else: st.session_state["GEMINI_API_KEY"] = None
            
            suggestions = generate_seo_suggestions(pages_data_for_suggestions=pages_data_for_suggestions)

            st.session_state["MISTRAL_API_KEY"] = original_mistral_key
            st.session_state["GEMINI_API_KEY"] = original_gemini_key

            if suggestions and suggestions.strip():
                logging.info(f"Successfully generated suggestions using fallback {fallback}")
                return suggestions
            else:
                logging.warning(f"Empty or invalid response from fallback {fallback}")
                
        except Exception as e:
            logging.error(f"Error generating suggestions with fallback {fallback}: {str(e)}")
            st.session_state["MISTRAL_API_KEY"] = original_mistral_key
            st.session_state["GEMINI_API_KEY"] = original_gemini_key
    
    logging.error("Both primary and fallback AI services failed to generate suggestions")
    return None

def get_article_writer_cta_text(suggestions_data, lang):
    """Generates CTA text if actionable article tasks are found in suggestions."""
    if isinstance(suggestions_data, dict):
        content_ideas = suggestions_data.get("content_creation_ideas")
        if isinstance(content_ideas, dict):
            article_tasks = content_ideas.get("article_content_tasks")
            if isinstance(article_tasks, list) and article_tasks:
                num_article_tasks = len(article_tasks)
                # New language key for the modified CTA
                cta_question_key = "seo_helper_prepare_for_article_writer_cta"
                return language_manager.get_text(
                    cta_question_key, lang, num_article_tasks,
                    fallback=f"\n\nI've identified {num_article_tasks} potential article ideas from this analysis. I can prepare these for you to work on in the Article Writer. Would you like to do that? (Type 'yes' or 'no')"
                )
    return ""

def handle_seo_suggestions_generation(lang):
    """Handle the generation of SEO suggestions with proper error handling."""
    try:
        llm_analysis_available = (
            st.session_state.get("full_report") and
            isinstance(st.session_state.full_report, dict) and
            st.session_state.full_report.get("llm_analysis_all") and
            isinstance(st.session_state.full_report["llm_analysis_all"], dict) and
            st.session_state.full_report["llm_analysis_all"]
        )

        text_report_available = bool(st.session_state.get("text_report"))
        data_for_suggestions = None
        
        if llm_analysis_available:
            user_selected_page_keys = st.session_state.get("selected_pages_for_seo_suggestions", [])
            llm_data = st.session_state.full_report["llm_analysis_all"]
            
            if user_selected_page_keys:
                valid_selected_keys = [key for key in user_selected_page_keys if key in llm_data and llm_data[key]]
                if valid_selected_keys:
                    data_for_suggestions = {key: llm_data[key] for key in valid_selected_keys}
                    st.sidebar.success(language_manager.get_text("using_selected_pages_for_suggestions", lang, ', '.join(valid_selected_keys), fallback=f"Generating suggestions for selected pages: {', '.join(valid_selected_keys)}"))
                else:
                    st.sidebar.error(language_manager.get_text("error_selected_pages_no_valid_data", lang, fallback="Error: None of the selected pages have data available for suggestions."))
                    return
            else: 
                if text_report_available:
                    data_for_suggestions = {"_source_type_": "text_report", "content": st.session_state.text_report}
                    st.sidebar.info(language_manager.get_text("using_text_report_for_suggestions", lang, fallback="No specific pages selected. Generating general suggestions based on the text report."))
                else:
                    st.sidebar.error(language_manager.get_text("error_no_text_report_available", lang, fallback="Error: No text report available for suggestions."))
                    return
        elif text_report_available:
            data_for_suggestions = {"_source_type_": "text_report", "content": st.session_state.text_report}
            st.sidebar.info(language_manager.get_text("using_text_report_for_suggestions", lang, fallback="Generating general suggestions based on the text report."))
        else:
            st.sidebar.error(language_manager.get_text("error_no_text_report_available", lang, fallback="Error: No text report available for suggestions."))
            return

        if data_for_suggestions:
            with st.spinner(language_manager.get_text("processing_request", lang)):
                suggestions_raw_manual = generate_seo_suggestions_with_fallback(
                    pages_data_for_suggestions=data_for_suggestions,
                    primary_service="gemini" 
                )
                
                if suggestions_raw_manual:
                    parsed_manual_suggestions = parse_auto_suggestions(suggestions_raw_manual)
                    
                    current_url = st.session_state.get("url")
                    if current_url:
                        st.session_state.auto_suggestions_data = parsed_manual_suggestions
                        st.session_state.current_report_url_for_suggestions = current_url
                        
                        supabase_client = get_supabase_client()
                        user_id = st.session_state.get("user_id")
                        save_auto_suggestions_to_supabase(current_url, parsed_manual_suggestions, supabase_client, user_id) 
                        logging.info(f"SEO_Helper: Updated auto_suggestions_data with MANUALLY generated suggestions for {current_url}")

                    chat_content_for_manual_suggestions = suggestions_raw_manual
                    
                    if not st.session_state.get("awaiting_seo_helper_cta_response"):
                        cta_text_if_any = get_article_writer_cta_text(parsed_manual_suggestions, lang)
                        if cta_text_if_any:
                            chat_content_for_manual_suggestions += cta_text_if_any
                            st.session_state.awaiting_seo_helper_cta_response = True
                            st.session_state.seo_helper_cta_context = {
                                "type": "article_writer",
                                "tasks": parsed_manual_suggestions.get("content_creation_ideas", {}).get("article_content_tasks", [])
                            }
                            logging.info(f"CTA activated after manual suggestion. Context: {st.session_state.seo_helper_cta_context}")
                    
                    last_message_content = st.session_state.messages[-1]["content"] if st.session_state.messages else None
                    if last_message_content != chat_content_for_manual_suggestions: 
                        st.session_state.messages.append({"role": "assistant", "content": chat_content_for_manual_suggestions})
                        st.rerun()
                else:
                    st.sidebar.error(language_manager.get_text("error_all_ai_services_failed", lang, fallback="All AI services failed to generate suggestions. Please try again later."))
                    
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {str(e)}")
        st.sidebar.error(language_manager.get_text("error_generating_suggestions", lang, fallback="An error occurred while generating suggestions. Please try again."))


async def main_seo_helper():
    """Main function for SEO Helper page."""
    try:
        init_shared_session_state()
        supabase_client = get_supabase_client() # Get client once
        
        if "language" not in st.session_state:
            st.session_state.language = "en"
        lang = st.session_state.language
        
        if "url_for_auto_suggestions" not in st.session_state:
            st.session_state.url_for_auto_suggestions = None
        if "auto_suggestions_generated_for_current_url" not in st.session_state:
            st.session_state.auto_suggestions_generated_for_current_url = False

        st.title(language_manager.get_text("seo_helper_button", lang))
        
        if st.session_state.get("current_page") != "seo":
            update_page_history("seo")
        
        if st.session_state.get("url") and st.session_state.get("text_report"):
            target_welcome_message_seo = language_manager.get_text("welcome_seo_helper_analyzed", lang, st.session_state.url, fallback=f"Welcome to the SEO Helper. Analysis for **{st.session_state.url}** is available. How can I assist you further?")
        else:
            username = st.session_state.get("username", "User")
            target_welcome_message_seo = language_manager.get_text("welcome_authenticated", lang, username, fallback=f"Welcome, {username}! Enter a URL to analyze or ask an SEO question.")

        if "messages" not in st.session_state or not st.session_state.messages:
            st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_seo}]
        elif (st.session_state.messages and st.session_state.messages[0].get("role") == "assistant" and st.session_state.messages[0].get("content") != target_welcome_message_seo):
            if not st.session_state.get("awaiting_seo_helper_cta_response"):
                 st.session_state.messages[0]["content"] = target_welcome_message_seo
        
        check_auth()
        user_id = st.session_state.get("user_id") # Get user_id for saving suggestions
        
        if (st.session_state.get("analysis_in_progress") and st.session_state.get("url_being_analyzed")):
            st.info(language_manager.get_text("analysis_in_progress_for", lang, st.session_state.url_being_analyzed))

        llm_analysis_available = (st.session_state.get("full_report") and isinstance(st.session_state.full_report, dict) and st.session_state.full_report.get("llm_analysis_all") and isinstance(st.session_state.full_report["llm_analysis_all"], dict) and st.session_state.full_report["llm_analysis_all"])
        text_report_available = bool(st.session_state.get("text_report"))
        current_analyzed_url = st.session_state.get("url")

        if llm_analysis_available and text_report_available and current_analyzed_url:
            if (st.session_state.url_for_auto_suggestions != current_analyzed_url or 
                not st.session_state.auto_suggestions_generated_for_current_url):
                
                existing_suggestions_structured = load_auto_suggestions_from_supabase(current_analyzed_url, supabase_client, parse_auto_suggestions)
                suggestions_to_display_in_chat = None 
                current_auto_suggestions_data_for_cta = None
                
                if existing_suggestions_structured:
                    st.info(language_manager.get_text("loading_existing_suggestions", lang, fallback="Loading existing SEO suggestions from database..."))
                    current_auto_suggestions_data_for_cta = existing_suggestions_structured
                    
                    # ... (code for formatting existing_suggestions_structured for display - unchanged) ...
                    suggestions_text_parts = ["**Loaded SEO Analysis & Content Ideas:**\n"]
                    if existing_suggestions_structured.get("seo_analysis"):
                        suggestions_text_parts.append("## SEO Analysis\n")
                        seo_analysis = existing_suggestions_structured["seo_analysis"]
                        for section, items in seo_analysis.items():
                            if items and section not in ["raw_content", "raw_suggestions", "parsing_error", "generated_timestamp","_source"]:
                                suggestions_text_parts.append(f"**{section.replace('_', ' ').title()}:**\n")
                                if isinstance(items, list):
                                    for item in items: suggestions_text_parts.append(f"- {item}\n")
                                elif isinstance(items, str): suggestions_text_parts.append(f"{items}\n")
                                suggestions_text_parts.append("\n")
                        if "raw_content" in seo_analysis and not any(seo_analysis.get(s) for s in ["technical_issues", "content_recommendations","on_page_seo", "off_page_seo", "content_strategy"]):
                             suggestions_text_parts.append(f"**Raw Analysis:**\n{seo_analysis['raw_content']}\n\n")

                    if existing_suggestions_structured.get("content_creation_ideas"):
                        suggestions_text_parts.append("## Content Creation/Update Ideas\n")
                        content_ideas = existing_suggestions_structured["content_creation_ideas"]
                        for section, items in content_ideas.items():
                            if items and section not in ["raw_content", "raw_suggestions", "parsing_error", "generated_timestamp", "_source", "parsing_error_detail"]:
                                suggestions_text_parts.append(f"**{section.replace('_', ' ').title()}:**\n")
                                if isinstance(items, list): 
                                    for item_idx, item_task in enumerate(items):
                                        if isinstance(item_task, dict): 
                                            title_from_task = item_task.get('suggested_title', item_task.get('title', f"Task {item_idx+1}"))
                                            suggestions_text_parts.append(f"- **{title_from_task}**\n")
                                            for k,v in item_task.items():
                                                if k not in ['suggested_title', 'title']:
                                                     suggestions_text_parts.append(f"  - {k.replace('_',' ').title()}: {v}\n")
                                        else: 
                                            suggestions_text_parts.append(f"- {item_task}\n")
                                elif isinstance(items, str): suggestions_text_parts.append(f"{items}\n")
                                suggestions_text_parts.append("\n")
                        if "raw_content" in content_ideas and not any(content_ideas.get(s) for s in ["blog_posts", "page_improvements", "article_content_tasks", "product_content_tasks"]):
                             suggestions_text_parts.append(f"**Raw Ideas:**\n{content_ideas['raw_content']}\n\n")

                    if existing_suggestions_structured.get("parsing_error"):
                         suggestions_text_parts.append(f"\n*Note: There was an error parsing these suggestions previously. Displaying best effort from raw data.* Error: {existing_suggestions_structured['parsing_error']}\n")
                    if existing_suggestions_structured.get("generated_timestamp"):
                        generated_time_str = existing_suggestions_structured['generated_timestamp']
                        try:
                            dt_obj = datetime.fromisoformat(generated_time_str.replace("Z", "+00:00"))
                            formatted_time = dt_obj.strftime("%Y-%m-%d %H:%M:%S UTC")
                            suggestions_text_parts.append(f"\n*Suggestions from: {formatted_time}*")
                        except ValueError:
                            suggestions_text_parts.append(f"\n*Suggestions from: {generated_time_str}*")
                    suggestions_to_display_in_chat = "".join(suggestions_text_parts)
                    
                    st.session_state.auto_suggestions_data = existing_suggestions_structured
                    st.session_state.current_report_url_for_suggestions = current_analyzed_url
                    logging.info(f"SEO_Helper: Set auto_suggestions_data from existing (DB) for {current_analyzed_url}")

                else: 
                    data_for_auto_suggestions = {"_source_type_": "text_report", "content": st.session_state.text_report}
                    auto_gen_message_placeholder = st.empty()
                    auto_gen_message_placeholder.info(language_manager.get_text("auto_generating_initial_suggestions", lang, fallback="Analysis complete. Automatically generating initial suggestions based on the text report..."))

                    suggestions_raw_new = None
                    with st.spinner(language_manager.get_text("auto_processing_initial_suggestions", lang, fallback="Auto-generating initial suggestions...")):
                        suggestions_raw_new = generate_seo_suggestions_with_fallback(pages_data_for_suggestions=data_for_auto_suggestions, primary_service="gemini")
                    
                    auto_gen_message_placeholder.empty()

                    if suggestions_raw_new:
                        newly_structured_suggestions = parse_auto_suggestions(suggestions_raw_new)
                        current_auto_suggestions_data_for_cta = newly_structured_suggestions
                        save_success = save_auto_suggestions_to_supabase(current_analyzed_url, newly_structured_suggestions, supabase_client, user_id)
                        if save_success: logging.info(f"Auto suggestions saved to Supabase for URL: {current_analyzed_url}")
                        else: logging.warning(f"Failed to save auto suggestions to Supabase for URL: {current_analyzed_url}")
                        
                        suggestions_to_display_in_chat = suggestions_raw_new 
                        
                        st.session_state.auto_suggestions_data = newly_structured_suggestions
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url
                        logging.info(f"SEO_Helper: Set auto_suggestions_data from NEWLY generated for {current_analyzed_url}")
                    else:
                        suggestions_to_display_in_chat = language_manager.get_text("error_auto_suggestions_failed", lang, fallback="Unable to generate automatic suggestions. You can still request manual suggestions using the sidebar.")
                        st.session_state.auto_suggestions_data = None
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url
                        logging.info(f"SEO_Helper: Set auto_suggestions_data to None (generation failed) for {current_analyzed_url}")
                
                if suggestions_to_display_in_chat and current_auto_suggestions_data_for_cta:
                    if not st.session_state.get("awaiting_seo_helper_cta_response"):
                        cta_text_if_any = get_article_writer_cta_text(current_auto_suggestions_data_for_cta, lang)
                        if cta_text_if_any:
                            suggestions_to_display_in_chat += cta_text_if_any
                            st.session_state.awaiting_seo_helper_cta_response = True
                            st.session_state.seo_helper_cta_context = {
                                "type": "article_writer",
                                "tasks": current_auto_suggestions_data_for_cta.get("content_creation_ideas", {}).get("article_content_tasks", [])
                            }
                            logging.info(f"CTA activated after auto-suggestion display. Context: {st.session_state.seo_helper_cta_context}")

                if suggestions_to_display_in_chat:
                    last_message_content = st.session_state.messages[-1]["content"] if st.session_state.messages else None
                    if last_message_content != suggestions_to_display_in_chat:
                        st.session_state.messages.append({"role": "assistant", "content": suggestions_to_display_in_chat})
                
                st.session_state.url_for_auto_suggestions = current_analyzed_url
                st.session_state.auto_suggestions_generated_for_current_url = True
                if (suggestions_to_display_in_chat and (last_message_content != suggestions_to_display_in_chat)) or \
                   (st.session_state.get("awaiting_seo_helper_cta_response") and 'cta_text_if_any' in locals() and cta_text_if_any): # Rerun if CTA was just added
                    st.rerun()


        if "selected_pages_for_seo_suggestions" not in st.session_state:
            st.session_state.selected_pages_for_seo_suggestions = []

        if llm_analysis_available or text_report_available: 
            st.sidebar.subheader(language_manager.get_text("seo_suggestions_for_pages_label", lang, fallback="SEO Suggestions:"))
            if llm_analysis_available:
                sorted_page_keys = get_available_pages()
                if sorted_page_keys:
                    current_selection = st.session_state.get("selected_pages_for_seo_suggestions", [])
                    selected_pages = st.sidebar.multiselect(
                        label=language_manager.get_text("select_pages_for_detailed_suggestions", lang, fallback="Select pages (leave empty for general suggestions):"),
                        options=sorted_page_keys, default=current_selection, key="multiselect_seo_suggestion_pages", 
                        help=language_manager.get_text("multiselect_seo_help_text_v3", lang, fallback="Select specific pages for focused suggestions. If empty, general suggestions will be generated from the text report. 'main_page' contains the homepage analysis."))
                    st.session_state.selected_pages_for_seo_suggestions = selected_pages
                else:
                    st.sidebar.warning(language_manager.get_text("no_pages_in_analysis_data", lang, fallback="No pages available in the analysis data."))
            else:
                st.sidebar.info(language_manager.get_text("text_report_suggestions_only", lang, fallback="Detailed page analysis not available. General suggestions will be generated from the text report."))

            if st.sidebar.button(language_manager.get_text("generate_seo_suggestions_button_text", lang, fallback="Generate SEO Suggestions")):
                handle_seo_suggestions_generation(lang)
        elif st.session_state.get("authenticated"): 
            st.sidebar.info(language_manager.get_text("analyze_url_first_for_suggestions", lang, fallback="Analyze a URL to enable SEO suggestions."))

        username_display = st.session_state.get("username", "User")
        st.markdown(language_manager.get_text("logged_in_as", lang, username_display))
        common_sidebar()
        
        if st.session_state.get("messages"):
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        placeholder_text = language_manager.get_text("enter_url_or_question_seo_helper", lang)
        if prompt := st.chat_input(placeholder_text):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            if main_process_url is None: 
                st.error("URL processing functionality is not available due to an import error.")
            else:
                has_mistral = bool(st.session_state.get("MISTRAL_API_KEY"))
                has_gemini = bool(st.session_state.get("GEMINI_API_KEY"))
                
                if not has_mistral and not has_gemini:
                    error_msg = language_manager.get_text("no_ai_api_keys_configured", lang, fallback="No AI API keys configured. Please check your configuration.")
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                else:
                    await process_chat_input(
                        prompt=prompt,
                        process_url_from_main=lambda url, lang_code: main_process_url(url, lang_code), 
                        MISTRAL_API_KEY=st.session_state.get("MISTRAL_API_KEY"),
                        GEMINI_API_KEY=st.session_state.get("GEMINI_API_KEY"),
                        message_list="messages"
                    )
                    
    except Exception as e:
        logging.error(f"Error in main_seo_helper: {str(e)}", exc_info=True) 
        lang_fallback = st.session_state.get("language", "en") 
        st.error(language_manager.get_text("unexpected_error_refresh", lang_fallback, fallback="An unexpected error occurred. Please refresh the page and try again."))

if __name__ == "__main__":
    asyncio.run(main_seo_helper())