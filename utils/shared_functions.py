#/utils/shared_functions.py
import streamlit as st
import os
import logging
import time
from supabase import Client
from analyzer.seo import SEOAnalyzer
from utils.s10tools import normalize_url
from utils.language_support import language_manager

#1
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
        st.session_state.current_page = "seo"
    if "page_history" not in st.session_state:
        st.session_state.page_history = {}
    # Analysis state
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
     # Initialize language if not set
    if "language" not in st.session_state:
        st.session_state.language = "en"
     # For tracking background detailed analysis
    if "detailed_analysis_info" not in st.session_state:
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": ""}            

def update_page_history(page_name):
    """Store the current page's message history"""
    # Save the current page's state before switching
    if st.session_state.current_page not in st.session_state.page_history:
        st.session_state.page_history[st.session_state.current_page] = []
    
    # Copy the current messages to the page history
    st.session_state.page_history[st.session_state.current_page] = st.session_state.messages.copy()
    
    # Update current page
    st.session_state.current_page = page_name
    
    # Restore messages from page history if available
    if page_name in st.session_state.page_history:
        st.session_state.messages = st.session_state.page_history[page_name].copy()
    else:
        # Initialize with welcome message for new page
        welcome_message = f"Welcome to the {page_name.capitalize()} page."
        
        # Add analysis info to welcome message if available
        if st.session_state.analysis_complete and st.session_state.url:
            welcome_message += f"\n\nUsing analysis for: {st.session_state.url}"
            
        st.session_state.messages = [{"role": "assistant", "content": welcome_message}]


# Display function for reports
def display_report_and_services(text_report, full_report, normalized_url, message_list="messages"):
    """Displays the report and sets up the session state."""
    st.session_state.text_report = text_report
    st.session_state.full_report = full_report
    st.session_state.url = normalized_url
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"Report for {normalized_url}:")
        st.text_area("Report", text_report, height=200)
        st.markdown("""
You can select one of the following services from the sidebar pages:
- SEO Helper: Get additional SEO suggestions
- Article Writer: Generate an article for your website
- Product Writer: Create product descriptions
        """)
        
    # Add the assistant's message to the appropriate message list
    report_message = {"role": "assistant", "content": f"Report for {normalized_url}:\n{text_report}"}
    st.session_state[message_list].append(report_message)
    
    st.rerun()
    
# Common sidebar layout
def common_sidebar():
    """Common sidebar content across all pages"""
    st.sidebar.title(" Main Settings:")
    
   # # Navigation buttons
    #st.sidebar.markdown("## Navigation")
    #col1, col2, col3 = st.sidebar.columns(3)
    
    #with col1:
     #   if st.button("SEO Helper"):
      #      update_page_history("seo")
       #     st.switch_page("pages/1_SEO_Helper.py")
    
    #with col2:
     #   if st.button("Article Writer"):
      #      update_page_history("article")
       #     st.switch_page("pages/2_Article_Writer.py")
    
    #with col3:
     #   if st.button("Product Writer"):
      #      update_page_history("product")
       #     st.switch_page("pages/3_Product_Writer.py")

    # Get current language
    lang = st.session_state.get("language", "en")
    
    # Add navigation buttons
   # st.sidebar.markdown("### Navigation")
    
    # Home button
    #if st.sidebar.button(language_manager.get_text("welcome_message", lang), key="home_button"):
    #    st.switch_page("main.py")
    
    # SEO Helper button
    #if st.sidebar.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_sidebar"):
     #   update_page_history("seo")
      #  st.switch_page("pages/1_SEO_Helper.py")
    
    # Article Writer button
    #if st.sidebar.button(language_manager.get_text("article_writer_button", lang), key="article_writer_sidebar"):
     #   update_page_history("article")
      #  st.switch_page("pages/2_Article_Writer.py")
    
    # Product Writer button
    #if st.sidebar.button(language_manager.get_text("product_writer_button", lang), key="product_writer_sidebar"):
     #   update_page_history("product")
      #  st.switch_page("pages/3_Product_Writer.py")
    
    # Language selector
    languages = language_manager.get_available_languages()
    language_names = {"en": "English", "tr": "Türkçe"}
    
    selected_language = st.sidebar.selectbox(
        "Language / Dil",
        languages,
        format_func=lambda x: language_names.get(x, x),
        index=languages.index(st.session_state.language),
        key="sidebar_language_selector"
    )
    
    # Update language if changed
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        st.rerun()   
    
    # Model selection (only if both models are available)
    if "GEMINI_API_KEY" in st.session_state and "MISTRAL_API_KEY" in st.session_state:
        if st.session_state.GEMINI_API_KEY and st.session_state.MISTRAL_API_KEY:
            model_options = ["o10", "Se10"]
            selected_model = st.sidebar.radio("Select AI Model:", model_options)
            st.session_state.use_mistral = (selected_model == "Se10")
    
    with st.sidebar.expander("View SEO Report", expanded=False):
        if st.session_state.text_report:
            st.sidebar.text_area(f"Your website report {st.session_state.url}", st.session_state.text_report, height=200)
        else:
            st.sidebar.write("No text report available.")


async def analyze_website(url: str, supabase: Client):
    """Analyzes website SEO and saves/retrieves reports from Supabase."""
    analyzer = SEOAnalyzer()
    try:
        results = await analyzer.analyze_url(url)
        if results:
            logging.info(f"Analysis completed for {url}. Preparing to save to Supabase.")
            normalized_url = normalize_url(url)
            existing_report = supabase.table('seo_reports').select('text_report, report').eq('url', normalized_url).execute()
            if existing_report.data and len(existing_report.data) > 0:
                logging.info(f"Report already exists for {url}.")
                text_report = existing_report.data[0].get('text_report', "Text report not available.")
                full_report = existing_report.data[0].get('report')
                return text_report, full_report
            else:
                text_report = results.get('text_report', "Text report not available.")
                full_report = results
                data_to_insert = {
                    'url': normalized_url,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'report': full_report,
                    'text_report': text_report
                }
                logging.info(f"Inserting data into Supabase: {data_to_insert}")
                insert_response = supabase.table('seo_reports').insert(data_to_insert).execute()
                logging.info(f"Supabase insert response: {insert_response}")
                return text_report, full_report
        else:
            logging.warning(f"No analysis results for {url}")
            return None, None
    except Exception as e:
        logging.error(f"Analysis error for {url}: {e}")
        return None, None

def load_saved_report(url: str, supabase: Client):
    """Loads a previously saved report from Supabase."""
    try:
        normalized_url = normalize_url(url)
        response = supabase.table('seo_reports').select('text_report, report').eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            text_report = response.data[0].get('text_report', "Text report not available.")
            full_report = response.data[0].get('report')
            return text_report, full_report
        else:
            logging.warning(f"No data found for URL {normalized_url}")
            return None, None
    except Exception as e:
        logging.error(f"Error loading from Supabase: {e}")
        return None, None            