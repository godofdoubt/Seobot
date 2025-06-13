#Seobot/pages/1_SEO_Helper.py
import streamlit as st

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="SEO Helper",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="auto"
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
    
    has_mistral = bool(os.getenv("MISTRAL_API_KEY")) # Check env var directly
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))   # Check env var directly
    
    if not has_mistral and not has_gemini:
        logging.error("No AI API keys available for suggestions generation")
        return None
    
    # Determine preferred service and fallback based on st.session_state.use_mistral
    # And available keys.
    service_preference = "mistral" if st.session_state.get("use_mistral", True) and has_mistral else "gemini"

    if service_preference == "mistral":
        primary = "mistral"
        fallback = "gemini" if has_gemini else None
    else: # Defaulting to Gemini or if Mistral key not present / not preferred
        primary = "gemini" if has_gemini else "mistral" if has_mistral else None
        fallback = "mistral" if has_mistral and primary != "mistral" else None
    
    if not primary: # No primary service could be determined
        logging.error("No primary AI service could be determined based on available keys and preference.")
        return None

    original_use_mistral_session = st.session_state.get("use_mistral") 

    try:
        logging.info(f"Attempting to generate suggestions using {primary}")
        st.session_state["use_mistral"] = (primary == "mistral")
        suggestions = generate_seo_suggestions(pages_data_for_suggestions=pages_data_for_suggestions)
        
        if original_use_mistral_session is not None:
            st.session_state["use_mistral"] = original_use_mistral_session
        else:
            if "use_mistral" in st.session_state: del st.session_state["use_mistral"]

        if suggestions and suggestions.strip():
            logging.info(f"Successfully generated suggestions using {primary}")
            return suggestions
        else:
            logging.warning(f"Empty or invalid response from {primary}")
            
    except Exception as e:
        logging.error(f"Error generating suggestions with {primary}: {str(e)}")
        if original_use_mistral_session is not None:
            st.session_state["use_mistral"] = original_use_mistral_session
        else:
            if "use_mistral" in st.session_state: del st.session_state["use_mistral"]
    
    if fallback:
        try:
            logging.info(f"Falling back to {fallback} for suggestions generation")
            st.info(language_manager.get_text("fallback_ai_service", lang, fallback.title(), fallback=f"Primary AI service unavailable or failed. Using {fallback.title()} as fallback..."))
            
            st.session_state["use_mistral"] = (fallback == "mistral")
            suggestions = generate_seo_suggestions(pages_data_for_suggestions=pages_data_for_suggestions)

            if original_use_mistral_session is not None:
                st.session_state["use_mistral"] = original_use_mistral_session
            else:
                if "use_mistral" in st.session_state: del st.session_state["use_mistral"]

            if suggestions and suggestions.strip():
                logging.info(f"Successfully generated suggestions using fallback {fallback}")
                return suggestions
            else:
                logging.warning(f"Empty or invalid response from fallback {fallback}")
                
        except Exception as e:
            logging.error(f"Error generating suggestions with fallback {fallback}: {str(e)}")
            if original_use_mistral_session is not None:
                st.session_state["use_mistral"] = original_use_mistral_session
            else:
                if "use_mistral" in st.session_state: del st.session_state["use_mistral"]

    logging.error("Both primary and fallback AI services failed to generate suggestions")
    return None

def get_content_creation_cta_text(suggestions_data, lang):
    """
    Generates CTA text if actionable tasks (article or product) are found.
    Prioritizes article tasks. If product tasks also exist, they are noted as secondary.
    Includes the name of the first primary task and offers yes/skip/stop options.

    Returns:
        tuple: (
            cta_text: str or None,
            primary_task_type: str or None,
            primary_tasks: list or None,
            secondary_task_info: dict or None 
                (e.g., {'type': 'product_writer', 'tasks': [...]})
        )
    """
    primary_task_type = None
    primary_tasks = None
    primary_cta_text = None
    secondary_task_info = None

    identified_article_tasks = None
    identified_product_tasks = None

    if isinstance(suggestions_data, dict):
        content_ideas = suggestions_data.get("content_creation_ideas")
        if isinstance(content_ideas, dict):
            article_tasks_list = content_ideas.get("article_content_tasks")
            if isinstance(article_tasks_list, list) and article_tasks_list:
                identified_article_tasks = article_tasks_list
            
            product_tasks_list = content_ideas.get("product_content_tasks")
            if isinstance(product_tasks_list, list) and product_tasks_list:
                identified_product_tasks = product_tasks_list

    if identified_article_tasks:
        primary_task_type = "article_writer"
        primary_tasks = identified_article_tasks
        num_tasks = len(primary_tasks)
        first_task_details = primary_tasks[0]
        first_task_name = first_task_details.get("suggested_title", language_manager.get_text("the_first_article_generic", lang, fallback="the first article"))
        
        cta_question_key = "seo_helper_initial_cta_article_extended"
        primary_cta_text = language_manager.get_text(
            cta_question_key, lang, num_tasks=num_tasks, first_task_title=first_task_name,
            fallback=(f"\n\nI've identified {num_tasks} potential article ideas. "
                      f"The first is '{first_task_name}'. Shall I prepare it for the Article Writer? "
                      f"(Type 'yes' to prepare, 'skip' for the next, or 'stop' to cancel this process)")
        )
        logging.info(f"CTA: Primary tasks are articles. First: {first_task_name}. {num_tasks} total.")

        if identified_product_tasks:
            secondary_task_info = {"type": "product_writer", "tasks": identified_product_tasks}
            num_secondary_tasks = len(identified_product_tasks)
            logging.info(f"CTA: Secondary tasks identified: products ({num_secondary_tasks} tasks).")

    elif identified_product_tasks: # No article tasks, but product tasks exist
        primary_task_type = "product_writer"
        primary_tasks = identified_product_tasks
        num_tasks = len(primary_tasks)
        first_task_details = primary_tasks[0]
        first_task_name = first_task_details.get("product_name", language_manager.get_text("the_first_product_generic", lang, fallback="the first product"))

        cta_question_key = "seo_helper_initial_cta_product_extended"
        primary_cta_text = language_manager.get_text(
            cta_question_key, lang, num_tasks=num_tasks, first_task_title=first_task_name,
            fallback=(f"\n\nI've found {num_tasks} product description tasks. "
                      f"The first is for '{first_task_name}'. Shall I prepare it for the Product Writer? "
                      f"(Type 'yes' to prepare, 'skip' for the next, or 'stop' to cancel this process)")
        )
        logging.info(f"CTA: Primary tasks are products (no articles found). First: {first_task_name}. {num_tasks} total.")
        # No secondary tasks in this branch, as articles would have been primary if present.
    
    if not primary_cta_text:
        logging.info("CTA: No actionable article or product tasks found for CTA.")

    return primary_cta_text, primary_task_type, primary_tasks, secondary_task_info

