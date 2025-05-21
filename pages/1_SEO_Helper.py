#SeoTree/pages/1_SEO_Helper.py
import streamlit as st

# --- Streamlit Page Configuration ---
# This MUST be the first Streamlit command in the script
st.set_page_config(
    page_title="SEO Helper",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history
from utils.language_support import language_manager
from helpers.seo_main_helper8 import process_chat_input

# --- Import process_url from main.py ---
try:
    from main import process_url as main_process_url
except ImportError:
    st.error("Failed to import process_url from main.py. Ensure main.py is in the correct path.")
    # Fallback or stop execution if essential
    main_process_url = None

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def check_auth():
    """Check if user is authenticated"""
    if not st.session_state.authenticated:
        lang = st.session_state.get("language", "en")
        st.warning(language_manager.get_text("authentication_required", lang))
        if st.button(language_manager.get_text("go_to_login", lang)): # Added a button to go to main
            st.switch_page("main.py")
        st.stop()

async def main_seo_helper(): # Renamed to avoid conflict if main.py's main is imported
    init_shared_session_state()
    
    if "language" not in st.session_state:
        st.session_state.language = "en"
    lang = st.session_state.language
    
    st.title(language_manager.get_text("seo_helper_button", lang))
    
    if st.session_state.current_page != "seo":
        update_page_history("seo")
    
    check_auth() # Authentication check
    # Add after checking authentication but before displaying the chat interface
    if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
        st.info(language_manager.get_text("analysis_in_progress_for", lang, st.session_state.url_being_analyzed))
    
    # Optional: Add a refresh button to check analysis progress
    if st.button(language_manager.get_text("refresh_analysis_status", lang)):
        st.rerun()  # Simple refresh to check status
    # Sidebar button for SEO suggestions
    if st.session_state.get("full_report") and st.session_state.get("url"): # Use .get for safety
        from buttons.generate_seo_suggestions import generate_seo_suggestions
        
        if st.sidebar.button(language_manager.get_text("generate_seo_suggestions", lang)):
            with st.spinner(language_manager.get_text("processing_request", lang)): # Consistent spinner text
                # generate_seo_suggestions expects the full_report dictionary
                suggestions = generate_seo_suggestions(st.session_state.full_report)
                with st.chat_message("assistant"):
                    st.markdown(suggestions)
                # Add to messages only if it's a new suggestion
                if not st.session_state.messages or st.session_state.messages[-1].get("content") != suggestions:
                    st.session_state.messages.append({"role": "assistant", "content": suggestions})
    
    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    
    key_welcome_default = "welcome_authenticated" # Assuming this is a generic welcome
    key_welcome_analyzed = "welcome_seo_helper_analyzed"

    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message = language_manager.get_text(key_welcome_analyzed, lang, st.session_state.url)
    else:
        target_welcome_message = language_manager.get_text(key_welcome_default, lang, st.session_state.username)

    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message}]
    else:
        first_message = st.session_state.messages[0]
        if first_message.get("role") == "assistant":
            # Only update if the content is different and it's one of the known welcome messages
            # This prevents overwriting an initial "Report for URL X" message if `main_process_url` adds it.
            known_welcomes = [
                language_manager.get_text(key_welcome_default, lang, st.session_state.username),
                # If an analysis was just run, the welcome might be different, let `main_process_url` handle initial message
            ]
            if first_message.get("content") in known_welcomes and first_message.get("content") != target_welcome_message:
                 st.session_state.messages[0]["content"] = target_welcome_message

    common_sidebar()
    
    if "messages" in st.session_state:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    placeholder_text = language_manager.get_text("enter_url_or_question_seo_helper", lang) # More specific placeholder
    if prompt := st.chat_input(placeholder_text):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        if main_process_url is None:
            st.error("URL processing functionality is not available due to an import error.")
        else:
            await process_chat_input(
                prompt=prompt,
                process_url_from_main=lambda url, lang_code: main_process_url(url, lang_code), # Pass the imported function
                MISTRAL_API_KEY=st.session_state.MISTRAL_API_KEY,
                GEMINI_API_KEY=st.session_state.GEMINI_API_KEY,
                message_list="messages"
            )

if __name__ == "__main__":
    asyncio.run(main_seo_helper())