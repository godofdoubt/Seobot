


# utils/shared_functions.py
import streamlit as st
import os
import logging
import time
from supabase import Client
from analyzer.seo import SEOAnalyzer # Assuming SEOAnalyzer class is defined elsewhere
from utils.s10tools import normalize_url
from utils.language_support import language_manager
import re # For generate_text_report_from_structured_data if used for parsing within it
import traceback # For logging errors in analyze_website

# Helper functions for generate_text_report_from_structured_data
def _get_status_emoji(value, good_is_true=True, true_emoji="✅", false_emoji="❌", unknown_emoji="❓"):
    if value is None:
        return unknown_emoji
    return true_emoji if value == good_is_true else false_emoji

def _get_check_emoji(present, good_if_present=True, details=""):
    status_emoji = ""
    if present is None: 
        status_emoji = "❓" # Data point not available
    elif present: # Item is present or condition is true
        status_emoji = "✅" if good_if_present else "⚠️" # Good if present (e.g. SSL), Warning if present (e.g. an error flag)
    else: # Item is not present or condition is false
        status_emoji = "❌" if good_if_present else "✅" # Bad if not present (e.g. SSL), Good if not present (e.g. an error flag)
    
    return f"{status_emoji} {details}".strip()


def generate_text_report_from_structured_data(data: dict) -> str:
    lines = []
    main_url = data.get('url', 'N/A') # This should be the primary URL analyzed
    lines.append(f"# SEO Analysis Summary for: {main_url}")
    lines.append(f"Analysis Timestamp: {data.get('timestamp', 'N/A')}") # Timestamp of the analysis itself
    lines.append("---")

    # SEO Score
    seo_score_val = None
    if 'llm_analysis' in data and isinstance(data['llm_analysis'], dict): # Check if llm_analysis exists and is a dict
        seo_score_val = data['llm_analysis'].get('overall_seo_score') or \
                        data['llm_analysis'].get('seo_score') or \
                        data['llm_analysis'].get('score')
    if not seo_score_val: # Fallback to top-level keys if not in llm_analysis
        seo_score_val = data.get('overall_seo_score') or data.get('seo_score')

    if seo_score_val is not None:
        try:
            # Attempt to format as int if it's numeric, otherwise use as is
            score_num = float(seo_score_val)
            lines.append(f"Overall SEO Score: {int(score_num)}/100")
        except (ValueError, TypeError):
            lines.append(f"Overall SEO Score: {seo_score_val} (Note: May not be a standard 0-100 scale)")
    else:
        lines.append("Overall SEO Score: Not explicitly found in structured data.")
    lines.append("---")

    # Technical SEO
    lines.append("## Technical SEO Checklist:")
    robots_found = data.get('robots_txt_found')
    lines.append(f"Robots.txt Found: {_get_status_emoji(robots_found, True, '✅ Found', '❌ Not Found', '❓ Status Unknown')}")

    sitemaps_discovered_count = data.get('sitemap_urls_discovered_count') # Allow 0
    if sitemaps_discovered_count is not None:
        sitemaps_discovered = sitemaps_discovered_count > 0
        lines.append(f"Sitemap Discovered: {_get_status_emoji(sitemaps_discovered, True, '✅ Yes', '❌ No', '❓ Status Unknown')} ({sitemaps_discovered_count} sitemap URLs found in robots.txt or common paths)")
    else:
        lines.append(f"Sitemap Discovered: ❓ Status Unknown (data not available)")


    ssl_valid = data.get('ssl_is_valid') # Assuming SEOAnalyzer might add this key
    if ssl_valid is not None:
         lines.append(f"HTTPS/SSL Enabled and Valid: {_get_status_emoji(ssl_valid, True, '✅ Yes', '❌ No or Invalid', '❓ Status Unknown')}")
    else: # Basic inference from URL
        if main_url.startswith("https://"):
            lines.append(f"HTTPS/SSL Enabled: ✅ Yes (URL uses https; validation status not explicitly provided)")
        else:
            lines.append(f"HTTPS/SSL Enabled: ❌ No (URL does not use https, or status not explicitly provided)")


    total_crawled = data.get('crawled_internal_pages_count')
    mobile_viewport_pages = data.get('pages_with_mobile_viewport_count')

    if total_crawled is not None and mobile_viewport_pages is not None and total_crawled > 0:
        is_mobile_friendly_site = (mobile_viewport_pages == total_crawled)
        lines.append(f"Mobile-Friendly (Viewport Meta): {_get_status_emoji(is_mobile_friendly_site, True, '✅ Good', '⚠️ Partial or Issues', '❓ Status Unknown')} ({mobile_viewport_pages}/{total_crawled} pages confirmed with viewport)")
    elif total_crawled == 0:
        lines.append(f"Mobile-Friendly (Viewport Meta): ❓ No pages crawled to assess viewport.")
    else: # total_crawled or mobile_viewport_pages is None
        lines.append(f"Mobile-Friendly (Viewport Meta): ❓ Data missing for full assessment.")
    lines.append("---")

    # Content Metrics
    lines.append("## Content Metrics (Site-wide Averages/Totals):")
    lines.append(f"Total Crawled Pages: {total_crawled if total_crawled is not None else 'N/A'}")
    lines.append(f"Total Images Found: {data.get('total_images_count', 'N/A')}")
    
    missing_alt_tags = data.get('total_missing_alt_tags_count')
    if missing_alt_tags is not None:
        priority_alt_text = "Low"
        if missing_alt_tags > 0: 
            # Heuristic for priority based on percentage of images missing alt text
            total_images = data.get('total_images_count', 0)
            if total_images > 0:
                percentage_missing = (missing_alt_tags / total_images) * 100
                if percentage_missing > 50: priority_alt_text = "Critical"
                elif percentage_missing > 10: priority_alt_text = "High"
                else: priority_alt_text = "Medium"
            else: # No images, but missing_alt_tags > 0 (should not happen)
                priority_alt_text = "Medium" 
        lines.append(f"Images Missing Alt Text: {missing_alt_tags} (Priority: {priority_alt_text} Issue)")
    else:
        lines.append(f"Images Missing Alt Text: N/A")

    lines.append(f"Total Headings Found: {data.get('total_headings_count', 'N/A')}")
    avg_len = data.get('average_cleaned_content_length_per_page') # This is in characters
    lines.append(f"Average Content Length per Page: {f'{avg_len:.0f} characters' if isinstance(avg_len, float) else avg_len if avg_len is not None else 'N/A'}")
    if isinstance(avg_len, (int,float)) and avg_len > 0:
        # Average characters per word can vary (e.g., 4.7 for English)
        # Using a general estimate of 5.5 (including space)
        lines.append(f"Estimated Average Word Count per Page: ~{int(avg_len / 5.5)}") 
    lines.append("---")

    # On-Page SEO Elements (Main Page example)
    lines.append(f"## On-Page Elements (Main URL: {main_url}):")
    # The key for main page data in 'page_analysis' should match 'main_url'
    main_page_data = data.get('page_analysis', {}).get(main_url)

    if isinstance(main_page_data, dict):
        # Title Tag
        title = main_page_data.get('metadata', {}).get('title', '')
        title_present = bool(title)
        title_details = f"Length: {len(title)} chars. "
        if not title_present: title_details = "Missing!"
        elif not (10 <= len(title) <= 70) : title_details += "Review Length (Optimal: 10-70 chars)." # Common guideline
        else: title_details += "Good Length."
        lines.append(f"Title Tag: {_get_check_emoji(title_present, True, title_details)}")

        # Meta Description
        desc = main_page_data.get('metadata', {}).get('description', '')
        desc_present = bool(desc)
        desc_details = f"Length: {len(desc)} chars. "
        if not desc_present: desc_details = "Missing!"
        elif not (50 <= len(desc) <= 160): desc_details += "Review Length (Optimal: 50-160 chars)." # Common guideline
        else: desc_details += "Good Length."
        lines.append(f"Meta Description: {_get_check_emoji(desc_present, True, desc_details)}")
        
        # H1 Tag(s) on Main Page
        num_h1 = 0
        page_headings = main_page_data.get('headings', {}) # Expected format: {'H1': ['text1'], 'H2': [...]} or {'h1_count': N}
        if isinstance(page_headings, dict):
            if 'h1_count' in page_headings and isinstance(page_headings['h1_count'], int): # Direct count
                num_h1 = page_headings['h1_count']
            elif 'H1' in page_headings and isinstance(page_headings['H1'], list): # List of H1 texts
                num_h1 = len(page_headings['H1'])
            elif 'h1' in page_headings and isinstance(page_headings['h1'], list): # case-insensitive key
                num_h1 = len(page_headings['h1'])
            # Add more ways to find H1 count if structure varies

        h1_optimal = (num_h1 == 1) # General SEO advice: exactly one H1 tag
        h1_details = f"{num_h1} found. "
        if num_h1 == 1: h1_details += "Optimal."
        elif num_h1 == 0: h1_details += "Missing (High Priority Issue)!"
        else: h1_details += "Multiple found (Review recommended)."
        lines.append(f"H1 Tag(s) on Main Page: {_get_check_emoji(h1_optimal, True, h1_details)}")

    else:
        lines.append(f"Main page specific on-page element data not found or in unexpected format. Main URL key used: '{main_url}'")
    lines.append("---")

    # Placeholder for Issues by Priority if that data becomes available in 'results'
    # For example, if results['issues_summary'] = {'critical': 1, 'high': 5, 'medium': 2, 'low': 0}
    if 'issues_summary' in data and isinstance(data['issues_summary'], dict):
        lines.append("## Detected Issues by Priority (from 'issues_summary' field):")
        has_issues = False
        for prio, count in data['issues_summary'].items():
            if isinstance(count, int) and count > 0:
                lines.append(f"- {prio.title()} Priority: {count}")
                has_issues = True
        if not has_issues: lines.append("No specific issues listed in 'issues_summary'.")
    else:
        lines.append("## Detected Issues by Priority:")
        lines.append("A specific 'issues_summary' field was not found in the structured data. Issues like missing alt text or H1 tags are noted in their respective sections with priority hints.")

    lines.append("\nNote: This is an application-generated summary from structured data. For full details, refer to the complete JSON report if available.")
    return "\n".join(lines)
