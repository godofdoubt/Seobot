#Seobot/pages/1_SEO_Helper.py
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
import logging
import json 
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from urllib.parse import urlparse
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history
from utils.language_support import language_manager
# Import new utility functions
from utils.seo_data_parser import parse_auto_suggestions, load_auto_suggestions_from_supabase, save_auto_suggestions_to_supabase
from helpers.seo_main_helper8 import process_chat_input
import re

# --- Import from new helper file ---
from utils.seo_helper_functions import (
    get_supabase_client,
    check_auth,
    get_available_pages,
    generate_seo_suggestions_with_fallback,
    get_content_creation_cta_text,
    _build_suggestions_display_text,
    handle_seo_suggestions_generation,
    format_product_details_for_seo_helper_display
)

# --- Import Google Search Scraper and Analyzer ---
from utils.GREV1 import GoogleSearchScraper
from utils.seo_analyzer import analyze_keyword_difficulty
from utils.GREV2 import CompetitorContentScraper # <-- NEW: Import for competitor analysis

# --- Import process_url from main.py ---
try:
    from main import process_url as main_process_url
except ImportError:
    st.error("Failed to import process_url from main.py. Ensure main.py is in the correct path.")
    main_process_url = None

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


async def perform_google_search(keyword, region='en'):
    """
    Perform Google search using GREV1 scraper and return formatted results.
    """
    try:
        scraper = GoogleSearchScraper(region=region)
        await scraper.search_google(keyword)
        
        # Format results for display
        results_text = f"## 🔍 Google Search Results for: '{keyword}' (Region: {region.upper()})\n\n"
        
        if scraper.ads:
            results_text += f"### 🎯 Advertisements ({len(scraper.ads)} found)\n"
            for ad in scraper.ads:
                results_text += f"- **{ad['title']}**\n"
                if ad.get('url'):
                    results_text += f"  - 🔗 `{ad['url']}`\n"
        else:
            results_text += "✔️ No advertisements found.\n\n"

        if scraper.results:
            results_text += f"\n### 📊 Organic Results ({len(scraper.results)} found)\n"
            for result in scraper.results:
                results_text += f"**{result['position']}. {result['title']}**\n"
                results_text += f"   - 🔗 `{result['url']}`\n"
                if result.get('description'):
                    desc = result['description'][:200] + "..." if len(result['description']) > 200 else result['description']
                    results_text += f"   - 📝 {desc}\n"
        else:
            results_text += "\n❌ No organic results found.\n\n"

        if scraper.people_also_searched:
            results_text += f"\n### 🔄 Related Searches\n"
            for term in scraper.people_also_searched:
                results_text += f"- {term}\n"
        else:
            results_text += "\n❌ No related searches found."
        
        st.session_state.last_google_search = {
            'keyword': keyword, 'region': region, 'timestamp': datetime.now().isoformat(),
            'ads': scraper.ads, 'results': scraper.results, 'related_searches': scraper.people_also_searched
        }
        return results_text
        
    except Exception as e:
        logging.error(f"Error performing Google search: {str(e)}")
        return f"❌ An error occurred during the Google search for '{keyword}':\n\n`{str(e)}`\n\nThis can happen if Google blocks the request. Please try again later or with a different keyword."


def detect_google_search_intent(prompt):
    """Detect if user wants to perform a Google search based on their input."""
    search_keywords = [
        'google search', 'search google', 'serp', 'search results',
        'check ranking', 'keyword research', 'competitor analysis',
        'search for', 'google for', 'what ranks for'
    ]
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in search_keywords)


