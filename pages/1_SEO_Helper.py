#SeoTree/pages/1_SEO_Helper.py
import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history, analyze_website, load_saved_report
from utils.language_support import language_manager

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="SEO Helper",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def display_report_and_services(text_report, full_report, url):
    """Display SEO report and update session state"""
    st.session_state.text_report = text_report
    st.session_state.full_report = full_report
    st.session_state.url = url
    st.session_state.analysis_complete = True
    
    # Get the current language
    lang = st.session_state.get("language", "en")
    
    # Add assistant message to shared message history with proper translation
    assistant_message = language_manager.get_text("seo_analysis_completed", lang, url)
    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
    
    with st.chat_message("assistant"):
        st.markdown(assistant_message)
    # Force a rerun to update the sidebar
    st.rerun()    


def check_auth():
    """Check if user is authenticated"""
    if not st.session_state.authenticated:
        lang = st.session_state.get("language", "en")
        st.warning(language_manager.get_text("authentication_required", lang))
        st.stop()

async def main():
    # Initialize shared session state
    init_shared_session_state()
    
    # Initialize language if not set
    if "language" not in st.session_state:
        st.session_state.language = "en"
    
    # Get current language
    lang = st.session_state.language
    
    st.title(language_manager.get_text("seo_helper_button", lang))
    
    # Set current page to SEO
    if st.session_state.current_page != "seo":
        update_page_history("seo")
    
    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Check if user is authenticated
    check_auth()
    
    # Add language selector to sidebar
    languages = language_manager.get_available_languages()
    language_names = {"en": "English", "tr": "Türkçe"}
    
    # Add SEO-specific button to sidebar
    if st.session_state.full_report and st.session_state.url:
        from buttons.generate_seo_suggestions import generate_seo_suggestions
        
        if st.sidebar.button(language_manager.get_text("generate_seo_suggestions", lang)):
            with st.spinner(language_manager.get_text("analyzing_website", lang)):
                suggestions = generate_seo_suggestions(st.session_state.full_report)
                with st.chat_message("assistant"):
                    st.markdown(suggestions)
                    st.session_state.messages.append({"role": "assistant", "content": suggestions})
    
    # Display username
    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    
 # --- Refined Welcome Message Logic ---

    # Define the keys for the welcome messages
    key_welcome_default = "welcome_authenticated"
    key_welcome_analyzed = "welcome_seo_helper_analyzed" # Ensure this key exists in language_support.py

    # 1. Determine the target welcome message for the current state
    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message = language_manager.get_text(key_welcome_analyzed, lang, st.session_state.url)
    else:
        target_welcome_message = language_manager.get_text(key_welcome_default, lang, st.session_state.username)

    # 2. Ensure the welcome message is correctly set at the top, avoiding duplicates
    if "messages" not in st.session_state or not st.session_state.messages:
        # 3. If no messages exist, initialize the list with the welcome message
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message}]
    else:
        # 4. If messages exist, check the first message
        first_message = st.session_state.messages[0]
        if first_message.get("role") == "assistant":
            # 5. If the first message is from the assistant, ensure its content is up-to-date
            if first_message.get("content") != target_welcome_message:
                 # Only update if the determined message is different from the current one
                 st.session_state.messages[0]["content"] = target_welcome_message
                 # No rerun needed here, the display loop below will catch the change
        # else:
            # 6. If the first message is not from the assistant (e.g., user), do nothing.
            # Let the chat history flow naturally.
            pass

    # --- End of Refined Welcome Message Logic ---

    
    # Display sidebar
    common_sidebar()
    
    # Display chat messages from shared session state
    if "messages" in st.session_state:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Handle chat input
    placeholder_text = language_manager.get_text("enter_url", lang)
    if prompt := st.chat_input(placeholder_text):
        # Add user message to shared session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process the input using updated process_chat_input function
        from helpers.seo_main_helper8 import process_chat_input
        
        await process_chat_input(
            prompt=prompt,
            analyze_website=lambda url: analyze_website(url, supabase),
            load_saved_report=lambda url: load_saved_report(url, supabase),
            display_report_and_services=display_report_and_services,
            MISTRAL_API_KEY=st.session_state.MISTRAL_API_KEY,
            GEMINI_API_KEY=st.session_state.GEMINI_API_KEY,
            message_list="messages"  # Use shared messages list
        )

if __name__ == "__main__":
    asyncio.run(main())