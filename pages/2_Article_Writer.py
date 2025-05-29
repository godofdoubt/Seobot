#pages/2_Article_Writer.py
import streamlit as st
import asyncio
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history
from utils.language_support import language_manager
# Make sure these imports are correct and the files exist
from buttons.generate_article import generate_article
from helpers.article_main_helper import process_chat_input

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Streamlit Page Configuration
st.set_page_config(
    page_title="Article Writer - Se10 AI",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="auto"
)
# Hide Streamlit's default "/pages" sidebar nav
hide_pages_nav = """
<style>
  div[data-testid="stSidebarNav"] {
    display: none !important;
  }
</style>
"""
st.markdown(hide_pages_nav, unsafe_allow_html=True)

def check_auth():
    """Check if user is authenticated"""
    lang = st.session_state.language if "language" in st.session_state else "en"
    if not st.session_state.authenticated:
        st.warning(language_manager.get_text("authentication_required", lang))
        if st.button(language_manager.get_text("go_to_login", lang)):
            st.switch_page("main.py")
        st.stop()

def render_article_writer_sidebar_options():
    """Renders article-specific options in the sidebar, matching the original file's keys."""
    lang = st.session_state.language

    if st.session_state.get("full_report") and st.session_state.get("url"):
        st.sidebar.markdown(f"### {language_manager.get_text('article_options_title', lang, fallback='Article Options')}")

        if "article_options" not in st.session_state or not isinstance(st.session_state.article_options, dict):
            st.session_state.article_options = {
                "focus_keyword": "",
                "content_length": "Medium",
                "tone": "Professional",
                "keywords": "", # Additional keywords
                "custom_title": ""
            }

        st.session_state.article_options["focus_keyword"] = st.sidebar.text_input(
            label=language_manager.get_text("focus_keyword", lang, fallback="Focus Keyword"),
            value=st.session_state.article_options.get("focus_keyword", ""),
            help=language_manager.get_text("focus_keyword_help", lang, fallback="The main keyword your article will focus on")
        )

        content_length_internal_options = ["Short", "Medium", "Long", "Very Long"]
        content_length_display_options_map = {
            "Short": language_manager.get_text("content_length_short", lang, fallback="Short"),
            "Medium": language_manager.get_text("content_length_medium", lang, fallback="Medium"),
            "Long": language_manager.get_text("content_length_long", lang, fallback="Long"),
            "Very Long": language_manager.get_text("content_length_very_long", lang, fallback="Very Long"),
        }
        current_length_internal = st.session_state.article_options.get("content_length", "Medium")
        if current_length_internal not in content_length_internal_options:
            current_length_internal = "Medium"
            st.session_state.article_options["content_length"] = "Medium"

        selected_length_display = st.sidebar.selectbox(
            label=language_manager.get_text("content_length", lang, fallback="Content Length"),
            options=[content_length_display_options_map[opt] for opt in content_length_internal_options],
            index=content_length_internal_options.index(current_length_internal)
        )
        st.session_state.article_options["content_length"] = [
            k for k, v in content_length_display_options_map.items() if v == selected_length_display
        ][0]

        tone_internal_options = ["Professional", "Casual", "Enthusiastic", "Technical", "Friendly"]
        tone_display_options_map = {
            "Professional": language_manager.get_text("tone_professional", lang, fallback="Professional"),
            "Casual": language_manager.get_text("tone_casual", lang, fallback="Casual"),
            "Enthusiastic": language_manager.get_text("tone_enthusiastic", lang, fallback="Enthusiastic"),
            "Technical": language_manager.get_text("tone_technical", lang, fallback="Technical"),
            "Friendly": language_manager.get_text("tone_friendly", lang, fallback="Friendly"),
        }
        current_tone_internal = st.session_state.article_options.get("tone", "Professional")
        if current_tone_internal not in tone_internal_options:
            current_tone_internal = "Professional"
            st.session_state.article_options["tone"] = "Professional"

        selected_tone_display = st.sidebar.selectbox(
            label=language_manager.get_text("tone", lang, fallback="Article Tone"),
            options=[tone_display_options_map[opt] for opt in tone_internal_options],
            index=tone_internal_options.index(current_tone_internal)
        )
        st.session_state.article_options["tone"] = [
            k for k, v in tone_display_options_map.items() if v == selected_tone_display
        ][0]

        st.session_state.article_options["keywords"] = st.sidebar.text_area(
            label=language_manager.get_text("custom_keywords", lang, fallback="Additional Keywords (optional)"),
            value=st.session_state.article_options.get("keywords", ""),
            help=language_manager.get_text("custom_keywords_help", lang, fallback="Enter keywords separated by commas"),
            height=100
        )
        st.session_state.article_options["custom_title"] = st.sidebar.text_input(
            label=language_manager.get_text("custom_title", lang, fallback="Custom Title (optional)"),
            value=st.session_state.article_options.get("custom_title", "")
        )

        if st.sidebar.button(language_manager.get_text("generate_article", lang, fallback="Generate Article")):
            if not st.session_state.article_options.get("focus_keyword","").strip():
                st.sidebar.warning(language_manager.get_text("focus_keyword_required_warning", lang, fallback="Focus Keyword is required to generate an article."))
            else:
                st.session_state.article_generation_requested = True
    # else:
    #     st.sidebar.info(language_manager.get_text("analyze_site_for_article_options", lang,
    #     fallback="Analyze a site in SEO Helper to see article options."))


