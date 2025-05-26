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
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history
from utils.language_support import language_manager
from helpers.seo_main_helper8 import process_chat_input
from buttons.generate_seo_suggestions import generate_seo_suggestions

# --- Import process_url from main.py ---
try:
    from main import process_url as main_process_url
except ImportError:
    st.error("Failed to import process_url from main.py. Ensure main.py is in the correct path.")
    main_process_url = None

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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
                # User selected specific pages from llm_analysis_all
                valid_selected_keys = [
                    key for key in user_selected_page_keys if key in llm_data and llm_data[key]
                ]
                if valid_selected_keys:
                    data_for_suggestions = {
                        key: llm_data[key] 
                        for key in valid_selected_keys
                    }
                    st.sidebar.success(language_manager.get_text(
                        "using_selected_pages_for_suggestions", 
                        lang, 
                        ', '.join(valid_selected_keys), 
                        fallback=f"Generating suggestions for selected pages: {', '.join(valid_selected_keys)}"
                    ))
                else:
                    # User made selections, but none were valid keys in llm_data
                    st.sidebar.error(language_manager.get_text(
                        "error_selected_pages_no_valid_data", 
                        lang, 
                        fallback="Error: None of the selected pages have data available for suggestions."
                    ))
                    return
            else: 
                # No pages selected - fall back to text_report
                if text_report_available:
                    data_for_suggestions = {
                        "_source_type_": "text_report",
                        "content": st.session_state.text_report
                    }
                    st.sidebar.info(language_manager.get_text(
                        "using_text_report_for_suggestions", 
                        lang, 
                        fallback="No specific pages selected. Generating general suggestions based on the text report."
                    ))
                else:
                    st.sidebar.error(language_manager.get_text(
                        "error_no_text_report_available", 
                        lang, 
                        fallback="Error: No text report available for suggestions."
                    ))
                    return
        else:
            # Only text report available
            if text_report_available:
                data_for_suggestions = {
                    "_source_type_": "text_report",
                    "content": st.session_state.text_report
                }
                st.sidebar.info(language_manager.get_text(
                    "using_text_report_for_suggestions", 
                    lang, 
                    fallback="Generating general suggestions based on the text report."
                ))
            else:
                st.sidebar.error(language_manager.get_text(
                    "error_no_text_report_available", 
                    lang, 
                    fallback="Error: No text report available for suggestions."
                ))
                return

        if data_for_suggestions:
            with st.spinner(language_manager.get_text("processing_request", lang)):
                suggestions = generate_seo_suggestions(pages_data_for_suggestions=data_for_suggestions)
                
                # Add suggestions to chat if not already present
                if suggestions and (not st.session_state.get("messages") or 
                                 st.session_state.messages[-1].get("content") != suggestions):
                    st.session_state.messages.append({"role": "assistant", "content": suggestions})
                    st.rerun()  # Refresh to show the new message
                    
    except Exception as e:
        logging.error(f"Error generating SEO suggestions: {str(e)}")
        st.sidebar.error(language_manager.get_text(
            "error_generating_suggestions", 
            lang, 
            fallback="An error occurred while generating suggestions. Please try again."
        ))