def extract_search_keyword_from_prompt(prompt):
    """Extract the keyword to search for from user's prompt."""
    quoted_match = re.search(r'"([^"]+)"', prompt)
    if quoted_match:
        return quoted_match.group(1).strip()
    patterns = [
        r'search (?:for|google for|google)[:\s]+(.+)',
        r'serp (?:for|of)[:\s]+(.+)',
        r'keyword research (?:for|on)[:\s]+(.+)',
        r'what ranks for[:\s]+(.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


async def main_seo_helper():
    """Main function for SEO Helper page."""
    try:
        init_shared_session_state() 
        supabase_client = get_supabase_client() 
        
        if "language" not in st.session_state:
            st.session_state.language = "en"
        lang = st.session_state.language
        
        # --- NEW Session state for competitor analysis ---
        if "serp_competitors" not in st.session_state:
            st.session_state.serp_competitors = None
        if "last_serp_keyword" not in st.session_state:
            st.session_state.last_serp_keyword = None

        if "url_for_auto_suggestions" not in st.session_state:
            st.session_state.url_for_auto_suggestions = None
        if "auto_suggestions_generated_for_current_url" not in st.session_state:
            st.session_state.auto_suggestions_generated_for_current_url = False

        st.title(language_manager.get_text("seo_helper_button", lang))
        
        if st.session_state.get("current_page") != "seo":
            update_page_history("seo")
        
        if st.session_state.get("url") and st.session_state.get("text_report"):
            target_welcome_message_seo = language_manager.get_text("welcome_seo_helper_analyzed", lang, st.session_state.url, fallback=f"Welcome to the SEO Helper. Analysis for **{st.session_state.url}** is available. How can I assist you further?")
        else:
            username = st.session_state.get("username", "User")
            target_welcome_message_seo = language_manager.get_text("welcome_authenticated", lang, username, fallback=f"Welcome, {username}! Enter a URL to analyze, ask an SEO question, or request Google search results for keywords.")

        if "messages" not in st.session_state or not st.session_state.messages:
            st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_seo}]
        elif (st.session_state.messages and st.session_state.messages[0].get("role") == "assistant" and st.session_state.messages[0].get("content") != target_welcome_message_seo):
            if not st.session_state.get("awaiting_seo_helper_cta_response") and not st.session_state.get("paused_cta_context"): 
                 st.session_state.messages[0]["content"] = target_welcome_message_seo
        
        check_auth()
        user_id = st.session_state.get("user_id") 
        
        if (st.session_state.get("analysis_in_progress") and st.session_state.get("url_being_analyzed")):
            st.info(language_manager.get_text("analysis_in_progress_for", lang, st.session_state.url_being_analyzed))

        llm_analysis_available = (
            st.session_state.get("full_report") and
            isinstance(st.session_state.full_report, dict) and
            st.session_state.full_report.get("llm_analysis_all") and
            isinstance(st.session_state.full_report["llm_analysis_all"], dict) and
            st.session_state.full_report["llm_analysis_all"]
        )
        text_report_available = bool(st.session_state.get("text_report"))
        current_analyzed_url = st.session_state.get("url")

        if llm_analysis_available and text_report_available and current_analyzed_url:
            if (st.session_state.url_for_auto_suggestions != current_analyzed_url or 
                not st.session_state.auto_suggestions_generated_for_current_url):
                
                st.session_state.paused_cta_context = None
                st.session_state.awaiting_seo_helper_cta_response = False
                st.session_state.seo_helper_cta_context = None
                
                existing_suggestions_structured = None
                if st.session_state.get("current_report_url_for_suggestions") == current_analyzed_url:
                    potential_data = st.session_state.get("auto_suggestions_data")
                    if isinstance(potential_data, dict):
                        logging.info(f"SEO_Helper: Using pre-loaded dict 'auto_suggestions_data' from session for {current_analyzed_url}.")
                        existing_suggestions_structured = potential_data
                    elif isinstance(potential_data, str):
                        logging.info(f"SEO_Helper: 'auto_suggestions_data' from session is a string for {current_analyzed_url}. Parsing now.")
                        parsed_data = parse_auto_suggestions(potential_data)
                        if isinstance(parsed_data, dict) and not parsed_data.get("parsing_error_outer") and "content_creation_ideas" in parsed_data:
                            existing_suggestions_structured = parsed_data
                            st.session_state.auto_suggestions_data = parsed_data
                            logging.info(f"SEO_Helper: Successfully parsed string 'auto_suggestions_data' from session for {current_analyzed_url} and updated session.")
                        else:
                            logging.warning(f"SEO_Helper: Failed to parse string 'auto_suggestions_data' from session for {current_analyzed_url}. Will try DB load or generate new. Parsed result: {parsed_data}")
                            existing_suggestions_structured = None 
                    else: 
                        logging.info(f"SEO_Helper: 'auto_suggestions_data' in session for {current_analyzed_url} is None or unsuitable type ({type(potential_data)}).")
                        existing_suggestions_structured = None 

                if not existing_suggestions_structured:
                    logging.info(f"SEO_Helper: Not using session 'auto_suggestions_data'. Attempting to load from Supabase for {current_analyzed_url}.")
                    db_loaded_suggestions = load_auto_suggestions_from_supabase(current_analyzed_url, supabase_client, parse_auto_suggestions)
                    if db_loaded_suggestions: 
                        existing_suggestions_structured = db_loaded_suggestions
                        st.session_state.auto_suggestions_data = db_loaded_suggestions 
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url 
                        logging.info(f"SEO_Helper: Loaded 'auto_suggestions_data' from Supabase for {current_analyzed_url} and updated session.")

                suggestions_to_display_in_chat = None 
                current_auto_suggestions_data_for_cta = None
                
                if existing_suggestions_structured:
                    st.info(language_manager.get_text("loading_existing_suggestions", lang, fallback="Loading existing SEO suggestions from database..."))
                    current_auto_suggestions_data_for_cta = existing_suggestions_structured
                    suggestions_to_display_in_chat = _build_suggestions_display_text(
                        existing_suggestions_structured, 
                        lang, 
                        title_prefix="Loaded/Yüklendi",
                        is_loaded_suggestions=True
                    )
                    logging.info(f"SEO_Helper: Using existing suggestions (from session or DB) for {current_analyzed_url}")
                else: 
                    data_for_auto_suggestions = {"_source_type_": "text_report", "content": st.session_state.text_report}
                    auto_gen_message_placeholder = st.empty()
                    auto_gen_message_placeholder.info(language_manager.get_text("auto_generating_initial_suggestions", lang, fallback="Analysis complete. Automatically generating initial suggestions based on the text report..."))

                    suggestions_raw_new = None
                    with st.spinner(language_manager.get_text("auto_processing_initial_suggestions", lang, fallback="Auto-generating initial suggestions...")):
                        suggestions_raw_new = generate_seo_suggestions_with_fallback(pages_data_for_suggestions=data_for_auto_suggestions)
                    
                    auto_gen_message_placeholder.empty()

                    if suggestions_raw_new:
                        newly_structured_suggestions = parse_auto_suggestions(suggestions_raw_new)
                        current_auto_suggestions_data_for_cta = newly_structured_suggestions
                        save_success = save_auto_suggestions_to_supabase(current_analyzed_url, newly_structured_suggestions, supabase_client, user_id)
                        if save_success: logging.info(f"Auto suggestions saved to Supabase for URL: {current_analyzed_url}")
                        else: logging.warning(f"Failed to save auto suggestions to Supabase for URL: {current_analyzed_url}")
                        
                        suggestions_to_display_in_chat = _build_suggestions_display_text(
                            newly_structured_suggestions, 
                            lang, 
                            title_prefix="Auto-Generated",
                            is_loaded_suggestions=False
                        )
                        
                        st.session_state.auto_suggestions_data = newly_structured_suggestions
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url
                        logging.info(f"SEO_Helper: Set auto_suggestions_data from NEWLY generated for {current_analyzed_url}")
                    else:
                        suggestions_to_display_in_chat = language_manager.get_text("error_auto_suggestions_failed", lang, fallback="Unable to generate automatic suggestions. You can still request manual suggestions using the sidebar.")
                        st.session_state.auto_suggestions_data = None 
                        st.session_state.current_report_url_for_suggestions = current_analyzed_url 
                        logging.info(f"SEO_Helper: Set auto_suggestions_data to None (generation failed) for {current_analyzed_url}")
                
                if suggestions_to_display_in_chat and current_auto_suggestions_data_for_cta:
                    cta_text_if_any, cta_task_type, cta_tasks, cta_secondary_info = get_content_creation_cta_text(current_auto_suggestions_data_for_cta, lang)
                    if cta_text_if_any:
                        suggestions_to_display_in_chat += cta_text_if_any
                        st.session_state.awaiting_seo_helper_cta_response = True
                        st.session_state.seo_helper_cta_context = {
                            "type": cta_task_type,
                            "tasks": cta_tasks,
                            "current_task_index": 0,
                            "secondary_tasks_info": cta_secondary_info
                        }
                        logging.info(f"CTA activated after auto-suggestion. Primary: {cta_task_type}.")
                
                if suggestions_to_display_in_chat:
                    last_message_content = st.session_state.messages[-1]["content"] if st.session_state.messages else None
                    if last_message_content != suggestions_to_display_in_chat:
                        st.session_state.messages.append({"role": "assistant", "content": suggestions_to_display_in_chat})
                
                st.session_state.url_for_auto_suggestions = current_analyzed_url
                st.session_state.auto_suggestions_generated_for_current_url = True
                if (suggestions_to_display_in_chat and (not st.session_state.messages or last_message_content != suggestions_to_display_in_chat)) or \
                   (st.session_state.get("awaiting_seo_helper_cta_response") and 'cta_text_if_any' in locals() and cta_text_if_any):
                    st.rerun()

        if "selected_pages_for_seo_suggestions" not in st.session_state:
            st.session_state.selected_pages_for_seo_suggestions = []

        # --- Sidebar for SEO Suggestions ---
        if llm_analysis_available or text_report_available: 
            st.sidebar.subheader(language_manager.get_text("seo_suggestions_for_pages_label", lang, fallback="SEO Suggestions:"))
            if llm_analysis_available:
                sorted_page_keys = get_available_pages()
                if sorted_page_keys:
                    current_selection = st.session_state.get("selected_pages_for_seo_suggestions", [])
                    selected_pages = st.sidebar.multiselect(
                        label=language_manager.get_text("select_pages_for_detailed_suggestions", lang, fallback="Select pages (leave empty for general suggestions):"),
                        options=sorted_page_keys, default=current_selection, key="multiselect_seo_suggestion_pages", 
                        help=language_manager.get_text("multiselect_seo_help_text_v3", lang, fallback="Select specific pages for focused suggestions. If empty, general suggestions will be generated from the text report. 'main_page' contains the homepage analysis."))
                    st.session_state.selected_pages_for_seo_suggestions = selected_pages
                else:
                    st.sidebar.warning(language_manager.get_text("no_pages_in_analysis_data", lang, fallback="No pages available in the analysis data."))
            else:
                st.sidebar.info(language_manager.get_text("text_report_suggestions_only", lang, fallback="Detailed page analysis not available. General suggestions will be generated from the text report."))

            if st.sidebar.button(language_manager.get_text("generate_seo_suggestions_button_text", lang, fallback="Generate SEO Suggestions")):
                handle_seo_suggestions_generation(lang) 
        elif st.session_state.get("authenticated"): 
            st.sidebar.info(language_manager.get_text("analyze_url_first_for_suggestions", lang, fallback="Analyze a URL to enable SEO suggestions."))

        # --- Sidebar for Google Search Tool ---
        st.sidebar.subheader("🔍 Google Search Tool")
        
        region_options = {"International (English)": "en", "Turkey (Turkish)": "tr"}
        selected_region_display = st.sidebar.selectbox(
            "Select Search Region:",
            options=list(region_options.keys()),
            index=0,
            key="google_search_region"
        )
        selected_region = region_options[selected_region_display]
        
        search_keyword_input = st.sidebar.text_input(
            "Enter keyword to search:",
            placeholder="e.g., best pizza recipe",
            key="google_search_keyword",
            help="Enter a keyword for Google Search or SERP Analysis."
        )
        
        # --- Create columns for the two buttons ---
        col1, col2 = st.sidebar.columns(2)

        with col1:
            if st.button("🚀 Search", disabled=not search_keyword_input.strip(), help="Get Google search results including ads, organic results, and related searches."):
                if search_keyword_input.strip():
                    # Clear competitor list from previous SERP analysis to avoid confusion
                    st.session_state.serp_competitors = None
                    st.session_state.last_serp_keyword = None

                    with st.chat_message("user"):
                        st.markdown(f"Google search for: \"{search_keyword_input}\"")
                    st.session_state.messages.append({"role": "user", "content": f"Google search for: \"{search_keyword_input}\""})

                    with st.chat_message("assistant"):
                        with st.spinner("Searching Google... This may take a moment."):
                            search_results = await perform_google_search(search_keyword_input.strip(), selected_region)
                        st.markdown(search_results)
                    st.session_state.messages.append({"role": "assistant", "content": search_results})
                    st.rerun()

        with col2:
            # The SERP analysis button is disabled if no keyword is entered OR if no URL has been analyzed yet.
            serp_button_disabled = not search_keyword_input.strip() or not st.session_state.get("url")
            serp_help_text = "Analyze a URL first to enable SERP Analysis." if not st.session_state.get("url") else "Run a detailed SERP analysis for the keyword against your analyzed URL."
            
            if st.button("📊 SERP Analysis", disabled=serp_button_disabled, help=serp_help_text):
                user_url = st.session_state.get("url")
                keyword = search_keyword_input.strip()

                if user_url and keyword:
                    user_message_content = f"Run SERP Analysis for keyword \"{keyword}\" on my URL: `{user_url}`"
                    with st.chat_message("user"):
                        st.markdown(user_message_content)
                    st.session_state.messages.append({"role": "user", "content": user_message_content})

                    with st.chat_message("assistant"):
                        with st.spinner(f"Analyzing SERP for '{keyword}'... This may take a few moments."):
                            # UPDATED: Capture both report and competitor list
                            analysis_report, competitors_list = await analyze_keyword_difficulty(user_url, keyword, selected_region)
                            st.session_state.serp_competitors = competitors_list
                            st.session_state.last_serp_keyword = keyword
                        st.markdown(analysis_report)
                    st.session_state.messages.append({"role": "assistant", "content": analysis_report})
                    st.rerun()

        # --- NEW: Competitor Content Analysis Tool ---
        if st.session_state.get("serp_competitors"):
            st.sidebar.markdown("---")
            st.sidebar.subheader("🕵️‍♂️ Competitor Content Analysis")
            
            competitors = st.session_state.serp_competitors
            competitor_options = [f"{idx+1}. {comp['title'][:50]}..." for idx, comp in enumerate(competitors)]
            
            if competitor_options:
                selected_competitor_display = st.sidebar.selectbox(
                    "Choose a competitor to analyze:",
                    options=competitor_options,
                    index=0,
                    key="competitor_select",
                    help="Select a competitor from the list generated by the last SERP analysis."
                )
                
                selected_index = competitor_options.index(selected_competitor_display)
                selected_competitor_url = competitors[selected_index]['url']

                if st.sidebar.button("Analyze Competitor Content", key="analyze_competitor_content_btn"):
                    keyword_to_use = st.session_state.last_serp_keyword
                    
                    user_msg = f"Analyze content for competitor: `{selected_competitor_url}` with keyword: \"{keyword_to_use}\""
                    st.session_state.messages.append({"role": "user", "content": user_msg})
                    with st.chat_message("user"):
                        st.markdown(user_msg)

                    with st.chat_message("assistant"):
                        domain_name = urlparse(selected_competitor_url).netloc
                        with st.spinner(f"Analyzing content from {domain_name}..."):
                            scraper = CompetitorContentScraper(region=selected_region)
                            analysis_md = await scraper.analyze_competitor_content(keyword_to_use, selected_competitor_url)
                        st.markdown(analysis_md)
                    st.session_state.messages.append({"role": "assistant", "content": analysis_md})
                    st.rerun()
            else:
                st.sidebar.info("No direct competitors found in the last SERP analysis.")


        username_display = st.session_state.get("username", "User")
        st.markdown(language_manager.get_text("logged_in_as", lang, username=username_display))
        common_sidebar()    
        
        active_cta_context_display = st.session_state.get("seo_helper_cta_context")
        paused_cta_context_display = st.session_state.get("paused_cta_context")
        show_task_panel_display = False
        tasks_for_panel_display = None
        current_task_idx_panel_display = -1
        panel_status_message_display = ""
        is_paused_panel_display = False
        task_type_panel_display = None

        current_context_to_use = None
        if st.session_state.get("awaiting_seo_helper_cta_response") and active_cta_context_display:
            current_context_to_use = active_cta_context_display
        elif paused_cta_context_display:
            current_context_to_use = paused_cta_context_display
            is_paused_panel_display = True

        if current_context_to_use:
            task_type_panel_display = current_context_to_use.get("type")
            tasks_for_panel_display = current_context_to_use.get("tasks")
            current_task_idx_panel_display = current_context_to_use.get("current_task_index", 0)

            if tasks_for_panel_display and isinstance(tasks_for_panel_display, list) and 0 <= current_task_idx_panel_display < len(tasks_for_panel_display):
                current_task_item_display = tasks_for_panel_display[current_task_idx_panel_display]
                show_task_panel_display = True
                
                if task_type_panel_display == "article_writer":
                    task_title_for_status = current_task_item_display.get("suggested_title", f"task {current_task_idx_panel_display + 1}")
                    if is_paused_panel_display:
                        panel_status_message_display = language_manager.get_text("cta_status_paused_at", lang, title=task_title_for_status, fallback=f"Paused article task preparation at: '{task_title_for_status}'.")
                    else: 
                        panel_status_message_display = language_manager.get_text("cta_status_awaiting_response_for", lang, title=task_title_for_status, fallback=f"Awaiting response for article task: '{task_title_for_status}'.")
                elif task_type_panel_display == "product_writer":
                    task_title_for_status = current_task_item_display.get("product_name", f"product task {current_task_idx_panel_display + 1}")
                    if is_paused_panel_display:
                        panel_status_message_display = language_manager.get_text("cta_status_paused_at_product", lang, title=task_title_for_status, fallback=f"Paused product task preparation at: '{task_title_for_status}'.")
                    else: 
                        panel_status_message_display = language_manager.get_text("cta_status_awaiting_response_for_product", lang, title=task_title_for_status, fallback=f"Awaiting response for product task: '{task_title_for_status}'.")
                else:
                     panel_status_message_display = language_manager.get_text("cta_status_awaiting_response_generic", lang, fallback="Awaiting response for suggested task.")
            elif tasks_for_panel_display and isinstance(tasks_for_panel_display, list) and current_task_idx_panel_display >= len(tasks_for_panel_display):
                show_task_panel_display = True 
                panel_status_message_display = language_manager.get_text("cta_all_tasks_addressed_panel", lang, fallback="All content tasks in this batch have been addressed.")
                is_paused_panel_display = False

        if st.session_state.get("messages"):
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        placeholder_text_key = "enter_url_or_question_seo_helper"
        if st.session_state.get("awaiting_seo_helper_cta_response"):
            current_cta_ctx = st.session_state.get("seo_helper_cta_context")
            task_name_for_placeholder = "current task"
            if current_cta_ctx:
                tasks = current_cta_ctx.get("tasks", [])
                current_idx = current_cta_ctx.get("current_task_index", 0)
                if 0 <= current_idx < len(tasks):
                    current_task_item = tasks[current_idx]
                    task_type_for_ph = current_cta_ctx.get("type")
                    if task_type_for_ph == "article_writer":
                        task_name_for_placeholder = current_task_item.get("suggested_title", f"article {current_idx+1}")
                    elif task_type_for_ph == "product_writer":
                        task_name_for_placeholder = current_task_item.get("product_name", f"product {current_idx+1}")
            placeholder_text_key = "seo_helper_cta_input_placeholder_extended" 
            placeholder_text = language_manager.get_text(placeholder_text_key, lang, task_name=task_name_for_placeholder, fallback=f"Your response for '{task_name_for_placeholder}' (yes/skip/stop)...")
        else:
            placeholder_text = language_manager.get_text(placeholder_text_key, lang, fallback="Enter URL to analyze, ask an SEO question, or search Google for keywords...")

        if prompt := st.chat_input(placeholder_text):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Check if user wants to perform Google search via chat
            if detect_google_search_intent(prompt):
                keyword = extract_search_keyword_from_prompt(prompt)
                if keyword:
                    with st.chat_message("assistant"):
                        with st.spinner(f"Performing Google search for '{keyword}'..."):
                            # Use the region currently selected in the sidebar
                            search_results = await perform_google_search(keyword, selected_region)
                        st.markdown(search_results)
                    st.session_state.messages.append({"role": "assistant", "content": search_results})
                else:
                    error_msg = "I detected you want to perform a Google search, but couldn't extract the keyword. Please try again, for example: `search for \"best seo tools\"`"
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                # Process regular chat input
                if main_process_url is None: 
                    st.error("URL processing functionality is not available due to an import error.")
                else:
                    has_mistral_key = bool(os.getenv("MISTRAL_API_KEY"))
                    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
                    
                    if not has_mistral_key and not has_gemini_key:
                        error_msg = language_manager.get_text("no_ai_api_keys_configured", lang, fallback="No AI API keys configured. Please check your configuration.")
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    else:
                        await process_chat_input(
                            prompt=prompt,
                            process_url_from_main=lambda url, lang_code: main_process_url(url, supabase_client, lang_code), 
                            message_list="messages"
                        )

        if is_paused_panel_display and tasks_for_panel_display and \
           0 <= current_task_idx_panel_display < len(tasks_for_panel_display):
            
            task_to_resume_details = tasks_for_panel_display[current_task_idx_panel_display]
            resume_button_text_btn_display = ""
            
            if task_type_panel_display == "article_writer":
                task_to_resume_title_btn_display = task_to_resume_details.get("suggested_title", "the current article task")
                resume_button_text_key_btn_display = "resume_article_tasks_button"
                resume_button_text_btn_display = language_manager.get_text(resume_button_text_key_btn_display, lang, task_title=task_to_resume_title_btn_display, fallback=f"Resume with: '{task_to_resume_title_btn_display}'")
            elif task_type_panel_display == "product_writer":
                task_to_resume_title_btn_display = task_to_resume_details.get("product_name", "the current product task")
                resume_button_text_key_btn_display = "resume_product_tasks_button" 
                resume_button_text_btn_display = language_manager.get_text(resume_button_text_key_btn_display, lang, task_title=task_to_resume_title_btn_display, fallback=f"Resume with: '{task_to_resume_title_btn_display}'")

            if resume_button_text_btn_display and st.button(resume_button_text_btn_display, key="resume_cta_panel_button"):
                st.session_state.seo_helper_cta_context = st.session_state.paused_cta_context
                st.session_state.awaiting_seo_helper_cta_response = True
                st.session_state.paused_cta_context = None
                
                resumed_task_display_details = st.session_state.seo_helper_cta_context["tasks"][st.session_state.seo_helper_cta_context["current_task_index"]]
                resume_message_chat_display = ""

                if task_type_panel_display == "article_writer":
                    resumed_task_title_chat_prompt = resumed_task_display_details.get("suggested_title", "the selected article suggestion")
                    resume_chat_prompt_key_btn_display = "seo_helper_cta_resumed_chat_prompt_extended_options"
                    resume_message_chat_display = language_manager.get_text(
                        resume_chat_prompt_key_btn_display, lang, task_title=resumed_task_title_chat_prompt,
                        fallback=(f"Resuming article task preparation. I am now focused on '{resumed_task_title_chat_prompt}'. "
                                  f"Shall I prepare it, skip to the next, or stop this process? (Type 'yes', 'skip', or 'stop')")
                    )
                elif task_type_panel_display == "product_writer":
                    resumed_task_title_chat_prompt = resumed_task_display_details.get("product_name", "the selected product suggestion")
                    resume_chat_prompt_key_btn_display = "seo_helper_cta_resumed_chat_prompt_product_extended_options"
                    resume_message_chat_display = language_manager.get_text(
                        resume_chat_prompt_key_btn_display, lang, task_title=resumed_task_title_chat_prompt,
                        fallback=(f"Resuming product task preparation. I am now focused on '{resumed_task_title_chat_prompt}'. "
                                  f"Shall I prepare it, skip to the next, or stop this process? (Type 'yes', 'skip', or 'stop')")
                    )
                
                if resume_message_chat_display:
                    st.session_state.messages.append({"role": "assistant", "content": resume_message_chat_display})
                    logging.info(f"CTA Resumed from panel button. Re-prompting for task: {resumed_task_title_chat_prompt} (Type: {task_type_panel_display})")
                    st.rerun()

        if show_task_panel_display and tasks_for_panel_display:
            expander_title_key_display = "content_tasks_expander_title"
            expander_title_text_display = language_manager.get_text(expander_title_key_display, lang, fallback="Content Generation Tasks Progress")
            with st.expander(expander_title_text_display, expanded=False):
                if panel_status_message_display:
                    st.info(panel_status_message_display)

                if not (current_task_idx_panel_display >= len(tasks_for_panel_display) and not is_paused_panel_display):
                    for i, task_item_display in enumerate(tasks_for_panel_display):
                        item_style_display = "font-style: italic; color: gray;" 
                        prefix_icon_display = "📝"

                        if i < current_task_idx_panel_display:
                            task_is_completed = False
                            task_identifier_for_check = ""
                            if task_type_panel_display == "article_writer":
                                task_identifier_for_check = task_item_display.get("suggested_title")
                                if any(ct.get("suggested_title") == task_identifier_for_check for ct in st.session_state.get("completed_tasks_article", [])):
                                    task_is_completed = True
                            elif task_type_panel_display == "product_writer":
                                task_identifier_for_check = task_item_display.get("product_name")
                                if any(ct.get("product_name") == task_identifier_for_check for ct in st.session_state.get("completed_tasks_product", [])):
                                     task_is_completed = True
                            
                            if task_is_completed:
                                prefix_icon_display = "✅"
                                item_style_display = "color: green;" 
                            else: 
                                prefix_icon_display = "➖" 
                                item_style_display = "color: gray; text-decoration: line-through;"
                        elif i == current_task_idx_panel_display: 
                            if not is_paused_panel_display: 
                                prefix_icon_display = "➡️"
                                item_style_display = "font-weight: bold;"
                            else: 
                                prefix_icon_display = "⏸️"
                                item_style_display = "font-weight: bold; color: orange;"
                        
                       
                        if task_type_panel_display == "article_writer":
                            task_title_display = task_item_display.get("suggested_title", f"Article Task {i+1}")
                            st.markdown(f"<div style='{item_style_display}'>{prefix_icon_display} **{task_title_display}**</div>", unsafe_allow_html=True)
                            
                            task_details_list_display = []
                            if task_item_display.get("focus_keyword"): 
                                task_details_list_display.append(f"Focus Keyword: `{task_item_display.get('focus_keyword')}`")
                            if task_item_display.get("content_length"): 
                                task_details_list_display.append(f"Length: {task_item_display.get('content_length')}")
                            if task_item_display.get("article_tone"): 
                                task_details_list_display.append(f"Tone: {task_item_display.get('article_tone')}")
                            
                            additional_keywords_display = task_item_display.get("additional_keywords")
                            if additional_keywords_display:
                                kw_str = ", ".join(filter(None, additional_keywords_display)) if isinstance(additional_keywords_display, list) else str(additional_keywords_display).strip()
                                if kw_str: task_details_list_display.append(f"Other Keywords: `{kw_str}`")

                            if task_item_display.get("target_page_url"): 
                                task_details_list_display.append(f"Target Page URL: {task_item_display.get('target_page_url')}")
                            if task_item_display.get("content_gap_addressed"): 
                                task_details_list_display.append(f"Content Gap: {task_item_display.get('content_gap_addressed')}")
                            if task_item_display.get("target_audience"): 
                                task_details_list_display.append(f"Target Audience: {task_item_display.get('target_audience')}")
                            
                            content_outline_display = task_item_display.get("content_outline")
                            if content_outline_display:
                                outline_str = ", ".join(filter(None, [str(item) for item in content_outline_display])) if isinstance(content_outline_display, list) else str(content_outline_display).strip()
                                if outline_str:
                                    display_outline = outline_str[:150] + '...' if len(outline_str) > 150 else outline_str
                                    task_details_list_display.append(f"Outline Preview: {display_outline}")

                            internal_links_display = task_item_display.get("internal_linking_opportunities")
                            if internal_links_display:
                                links_str = ", ".join(filter(None, [str(item) for item in internal_links_display])) if isinstance(internal_links_display, list) else str(internal_links_display).strip()
                                if links_str:
                                    display_links = links_str[:150] + '...' if len(links_str) > 150 else links_str
                                    task_details_list_display.append(f"Linking Opps Preview: {display_links}")

                            if task_details_list_display:
                                details_html_display = "".join([f"<li style='font-size: small; {item_style_display.replace('font-weight: bold;','')} margin-left: 20px;'>{detail}</li>" for detail in task_details_list_display])
                                st.markdown(f"<ul>{details_html_display}</ul>", unsafe_allow_html=True)

                        elif task_type_panel_display == "product_writer":
                            task_product_name_display = task_item_display.get('product_name', f"Product Task {i+1}")
                            st.markdown(f"<div style='{item_style_display}'>{prefix_icon_display} **{task_product_name_display}**</div>", unsafe_allow_html=True)
                            
                            product_task_details_list_display = []
                            if task_item_display.get('description_length'): product_task_details_list_display.append(f"Length: {task_item_display.get('description_length')}")
                            if task_item_display.get('tone'): product_task_details_list_display.append(f"Tone: {task_item_display.get('tone')}")
                            
                            seo_keywords_prod_display = task_item_display.get('seo_keywords', [])
                            if isinstance(seo_keywords_prod_display, list) and seo_keywords_prod_display:
                                product_task_details_list_display.append(f"SEO Keywords: `{', '.join(seo_keywords_prod_display)}`")
                            elif isinstance(seo_keywords_prod_display, str) and seo_keywords_prod_display.strip():
                                product_task_details_list_display.append(f"SEO Keywords: `{seo_keywords_prod_display}`")
                            
                            product_details_input = task_item_display.get('product_details')
                            product_details_dict = {}
                            if isinstance(product_details_input, str):
                                try:
                                    product_details_dict = json.loads(product_details_input)
                                except json.JSONDecodeError:
                                    product_details_dict = {"raw_text": product_details_input}
                            elif isinstance(product_details_input, dict):
                                product_details_dict = product_details_input
                                
                            product_details_summary = format_product_details_for_seo_helper_display(product_details_dict, lang)
                            if product_details_summary != language_manager.get_text('no_details_provided_short', lang, fallback="No specific details provided.") and product_details_summary != language_manager.get_text('not_available_short', lang, fallback="N/A"):
                                product_task_details_list_display.append(f"Details: {product_details_summary}")

                            if product_task_details_list_display:
                                details_html_prod_display = "".join([f"<li style='font-size: small; {item_style_display.replace('font-weight: bold;','')} margin-left: 20px;'>{detail}</li>" for detail in product_task_details_list_display])
                                st.markdown(f"<ul>{details_html_prod_display}</ul>", unsafe_allow_html=True)
                    
    except Exception as e:
        logging.error(f"Error in main_seo_helper: {str(e)}", exc_info=True) 
        lang_fallback = st.session_state.get("language", "en") 
        st.error(language_manager.get_text("unexpected_error_refresh", lang_fallback, fallback="An unexpected error occurred. Please refresh the page and try again."))

if __name__ == "__main__":
    # Note for deployment (e.g., on Streamlit Cloud):
    # You might need to add system packages for Playwright to work.
    # Create a `packages.txt` file in your repository's root with content like:
    # libnss3
    # libnspr4
    # libdbus-1-3
    # libatk1.0-0
    # libatk-bridge2.0-0
    # libcups2
    # libdrm2
    # libxkbcommon0
    # libxcomposite1
    # libxdamage1
    # libxfixes3
    # libxrandr2
    # libgbm1
    # libasound2
    asyncio.run(main_seo_helper())