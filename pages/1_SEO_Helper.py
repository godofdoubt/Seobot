

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
        st.session_state.full_report["llm_analysis_all"] # Ensure it's not empty
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
        if not current_selection and "main_page" in sorted_page_keys:
            current_selection = ["main_page"]
        elif not current_selection and sorted_page_keys: 
            current_selection = [sorted_page_keys[0]]


        st.sidebar.subheader(language_manager.get_text("seo_suggestions_for_pages_label", lang, fallback="SEO Suggestions for Pages:"))
        
        selected_pages = st.sidebar.multiselect(
            label=language_manager.get_text("select_pages_for_seo_suggestions", lang, fallback="Select pages for analysis:"),
            options=sorted_page_keys,
            default=current_selection,
            key="multiselect_seo_suggestion_pages", 
            help="Select pages from the detailed analysis to generate SEO suggestions for. 'main_page' is often essential."
        )
        st.session_state.selected_pages_for_seo_suggestions = selected_pages


        if st.sidebar.button(language_manager.get_text("generate_seo_suggestions_button_text", lang, fallback="Generate SEO Suggestions for Selected Pages")):
            if not st.session_state.selected_pages_for_seo_suggestions: 
                st.sidebar.warning(language_manager.get_text("select_at_least_one_page_warning", lang, fallback="Please select at least one page."))
            else:
                data_for_suggestions = {
                    key: llm_data[key] 
                    for key in st.session_state.selected_pages_for_seo_suggestions
                    if key in llm_data
                }
                
                if not data_for_suggestions:
                     st.sidebar.error(language_manager.get_text("error_preparing_data_no_valid_pages", lang, fallback="Error: No valid page data for selected items."))
                else:
                    with st.spinner(language_manager.get_text("processing_request", lang)):
                        suggestions = generate_seo_suggestions(pages_data_for_suggestions=data_for_suggestions)
                        # MODIFIED SECTION:
                        # Remove direct display:
                        # with st.chat_message("assistant"):
                        #     st.markdown(suggestions)
                        
                        # Only append to session state. The main message loop will render it.
                        # The condition prevents adding the same message repeatedly if this block runs multiple times.
                        if not st.session_state.messages or st.session_state.messages[-1].get("content") != suggestions:
                            st.session_state.messages.append({"role": "assistant", "content": suggestions})
                        # A rerun is implicitly triggered by the button click, so the main message loop will pick this up.
    
    elif st.session_state.get("full_report") and st.session_state.get("url"):
        st.sidebar.info(language_manager.get_text("detailed_analysis_not_ready_for_suggestions", lang, 
                                                  fallback="Detailed page analysis (llm_analysis_all) not yet available or empty. Ensure full site analysis has completed and yielded results."))
    else:
        if st.session_state.get("authenticated"):
            st.sidebar.text(language_manager.get_text("analyze_url_first_for_suggestions", lang, fallback="Analyze a URL to enable SEO suggestions."))
    # --- End SEO Suggestions Button & Page Selection Logic ---

    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    common_sidebar()
    
    # This loop will now correctly render the suggestions once.
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
