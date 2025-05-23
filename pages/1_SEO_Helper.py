#SeoTree/pages/1_SEO_Helper.py
import streamlit as st

# --- Streamlit Page Configuration ---
# This MUST be the first Streamlit command in the script
st.set_page_config(
    page_title="SEO Helper",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="auto"
)
# Hide Streamlit's default "/pages" sidebar nav
hide_pages_nav = """
<style>
  /* hides the page navigation menu in the sidebar */
  div[data-testid="stSidebarNav"] { 
    display: none !important; 
  }
</style>
"""
st.markdown(hide_pages_nav, unsafe_allow_html=True)

import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
# Ensure update_page_history is imported
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
    
    # Set current page to seo and update history
    if st.session_state.current_page != "seo":
        update_page_history("seo") # This will set the welcome message or restore history
     # --- START: Update for SEO Helper Welcome Message ---
    # This logic ensures the correct welcome message for the SEO Helper page,
    # especially after a URL is processed within this page or navigating with existing analysis.
    # It mirrors the fix implemented in 2_Article_Writer.py
    lang = st.session_state.language # Ensure lang is current
    
    target_welcome_message_seo = ""
    if st.session_state.get("url") and st.session_state.get("text_report"):
        # Uses the language key "welcome_seo_helper_analyzed" from shared_functions
        target_welcome_message_seo = language_manager.get_text(
            "welcome_seo_helper_analyzed",
            lang,
            st.session_state.url, # Pass URL as an argument
            fallback=f"Welcome to the SEO Helper. Analysis for **{st.session_state.url}** is available. How can I assist you further?"
        )
    else:
        # Uses the language key "welcome_authenticated" from shared_functions
        target_welcome_message_seo = language_manager.get_text(
            "welcome_authenticated", 
            lang,
            st.session_state.username, # Pass username
            fallback=f"Welcome, {st.session_state.username}! Enter a URL to analyze or ask an SEO question."
        )

    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_seo}]
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
        # Update the first message if it's an assistant message and not the current target welcome message.
        if st.session_state.messages[0].get("content") != target_welcome_message_seo:
            st.session_state.messages[0]["content"] = target_welcome_message_seo
    # --- END: Update for SEO Helper Welcome Message ---    
    
    check_auth() # Authentication check
    # Add after checking authentication but before displaying the chat interface
    if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
        st.info(language_manager.get_text("analysis_in_progress_for", lang, st.session_state.url_being_analyzed))

    
    # Optional: Add a refresh button to check analysis progress
    #if st.button(language_manager.get_text("refresh_analysis_status", lang)):
     #   st.rerun()  # Simple refresh to check status
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
    
    # --- Welcome Message Logic (Removed, now handled by update_page_history) ---
    # Removed the block that looked like this:
    # key_welcome_default = "welcome_authenticated" # Assuming this is a generic welcome
    # key_welcome_analyzed = "welcome_seo_helper_analyzed"
    # if st.session_state.get("url") and st.session_state.get("text_report"): ...
    # if not st.session_state.messages: ...
    # --- End Welcome Message Logic ---

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