def _build_suggestions_display_text(structured_data, lang, title_prefix="", is_loaded_suggestions=False):
    """
    Helper to build display text from structured suggestions data.
    Always attempts to display insights from text_report if available.
    Then, displays structured suggestions.
    """
    display_parts = []
    insights_displayed_successfully = False

    # --- Try to display AI-Powered Strategic Insights from text_report ---
    if st.session_state.get("text_report"):
        text_report_content = st.session_state.text_report
        text_report_lower = text_report_content.lower()

       
        # === DÜZELTME BAŞLANGICI ===

        # 1. Doğru dil anahtarını kullanarak başlık metnini al.
        # Bu anahtar, llm_analysis_process.py'de kullanılan anahtarla AYNI OLMALI.
        insights_heading_key = "report_ai_powered_strategic_insights"
        heading_text_from_manager = language_manager.get_text(insights_heading_key, lang)
        
        # 2. Markdown başlığını (##) ekle ve büyük/küçük harfe duyarsız arama yap.
        heading_to_find_in_report = f"## {heading_text_from_manager}"
        
        # 3. text_report içinde büyük/küçük harfe duyarsız arama yap.
        insights_start_index = text_report_content.lower().find(heading_to_find_in_report.lower())

        # === DÜZELTME SONU ===
        
        if insights_start_index != -1:
            # Find original heading text with original casing to split correctly
            original_heading = text_report_content[insights_start_index : insights_start_index + len(heading_to_find_in_report)]
            section_content_start = insights_start_index + len(heading_to_find_in_report)

            # Find the end of the section
            next_separator_index = text_report_content.find("\n---", section_content_start)
            if next_separator_index != -1:
                insights_text_from_report = text_report_content[section_content_start:next_separator_index].strip()
            else:
                insights_text_from_report = text_report_content[section_content_start:].strip()
            
            # Build display title
            insights_section_base_title_text = language_manager.get_text("ai_powered_strategic_insights", lang, fallback="AI-Powered Strategic Insights & Recommendations")
            base_display_prefix = f"{title_prefix} " if title_prefix else ""
            current_insights_display_title = f"**{base_display_prefix}{insights_section_base_title_text}**\n\n"

            display_parts.append(current_insights_display_title)
            display_parts.append(insights_text_from_report)
            insights_displayed_successfully = True
            logging.info(f"Successfully extracted strategic insights section from text_report (lang: {lang}).")
        else:
            logging.warning(f"Strategic insights heading not found in text_report (lang: '{lang}'). Section will be skipped.")
            logging.debug(f"Aranan başlık: '{heading_to_find_in_report}'") #hata ayıklama
            logging.debug(f"Text report snippet (first 500 chars): {text_report_content[:500]}")
            
    
    # --- Display Structured SEO Suggestions & Content Ideas ---
    if insights_displayed_successfully and structured_data:
        display_parts.append("\n\n---\n\n")

    suggestions_base_title_text = language_manager.get_text("seo_suggestions_and_content_ideas_title", lang, fallback="SEO Suggestions & Content Ideas")
    
    current_suggestions_display_title = f"**{title_prefix} {suggestions_base_title_text}:**\n" if title_prefix else f"**{suggestions_base_title_text}:**\n"
    display_parts.append(current_suggestions_display_title)

    if structured_data is None:
        display_parts.append(language_manager.get_text("no_suggestions_data_available", lang, fallback="No suggestion data available to display."))
    else:
        # Pre-JSON prose
        if structured_data.get("pre_json_prose"):
            display_parts.append(f"{structured_data['pre_json_prose']}\n\n")

        # Content Creation Ideas
        if structured_data.get("content_creation_ideas"):
            display_parts.append(f"## {language_manager.get_text('content_tasks_subsection_title', lang, fallback='Content Tasks')}\n")
            content_ideas = structured_data["content_creation_ideas"]
            
            article_tasks = content_ideas.get("article_content_tasks")
            if isinstance(article_tasks, list) and article_tasks:
                display_parts.append(f"**{language_manager.get_text('article_content_tasks_label', lang, fallback='Article Content Tasks')}:**\n")
                for item_idx, item_task in enumerate(article_tasks):
                    if isinstance(item_task, dict): 
                        title_from_task = item_task.get('suggested_title', language_manager.get_text('article_task_generic_name', lang, number=item_idx+1, fallback=f"Article Task {item_idx+1}"))
                        display_parts.append(f"- **{title_from_task}**\n")
                        for k, v_task in item_task.items():
                            if k not in ['suggested_title', 'title']:
                                 display_parts.append(f"  - {k.replace('_',' ').title()}: {v_task}\n")
                    else: 
                        display_parts.append(f"- {item_task}\n") 
                display_parts.append("\n")

            product_tasks = content_ideas.get("product_content_tasks")
            if isinstance(product_tasks, list) and product_tasks:
                display_parts.append(f"**{language_manager.get_text('product_content_tasks_label', lang, fallback='Product Content Tasks')}:**\n")
                for item_idx, item_task in enumerate(product_tasks):
                    if isinstance(item_task, dict): 
                        title_from_task = item_task.get('product_name', language_manager.get_text('product_task_generic_name', lang, number=item_idx+1, fallback=f"Product Task {item_idx+1}"))
                        display_parts.append(f"- **{title_from_task}**\n")
                        for k, v_task in item_task.items():
                            if k not in ['product_name']:
                                 display_parts.append(f"  - {k.replace('_',' ').title()}: {v_task}\n")
                    else: 
                        display_parts.append(f"- {item_task}\n")
                display_parts.append("\n")
            
            other_task_keys = [k for k in content_ideas.keys() if k not in ["article_content_tasks", "product_content_tasks", "_source", "parsing_error_detail", "raw_unparsed_json_block"]]
            if other_task_keys:
                display_parts.append(f"**{language_manager.get_text('other_tasks_ideas_label', lang, fallback='Other Tasks/Ideas')}:**\n")
                for key in other_task_keys:
                    display_parts.append(f"***{key.replace('_', ' ').title()}:***\n{json.dumps(content_ideas[key], indent=2)}\n\n")

            if content_ideas.get("parsing_error_detail"):
                # FIX: Corrected the fallback argument to use a format template string instead of a nested f-string.
                display_parts.append(f"\n*{language_manager.get_text('note_prefix', lang, fallback='Note')}: {language_manager.get_text('error_parsing_content_tasks', lang, error_detail=content_ideas['parsing_error_detail'], fallback='Error parsing content tasks: {error_detail}')}*")
                if content_ideas.get("raw_unparsed_json_block"):
                    display_parts.append(f"\n*{language_manager.get_text('raw_json_block_unparsed_label', lang, fallback='Raw JSON block (could not parse)')}:*\n```json\n{content_ideas['raw_unparsed_json_block']}\n```\n")
            elif content_ideas.get("_source") == "no_json_block_found" or content_ideas.get("_source") == "no_json_block_found_or_empty":
                display_parts.append(f"*{language_manager.get_text('no_specific_json_tasks_found', lang, fallback='No specific JSON-formatted content tasks were found in the AI response.')}*\n")

        # Post-JSON prose
        if structured_data.get("post_json_prose"):
            display_parts.append(f"\n\n{structured_data['post_json_prose']}\n")

        # Outer parsing error
        if structured_data.get("parsing_error_outer"):
            # FIX: Corrected the fallback argument to use a format template string instead of a nested f-string.
            display_parts.append(f"\n*{language_manager.get_text('note_prefix', lang, fallback='Note')}: {language_manager.get_text('major_error_parsing_suggestions', lang, error_outer=structured_data['parsing_error_outer'], fallback='There was a major error parsing these suggestions. Error: {error_outer}')}*\n")
            if structured_data.get("failed_input_text_on_error"):
                display_parts.append(f"{language_manager.get_text('problematic_input_text_label', lang, fallback='Problematic input text (first 500 chars)')}:\n```\n{structured_data['failed_input_text_on_error'][:500]}...\n```\n")

        # Timestamp (applies to structured_data)
        if structured_data.get("generated_timestamp"):
            generated_time_str = structured_data['generated_timestamp']
            try:
                if generated_time_str.endswith("Z"):
                    dt_obj = datetime.fromisoformat(generated_time_str[:-1] + "+00:00")
                else:
                    dt_obj = datetime.fromisoformat(generated_time_str)
                formatted_time = dt_obj.strftime("%Y-%m-%d %H:%M:%S UTC")
                display_parts.append(f"\n\n*{language_manager.get_text('suggestions_data_generated_label', lang, formatted_time=formatted_time, fallback=f'Suggestions data generated/updated: {formatted_time}')}*")
            except ValueError:
                display_parts.append(f"\n\n*{language_manager.get_text('suggestions_data_generated_label_raw', lang, generated_time_str=generated_time_str, fallback=f'Suggestions data generated/updated: {generated_time_str}')}*")
    
    return "".join(display_parts)


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
                    pages_data_for_suggestions=data_for_suggestions
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

                    chat_content_for_manual_suggestions = _build_suggestions_display_text(
                        parsed_manual_suggestions, 
                        lang, 
                        title_prefix="Manually Generated",
                        is_loaded_suggestions=False
                    )
                    
                    st.session_state.paused_cta_context = None
                    st.session_state.awaiting_seo_helper_cta_response = False 
                    st.session_state.seo_helper_cta_context = None

                    cta_text_if_any, cta_task_type, cta_tasks, cta_secondary_info = get_content_creation_cta_text(parsed_manual_suggestions, lang)
                    
                    if cta_text_if_any:
                        chat_content_for_manual_suggestions += cta_text_if_any
                        st.session_state.awaiting_seo_helper_cta_response = True
                        st.session_state.seo_helper_cta_context = {
                            "type": cta_task_type,
                            "tasks": cta_tasks,
                            "current_task_index": 0,
                            "secondary_tasks_info": cta_secondary_info
                        }
                        logging.info(f"CTA activated after manual suggestion. Primary: {cta_task_type}.")
                    
                    last_message_content = st.session_state.messages[-1]["content"] if st.session_state.messages else None
                    if last_message_content != chat_content_for_manual_suggestions: 
                        st.session_state.messages.append({"role": "assistant", "content": chat_content_for_manual_suggestions})
                        st.rerun()
                else:
                    st.sidebar.error(language_manager.get_text("error_all_ai_services_failed", lang, fallback="All AI services failed to generate suggestions. Please try again later."))
                    
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {str(e)}")
        st.sidebar.error(language_manager.get_text("error_generating_suggestions", lang, fallback="An error occurred while generating suggestions. Please try again."))

