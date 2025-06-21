# /Seobot/utils/seo_helper_functions.py
import streamlit as st
import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.language_support import language_manager
from utils.seo_data_parser import parse_auto_suggestions, save_auto_suggestions_to_supabase
from buttons.generate_seo_suggestions import generate_seo_suggestions

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

        insights_heading_key = "report_ai_powered_strategic_insights"
        heading_text_from_manager = language_manager.get_text(insights_heading_key, lang)
        
        heading_to_find_in_report = f"## {heading_text_from_manager}"
        
        insights_start_index = text_report_content.lower().find(heading_to_find_in_report.lower())
        
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