async def main():
    init_shared_session_state()
    lang = st.session_state.language

    if "article_generation_requested" not in st.session_state:
        st.session_state.article_generation_requested = False

    is_triggered_by_seo_helper = False
    task_title_from_trigger = None
    if st.session_state.get("trigger_article_suggestion_from_seo_helper", False):
        logging.info("Article Writer: Triggered by SEO Helper for option pre-fill / generation.")
        is_triggered_by_seo_helper = True
        # Pop the trigger details to ensure they are processed once for pre-filling
        task_details = st.session_state.pop("article_suggestion_to_trigger_details", None)
        st.session_state.trigger_article_suggestion_from_seo_helper = False # Clear trigger

        if task_details and isinstance(task_details, dict):
            if "article_options" not in st.session_state or not isinstance(st.session_state.article_options, dict):
                st.session_state.article_options = {}

            task_title_from_trigger = task_details.get('suggested_title', 'the selected article topic')
            st.session_state.article_options["focus_keyword"] = task_details.get("focus_keyword", "")

            valid_lengths = ["Short", "Medium", "Long", "Very Long"]
            task_length_val = task_details.get("content_length")
            st.session_state.article_options["content_length"] = task_length_val if task_length_val in valid_lengths else "Medium"
            if task_length_val not in valid_lengths and task_length_val != "N/A (Key Missing)": logging.warning(f"AW - SEO Helper Trigger: Invalid content length '{task_length_val}'. Defaulting to Medium.")

            valid_tones = ["Professional", "Casual", "Enthusiastic", "Technical", "Friendly"]
            task_tone_val = task_details.get("article_tone")
            st.session_state.article_options["tone"] = task_tone_val if task_tone_val in valid_tones else "Professional"
            if task_tone_val not in valid_tones and task_tone_val != "N/A (Key Missing)": logging.warning(f"AW - SEO Helper Trigger: Invalid tone '{task_tone_val}'. Defaulting to Professional.")

            additional_kws_val = task_details.get("additional_keywords", [])
            st.session_state.article_options["keywords"] = ", ".join(additional_kws_val) if isinstance(additional_kws_val, list) else (str(additional_kws_val) if additional_kws_val else "")
            st.session_state.article_options["custom_title"] = task_details.get("suggested_title", "")

            if st.session_state.article_options["focus_keyword"]:
                st.session_state.article_generation_requested = True
                logging.info(f"Article Writer: Options populated from SEO Helper: {st.session_state.article_options}. Article generation requested.")
            else:
                logging.warning("Article Writer: Triggered by SEO Helper, but focus_keyword is missing. Article generation not auto-requested.")
        else:
            logging.warning("Article Writer: Triggered by SEO Helper, but task_details are missing or invalid.")
            is_triggered_by_seo_helper = False # Reset as trigger was invalid
        
        # Ensure these are cleared if they were set by older logic, though pop should handle article_suggestion_to_trigger_details
        # st.session_state.trigger_article_suggestion_from_seo_helper = False # Already done above
        # st.session_state.article_suggestion_to_trigger_details = None # Already popped

    st.title(language_manager.get_text("article_writer_button", lang, fallback="Article Writer"))

    if st.session_state.current_page != "article":
        update_page_history("article")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    check_auth()

    common_sidebar(page_specific_content_func=render_article_writer_sidebar_options)

    final_welcome_message = ""
    if is_triggered_by_seo_helper and task_title_from_trigger and st.session_state.article_generation_requested:
        final_welcome_message = language_manager.get_text(
            "article_writer_activated_by_seo_helper", lang, task_title=task_title_from_trigger,
            fallback=f"Article Writer activated by SEO Helper for: **{task_title_from_trigger}**. Generating article..."
        )
    elif is_triggered_by_seo_helper and task_title_from_trigger and not st.session_state.article_generation_requested:
         final_welcome_message = language_manager.get_text(
            "article_writer_options_prefilled_by_seo_helper", lang, task_title=task_title_from_trigger,
            fallback=f"Article Writer options pre-filled by SEO Helper for: **{task_title_from_trigger}**. Review and click 'Generate Article'."
        )
    else:
        if st.session_state.get("url") and st.session_state.get("text_report"):
            final_welcome_message = language_manager.get_text(
                "welcome_article_writer_analyzed", lang, st.session_state.url,
                fallback=f"Welcome to the Article Writer page. Ready to help you write an article based on the analysis of **{st.session_state.url}**."
            )
        else:
            final_welcome_message = language_manager.get_text(
                "welcome_article_writer_not_analyzed", lang,
                fallback="Welcome to the Article Writer page. Please analyze a website in the SEO Helper page first to proceed."
            )

    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": final_welcome_message}]
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
        current_first_message = st.session_state.messages[0].get("content", "")
        is_generic_welcome_candidate = any(kw in current_first_message.lower() for kw in ["welcome to the article writer", "welcome back"])

        if (is_triggered_by_seo_helper and current_first_message != final_welcome_message) or \
           (not is_triggered_by_seo_helper and is_generic_welcome_candidate and current_first_message != final_welcome_message):
             st.session_state.messages[0]["content"] = final_welcome_message

    # --- MODIFIED BLOCK START: Process list/item(s) of articles from SEO Helper ---
    articles_processed_in_this_run = False
    articles_to_add_to_chat = []
    processed_article_titles_this_run = set() # To help de-duplicate within this run

    # 1. Process the primary state: articles_pending_display_on_aw (list of dicts)
    # Use pop to get and remove the data, ensuring it's processed once.
    pending_articles_data = st.session_state.pop("articles_pending_display_on_aw", None) 

    if pending_articles_data:
        # Ensure pending_articles_data is treated as a list
        if not isinstance(pending_articles_data, list):
            logging.warning(f"Article Writer: 'articles_pending_display_on_aw' was not a list (type: {type(pending_articles_data)}). Wrapping in a list. Data: {str(pending_articles_data)[:200]}")
            pending_articles_data = [pending_articles_data]

        logging.info(f"Article Writer: Processing {len(pending_articles_data)} item(s) from 'articles_pending_display_on_aw' state.")
        for article_details in pending_articles_data:
            if isinstance(article_details, dict) and "title" in article_details and "content" in article_details:
                articles_to_add_to_chat.append(article_details)
                processed_article_titles_this_run.add(article_details.get("title"))
            else:
                logging.warning(f"Article Writer: Skipping invalid article_details from 'articles_pending_display_on_aw' source: {article_details}")
    
    # 2. For backward compatibility/transition: Check the old single-item state `display_newly_generated_article_on_aw`
    # This is if seo_main_helper8.py is still setting this old variable.
    legacy_article_data = st.session_state.pop("display_newly_generated_article_on_aw", None)
    if legacy_article_data:
        if isinstance(legacy_article_data, dict) and "title" in legacy_article_data and "content" in legacy_article_data:
            legacy_article_title = legacy_article_data.get("title")
            # Add if not already processed from the primary list (basic title check for de-duplication)
            if legacy_article_title not in processed_article_titles_this_run:
                logging.info(f"Article Writer: Found and adding article from legacy state 'display_newly_generated_article_on_aw': {legacy_article_title}.")
                articles_to_add_to_chat.append(legacy_article_data)
                processed_article_titles_this_run.add(legacy_article_title) # Add to set for this run
            else:
                logging.info(f"Article Writer: Article from legacy state '{legacy_article_title}' was already processed from 'articles_pending_display_on_aw' or is a duplicate. Skipping.")
        else:
             logging.warning(f"Article Writer: Invalid data found and cleared from legacy state 'display_newly_generated_article_on_aw': {legacy_article_data}")

    if articles_to_add_to_chat:
        if "messages" not in st.session_state: # Ensure messages list exists
            st.session_state.messages = []

        for i, article_details in enumerate(articles_to_add_to_chat):
            title = article_details.get("title", f"Generated Article {i+1}") # Fallback title
            content = article_details.get("content", "No content.")
            article_display_message_content = f"**{language_manager.get_text('generated_article_from_seo_helper_title', lang, title=title, fallback=f'Generated Article (from SEO Helper): {title}')}**\n\n{content}"
            
            # Basic check to prevent adding the exact same message if it's already the last one.
            # This is a simple safeguard against immediate rerun loops if pop() wasn't perfectly timed with reruns.
            is_already_last_message = False
            if st.session_state.messages and \
               st.session_state.messages[-1].get("role") == "assistant" and \
               st.session_state.messages[-1].get("content") == article_display_message_content:
                is_already_last_message = True
            
            if not is_already_last_message:
                st.session_state.messages.append({"role": "assistant", "content": article_display_message_content})
                logging.info(f"Article Writer: Appended article '{title}' (from SEO Helper transfer) to messages. Total messages: {len(st.session_state.messages)}")
                articles_processed_in_this_run = True
            else:
                logging.info(f"Article Writer: Article '{title}' (from SEO Helper transfer) appears to be a duplicate of the last message. Skipping append.")
                
    if articles_processed_in_this_run: # If any new articles were actually added to chat
        st.rerun() 
    # --- MODIFIED BLOCK END ---


    display_suggestions_condition = (
        st.session_state.get("url") and
        st.session_state.get("text_report") and
        st.session_state.get("auto_suggestions_data") and
        st.session_state.get("current_report_url_for_suggestions") == st.session_state.get("url")
    )

    if display_suggestions_condition:
        auto_suggestions = st.session_state.auto_suggestions_data
        article_tasks = []
        if auto_suggestions and isinstance(auto_suggestions, dict) and \
           "content_creation_ideas" in auto_suggestions and \
           isinstance(auto_suggestions.get("content_creation_ideas"), dict) and \
           "article_content_tasks" in auto_suggestions.get("content_creation_ideas", {}) and \
           isinstance(auto_suggestions.get("content_creation_ideas", {}).get("article_content_tasks"), list):
            article_tasks = auto_suggestions["content_creation_ideas"]["article_content_tasks"]

        if article_tasks:
            st.subheader(language_manager.get_text("suggested_article_tasks_title", lang, fallback="Suggested Article Tasks"))
            st.markdown(language_manager.get_text("suggested_article_tasks_intro", lang, fallback="We found some article suggestions based on the SEO analysis. Select one to pre-fill the article options:"))

            if "last_url_for_suggestion_selection" not in st.session_state or \
               st.session_state.last_url_for_suggestion_selection != st.session_state.url:
                st.session_state.selected_auto_suggestion_task_index = None
                st.session_state.last_url_for_suggestion_selection = st.session_state.url

            for i, task in enumerate(article_tasks):
                if not isinstance(task, dict):
                    logging.warning(f"Article Writer: Skipping non-dict article task at index {i}: {task}")
                    continue

                # task_data is used for populating sidebar options, keep it as is
                task_data = {}
                required_keys_for_sidebar = ["focus_keyword", "content_length", "article_tone", "additional_keywords", "suggested_title"]
                for r_key in required_keys_for_sidebar:
                    task_data[r_key] = task.get(r_key, "N/A (Key Missing)" if r_key != "additional_keywords" else [])

                task_title_display = task_data.get('suggested_title', 'Untitled Suggestion')
                if not task_title_display or task_title_display == "N/A (Key Missing)": task_title_display = f'Suggestion {i+1}'

                with st.expander(f"{language_manager.get_text('suggestion_task_label', lang, fallback='Suggestion')} {i+1}: {task_title_display}",
                                 expanded=(st.session_state.selected_auto_suggestion_task_index == i)):
                    st.markdown(f"**{language_manager.get_text('suggested_title_label', lang, fallback='Suggested Title')}:** {task_data.get('suggested_title', 'N/A')}")
                    st.markdown(f"**{language_manager.get_text('focus_keyword_label', lang, fallback='Focus Keyword')}:** {task_data.get('focus_keyword', 'N/A')}")
                    st.markdown(f"**{language_manager.get_text('content_length_label', lang, fallback='Content Length')}:** {task_data.get('content_length', 'N/A')}")
                    
                    # Display tone using the mapped display name if possible
                    tone_internal_options_display = ["Professional", "Casual", "Enthusiastic", "Technical", "Friendly"] # Used for matching
                    tone_display_map_expander = {
                        "Professional": language_manager.get_text("tone_professional", lang, fallback="Professional"),
                        "Casual": language_manager.get_text("tone_casual", lang, fallback="Casual"),
                        "Enthusiastic": language_manager.get_text("tone_enthusiastic", lang, fallback="Enthusiastic"),
                        "Technical": language_manager.get_text("tone_technical", lang, fallback="Technical"),
                        "Friendly": language_manager.get_text("tone_friendly", lang, fallback="Friendly"),
                    }
                    task_tone_val_expander = task_data.get('article_tone', 'N/A')
                    display_tone = tone_display_map_expander.get(task_tone_val_expander, task_tone_val_expander)
                    st.markdown(f"**{language_manager.get_text('article_tone_label', lang, fallback='Article Tone')}:** {display_tone}")


                    add_keywords_val_display = task_data.get('additional_keywords', [])
                    if isinstance(add_keywords_val_display, list):
                        add_keywords_val_display = ", ".join(add_keywords_val_display) if add_keywords_val_display else "None"
                    elif not add_keywords_val_display: # Handle "N/A (Key Missing)" or other non-list but empty values
                        add_keywords_val_display = "None"
                    st.markdown(f"**{language_manager.get_text('additional_keywords_label', lang, fallback='Additional Keywords')}:** {add_keywords_val_display}")

                    # --- MODIFICATION START: Display additional fields ---
                    target_page_url_val = task.get('target_page_url')
                    if target_page_url_val: # Only display if not None or empty
                        st.markdown(f"**{language_manager.get_text('target_page_url_label', lang, fallback='Target Page URL')}:** {target_page_url_val}")

                    content_gap_val = task.get('content_gap')
                    if content_gap_val:
                        st.markdown(f"**{language_manager.get_text('content_gap_label', lang, fallback='Content Gap')}:** {content_gap_val}")
                    
                    target_audience_val = task.get('target_audience')
                    if target_audience_val:
                        st.markdown(f"**{language_manager.get_text('target_audience_label', lang, fallback='Target Audience')}:** {target_audience_val}")

                    outline_preview_val = task.get('outline_preview')
                    if outline_preview_val:
                        st.markdown(f"**{language_manager.get_text('outline_preview_label', lang, fallback='Outline Preview')}:**")
                        # Using blockquote style for potentially longer/multi-line outline
                        st.markdown(f"> {str(outline_preview_val).replace(chr(10), chr(10) + '> ')}")
                    # --- MODIFICATION END ---

                    if st.button(language_manager.get_text("use_this_suggestion_button", lang, fallback="Use This Suggestion"), key=f"use_suggestion_{i}"):
                        if "article_options" not in st.session_state: st.session_state.article_options = {}
                        st.session_state.article_options["focus_keyword"] = task_data.get("focus_keyword", "")

                        valid_lengths = ["Short", "Medium", "Long", "Very Long"]
                        task_length_val = task_data.get("content_length")
                        st.session_state.article_options["content_length"] = task_length_val if task_length_val in valid_lengths else "Medium"
                        if task_length_val not in valid_lengths and task_length_val != "N/A (Key Missing)": st.warning(f"Invalid content length '{task_length_val}' in suggestion. Defaulting to Medium.")

                        valid_tones = ["Professional", "Casual", "Enthusiastic", "Technical", "Friendly"]
                        task_tone_val = task_data.get("article_tone")
                        st.session_state.article_options["tone"] = task_tone_val if task_tone_val in valid_tones else "Professional"
                        if task_tone_val not in valid_tones and task_tone_val != "N/A (Key Missing)": st.warning(f"Invalid article tone '{task_tone_val}' in suggestion. Defaulting to Professional.")

                        additional_kws_val = task_data.get("additional_keywords", [])
                        st.session_state.article_options["keywords"] = ", ".join(additional_kws_val) if isinstance(additional_kws_val, list) else (str(additional_kws_val) if additional_kws_val and additional_kws_val != "N/A (Key Missing)" else "")
                        st.session_state.article_options["custom_title"] = task_data.get("suggested_title", "")
                        st.session_state.selected_auto_suggestion_task_index = i

                        if st.session_state.article_options["focus_keyword"] and st.session_state.article_options["focus_keyword"] != "N/A (Key Missing)":
                            st.session_state.article_generation_requested = True
                        else:
                            st.warning(language_manager.get_text("focus_keyword_required_for_auto_gen", lang, fallback="Focus keyword is missing in this suggestion. Please provide one in the sidebar to generate."))
                        st.rerun()
            st.divider()
        elif display_suggestions_condition:
            st.info(language_manager.get_text("no_article_suggestions_found", lang, fallback="No specific article suggestions found in the current report's auto_suggestions data, or the data format is unrecognized."))

    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))

    if "messages" in st.session_state and st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if st.session_state.article_generation_requested:
        options = st.session_state.get("article_options", {})
        if not options.get("focus_keyword") or options.get("focus_keyword") == "N/A (Key Missing)":
            st.warning(language_manager.get_text("focus_keyword_required_warning", lang, fallback="Focus Keyword is required to generate an article. Please fill it in the sidebar."))
            st.session_state.article_generation_requested = False # Reset flag
        elif not st.session_state.get("text_report"):
            st.warning(language_manager.get_text("article_generation_prerequisites_warning", lang, fallback="Cannot generate article. Ensure a site is analyzed and topic is provided in the sidebar."))
            st.session_state.article_generation_requested = False # Reset flag
        else:
            with st.spinner(language_manager.get_text("generating_article", lang, fallback="Generating article... This may take a moment.")):
                try:
                    current_article_options = st.session_state.get("article_options", {})
                    article_content = generate_article(
                        st.session_state.text_report,
                        st.session_state.url,
                        current_article_options
                    )
                    if "messages" not in st.session_state: # Should exist, but defensive
                        st.session_state.messages = []
                    st.session_state.messages.append({"role": "assistant", "content": article_content})
                except Exception as e:
                    logging.error(f"Error generating article: {e}", exc_info=True)
                    error_msg_text = language_manager.get_text('error_processing_request', lang, error=str(e), fallback=f"An error occurred: {str(e)}")
                    st.error(error_msg_text)
                    if "messages" not in st.session_state: st.session_state.messages = [] # Defensive
                    st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text('could_not_generate_article', lang, fallback="Sorry, I couldn't generate the article at this time.")})

            st.session_state.article_generation_requested = False # Reset flag after attempt
            st.rerun() # Rerun to display the new article or error

    if not st.session_state.get("text_report"):
        st.warning(language_manager.get_text("analyze_website_first_article", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with article writing."))
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(language_manager.get_text("seo_helper_button", lang, fallback="SEO Helper"), key="seo_helper_button_redirect_article"):
                update_page_history("seo")
                st.switch_page("pages/1_SEO_Helper.py")

    if prompt := st.chat_input(language_manager.get_text("article_writer_prompt", lang, fallback="What kind of article would you like to write?")):
        if "messages" not in st.session_state: st.session_state.messages = []
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not st.session_state.get("text_report"):
            with st.chat_message("assistant"):
                response = language_manager.get_text("analyze_website_first_chat_article", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with article writing.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            await process_chat_input(
                prompt,
                MISTRAL_API_KEY=st.session_state.get("MISTRAL_API_KEY"),
                GEMINI_API_KEY=st.session_state.get("GEMINI_API_KEY"),
                message_list="messages"
            )
        st.rerun()

if __name__ == "__main__":
    asyncio.run(main())