def format_product_details_for_seo_helper_display(details_dict, lang="en"):
    """Formats structured product details for concise display in SEO Helper."""
    if not isinstance(details_dict, dict):
        return language_manager.get_text('not_available_short', lang, fallback="N/A")
    
    parts = []
    features = details_dict.get("features", [])
    if features:
        parts.append(f"**{language_manager.get_text('features_label', lang, fallback='Features')}:** {', '.join(features[:2])}{'...' if len(features) > 2 else ''}")

    benefits = details_dict.get("benefits", [])
    if benefits:
        parts.append(f"**{language_manager.get_text('benefits_label', lang, fallback='Benefits')}:** {', '.join(benefits[:2])}{'...' if len(benefits) > 2 else ''}")

    target_audience = details_dict.get("target_audience")
    if target_audience:
        parts.append(f"**{language_manager.get_text('target_audience_label', lang, fallback='Target Audience')}:** {target_audience[:50]}{'...' if len(target_audience) > 50 else ''}")
    
    if not parts:
        return language_manager.get_text('no_details_provided_short', lang, fallback="No specific details provided.")
        
    return "; ".join(parts)

async def main_seo_helper():
    """Main function for SEO Helper page."""
    try:
        init_shared_session_state() 
        supabase_client = get_supabase_client() 
        
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
            if not st.session_state.get("awaiting_seo_helper_cta_response") and not st.session_state.get("paused_cta_context"): 
                 st.session_state.messages[0]["content"] = target_welcome_message_seo
        
        check_auth()
        user_id = st.session_state.get("user_id") 
        
        if (st.session_state.get("analysis_in_progress") and st.session_state.get("url_being_analyzed")):
            st.info(language_manager.get_text("analysis_in_progress_for", lang, st.session_state.url_being_analyzed))

        llm_analysis_available = (
            st.session_state.get("full_report") and
            isinstance(st.session_state.full_report, dict) and
            st.session_state.full_report.get("llm_analysis_all") and
            isinstance(st.session_state.full_report["llm_analysis_all"], dict) and
            st.session_state.full_report["llm_analysis_all"]
        )
        text_report_available = bool(st.session_state.get("text_report"))
        current_analyzed_url = st.session_state.get("url")

        if llm_analysis_available and text_report_available and current_analyzed_url:
            if (st.session_state.url_for_auto_suggestions != current_analyzed_url or 
                not st.session_state.auto_suggestions_generated_for_current_url):
                
                st.session_state.paused_cta_context = None
                st.session_state.awaiting_seo_helper_cta_response = False
                st.session_state.seo_helper_cta_context = None
                
                existing_suggestions_structured = None
                if st.session_state.get("current_report_url_for_suggestions") == current_analyzed_url:
                    potential_data = st.session_state.get("auto_suggestions_data")
                    if isinstance(potential_data, dict):
                        logging.info(f"SEO_Helper: Using pre-loaded dict 'auto_suggestions_data' from session for {current_analyzed_url}.")
                        existing_suggestions_structured = potential_data
                    elif isinstance(potential_data, str):
                        logging.info(f"SEO_Helper: 'auto_suggestions_data' from session is a string for {current_analyzed_url}. Parsing now.")
                        parsed_data = parse_auto_suggestions(potential_data)
                        if isinstance(parsed_data, dict) and not parsed_data.get("parsing_error_outer") and "content_creation_ideas" in parsed_data:
                            existing_suggestions_structured = parsed_data
                            st.session_state.auto_suggestions_data = parsed_data
                            logging.info(f"SEO_Helper: Successfully parsed string 'auto_suggestions_data' from session for {current_analyzed_url} and updated session.")
                        else:
                            logging.warning(f"SEO_Helper: Failed to parse string 'auto_suggestions_data' from session for {current_analyzed_url}. Will try DB load or generate new. Parsed result: {parsed_data}")
                            existing_suggestions_structured = None 
                    else: 
                        logging.info(f"SEO_Helper: 'auto_suggestions_data' in session for {current_analyzed_url} is None or unsuitable type ({type(potential_data)}).")
                        existing_suggestions_structured = None 

                if not existing_suggestions_structured:
                    logging.info(f"SEO_Helper: Not using session 'auto_suggestions_data'. Attempting to load from Supabase for {current_analyzed_url}.")
                    db_loaded_suggestions = load_auto_suggestions_from_supabase(current_analyzed_url, supabase_client, parse_auto_suggestions)
                    if db_loaded_suggestions: 
                        existing_suggestions_structured = db_loaded_suggestions
                        st.session_state.auto_suggestions_data = db_loaded_suggestions 
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url 
                        logging.info(f"SEO_Helper: Loaded 'auto_suggestions_data' from Supabase for {current_analyzed_url} and updated session.")

                suggestions_to_display_in_chat = None 
                current_auto_suggestions_data_for_cta = None
                
                if existing_suggestions_structured:
                    st.info(language_manager.get_text("loading_existing_suggestions", lang, fallback="Loading existing SEO suggestions from database..."))
                    current_auto_suggestions_data_for_cta = existing_suggestions_structured
                    suggestions_to_display_in_chat = _build_suggestions_display_text(
                        existing_suggestions_structured, 
                        lang, 
                        title_prefix="Loaded/Yüklendi",
                        is_loaded_suggestions=True
                    )
                    logging.info(f"SEO_Helper: Using existing suggestions (from session or DB) for {current_analyzed_url}")
                else: 
                    data_for_auto_suggestions = {"_source_type_": "text_report", "content": st.session_state.text_report}
                    auto_gen_message_placeholder = st.empty()
                    auto_gen_message_placeholder.info(language_manager.get_text("auto_generating_initial_suggestions", lang, fallback="Analysis complete. Automatically generating initial suggestions based on the text report..."))

                    suggestions_raw_new = None
                    with st.spinner(language_manager.get_text("auto_processing_initial_suggestions", lang, fallback="Auto-generating initial suggestions...")):
                        suggestions_raw_new = generate_seo_suggestions_with_fallback(pages_data_for_suggestions=data_for_auto_suggestions)
                    
                    auto_gen_message_placeholder.empty()

                    if suggestions_raw_new:
                        newly_structured_suggestions = parse_auto_suggestions(suggestions_raw_new)
                        current_auto_suggestions_data_for_cta = newly_structured_suggestions
                        save_success = save_auto_suggestions_to_supabase(current_analyzed_url, newly_structured_suggestions, supabase_client, user_id)
                        if save_success: logging.info(f"Auto suggestions saved to Supabase for URL: {current_analyzed_url}")
                        else: logging.warning(f"Failed to save auto suggestions to Supabase for URL: {current_analyzed_url}")
                        
                        suggestions_to_display_in_chat = _build_suggestions_display_text(
                            newly_structured_suggestions, 
                            lang, 
                            title_prefix="Auto-Generated",
                            is_loaded_suggestions=False
                        )
                        
                        st.session_state.auto_suggestions_data = newly_structured_suggestions
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url
                        logging.info(f"SEO_Helper: Set auto_suggestions_data from NEWLY generated for {current_analyzed_url}")
                    else:
                        suggestions_to_display_in_chat = language_manager.get_text("error_auto_suggestions_failed", lang, fallback="Unable to generate automatic suggestions. You can still request manual suggestions using the sidebar.")
                        st.session_state.auto_suggestions_data = None 
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url 
                        logging.info(f"SEO_Helper: Set auto_suggestions_data to None (generation failed) for {current_analyzed_url}")
                
                if suggestions_to_display_in_chat and current_auto_suggestions_data_for_cta:
                    cta_text_if_any, cta_task_type, cta_tasks, cta_secondary_info = get_content_creation_cta_text(current_auto_suggestions_data_for_cta, lang)
                    if cta_text_if_any:
                        suggestions_to_display_in_chat += cta_text_if_any
                        st.session_state.awaiting_seo_helper_cta_response = True
                        st.session_state.seo_helper_cta_context = {
                            "type": cta_task_type,
                            "tasks": cta_tasks,
                            "current_task_index": 0,
                            "secondary_tasks_info": cta_secondary_info
                        }
                        logging.info(f"CTA activated after auto-suggestion. Primary: {cta_task_type}.")
                
                if suggestions_to_display_in_chat:
                    last_message_content = st.session_state.messages[-1]["content"] if st.session_state.messages else None
                    if last_message_content != suggestions_to_display_in_chat:
                        st.session_state.messages.append({"role": "assistant", "content": suggestions_to_display_in_chat})
                
                st.session_state.url_for_auto_suggestions = current_analyzed_url
                st.session_state.auto_suggestions_generated_for_current_url = True
                if (suggestions_to_display_in_chat and (not st.session_state.messages or last_message_content != suggestions_to_display_in_chat)) or \
                   (st.session_state.get("awaiting_seo_helper_cta_response") and 'cta_text_if_any' in locals() and cta_text_if_any):
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
        st.markdown(language_manager.get_text("logged_in_as", lang, username=username_display))
        common_sidebar()    
        
        active_cta_context_display = st.session_state.get("seo_helper_cta_context")
        paused_cta_context_display = st.session_state.get("paused_cta_context")
        show_task_panel_display = False
        tasks_for_panel_display = None
        current_task_idx_panel_display = -1
        panel_status_message_display = ""
        is_paused_panel_display = False
        task_type_panel_display = None

        current_context_to_use = None
        if st.session_state.get("awaiting_seo_helper_cta_response") and active_cta_context_display:
            current_context_to_use = active_cta_context_display
        elif paused_cta_context_display:
            current_context_to_use = paused_cta_context_display
            is_paused_panel_display = True

        if current_context_to_use:
            task_type_panel_display = current_context_to_use.get("type")
            tasks_for_panel_display = current_context_to_use.get("tasks")
            current_task_idx_panel_display = current_context_to_use.get("current_task_index", 0)

            if tasks_for_panel_display and isinstance(tasks_for_panel_display, list) and 0 <= current_task_idx_panel_display < len(tasks_for_panel_display):
                current_task_item_display = tasks_for_panel_display[current_task_idx_panel_display]
                show_task_panel_display = True
                
                if task_type_panel_display == "article_writer":
                    task_title_for_status = current_task_item_display.get("suggested_title", f"task {current_task_idx_panel_display + 1}")
                    if is_paused_panel_display:
                        panel_status_message_display = language_manager.get_text("cta_status_paused_at", lang, title=task_title_for_status, fallback=f"Paused article task preparation at: '{task_title_for_status}'.")
                    else: 
                        panel_status_message_display = language_manager.get_text("cta_status_awaiting_response_for", lang, title=task_title_for_status, fallback=f"Awaiting response for article task: '{task_title_for_status}'.")
                elif task_type_panel_display == "product_writer":
                    task_title_for_status = current_task_item_display.get("product_name", f"product task {current_task_idx_panel_display + 1}")
                    if is_paused_panel_display:
                        panel_status_message_display = language_manager.get_text("cta_status_paused_at_product", lang, title=task_title_for_status, fallback=f"Paused product task preparation at: '{task_title_for_status}'.")
                    else: 
                        panel_status_message_display = language_manager.get_text("cta_status_awaiting_response_for_product", lang, title=task_title_for_status, fallback=f"Awaiting response for product task: '{task_title_for_status}'.")
                else:
                     panel_status_message_display = language_manager.get_text("cta_status_awaiting_response_generic", lang, fallback="Awaiting response for suggested task.")
            elif tasks_for_panel_display and isinstance(tasks_for_panel_display, list) and current_task_idx_panel_display >= len(tasks_for_panel_display):
                show_task_panel_display = True 
                panel_status_message_display = language_manager.get_text("cta_all_tasks_addressed_panel", lang, fallback="All content tasks in this batch have been addressed.")
                is_paused_panel_display = False

        if st.session_state.get("messages"):
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        placeholder_text_key = "enter_url_or_question_seo_helper"
        if st.session_state.get("awaiting_seo_helper_cta_response"):
            current_cta_ctx = st.session_state.get("seo_helper_cta_context")
            task_name_for_placeholder = "current task"
            if current_cta_ctx:
                tasks = current_cta_ctx.get("tasks", [])
                current_idx = current_cta_ctx.get("current_task_index", 0)
                if 0 <= current_idx < len(tasks):
                    current_task_item = tasks[current_idx]
                    task_type_for_ph = current_cta_ctx.get("type")
                    if task_type_for_ph == "article_writer":
                        task_name_for_placeholder = current_task_item.get("suggested_title", f"article {current_idx+1}")
                    elif task_type_for_ph == "product_writer":
                        task_name_for_placeholder = current_task_item.get("product_name", f"product {current_idx+1}")
            placeholder_text_key = "seo_helper_cta_input_placeholder_extended" 
            placeholder_text = language_manager.get_text(placeholder_text_key, lang, task_name=task_name_for_placeholder, fallback=f"Your response for '{task_name_for_placeholder}' (yes/skip/stop)...")
        else:
            placeholder_text = language_manager.get_text(placeholder_text_key, lang, fallback="Enter URL to analyze, or ask an SEO question...")