# --- END OF generate_text_report_from_structured_data and its helpers ---


def init_shared_session_state():
    """Initialize shared session state variables across all pages"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "text_report" not in st.session_state:
        st.session_state.text_report = None
    if "full_report" not in st.session_state:
        st.session_state.full_report = None 
    if "url" not in st.session_state:
        st.session_state.url = None
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "seo_suggestions_generated" not in st.session_state:
        st.session_state.seo_suggestions_generated = False    
    if "use_mistral" not in st.session_state:
        st.session_state.use_mistral = False 
    if "current_page" not in st.session_state:
        st.session_state.current_page = None 
    if "page_history" not in st.session_state:
        st.session_state.page_history = {}
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "language" not in st.session_state:
        st.session_state.language = "en"
    if "detailed_analysis_info" not in st.session_state:
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
    if "url_being_analyzed" not in st.session_state:
        st.session_state.url_being_analyzed = None
    if "analysis_in_progress" not in st.session_state:
        st.session_state.analysis_in_progress = False
    if 'sidebar_report_view_full' not in st.session_state:
        st.session_state.sidebar_report_view_full = False
    
    if "auto_suggestions_data" not in st.session_state: 
        st.session_state.auto_suggestions_data = None
    if "current_report_url_for_suggestions" not in st.session_state:  
        st.session_state.current_report_url_for_suggestions = None
    
    if "selected_auto_suggestion_task_index" not in st.session_state: 
        st.session_state.selected_auto_suggestion_task_index = None
    if "last_url_for_suggestion_selection" not in st.session_state: 
        st.session_state.last_url_for_suggestion_selection = None

    if "selected_auto_suggestion_product_task_index" not in st.session_state: 
        st.session_state.selected_auto_suggestion_product_task_index = None
    if "last_url_for_product_suggestion_selection" not in st.session_state: 
        st.session_state.last_url_for_product_suggestion_selection = None

    if "awaiting_seo_helper_cta_response" not in st.session_state:
        st.session_state.awaiting_seo_helper_cta_response = False
    if "trigger_article_suggestion_from_seo_helper" not in st.session_state:
        st.session_state.trigger_article_suggestion_from_seo_helper = False
    if "article_suggestion_to_trigger_details" not in st.session_state:
        st.session_state.article_suggestion_to_trigger_details = None
    if "seo_helper_cta_context" not in st.session_state: 
        st.session_state.seo_helper_cta_context = None
    if "completed_tasks_article" not in st.session_state: 
        st.session_state.completed_tasks_article = []
    
    # NEW STATES for product writer CTA flow
    if "trigger_product_suggestion_from_seo_helper" not in st.session_state:
        st.session_state.trigger_product_suggestion_from_seo_helper = False
    if "product_suggestion_to_trigger_details" not in st.session_state:
        st.session_state.product_suggestion_to_trigger_details = None
    if "completed_tasks_product" not in st.session_state: 
        st.session_state.completed_tasks_product = []
    if "products_pending_display_on_pw" not in st.session_state: # New for direct product gen
        st.session_state.products_pending_display_on_pw = []


    if "articles_pending_display_on_aw" not in st.session_state:
        st.session_state.articles_pending_display_on_aw = [] 
        
    if "paused_cta_context" not in st.session_state:
        st.session_state.paused_cta_context = None
    # ... add other session state initializations as needed


def update_page_history(page_name):
    lang = st.session_state.get("language", "en") 

    if st.session_state.current_page and st.session_state.current_page != page_name:
        # If leaving a page where a CTA might have been active but not completed,
        # it might be desirable to pause it automatically.
        if st.session_state.current_page == "seo" and \
           st.session_state.get("awaiting_seo_helper_cta_response") and \
           st.session_state.get("seo_helper_cta_context"):
            st.session_state.paused_cta_context = st.session_state.seo_helper_cta_context
            st.session_state.awaiting_seo_helper_cta_response = False
            st.session_state.seo_helper_cta_context = None
            logging.info(f"Paused active SEO Helper CTA due to page switch from 'seo'.")

        st.session_state.page_history[st.session_state.current_page] = st.session_state.messages.copy()
        logging.info(f"Saved chat history for '{st.session_state.current_page}' (length: {len(st.session_state.messages)})")

    st.session_state.current_page = page_name
    logging.info(f"Attempting to switch to page: '{page_name}'")

    if page_name in st.session_state.page_history:
        st.session_state.messages = st.session_state.page_history[page_name].copy()
        logging.info(f"Restored chat history for '{page_name}' (length: {len(st.session_state.messages)})")
        
        # If returning to SEO Helper and a CTA was paused, offer to resume or show its state.
        # The SEO Helper page itself will handle displaying the paused CTA panel.
        # No explicit message needed here, the panel should be enough.
    else:
        welcome_message = ""
        # Page-specific welcome message logic is primarily handled within each page now
        # to ensure it reflects the most current state (e.g., analyzed URL).
        # A generic fallback can be set here if needed, or rely on page init.
        if page_name == "seo":
            # This will be set by 1_SEO_Helper.py based on its state
            welcome_message = language_manager.get_text("welcome_authenticated", lang, st.session_state.get("username", "user"))
        elif page_name == "article":
            # This will be (or should be) set by 2_Article_Writer.py based on its state
            # Fallback for initial load if page hasn't set it yet.
            welcome_message = language_manager.get_text("welcome_article_writer_not_analyzed", lang, fallback="Welcome to the Article Writer page. Analyze a site first.")
        elif page_name == "main": 
            if st.session_state.get("authenticated"):
                welcome_message = language_manager.get_text("welcome_authenticated", lang, st.session_state.get("username", "user"))
            else:
                welcome_message = language_manager.get_text("welcome_seo", lang)
        elif page_name == "product": 
            # This will be (or should be) set by 3_Product_Writer.py based on its state
            # Fallback for initial load.
            welcome_message = language_manager.get_text("welcome_product_writer_not_analyzed", lang, fallback="Welcome to the Product Writer page. Analyze a site first.")
        else:
            welcome_message = language_manager.get_text("generic_page_welcome", lang, page_name=page_name.replace('_', ' ').title())
            if not welcome_message or welcome_message.startswith("generic_page_welcome"): 
                 welcome_message = f"Welcome to the {page_name.replace('_', ' ').title()} page."

        st.session_state.messages = [{"role": "assistant", "content": welcome_message}]
        logging.info(f"Initialized new chat history for '{page_name}' with welcome message (update_page_history): \"{welcome_message[:100]}...\"")


def display_report_and_services(text_report, full_report, normalized_url, message_list="messages"):
    st.session_state.text_report = text_report
    st.session_state.full_report = full_report 
    st.session_state.url = normalized_url # Ensure global URL is set

    # Update chat message for report display
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"Report for {normalized_url}:")
        st.markdown(text_report) 
        st.markdown("""
