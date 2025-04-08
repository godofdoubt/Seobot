#/pages/2_Article_Writer.py
import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history, load_saved_report
from utils.language_support import language_manager

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Article Writer Beta",
    page_icon=":robot_face:",
    layout="wide",
    initial_sidebar_state="expanded"
)

def check_auth():
    """Check if user is authenticated"""
    lang = st.session_state.language if "language" in st.session_state else "en"
    if not st.session_state.authenticated:
        st.warning(language_manager.get_text("authentication_required", lang))
        st.stop()

async def main():
    # Initialize shared session state
    init_shared_session_state()
    
    # Initialize article generation flag if not present
    if "article_generation_requested" not in st.session_state:
        st.session_state.article_generation_requested = False
    
    # Get current language
    lang = st.session_state.language if "language" in st.session_state else "en"
    
    st.title(language_manager.get_text("article_writer_button", lang))

    
    
    # Set current page to article
    if st.session_state.current_page != "article":
        update_page_history("article")
    
    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Check if user is authenticated
    check_auth()


    # --- Welcome Message Logic ---
    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message = language_manager.get_text("welcome_article_writer_analyzed", lang, st.session_state.url)
    else:
        target_welcome_message = language_manager.get_text("welcome_article_writer_not_analyzed", lang)
    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message}]
    else:
        first_message = st.session_state.messages[0]
        if first_message.get("role") == "assistant" and first_message.get("content") != target_welcome_message:
            st.session_state.messages[0]["content"] = target_welcome_message
    # --- End Welcome Message Logic ---

    # --- New Right Sidebar for Article Options ---
    if st.session_state.full_report and st.session_state.url:
        with st.sidebar:
            st.markdown(f"### {language_manager.get_text('article_options_title', lang)}")
    
            # Initialize article options in session state if not present
            if "article_options" not in st.session_state:
                st.session_state.article_options = {
                    "content_length": "Medium",
                    "tone": "Professional",
                    "keywords": "",
                    "custom_title": "",
                    "focus_keyword": ""
                }
            # Add focus keyword input (new feature)
            st.session_state.article_options["focus_keyword"] = st.text_input(
                label=language_manager.get_text("focus_keyword", lang, fallback="Focus Keyword"),
                value=st.session_state.article_options.get("focus_keyword", ""),
                # Use the new help key
                help=language_manager.get_text("focus_keyword_help", lang, fallback="The main keyword your article will focus on")
            )
    
            # --- Dynamic Content Length Options ---
            content_length_keys = ["content_length_short", "content_length_medium", "content_length_long", "content_length_very_long"]
            content_length_display_options = [language_manager.get_text(key, lang) for key in content_length_keys]
            # Map internal values (English) to display options for finding the index
            internal_to_display_map_length = {
                "Short": language_manager.get_text("content_length_short", lang),
                "Medium": language_manager.get_text("content_length_medium", lang),
                "Long": language_manager.get_text("content_length_long", lang),
                "Very Long": language_manager.get_text("content_length_very_long", lang),
            }
            # Find the index based on the *current* display language's option corresponding to the stored English value
            current_display_value_length = internal_to_display_map_length.get(st.session_state.article_options["content_length"], content_length_display_options[1]) # Default to medium if mapping fails
            try:
                current_index_length = content_length_display_options.index(current_display_value_length)
            except ValueError:
                 current_index_length = 1 # Default index if value not found

            selected_length_display = st.selectbox(
                label=language_manager.get_text("content_length", lang, fallback="Content Length"),
                options=content_length_display_options,
                index=current_index_length
            )
            # Find the internal English key corresponding to the selected display option
            display_to_internal_map_length = {v: k for k, v in internal_to_display_map_length.items()}
            st.session_state.article_options["content_length"] = display_to_internal_map_length.get(selected_length_display, "Medium") # Store the English key


            # --- Dynamic Tone Options ---
            tone_keys = ["tone_professional", "tone_casual", "tone_enthusiastic", "tone_technical", "tone_friendly"]
            tone_display_options = [language_manager.get_text(key, lang) for key in tone_keys]
            internal_to_display_map_tone = {
                "Professional": language_manager.get_text("tone_professional", lang),
                "Casual": language_manager.get_text("tone_casual", lang),
                "Enthusiastic": language_manager.get_text("tone_enthusiastic", lang),
                "Technical": language_manager.get_text("tone_technical", lang),
                "Friendly": language_manager.get_text("tone_friendly", lang),
            }
            current_display_value_tone = internal_to_display_map_tone.get(st.session_state.article_options["tone"], tone_display_options[0]) # Default to professional
            try:
                current_index_tone = tone_display_options.index(current_display_value_tone)
            except ValueError:
                 current_index_tone = 0 # Default index

            selected_tone_display = st.selectbox(
                label=language_manager.get_text("tone", lang, fallback="Article Tone"),
                options=tone_display_options,
                index=current_index_tone
            )
            display_to_internal_map_tone = {v: k for k, v in internal_to_display_map_tone.items()}
            st.session_state.article_options["tone"] = display_to_internal_map_tone.get(selected_tone_display, "Professional") # Store the English key


            # Custom keywords (using new help key)
            st.session_state.article_options["keywords"] = st.text_area(
                label=language_manager.get_text("custom_keywords", lang, fallback="Additional Keywords (optional)"),
                value=st.session_state.article_options["keywords"],
                 # Use the new help key
                help=language_manager.get_text("custom_keywords_help", lang, fallback="Enter keywords separated by commas"),
                height=100
            )
    
            # Custom title
            st.session_state.article_options["custom_title"] = st.text_input(
                label=language_manager.get_text("custom_title", lang, fallback="Custom Title (optional)"),
                value=st.session_state.article_options["custom_title"]
            )

        # Add Article Writer-specific button to sidebar
    
            from buttons.generate_article import generate_article
        
        # Handle button click to set the request flag
        if st.sidebar.button(language_manager.get_text("generate_article", lang, fallback="Generate Article")):
            st.session_state.article_generation_requested = True
            st.rerun()  # Rerun to process the flag

        # Handle article generation if requested
        if st.session_state.article_generation_requested:
            with st.spinner(language_manager.get_text("generating_article", lang, fallback="Generating article...")):
                article = generate_article(
                    st.session_state.text_report, 
                    st.session_state.url,
                    st.session_state.article_options
                )
                # Add the article to session state messages
                st.session_state.messages.append({"role": "assistant", "content": article})
                # Reset the flag
                st.session_state.article_generation_requested = False
    
    # Display username
    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    


    
    
    # Display chat messages from shared session state
    if "messages" in st.session_state:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Add a check for SEO data
    if not st.session_state.text_report:
        st.warning(language_manager.get_text("analyze_website_first", lang, fallback="Please analyze a website first in the SEO Helper page."))
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button"):
                update_page_history("seo")
                st.switch_page("pages/1_SEO_Helper.py")

    # Handle chat input
    if prompt := st.chat_input(language_manager.get_text("article_prompt", lang, fallback="What kind of article would you like to write?")):
        # Add user message to shared session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Check if URL has been analyzed
        if not st.session_state.text_report:
            with st.chat_message("assistant"):
                response = language_manager.get_text("analyze_website_first_chat", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with article writing.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            # Process the input using the enhanced article_main_helper that supports both models
            from helpers.article_main_helper import process_chat_input
            
            # Process with available API keys
            await process_chat_input(
                prompt,
                MISTRAL_API_KEY=st.session_state.MISTRAL_API_KEY,
                GEMINI_API_KEY=st.session_state.GEMINI_API_KEY,
                message_list="messages"  # Use shared messages list
            )

    # Display sidebar - using the common sidebar that already includes model selection
    common_sidebar()

if __name__ == "__main__":
    asyncio.run(main())