async def main_seo_helper():
    """Main function for SEO Helper page."""
    try:
        init_shared_session_state()
        
        if "language" not in st.session_state:
            st.session_state.language = "en"
        lang = st.session_state.language
        
        st.title(language_manager.get_text("seo_helper_button", lang))
        
        if st.session_state.get("current_page") != "seo":
            update_page_history("seo")
        
        # Set up welcome message
        if st.session_state.get("url") and st.session_state.get("text_report"):
            target_welcome_message_seo = language_manager.get_text(
                "welcome_seo_helper_analyzed",
                lang,
                st.session_state.url,
                fallback=f"Welcome to the SEO Helper. Analysis for **{st.session_state.url}** is available. How can I assist you further?"
            )
        else:
            username = st.session_state.get("username", "User")
            target_welcome_message_seo = language_manager.get_text(
                "welcome_authenticated", 
                lang,
                username,
                fallback=f"Welcome, {username}! Enter a URL to analyze or ask an SEO question."
            )

        # Initialize or update messages
        if "messages" not in st.session_state or not st.session_state.messages:
            st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_seo}]
        elif (st.session_state.messages and 
              st.session_state.messages[0].get("role") == "assistant" and
              st.session_state.messages[0].get("content") != target_welcome_message_seo):
            st.session_state.messages[0]["content"] = target_welcome_message_seo
        
        check_auth()
        
        # Show analysis progress if applicable
        if (st.session_state.get("analysis_in_progress") and 
            st.session_state.get("url_being_analyzed")):
            st.info(language_manager.get_text(
                "analysis_in_progress_for", 
                lang, 
                st.session_state.url_being_analyzed
            ))

        # --- SEO Suggestions Section ---
        if "selected_pages_for_seo_suggestions" not in st.session_state:
            st.session_state.selected_pages_for_seo_suggestions = []

        llm_analysis_available = (
            st.session_state.get("full_report") and
            isinstance(st.session_state.full_report, dict) and
            st.session_state.full_report.get("llm_analysis_all") and
            isinstance(st.session_state.full_report["llm_analysis_all"], dict) and
            st.session_state.full_report["llm_analysis_all"]
        )

        text_report_available = bool(st.session_state.get("text_report"))

        # Show SEO suggestions section if we have analysis data
        if llm_analysis_available or text_report_available:
            st.sidebar.subheader(language_manager.get_text(
                "seo_suggestions_for_pages_label", 
                lang, 
                fallback="SEO Suggestions:"
            ))
            
            if llm_analysis_available:
                # Show page selection when detailed analysis is available
                sorted_page_keys = get_available_pages()
                
                if sorted_page_keys:
                    current_selection = st.session_state.get("selected_pages_for_seo_suggestions", [])
                    if not current_selection and "main_page" in sorted_page_keys:
                        current_selection = ["main_page"]

                    selected_pages = st.sidebar.multiselect(
                        label=language_manager.get_text(
                            "select_pages_for_detailed_suggestions", 
                            lang, 
                            fallback="Select pages (leave empty for general suggestions):"
                        ),
                        options=sorted_page_keys,
                        default=current_selection,
                        key="multiselect_seo_suggestion_pages", 
                        help=language_manager.get_text(
                            "multiselect_seo_help_text_v3", 
                            lang, 
                            fallback="Select specific pages for focused suggestions. If empty, general suggestions will be generated from the text report. 'main_page' contains the homepage analysis."
                        )
                    )
                    st.session_state.selected_pages_for_seo_suggestions = selected_pages
                else:
                    st.sidebar.warning("No pages available in the analysis data.")
            else:
                # Only text report available - show info message
                st.sidebar.info(language_manager.get_text(
                    "text_report_suggestions_only", 
                    lang, 
                    fallback="Detailed page analysis not available. General suggestions will be generated from the text report."
                ))

            # SEO Suggestions Button
            if st.sidebar.button(language_manager.get_text(
                "generate_seo_suggestions_button_text", 
                lang, 
                fallback="Generate SEO Suggestions"
            )):
                handle_seo_suggestions_generation(lang)

        elif st.session_state.get("authenticated"):
            st.sidebar.info(language_manager.get_text(
                "analyze_url_first_for_suggestions", 
                lang, 
                fallback="Analyze a URL to enable SEO suggestions."
            ))

        # --- Main Content Area ---
        username = st.session_state.get("username", "User")
        st.markdown(language_manager.get_text("logged_in_as", lang, username))
        common_sidebar()
        
        # Display chat messages
        if st.session_state.get("messages"):
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input
        placeholder_text = language_manager.get_text("enter_url_or_question_seo_helper", lang)
        if prompt := st.chat_input(placeholder_text):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            if main_process_url is None:
                st.error("URL processing functionality is not available due to an import error.")
            else:
                # Check API keys before processing
                has_mistral = bool(st.session_state.get("MISTRAL_API_KEY"))
                has_gemini = bool(st.session_state.get("GEMINI_API_KEY"))
                
                if not has_mistral and not has_gemini:
                    error_msg = "No AI API keys configured. Please check your configuration."
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
        logging.error(f"Error in main_seo_helper: {str(e)}")
        st.error(f"An unexpected error occurred. Please refresh the page and try again.")

if __name__ == "__main__":
    asyncio.run(main_seo_helper())