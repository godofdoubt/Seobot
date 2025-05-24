#SeoTree/pages/1_SEO_Helper.py
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
from dotenv import load_dotenv
from supabase import create_client, Client # Keep Client if used directly, else remove
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history
from utils.language_support import language_manager
from helpers.seo_main_helper8 import process_chat_input
from buttons.generate_seo_suggestions import generate_seo_suggestions # Corrected import

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
    if not st.session_state.authenticated:
        lang = st.session_state.get("language", "en")
        st.warning(language_manager.get_text("authentication_required", lang))
        if st.button(language_manager.get_text("go_to_login", lang)):
            st.switch_page("main.py")
        st.stop()

async def main_seo_helper():
    init_shared_session_state()
    
    if "language" not in st.session_state:
        st.session_state.language = "en"
    lang = st.session_state.language
    
    st.title(language_manager.get_text("seo_helper_button", lang))
    
    if st.session_state.current_page != "seo":
        update_page_history("seo")
    
    lang = st.session_state.language
    target_welcome_message_seo = ""
    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message_seo = language_manager.get_text(
            "welcome_seo_helper_analyzed",
            lang,
            st.session_state.url,
            fallback=f"Welcome to the SEO Helper. Analysis for **{st.session_state.url}** is available. How can I assist you further?"
        )
    else:
        target_welcome_message_seo = language_manager.get_text(
            "welcome_authenticated", 
            lang,
            st.session_state.username,
            fallback=f"Welcome, {st.session_state.username}! Enter a URL to analyze or ask an SEO question."
        )

    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_seo}]
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
        if st.session_state.messages[0].get("content") != target_welcome_message_seo:
            st.session_state.messages[0]["content"] = target_welcome_message_seo
    
    check_auth()
    
    if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
        st.info(language_manager.get_text("analysis_in_progress_for", lang, st.session_state.url_being_analyzed))

    # --- SEO Suggestions Button & Page Selection Logic ---
    if "selected_pages_for_seo_suggestions" not in st.session_state:
        st.session_state.selected_pages_for_seo_suggestions = []

    llm_analysis_available = (
        st.session_state.get("full_report") and
        isinstance(st.session_state.full_report, dict) and
        st.session_state.full_report.get("llm_analysis_all") and
        isinstance(st.session_state.full_report["llm_analysis_all"], dict) and
        st.session_state.full_report["llm_analysis_all"] # Ensure it's not empty (truthy, e.g. not {})
    )

    if llm_analysis_available:
        llm_data = st.session_state.full_report["llm_analysis_all"]
        available_page_keys = list(llm_data.keys())

        sorted_page_keys = []
        if "main_page" in available_page_keys:
            sorted_page_keys.append("main_page")
            for key in available_page_keys:
                if key != "main_page":
                    sorted_page_keys.append(key)
        else:
            sorted_page_keys = available_page_keys
        
        current_selection = st.session_state.selected_pages_for_seo_suggestions
        # Keep default selection logic if desired, or remove if "empty means text_report" is the primary default
        if not current_selection and "main_page" in sorted_page_keys:
             current_selection = ["main_page"] # Default to main_page if available and nothing selected
        # elif not current_selection and sorted_page_keys: 
        #     current_selection = [sorted_page_keys[0]] # Or first page

        st.sidebar.subheader(language_manager.get_text("seo_suggestions_for_pages_label", lang, fallback="SEO Suggestions:"))
        
        selected_pages = st.sidebar.multiselect(
            label=language_manager.get_text("select_pages_for_detailed_suggestions", lang, fallback="Select pages (or leave empty for general report suggestions):"),
            options=sorted_page_keys,
            default=current_selection,
            key="multiselect_seo_suggestion_pages", 
            help=language_manager.get_text("multiselect_seo_help_text_v2", lang, fallback="Select pages for detailed suggestions. If empty, suggestions use the general text report of the site. 'main_page' is often key for page-specific analysis.")
        )
        st.session_state.selected_pages_for_seo_suggestions = selected_pages


        if st.sidebar.button(language_manager.get_text("generate_seo_suggestions_button_text", lang, fallback="Generate SEO Suggestions")):
            
            user_selected_page_keys = st.session_state.selected_pages_for_seo_suggestions
            data_for_suggestions = None # Initialize

            if user_selected_page_keys:
                # User selected specific pages from llm_analysis_all
                valid_selected_keys = [
                    key for key in user_selected_page_keys if key in llm_data
                ]
                if valid_selected_keys:
                    data_for_suggestions = {
                        key: llm_data[key] 
                        for key in valid_selected_keys
                    }
                    # Optional: Add a type indicator if generate_seo_suggestions needs it
                    # data_for_suggestions["_source_type_"] = "detailed_pages" 
                else:
                    # User made selections, but none were valid keys in llm_data
                    st.sidebar.error(language_manager.get_text("error_selected_pages_no_valid_data", lang, fallback="Error: None of the selected pages have data available for suggestions."))
            
            else: # No pages selected by the user from the multiselect, default to text_report
                if st.session_state.get("text_report"):
                    # Prepare data_for_suggestions using the text_report.
                    # The structure should be something generate_seo_suggestions can differentiate.
                    data_for_suggestions = {
                        "_source_type_": "text_report",  # Key to indicate the source
                        "content": st.session_state.text_report
                    }
                    st.sidebar.info(language_manager.get_text("using_text_report_for_suggestions", lang, fallback="No specific pages selected. Generating suggestions based on the general text report."))
                else:
                    # No pages selected AND no text_report available (should be rare if URL was processed and llm_analysis_available is true)
                    st.sidebar.error(language_manager.get_text("error_no_pages_selected_no_text_report", lang, fallback="Error: No pages selected and no general text report available for suggestions."))

            if data_for_suggestions:
                with st.spinner(language_manager.get_text("processing_request", lang)):
                    # generate_seo_suggestions must now be able to handle the two forms of `data_for_suggestions`:
                    # 1. Dict of page analyses: { "page1": {...}, "page2": {...} }
                    # 2. Dict for text report: { "_source_type_": "text_report", "content": "..." }
                    suggestions = generate_seo_suggestions(pages_data_for_suggestions=data_for_suggestions)
                    
                    if not st.session_state.messages or st.session_state.messages[-1].get("content") != suggestions:
                        st.session_state.messages.append({"role": "assistant", "content": suggestions})
            # else: Error messages would have been displayed above.
    
    elif st.session_state.get("full_report") and st.session_state.get("url"): # llm_analysis_all not available or empty
        st.sidebar.info(language_manager.get_text("detailed_analysis_not_ready_for_suggestions", lang, 
                                                  fallback="Detailed page analysis (llm_analysis_all) not yet available or empty. Ensure full site analysis has completed and yielded results. General suggestions might be possible via chat if a text report exists."))
    else: # No full_report or URL
        if st.session_state.get("authenticated"):
            st.sidebar.text(language_manager.get_text("analyze_url_first_for_suggestions", lang, fallback="Analyze a URL to enable SEO suggestions."))
    # --- End SEO Suggestions Button & Page Selection Logic ---

    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    common_sidebar()
    
    if "messages" in st.session_state:
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
            await process_chat_input(
                prompt=prompt,
                process_url_from_main=lambda url, lang_code: main_process_url(url, lang_code),
                MISTRAL_API_KEY=st.session_state.MISTRAL_API_KEY,
                GEMINI_API_KEY=st.session_state.GEMINI_API_KEY,
                message_list="messages"
            )

if __name__ == "__main__":
    asyncio.run(main_seo_helper())