# /SeoBot/pages/1_SEO_Helper.py

# ... (fix for new analysis on page 1)

        if prompt := st.chat_input(placeholder_text):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            if main_process_url is None: 
                st.error("URL processing functionality is not available due to an import error.")
            else:
                has_mistral_key = bool(os.getenv("MISTRAL_API_KEY"))
                has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
                
                if not has_mistral_key and not has_gemini_key:
                    error_msg = language_manager.get_text("no_ai_api_keys_configured", lang, fallback="No AI API keys configured. Please check your configuration.")
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                else:
                    await process_chat_input(
                        prompt=prompt,
                        process_url_from_main=lambda url, lang_code: main_process_url(url, supabase_client, lang_code), 
                        message_list="messages"
                    )

# ... (rest of the file)
        if is_paused_panel_display and tasks_for_panel_display and \
           0 <= current_task_idx_panel_display < len(tasks_for_panel_display):
            
            task_to_resume_details = tasks_for_panel_display[current_task_idx_panel_display]
            resume_button_text_btn_display = ""
            
            if task_type_panel_display == "article_writer":
                task_to_resume_title_btn_display = task_to_resume_details.get("suggested_title", "the current article task")
                resume_button_text_key_btn_display = "resume_article_tasks_button"
                resume_button_text_btn_display = language_manager.get_text(resume_button_text_key_btn_display, lang, task_title=task_to_resume_title_btn_display, fallback=f"Resume with: '{task_to_resume_title_btn_display}'")
            elif task_type_panel_display == "product_writer":
                task_to_resume_title_btn_display = task_to_resume_details.get("product_name", "the current product task")
                resume_button_text_key_btn_display = "resume_product_tasks_button" 
                resume_button_text_btn_display = language_manager.get_text(resume_button_text_key_btn_display, lang, task_title=task_to_resume_title_btn_display, fallback=f"Resume with: '{task_to_resume_title_btn_display}'")

            if resume_button_text_btn_display and st.button(resume_button_text_btn_display, key="resume_cta_panel_button"):
                st.session_state.seo_helper_cta_context = st.session_state.paused_cta_context
                st.session_state.awaiting_seo_helper_cta_response = True
                st.session_state.paused_cta_context = None
                
                resumed_task_display_details = st.session_state.seo_helper_cta_context["tasks"][st.session_state.seo_helper_cta_context["current_task_index"]]
                resume_message_chat_display = ""

                if task_type_panel_display == "article_writer":
                    resumed_task_title_chat_prompt = resumed_task_display_details.get("suggested_title", "the selected article suggestion")
                    resume_chat_prompt_key_btn_display = "seo_helper_cta_resumed_chat_prompt_extended_options"
                    resume_message_chat_display = language_manager.get_text(
                        resume_chat_prompt_key_btn_display, lang, task_title=resumed_task_title_chat_prompt,
                        fallback=(f"Resuming article task preparation. I am now focused on '{resumed_task_title_chat_prompt}'. "
                                  f"Shall I prepare it, skip to the next, or stop this process? (Type 'yes', 'skip', or 'stop')")
                    )
                elif task_type_panel_display == "product_writer":
                    resumed_task_title_chat_prompt = resumed_task_display_details.get("product_name", "the selected product suggestion")
                    resume_chat_prompt_key_btn_display = "seo_helper_cta_resumed_chat_prompt_product_extended_options"
                    resume_message_chat_display = language_manager.get_text(
                        resume_chat_prompt_key_btn_display, lang, task_title=resumed_task_title_chat_prompt,
                        fallback=(f"Resuming product task preparation. I am now focused on '{resumed_task_title_chat_prompt}'. "
                                  f"Shall I prepare it, skip to the next, or stop this process? (Type 'yes', 'skip', or 'stop')")
                    )
                
                if resume_message_chat_display:
                    st.session_state.messages.append({"role": "assistant", "content": resume_message_chat_display})
                    logging.info(f"CTA Resumed from panel button. Re-prompting for task: {resumed_task_title_chat_prompt} (Type: {task_type_panel_display})")
                    st.rerun()

        if show_task_panel_display and tasks_for_panel_display:
            expander_title_key_display = "content_tasks_expander_title"
            expander_title_text_display = language_manager.get_text(expander_title_key_display, lang, fallback="Content Generation Tasks Progress")
            with st.expander(expander_title_text_display, expanded=False):
                if panel_status_message_display:
                    st.info(panel_status_message_display)

                if not (current_task_idx_panel_display >= len(tasks_for_panel_display) and not is_paused_panel_display):
                    for i, task_item_display in enumerate(tasks_for_panel_display):
                        item_style_display = "font-style: italic; color: gray;" 
                        prefix_icon_display = "📝"

                        if i < current_task_idx_panel_display:
                            task_is_completed = False
                            task_identifier_for_check = ""
                            if task_type_panel_display == "article_writer":
                                task_identifier_for_check = task_item_display.get("suggested_title")
                                if any(ct.get("suggested_title") == task_identifier_for_check for ct in st.session_state.get("completed_tasks_article", [])):
                                    task_is_completed = True
                            elif task_type_panel_display == "product_writer":
                                task_identifier_for_check = task_item_display.get("product_name")
                                if any(ct.get("product_name") == task_identifier_for_check for ct in st.session_state.get("completed_tasks_product", [])):
                                     task_is_completed = True
                            
                            if task_is_completed:
                                prefix_icon_display = "✅"
                                item_style_display = "color: green;" 
                            else: 
                                prefix_icon_display = "➖" 
                                item_style_display = "color: gray; text-decoration: line-through;"
                        elif i == current_task_idx_panel_display: 
                            if not is_paused_panel_display: 
                                prefix_icon_display = "➡️"
                                item_style_display = "font-weight: bold;"
                            else: 
                                prefix_icon_display = "⏸️"
                                item_style_display = "font-weight: bold; color: orange;"
                        
                       
                        if task_type_panel_display == "article_writer":
                            task_title_display = task_item_display.get("suggested_title", f"Article Task {i+1}")
                            st.markdown(f"<div style='{item_style_display}'>{prefix_icon_display} **{task_title_display}**</div>", unsafe_allow_html=True)
                            
                            task_details_list_display = []
                            if task_item_display.get("focus_keyword"): 
                                task_details_list_display.append(f"Focus Keyword: `{task_item_display.get('focus_keyword')}`")
                            if task_item_display.get("content_length"): 
                                task_details_list_display.append(f"Length: {task_item_display.get('content_length')}")
                            if task_item_display.get("article_tone"): 
                                task_details_list_display.append(f"Tone: {task_item_display.get('article_tone')}")
                            
                            additional_keywords_display = task_item_display.get("additional_keywords")
                            if additional_keywords_display:
                                kw_str = ", ".join(filter(None, additional_keywords_display)) if isinstance(additional_keywords_display, list) else str(additional_keywords_display).strip()
                                if kw_str: task_details_list_display.append(f"Other Keywords: `{kw_str}`")

                            if task_item_display.get("target_page_url"): 
                                task_details_list_display.append(f"Target Page URL: {task_item_display.get('target_page_url')}")
                            if task_item_display.get("content_gap_addressed"): 
                                task_details_list_display.append(f"Content Gap: {task_item_display.get('content_gap_addressed')}")
                            if task_item_display.get("target_audience"): 
                                task_details_list_display.append(f"Target Audience: {task_item_display.get('target_audience')}")
                            
                            content_outline_display = task_item_display.get("content_outline")
                            if content_outline_display:
                                outline_str = ", ".join(filter(None, [str(item) for item in content_outline_display])) if isinstance(content_outline_display, list) else str(content_outline_display).strip()
                                if outline_str:
                                    display_outline = outline_str[:150] + '...' if len(outline_str) > 150 else outline_str
                                    task_details_list_display.append(f"Outline Preview: {display_outline}")

                            internal_links_display = task_item_display.get("internal_linking_opportunities")
                            if internal_links_display:
                                links_str = ", ".join(filter(None, [str(item) for item in internal_links_display])) if isinstance(internal_links_display, list) else str(internal_links_display).strip()
                                if links_str:
                                    display_links = links_str[:150] + '...' if len(links_str) > 150 else links_str
                                    task_details_list_display.append(f"Linking Opps Preview: {display_links}")

                            if task_details_list_display:
                                details_html_display = "".join([f"<li style='font-size: small; {item_style_display.replace('font-weight: bold;','')} margin-left: 20px;'>{detail}</li>" for detail in task_details_list_display])
                                st.markdown(f"<ul>{details_html_display}</ul>", unsafe_allow_html=True)

                        elif task_type_panel_display == "product_writer":
                            task_product_name_display = task_item_display.get('product_name', f"Product Task {i+1}")
                            st.markdown(f"<div style='{item_style_display}'>{prefix_icon_display} **{task_product_name_display}**</div>", unsafe_allow_html=True)
                            
                            product_task_details_list_display = []
                            if task_item_display.get('description_length'): product_task_details_list_display.append(f"Length: {task_item_display.get('description_length')}")
                            if task_item_display.get('tone'): product_task_details_list_display.append(f"Tone: {task_item_display.get('tone')}")
                            
                            seo_keywords_prod_display = task_item_display.get('seo_keywords', [])
                            if isinstance(seo_keywords_prod_display, list) and seo_keywords_prod_display:
                                product_task_details_list_display.append(f"SEO Keywords: `{', '.join(seo_keywords_prod_display)}`")
                            elif isinstance(seo_keywords_prod_display, str) and seo_keywords_prod_display.strip():
                                product_task_details_list_display.append(f"SEO Keywords: `{seo_keywords_prod_display}`")
                            
                            product_details_input = task_item_display.get('product_details')
                            product_details_dict = {}
                            if isinstance(product_details_input, str):
                                try:
                                    product_details_dict = json.loads(product_details_input)
                                except json.JSONDecodeError:
                                    product_details_dict = {"raw_text": product_details_input}
                            elif isinstance(product_details_input, dict):
                                product_details_dict = product_details_input
                                
                            product_details_summary = format_product_details_for_seo_helper_display(product_details_dict, lang)
                            if product_details_summary != language_manager.get_text('no_details_provided_short', lang, fallback="No specific details provided.") and product_details_summary != language_manager.get_text('not_available_short', lang, fallback="N/A"):
                                product_task_details_list_display.append(f"Details: {product_details_summary}")

                            if product_task_details_list_display:
                                details_html_prod_display = "".join([f"<li style='font-size: small; {item_style_display.replace('font-weight: bold;','')} margin-left: 20px;'>{detail}</li>" for detail in product_task_details_list_display])
                                st.markdown(f"<ul>{details_html_prod_display}</ul>", unsafe_allow_html=True)
                    
    except Exception as e:
        logging.error(f"Error in main_seo_helper: {str(e)}", exc_info=True) 
        lang_fallback = st.session_state.get("language", "en") 
        st.error(language_manager.get_text("unexpected_error_refresh", lang_fallback, fallback="An unexpected error occurred. Please refresh the page and try again."))

if __name__ == "__main__":
    asyncio.run(main_seo_helper())