You can select one of the following services from the sidebar pages:
- SEO Helper: Get additional SEO suggestions
- Article Writer: Generate an article for your website
- Product Writer: Create product descriptions
        """)
        
    report_message_content = f"Report for {normalized_url}:\n{text_report}\n\nYou can select one of the following services from the sidebar pages:\n- SEO Helper: Get additional SEO suggestions\n- Article Writer: Generate an article for your website\n- Product Writer: Create product descriptions"
    
    # Add to message history if not already the last message or very similar
    current_messages = st.session_state.get(message_list, [])
    if not current_messages or not current_messages[-1]["content"].startswith(f"Report for {normalized_url}"):
        current_messages.append({"role": "assistant", "content": report_message_content})
        st.session_state[message_list] = current_messages
    
    st.rerun()
    
def common_sidebar(page_specific_content_func=None):
    lang = st.session_state.get("language", "en")
    
    # --- TOP NAVIGATION ---
    st.sidebar.title(language_manager.get_text("main_settings_title", lang, fallback="Navigation")) # Changed fallback for clarity
    is_analysis_in_progress = st.session_state.get("analysis_in_progress", False)

    st.sidebar.page_link("main.py", label=language_manager.get_text("home_page_label", lang))
    st.sidebar.page_link("pages/1_SEO_Helper.py", label=language_manager.get_text("seo_helper_button", lang))
    
    article_writer_path = "pages/2_Article_Writer.py"
    product_writer_path = "pages/3_Product_Writer.py"

    if os.path.exists(article_writer_path):
        st.sidebar.page_link(
            article_writer_path,
            label=language_manager.get_text("article_writer_button", lang),
            disabled=is_analysis_in_progress
        )
    
    if os.path.exists(product_writer_path):
        st.sidebar.page_link(
            product_writer_path,
            label=language_manager.get_text("product_writer_button", lang),
            disabled=is_analysis_in_progress
        )
    
    st.sidebar.divider()

    # --- PAGE-SPECIFIC CONTENT (MIDDLE) ---
    if page_specific_content_func:
        page_specific_content_func() # This function will render UI elements using st.sidebar.X
        st.sidebar.divider()

    # --- GLOBAL SETTINGS (BOTTOM) ---
    # Title for this section can be added if desired, e.g., st.sidebar.markdown("--- \n**Global Settings**")
    disable_interactive_elements = is_analysis_in_progress

    languages = language_manager.get_available_languages()
    language_names = {"en": "English", "tr": "Türkçe"}
    original_language = st.session_state.language
    
    selected_language = st.sidebar.selectbox(
        language_manager.get_text("language_select_label", lang),
        languages,
        format_func=lambda x: language_names.get(x, x),
        index=languages.index(st.session_state.language),
        key="sidebar_language_selector",
        disabled=disable_interactive_elements
    )
    
    if not disable_interactive_elements and selected_language != original_language:
        st.session_state.language = selected_language
        st.session_state.sidebar_report_view_full = False
        st.rerun()   
    
    if "GEMINI_API_KEY" in st.session_state and "MISTRAL_API_KEY" in st.session_state:
        if st.session_state.GEMINI_API_KEY and st.session_state.MISTRAL_API_KEY:
            model_options_map = {
                "o10": language_manager.get_text("model_o10", lang),
                "Se10": language_manager.get_text("model_Se10", lang)
            }
            model_keys = list(model_options_map.keys())
            model_display_names = [model_options_map[k] for k in model_keys]
            
            original_use_mistral = st.session_state.get("use_mistral", False)
            current_model_key = "Se10" if original_use_mistral else "o10"
            try:
                current_model_index = model_keys.index(current_model_key)
            except ValueError:
                current_model_index = 0 

            selected_model_display_name = st.sidebar.radio(
                language_manager.get_text("select_ai_model_label", lang), 
                model_display_names,
                index=current_model_index,
                disabled=disable_interactive_elements
            )
            if not disable_interactive_elements:
                selected_model_key_for_update = model_keys[model_display_names.index(selected_model_display_name)]
                new_use_mistral = (selected_model_key_for_update == "Se10")
                if new_use_mistral != original_use_mistral:
                    st.session_state.use_mistral = new_use_mistral
    
    with st.sidebar.expander(language_manager.get_text("view_seo_report_expander_label", lang), expanded=False):
        if st.session_state.get("text_report") and st.session_state.get("url"): 
            report_label = language_manager.get_text("your_website_report_label", lang, st.session_state.url)
            st.sidebar.markdown(f"**{report_label}**")

            report_content = st.session_state.text_report
            report_lines = report_content.splitlines()
            preview_lines_count = 7 
            
            if 'sidebar_report_view_full' not in st.session_state:
                st.session_state.sidebar_report_view_full = False

            if len(report_lines) > preview_lines_count:
                if st.session_state.sidebar_report_view_full:
                    st.sidebar.markdown(report_content)
                    if st.sidebar.button(
                        language_manager.get_text("show_less_report_sidebar", lang, fallback="Show less"), 
                        key="sidebar_show_less_report_button",
                        disabled=disable_interactive_elements
                    ):
                        st.session_state.sidebar_report_view_full = False
                        st.rerun()
                else:
                    preview_content = "\n".join(report_lines[:preview_lines_count])
                    if len(preview_content.strip()) < len(report_content.strip()):
                         preview_content += "\n..."
                    st.sidebar.markdown(preview_content)
                    if st.sidebar.button(
                        language_manager.get_text("read_more_report_sidebar", lang, fallback="Read more"), 
                        key="sidebar_read_more_report_button",
                        disabled=disable_interactive_elements
                    ):
                        st.session_state.sidebar_report_view_full = True
                        st.rerun()
            else:
                st.sidebar.markdown(report_content)
        else:
            st.sidebar.write(language_manager.get_text("no_text_report_available", lang))

    if is_analysis_in_progress:
        st.sidebar.info(language_manager.get_text("analysis_running_sidebar_info", lang))
    
    st.sidebar.divider() # Divider before logout

    if st.sidebar.button(
        language_manager.get_text("logout_button", lang), 
        key="common_sidebar_logout_button",
        disabled=is_analysis_in_progress
    ):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.messages = []
        if 'page_history' in st.session_state:
            st.session_state.page_history = {}
        st.session_state.analysis_complete = False
        st.session_state.analysis_in_progress = False
        st.session_state.url_being_analyzed = None    
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
        st.session_state.sidebar_report_view_full = False 
        
        keys_to_clear_on_logout = [
            'text_report', 'full_report', 'url', 
            'main_page_analysis', 'other_pages_analysis', 'selected_pages_for_seo_suggestions',
            'auto_suggestions_data', 'current_report_url_for_suggestions', 
            'selected_auto_suggestion_task_index', 'last_url_for_suggestion_selection',
            'awaiting_seo_helper_cta_response', 'trigger_article_suggestion_from_seo_helper', 
            'article_suggestion_to_trigger_details', 'completed_tasks_article',
            'trigger_product_suggestion_from_seo_helper', 'product_suggestion_to_trigger_details', 'completed_tasks_product',
            'products_pending_display_on_pw', # Added new state for product gen
            'seo_helper_cta_context', 'paused_cta_context', 
            'articles_pending_display_on_aw', 
            'product_options', 'article_options', 
            'selected_auto_suggestion_product_task_index', 
            'last_url_for_product_suggestion_selection'
        ]
        for key_to_del in keys_to_clear_on_logout:
            if key_to_del in st.session_state:
                del st.session_state[key_to_del]
        
        st.query_params.clear() 
        st.switch_page("main.py")

        
async def analyze_website(url: str, supabase: Client):
    analyzer = SEOAnalyzer() # Actual SEOAnalyzer class needs to be available
    try:
        results = await analyzer.analyze_url(url) # This is where the analysis happens
        
        if results and isinstance(results, dict): # Ensure results is a dictionary
            logging.info(f"analyze_website: Raw analysis results received for {url}. Preparing to process.")
            # Normalize URL for consistency in storage and retrieval
            # s10tools.normalize_url should handle common cases like adding scheme, stripping fragments.
            normalized_url = normalize_url(url) 
            if not normalized_url: # If normalization fails, log and use original or handle error
                logging.error(f"analyze_website: URL normalization failed for input: {url}. Using original as fallback.")
                normalized_url = url # Fallback, though this might indicate an invalid URL
            
            # Attempt to get text_report from analyzer's results
            text_report_value_from_analyzer = results.get('text_report')
            
            # Define minimum length for a "valid" report from analyzer to avoid short/placeholder messages
            min_analyzer_report_length = 100 # characters, arbitrary threshold

            if not text_report_value_from_analyzer or \
               str(text_report_value_from_analyzer).strip() == "Text report not available." or \
               len(str(text_report_value_from_analyzer).strip()) < min_analyzer_report_length:
                
                log_message_reason = "not found"
                if text_report_value_from_analyzer: # If it exists but is short or placeholder
                    log_message_reason = f"placeholder or too short (length: {len(str(text_report_value_from_analyzer).strip())})"

                logging.warning(
                    f"analyze_website: 'text_report' from SEOAnalyzer for {url} (normalized: {normalized_url}) is {log_message_reason}. "
                    f"Generating a new summary from structured data."
                )
                # Generate text_report from the structured 'results'
                text_report_from_analysis = generate_text_report_from_structured_data(results)
                # Update/add the 'text_report' field within the 'results' object itself for consistency.
                # This ensures the JSON 'report' column also contains this definitive text_report.
                results['text_report'] = text_report_from_analysis 
            else:
                # Use the text_report provided by the analyzer as it seems valid
                text_report_from_analysis = str(text_report_value_from_analyzer) # Ensure string type
                logging.info(f"analyze_website: Using 'text_report' as provided by SEOAnalyzer for {url} (normalized: {normalized_url}).")

            # full_report_from_analysis is the complete 'results' object, now potentially with an updated 'text_report'
            full_report_from_analysis = results 

            data_to_upsert = {
                'url': normalized_url, # Use the consistently normalized URL
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), # Consider UTC: datetime.utcnow().isoformat()
                'report': full_report_from_analysis,
                'text_report': text_report_from_analysis,
                'llm_analysis_all_completed': False, # Reset for new/updated analysis
                'llm_analysis_all': None,          # Clear old LLM analysis
                'auto_suggestions': None           # Clear old auto suggestions
            }
            
            upsert_response = supabase.table('seo_reports').upsert(data_to_upsert, on_conflict='url').execute()

            logging.info(f"analyze_website: Supabase upsert response for {normalized_url}: {upsert_response}")
            if upsert_response.data:
                 logging.info(f"analyze_website: Upsert successful for {normalized_url}.")
                 # Return the (potentially generated) text_report and the full_report
                 return text_report_from_analysis, full_report_from_analysis
            else:
                # Log error but still return what was analyzed, as data might be useful even if DB write had issues
                logging.error(f"analyze_website: Supabase upsert failed or returned no data for {normalized_url}. Error: {upsert_response.error}")
                return text_report_from_analysis, full_report_from_analysis 
                
        elif results is None: # Explicitly handle None return from analyzer
            logging.warning(f"analyze_website: SEOAnalyzer returned None for {url}. No analysis data.")
            return None, None # Or return placeholder error reports
        else: # Handle case where results is not a dict (unexpected)
             logging.error(f"analyze_website: SEOAnalyzer returned unexpected data type for {url}: {type(results)}. Expected dict.")
             # Return an error message and a minimal error structure for full_report
             return "Error: Analysis returned unexpected data type.", {"error": "Analysis returned unexpected data type", "url": url}

    except Exception as e:
        logging.error(f"analyze_website: Analysis error for {url}: {e}", exc_info=True)
        # Return error messages that can be displayed or logged further
        error_text_report = f"Error during analysis for {url}: {str(e)}"
        error_full_report = {"error": str(e), "url": url, "traceback": traceback.format_exc()}
        return error_text_report, error_full_report

def load_saved_report(url: str, supabase: Client):
    try:
        normalized_url = normalize_url(url)
        logging.info(f"load_saved_report: Attempting to load report for normalized_url: {normalized_url}")
        
        response = supabase.table('seo_reports').select(
            'text_report, report, llm_analysis_all, llm_analysis_all_completed, auto_suggestions, url' # Ensure 'url' is explicitly selected
        ).eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute() 
        
        if response.data and len(response.data) > 0:
            data = response.data[0]
            logging.info(f"load_saved_report: Data FOUND for {normalized_url}. Raw data keys: {list(data.keys())}")

            text_report = data.get('text_report', "Text report not available.")
            
            base_report_json = data.get('report', {})
            if not isinstance(base_report_json, dict):
                logging.warning(f"load_saved_report: 'report' field from DB was not a dict for {normalized_url}. Using empty dict.")
                base_report_json = {}
            
            current_full_report = base_report_json.copy() # Start with the base 'report' data

            llm_analysis_data = data.get('llm_analysis_all')
            if data.get('llm_analysis_all_completed') and isinstance(llm_analysis_data, dict) and llm_analysis_data:
                current_full_report['llm_analysis_all'] = llm_analysis_data
            elif data.get('llm_analysis_all_completed') and (not isinstance(llm_analysis_data, dict) or not llm_analysis_data) :
                logging.warning(f"load_saved_report: 'llm_analysis_all_completed' is true but 'llm_analysis_all' is missing or not a dict for {normalized_url}.")
            
            retrieved_auto_suggestions = data.get('auto_suggestions')
            st.session_state.auto_suggestions_data = retrieved_auto_suggestions # Set it regardless of type for now
            logging.info(f"load_saved_report: Set st.session_state.auto_suggestions_data to type: {type(retrieved_auto_suggestions)}")
            if retrieved_auto_suggestions is not None:
                 logging.info(f"load_saved_report: auto_suggestions_data (first 100 chars if long): {str(retrieved_auto_suggestions)[:100]}")
            else:
                 logging.info("load_saved_report: auto_suggestions_data is None from DB.")

            db_url_field = data.get('url') # This is the 'url' column from the database record
            if db_url_field:
                st.session_state.current_report_url_for_suggestions = db_url_field
                logging.info(f"load_saved_report: Set st.session_state.current_report_url_for_suggestions to DB 'url' field: {db_url_field}")
                # Also update the main session URL if the DB URL is more canonical (e.g. http vs https resolved)
                st.session_state.url = db_url_field 
            else:
                # Fallback if 'url' field is somehow missing from data, though it was selected
                st.session_state.current_report_url_for_suggestions = normalized_url
                st.session_state.url = normalized_url 
                logging.warning(
                    f"load_saved_report: 'url' field from DB response was None for {normalized_url}. "
                    f"Using queried normalized_url for current_report_url_for_suggestions and st.session_state.url: {normalized_url}"
                )

            st.session_state.text_report = text_report
            st.session_state.full_report = current_full_report
            logging.info(f"load_saved_report: Final session states: url='{st.session_state.url}', "
                         f"text_report_present={bool(st.session_state.text_report)}, "
                         f"full_report_keys={list(st.session_state.full_report.keys()) if isinstance(st.session_state.full_report, dict) else 'Not a dict'}, "
                         f"auto_suggestions_data_type={type(st.session_state.auto_suggestions_data)}, "
                         f"current_report_url_for_suggestions='{st.session_state.current_report_url_for_suggestions}'")

            return text_report, current_full_report
        else:
            logging.warning(f"load_saved_report: No data found in DB for URL {normalized_url}.")
            st.session_state.auto_suggestions_data = None 
            st.session_state.current_report_url_for_suggestions = None
            # Potentially clear other report-related states or leave them as they were
            # st.session_state.url = normalized_url # Keep the URL that was attempted
            # st.session_state.text_report = None
            # st.session_state.full_report = None
            logging.info(f"load_saved_report: Set session auto_suggestions_data and current_report_url_for_suggestions to None (no data found for {normalized_url}).")
            return None, None
    except Exception as e:
        logging.error(f"load_saved_report: EXCEPTION while loading report for {url}: {e}", exc_info=True)
        st.session_state.auto_suggestions_data = None 
        st.session_state.current_report_url_for_suggestions = None 
        logging.error(f"load_saved_report: Set session auto_suggestions_data and current_report_url_for_suggestions to None due to EXCEPTION for {url}.")
        return None, None



def check_and_update_report_status(supabase: Client, report_id: int, lang: str = "en"):
    try:
        logging.info(f"check_and_update_report_status: Checking status for report ID {report_id}")
        response = supabase.table('seo_reports').select(
            'llm_analysis_all_completed, llm_analysis_all_error, text_report, report, llm_analysis_all, url, auto_suggestions'
        ).eq('id', report_id).single().execute()
        
        report_data = response.data
        
        if not report_data:
            logging.warning(f"check_and_update_report_status: No report found with ID {report_id}. Response: {response}")
            if st.session_state.detailed_analysis_info.get("report_id") == report_id:
                 st.session_state.detailed_analysis_info["status"] = "error"
                 st.session_state.detailed_analysis_info["status_message"] = "Report not found."
            return False, "error", "Report not found"
        
        logging.info(f"check_and_update_report_status: Data found for report ID {report_id}.") ##Raw report_data from DB: {report_data}

        llm_analysis_completed = report_data.get('llm_analysis_all_completed', False)
        llm_analysis_error = report_data.get('llm_analysis_all_error')
        
        current_detailed_info_status = st.session_state.detailed_analysis_info.get("status")
        new_status = current_detailed_info_status
        new_message = st.session_state.detailed_analysis_info.get("status_message", "")
        status_or_data_changed = False # Flag if either status text or underlying report data changes
        
        if llm_analysis_completed:
            candidate_status = "complete"
            candidate_message = language_manager.get_text("full_site_analysis_complete", lang)
            
            db_text_report = report_data.get('text_report', '')
            db_base_report_json = report_data.get('report', {})
            if not isinstance(db_base_report_json, dict): db_base_report_json = {}
            db_llm_analysis_all_json = report_data.get('llm_analysis_all', {})
            if not isinstance(db_llm_analysis_all_json, dict): db_llm_analysis_all_json = {}
            
            db_url = report_data.get('url')
            db_auto_suggestions = report_data.get('auto_suggestions')

            comprehensive_full_report = db_base_report_json.copy()
            if db_llm_analysis_all_json:
                comprehensive_full_report['llm_analysis_all'] = db_llm_analysis_all_json
            
            # Condition to update session state based on this fetched data
            # Only update if the report ID matches and the URL from DB matches the current detailed_analysis_info URL
            if st.session_state.detailed_analysis_info.get("report_id") == report_id and \
               st.session_state.detailed_analysis_info.get("url") == db_url:
                
                data_changed_in_session = False # Tracks if actual data fields need update
                
                if st.session_state.get('text_report') != db_text_report: data_changed_in_session = True
                if st.session_state.get('full_report') != comprehensive_full_report: data_changed_in_session = True
                
                # Defensively update auto_suggestions and current_report_url_for_suggestions
                # Only update if the new DB value is not None and different from current session state
                if db_auto_suggestions is not None and st.session_state.get('auto_suggestions_data') != db_auto_suggestions:
                    data_changed_in_session = True
                
                # db_url from this fetch should ideally match st.session_state.url if the outer condition held
                # st.session_state.url should have been set by load_saved_report or a previous call here.
                # st.session_state.current_report_url_for_suggestions uses this db_url
                if db_url is not None and st.session_state.get('current_report_url_for_suggestions') != db_url:
                    data_changed_in_session = True
                if db_url is not None and st.session_state.get('url') != db_url: # also ensure main url is consistent
                    data_changed_in_session = True

                if data_changed_in_session:
                    logging.info(f"check_and_update_report_status: Updating session state data for COMPLETED report {report_id} ({db_url})")
                    st.session_state.text_report = db_text_report
                    st.session_state.full_report = comprehensive_full_report
                    
                    if db_url is not None: # This should be true given the outer 'if'
                        st.session_state.url = db_url
                        st.session_state.current_report_url_for_suggestions = db_url
                    else: # Should not happen if outer condition on db_url is met
                        logging.warning(f"check_and_update_report_status: db_url is None but was expected. Session url/current_report_url_for_suggestions not updated from this source for report {report_id}")

                    if db_auto_suggestions is not None:
                        st.session_state.auto_suggestions_data = db_auto_suggestions
                    else:
                        logging.info(f"check_and_update_report_status: db_auto_suggestions is None from this fetch for {report_id}. Session 'auto_suggestions_data' (current type: {type(st.session_state.get('auto_suggestions_data'))}) preserved.")
                    
                    st.session_state.seo_suggestions_generated = False 
                    status_or_data_changed = True # Indicates data was refreshed
            
            new_status = candidate_status
            new_message = candidate_message
            if current_detailed_info_status != new_status: status_or_data_changed = True # Status text itself changed

            if llm_analysis_error:
                logging.warning(f"check_and_update_report_status: Report {report_id} completed but also has an error flag: {llm_analysis_error}")
                new_message += f" (Note: An error was logged during analysis: {llm_analysis_error})"
                
        elif llm_analysis_error:
            new_status = "error"
            new_message = language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error)
            if current_detailed_info_status != new_status: status_or_data_changed = True
        else: 
            new_status = "in_progress"
            new_message = language_manager.get_text("detailed_analysis_inprogress", lang)
            if current_detailed_info_status != new_status: status_or_data_changed = True
        
        if status_or_data_changed or \
           st.session_state.detailed_analysis_info.get("status_message") != new_message or \
           st.session_state.detailed_analysis_info.get("status") != new_status :
            
            st.session_state.detailed_analysis_info.update({
                "status": new_status,
                "status_message": new_message
            })
            logging.info(f"check_and_update_report_status: detailed_analysis_info updated for report {report_id}. New status: {new_status}. Status_or_data_changed (includes data refresh or status text change): {status_or_data_changed}")
            return True, new_status, new_message 
        
        return False, new_status, new_message
        
    except Exception as e:
        error_msg = f"check_and_update_report_status: EXCEPTION for ID {report_id}: {str(e)}"
        logging.error(error_msg, exc_info=True)
        if st.session_state.detailed_analysis_info.get("report_id") == report_id:
            st.session_state.detailed_analysis_info["status"] = "error"
            st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text("status_check_failed_error", lang, fallback="Failed to check report status due to an error.")
        return True, "error", st.session_state.detailed_analysis_info.get("status_message", error_msg)

# ... (rest of the file) ...

def display_detailed_analysis_status_enhanced(supabase: Client, lang: str = "en"):
    if not isinstance(st.session_state.get("detailed_analysis_info"), dict) or \
       not st.session_state.detailed_analysis_info.get("report_id") or \
       st.session_state.detailed_analysis_info.get("url") != st.session_state.get("url"):
        return 
    
    detailed_info = st.session_state.detailed_analysis_info
    report_id = detailed_info["report_id"]
    current_display_status = detailed_info.get("status", "in_progress") # Default to in_progress if None
    status_message = detailed_info.get("status_message", "...")

    if current_display_status == "complete":
        st.success(f"✅ {status_message}")
        if st.button(
            language_manager.get_text("recheck_comprehensive_report", lang, fallback="🔄 Re-check Analysis"), 
            key=f"recheck_comprehensive_{report_id}"
        ):
            status_changed, _, _ = check_and_update_report_status(supabase, report_id, lang)
            if status_changed: 
                 st.rerun()
            else: # No change, but confirm it's still complete
                 st.toast(language_manager.get_text("report_up_to_date_toast", lang, fallback="Report is up-to-date."), icon="✅")

    elif current_display_status == "error":
        st.warning(f"⚠️ {status_message}")
    else:  # in_progress or initial state
        st.info(f"🔄 {status_message}")
    
    if current_display_status == "in_progress":
        col1_width, col2_width = (1, 1) if lang != "tr" else (1.2, 1) # Adjust for longer Turkish text
        col1, col2 = st.columns([col1_width, col2_width])

        with col1:
            if st.button(
                language_manager.get_text("check_report_update_button", lang, fallback="Check Now"), 
                key=f"manual_check_{report_id}"
            ):
                status_changed, _, _ = check_and_update_report_status(supabase, report_id, lang)
                if status_changed:
                    st.rerun() 
        
        with col2:
            auto_refresh_key = f"auto_refresh_{report_id}"
            if auto_refresh_key not in st.session_state: 
                st.session_state[auto_refresh_key] = True # Default to on

            auto_refresh_enabled = st.checkbox(
                language_manager.get_text("auto_refresh_checkbox", lang, fallback="🔄 Auto-check"), 
                value=st.session_state.get(auto_refresh_key, True), # Use .get for safety
                key=f"auto_refresh_toggle_widget_{report_id}", 
                help=language_manager.get_text("auto_refresh_help", lang, fallback="Automatically checks for completion")
            )
            # Only update the session state if the checkbox value actually changes from its previous state
            if st.session_state.get(auto_refresh_key) != auto_refresh_enabled:
                st.session_state[auto_refresh_key] = auto_refresh_enabled
                st.rerun() # Rerun if the checkbox state itself changed, to update UI or stop/start timer effect
        
        if st.session_state.get(auto_refresh_key, False): # Check current state of auto-refresh
            status_changed_by_auto, new_status_by_auto, _ = enhanced_auto_refresh_with_completion_detection(
                supabase, report_id, lang
            )
            if status_changed_by_auto and new_status_by_auto in ["complete", "error"]:
                time.sleep(0.1) 
                st.rerun()
            elif current_display_status == "in_progress": # Still in progress after auto-check attempt
                # To provide a countdown without forcing too many reruns from here:
                # We rely on Streamlit's natural rerun cycle or a user action.
                # If we want a live countdown, Streamlit doesn't support it well without hacks.
                # The info message will just show "in progress".
                # The enhanced_auto_refresh_with_completion_detection has its own timer.
                pass


def enhanced_auto_refresh_with_completion_detection(supabase: Client, report_id: int, lang: str = "en"):
    auto_refresh_session_key = f"auto_refresh_{report_id}"
    if not st.session_state.get(auto_refresh_session_key, False):
        return False, st.session_state.detailed_analysis_info.get("status"), "Auto-refresh disabled by session state"
    
    current_time = time.time()
    last_check_key = f"last_check_{report_id}"
    last_check_time = st.session_state.get(last_check_key, 0)
    check_interval = 5 
    
    if current_time - last_check_time >= check_interval:
        st.session_state[last_check_key] = current_time
        logging.info(f"enhanced_auto_refresh: Interval reached. Checking status for report ID {report_id}")
        
        status_changed, new_status, message = check_and_update_report_status(supabase, report_id, lang)
        
        if new_status in ["complete", "error"]:
            logging.info(f"enhanced_auto_refresh: Analysis {new_status} for report {report_id}. Disabling its auto-refresh flag '{auto_refresh_session_key}'.")
            st.session_state[auto_refresh_session_key] = False 
        
        return status_changed, new_status, message
    
    return False, st.session_state.detailed_analysis_info.get("status"), "Not time for scheduled check"


def trigger_detailed_analysis_background_process_with_callback(report_id: int, supabase: Client):
    try:
        current_url_for_trigger = st.session_state.get("url") # URL of the report being triggered
        if not current_url_for_trigger:
            # This should ideally not happen if a report (and thus URL) exists to be analyzed
            logging.error(f"trigger_detailed_analysis: Active URL not found in session state. Cannot proceed for report ID {report_id}")
            # Update detailed_analysis_info if it's for this report_id, or create a new one
            st.session_state.detailed_analysis_info = {
                "report_id": report_id, "url": None, "status": "error",
                "status_message": "Error: Active URL for analysis not found in session."
            }
            return False

        logging.info(f"trigger_detailed_analysis: Initiating for report ID {report_id}, URL: {current_url_for_trigger}")
        
        st.session_state.detailed_analysis_info = {
            "report_id": report_id,
            "url": current_url_for_trigger, 
            "status": "in_progress", 
            "status_message": language_manager.get_text("detailed_analysis_initiated", st.session_state.language)
        }
        
        st.session_state[f"analysis_start_time_{report_id}"] = time.time()
        st.session_state[f"auto_refresh_{report_id}"] = True 
        st.session_state[f"last_check_{report_id}"] = 0 

        # Actual trigger of the background task would happen here.
        # For example, calling a Supabase Edge Function or an external API.
        # supabase.functions.invoke('process-detailed-analysis', body={'report_id': report_id})
        # This is a placeholder for that logic.
        logging.info(f"trigger_detailed_analysis: Background task trigger (simulated) for report ID {report_id} would happen here.")
        
        # Example: Update DB to mark it as "processing" if your backend relies on a DB flag
        # response = supabase.table('seo_reports').update({'llm_analysis_processing_started': True}).eq('id', report_id).execute()
        # logging.info(f"DB update for llm_analysis_processing_started: {response}")

        return True
        
    except Exception as e:
        logging.error(f"trigger_detailed_analysis: EXCEPTION for report ID {report_id}: {e}", exc_info=True)
        # Ensure detailed_analysis_info is updated with error, preserving report_id and url if possible
        existing_info = st.session_state.get("detailed_analysis_info", {})
        st.session_state.detailed_analysis_info = {
            "report_id": report_id, 
            "url": existing_info.get("url") if existing_info.get("report_id") == report_id else None, 
            "status": "error",
            "status_message": f"Failed to trigger analysis: {e}"
        }
        return False
