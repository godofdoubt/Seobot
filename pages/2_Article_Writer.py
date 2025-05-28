#/pages/2_Article_Writer.py
import streamlit as st
import asyncio
import os
import logging 
from dotenv import load_dotenv
from supabase import create_client, Client
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history, load_saved_report
from utils.language_support import language_manager

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

st.set_page_config(
    page_title="Article Writer Beta",
    page_icon="✍️",
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

def check_auth():
    lang = st.session_state.language if "language" in st.session_state else "en"
    if not st.session_state.authenticated:
        st.warning(language_manager.get_text("authentication_required", lang))
        
        if st.button(language_manager.get_text("go_to_login", lang)): 
            st.switch_page("main.py")
        st.stop()

async def main():
    init_shared_session_state()
    lang = st.session_state.language if "language" in st.session_state else "en"

    if "article_generation_requested" not in st.session_state:
        st.session_state.article_generation_requested = False

    # --- START: Check for trigger from SEO Helper (for pre-filling options if generation failed/skipped there) ---
    is_triggered_by_seo_helper = False
    task_title_from_trigger = None
    if st.session_state.get("trigger_article_suggestion_from_seo_helper", False):
        logging.info("Article Writer: Triggered by SEO Helper for option pre-fill / generation.")
        is_triggered_by_seo_helper = True
        task_details = st.session_state.get("article_suggestion_to_trigger_details") 

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
            logging.warning("Article Writer: Triggered by SEO Helper, but task_details are missing or invalid. Resetting trigger.")
            is_triggered_by_seo_helper = False 

        st.session_state.trigger_article_suggestion_from_seo_helper = False
        st.session_state.article_suggestion_to_trigger_details = None
    # --- END: Check for trigger from SEO Helper (for pre-filling options) ---
    
    st.title(language_manager.get_text("article_writer_button", lang))

    if st.session_state.current_page != "article":
        update_page_history("article") 
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    check_auth()

    # --- Welcome Message Logic ---
    final_welcome_message = ""
    if is_triggered_by_seo_helper and task_title_from_trigger and st.session_state.article_generation_requested:
        final_welcome_message = language_manager.get_text(
            "article_writer_activated_by_seo_helper", lang, task_title=task_title_from_trigger, #Ensure task_title kwarg
            fallback=f"Article Writer activated by SEO Helper for: **{task_title_from_trigger}**. Generating article..."
        )
    elif is_triggered_by_seo_helper and task_title_from_trigger and not st.session_state.article_generation_requested:
         final_welcome_message = language_manager.get_text(
            "article_writer_options_prefilled_by_seo_helper", lang, task_title=task_title_from_trigger, #Ensure task_title kwarg
            fallback=f"Article Writer options pre-filled by SEO Helper for: **{task_title_from_trigger}**. Review and click 'Generate Article'."
        )
    else:
        if st.session_state.get("url") and st.session_state.get("text_report"):
            final_welcome_message = language_manager.get_text(
                "welcome_article_writer_analyzed", lang, url=st.session_state.url, #Ensure url kwarg
                fallback=f"Welcome to the Article Writer page.\nUsing analysis for: **{st.session_state.url}**"
            )
        else:
            final_welcome_message = language_manager.get_text(
                "welcome_article_writer_not_analyzed", lang,
                fallback="Welcome to the Article Writer page. Please analyze a website in the SEO Helper page first to proceed."
            )

    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": final_welcome_message}]
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
        # Only update the first message if it's an old generic welcome, or if a specific trigger provides a new welcome
        current_first_message = st.session_state.messages[0].get("content", "")
        is_generic_welcome_candidate = any(kw in current_first_message.lower() for kw in ["welcome to the article writer", "welcome back"])
        
        if (is_triggered_by_seo_helper and current_first_message != final_welcome_message) or \
           (not is_triggered_by_seo_helper and is_generic_welcome_candidate and current_first_message != final_welcome_message):
             st.session_state.messages[0]["content"] = final_welcome_message
    # --- END Welcome Message Logic ---

    # --- START: Process newly generated article from SEO Helper for display ---
    message_added_from_seo_helper_signal = False
    if st.session_state.get("display_newly_generated_article_on_aw"):
        article_details = st.session_state.display_newly_generated_article_on_aw
        title = article_details.get("title", "Generated Article")
        content = article_details.get("content", "No content.")
        
        article_display_message_content = f"**{language_manager.get_text('generated_article_from_seo_helper_title', lang, title=title, fallback=f'Generated Article (from SEO Helper): {title}')}**\n\n{content}"
        
        is_already_displayed = False
        if st.session_state.get("messages") and st.session_state.messages[-1].get("role") == "assistant" and \
           st.session_state.messages[-1].get("content") == article_display_message_content:
            is_already_displayed = True

        if not is_already_displayed:
            if "messages" not in st.session_state: # Should be initialized by welcome logic, but defensive
                 st.session_state.messages = []
            st.session_state.messages.append({"role": "assistant", "content": article_display_message_content})
            logging.info(f"Article Writer: Appended newly generated article from SEO Helper to messages: {title}")
            message_added_from_seo_helper_signal = True
        else:
            logging.info(f"Article Writer: Newly generated article from SEO Helper already displayed or last message matches: {title}")
        
        st.session_state.display_newly_generated_article_on_aw = None 
        if message_added_from_seo_helper_signal:
            st.rerun()
    # --- END: Process newly generated article from SEO Helper for display ---

    # --- Automated Article Suggestion Tasks Display ---
    # (This section remains largely the same as it's for *new* selections)
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
                
                task_data = {} 
                required_keys = ["focus_keyword", "content_length", "article_tone", "additional_keywords", "suggested_title"]
                for r_key in required_keys:
                    task_data[r_key] = task.get(r_key, "N/A (Key Missing)" if r_key != "additional_keywords" else [])

                task_title_display = task_data.get('suggested_title', 'Untitled Suggestion')
                if not task_title_display or task_title_display == "N/A (Key Missing)": task_title_display = f'Suggestion {i+1}'


                with st.expander(f"{language_manager.get_text('suggestion_task_label', lang, fallback='Suggestion')} {i+1}: {task_title_display}",
                                 expanded=(st.session_state.selected_auto_suggestion_task_index == i)):
                    st.markdown(f"**{language_manager.get_text('focus_keyword_label', lang, fallback='Focus Keyword')}:** {task_data.get('focus_keyword', 'N/A')}")
                    st.markdown(f"**{language_manager.get_text('content_length_label', lang, fallback='Content Length')}:** {task_data.get('content_length', 'N/A')}")
                    st.markdown(f"**{language_manager.get_text('article_tone_label', lang, fallback='Article Tone')}:** {task_data.get('article_tone', 'N/A')}")
                    
                    add_keywords_val_display = task_data.get('additional_keywords', [])
                    if isinstance(add_keywords_val_display, list):
                        add_keywords_val_display = ", ".join(add_keywords_val_display) if add_keywords_val_display else "None"
                    elif not add_keywords_val_display: 
                        add_keywords_val_display = "None"
                    st.markdown(f"**{language_manager.get_text('additional_keywords_label', lang, fallback='Additional Keywords')}:** {add_keywords_val_display}")
                    st.markdown(f"**{language_manager.get_text('suggested_title_label', lang, fallback='Suggested Title')}:** {task_data.get('suggested_title', 'N/A')}")

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
    # --- END Automated Article Suggestion Tasks ---

    # --- Right Sidebar for Article Options ---
    if st.session_state.get("full_report") and st.session_state.get("url"): 
        with st.sidebar:
            st.markdown(f"### {language_manager.get_text('article_options_title', lang)}")
            if "article_options" not in st.session_state or not isinstance(st.session_state.article_options, dict):
                st.session_state.article_options = {"content_length": "Medium", "tone": "Professional", "keywords": "", "custom_title": "", "focus_keyword": ""}
            
            st.session_state.article_options["focus_keyword"] = st.text_input(
                label=language_manager.get_text("focus_keyword", lang, fallback="Focus Keyword"),
                value=st.session_state.article_options.get("focus_keyword", ""),
                help=language_manager.get_text("focus_keyword_help", lang, fallback="The main keyword your article will focus on")
            )
            
            content_length_keys = ["content_length_short", "content_length_medium", "content_length_long", "content_length_very_long"]
            content_length_display_options = [language_manager.get_text(key, lang) for key in content_length_keys]
            internal_to_display_map_length = {
                "Short": language_manager.get_text("content_length_short", lang),
                "Medium": language_manager.get_text("content_length_medium", lang),
                "Long": language_manager.get_text("content_length_long", lang),
                "Very Long": language_manager.get_text("content_length_very_long", lang),
            }
            current_length_internal = st.session_state.article_options.get("content_length", "Medium")
            current_display_value_length = internal_to_display_map_length.get(current_length_internal, content_length_display_options[1]) 
            try:
                current_index_length = content_length_display_options.index(current_display_value_length)
            except ValueError:
                 logging.warning(f"Article Writer: Content length '{current_display_value_length}' (internal: '{current_length_internal}') not in display options. Defaulting index.")
                 current_index_length = 1 

            selected_length_display = st.selectbox(
                label=language_manager.get_text("content_length", lang, fallback="Content Length"),
                options=content_length_display_options,
                index=current_index_length
            )
            display_to_internal_map_length = {v: k for k, v in internal_to_display_map_length.items()}
            st.session_state.article_options["content_length"] = display_to_internal_map_length.get(selected_length_display, "Medium")

            tone_keys = ["tone_professional", "tone_casual", "tone_enthusiastic", "tone_technical", "tone_friendly"]
            tone_display_options = [language_manager.get_text(key, lang) for key in tone_keys]
            internal_to_display_map_tone = {
                "Professional": language_manager.get_text("tone_professional", lang),
                "Casual": language_manager.get_text("tone_casual", lang),
                "Enthusiastic": language_manager.get_text("tone_enthusiastic", lang),
                "Technical": language_manager.get_text("tone_technical", lang),
                "Friendly": language_manager.get_text("tone_friendly", lang),
            }
            current_tone_internal = st.session_state.article_options.get("tone", "Professional")
            current_display_value_tone = internal_to_display_map_tone.get(current_tone_internal, tone_display_options[0]) 
            try:
                current_index_tone = tone_display_options.index(current_display_value_tone)
            except ValueError:
                 logging.warning(f"Article Writer: Tone '{current_display_value_tone}' (internal: '{current_tone_internal}') not in display options. Defaulting index.")
                 current_index_tone = 0 

            selected_tone_display = st.selectbox(
                label=language_manager.get_text("tone", lang, fallback="Article Tone"),
                options=tone_display_options,
                index=current_index_tone
            )
            display_to_internal_map_tone = {v: k for k, v in internal_to_display_map_tone.items()}
            st.session_state.article_options["tone"] = display_to_internal_map_tone.get(selected_tone_display, "Professional")

            st.session_state.article_options["keywords"] = st.text_area(
                label=language_manager.get_text("custom_keywords", lang, fallback="Additional Keywords (optional)"),
                value=st.session_state.article_options.get("keywords", ""),
                help=language_manager.get_text("custom_keywords_help", lang, fallback="Enter keywords separated by commas"),
                height=100
            )
            st.session_state.article_options["custom_title"] = st.text_input(
                label=language_manager.get_text("custom_title", lang, fallback="Custom Title (optional)"),
                value=st.session_state.article_options.get("custom_title", "")
            )

            from buttons.generate_article import generate_article 
            if st.sidebar.button(language_manager.get_text("generate_article", lang, fallback="Generate Article")):
                st.session_state.article_generation_requested = True
        
        if st.session_state.article_generation_requested:
            options = st.session_state.get("article_options", {})
            if not options.get("focus_keyword") or options.get("focus_keyword") == "N/A (Key Missing)":
                st.warning(language_manager.get_text("focus_keyword_required_warning", lang, fallback="Focus Keyword is required to generate an article. Please fill it in the sidebar."))
                st.session_state.article_generation_requested = False
                # Removed st.rerun() here to prevent loop if focus keyword is missing and trigger was active
            else:
                with st.spinner(language_manager.get_text("generating_article", lang, fallback="Generating article...")):
                    current_article_options = st.session_state.get("article_options", {})
                    article = generate_article(
                        st.session_state.text_report, 
                        st.session_state.url,
                        current_article_options
                    )
                    # Ensure messages list exists before appending
                    if "messages" not in st.session_state:
                        st.session_state.messages = []
                    st.session_state.messages.append({"role": "assistant", "content": article})
                    st.session_state.article_generation_requested = False 
                st.rerun() 
    
    st.markdown(language_manager.get_text("logged_in_as", lang, username=st.session_state.username)) #Ensure username kwarg
    if "messages" in st.session_state and st.session_state.messages: # Check if messages is not empty
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    if not st.session_state.get("text_report"):
        st.warning(language_manager.get_text("analyze_website_first", lang, fallback="Please analyze a website first in the SEO Helper page."))
        if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_redirect_article"):
            update_page_history("seo") # This should be the page name, not 'article' here
            st.switch_page("pages/1_SEO_Helper.py")

    if prompt := st.chat_input(language_manager.get_text("article_prompt", lang, fallback="What kind of article would you like to write?")):
        if "messages" not in st.session_state: st.session_state.messages = [] # Defensive
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        if not st.session_state.get("text_report"):
            with st.chat_message("assistant"):
                response = language_manager.get_text("analyze_website_first_chat", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with article writing.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            from helpers.article_main_helper import process_chat_input
            await process_chat_input(
                prompt,
                MISTRAL_API_KEY=st.session_state.get("MISTRAL_API_KEY"),
                GEMINI_API_KEY=st.session_state.get("GEMINI_API_KEY"),
                message_list="messages"
            )
            st.rerun() 

    common_sidebar()

if __name__ == "__main__":
    asyncio.run(main())