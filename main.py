#/SeoTree/main.py
import streamlit as st
import os
from dotenv import load_dotenv
import logging
import asyncio
from utils.shared_functions import analyze_website, load_saved_report, init_shared_session_state, common_sidebar
from utils.s10tools import normalize_url
from utils.language_support import language_manager
from supabase import create_client, Client


# --- Configuration & Setup ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Load environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

# Store API keys in session state for access across pages
if "GEMINI_API_KEY" not in st.session_state:
    st.session_state.GEMINI_API_KEY = GEMINI_API_KEY
if "MISTRAL_API_KEY" not in st.session_state:
    st.session_state.MISTRAL_API_KEY = MISTRAL_API_KEY

# Load user API keys from .env file
USER_API_KEYS = {}
for key, value in os.environ.items():
    if key.startswith('USER') and key.endswith('_API_KEY'):
        USER_API_KEYS[value] = key.replace('_API_KEY', '')

# Authentication function
def authenticate_user(api_key):
    """Authenticate a user based on their API key"""
    if api_key in USER_API_KEYS:
        return True, USER_API_KEYS[api_key]
    return False, None

def display_report(text_report, full_report, normalized_url):
    """Displays the report and sets up the session state."""
    st.session_state.text_report = text_report
    st.session_state.full_report = full_report
    st.session_state.url = normalized_url
    st.session_state.analysis_complete = True
    
    # Force a rerun to update the UI after setting session state variables
    st.rerun()

# --- Streamlit App ---
st.set_page_config(
    page_title="SE10 Web Services Beta",
    page_icon="👋",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.seo1.com/help',
        'Report a bug': "https://www.se10.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

def main():
    st.title("Se10 Web Servies")
    init_shared_session_state()

    # Initialize language if not set
    if "language" not in st.session_state:
        st.session_state.language = "en"
    
    # Get current language
    lang = st.session_state.language

    # Initialize analysis_complete state if it doesn't exist
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False

    # Validate Supabase configurations (required)
    for config_name, config_value in {
        'Supabase URL': SUPABASE_URL,
        'Supabase Key': SUPABASE_KEY
    }.items():
        if not config_value:
            st.error(f"{config_name} is missing.")
            st.stop()

    # Check if at least one AI model is configured
    if not GEMINI_API_KEY and not MISTRAL_API_KEY:
        st.error(language_manager.get_text("no_ai_model", lang))
        st.stop()

    # Authentication screen
    if not st.session_state.authenticated:
        st.markdown(language_manager.get_text("welcome_seo", lang))
        st.markdown(language_manager.get_text("enter_api_key", lang))
        
        # Add language selector
        languages = language_manager.get_available_languages()
        language_names = {"en": "English", "tr": "Türkçe"}

        selected_language = st.selectbox(
            "Language / Dil",
            languages,
            format_func=lambda x: language_names.get(x, x),
            index=languages.index(st.session_state.language)
        )
        
        # Update language if changed
        if selected_language != st.session_state.language:
            st.session_state.language = selected_language
            st.rerun()
        
        with st.form("login_form"):
            api_key = st.text_input(language_manager.get_text("enter_api_key", lang), type="password")
            submit_button = st.form_submit_button(language_manager.get_text("login_button", lang))
            
            if submit_button:
                is_authenticated, username = authenticate_user(api_key)
                if is_authenticated:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    welcome_msg = language_manager.get_text("welcome_authenticated", lang, username)
                    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]
                    st.rerun()
                else:
                    st.error(language_manager.get_text("login_failed", lang))
    else:
        # User is authenticated, show the main application
        st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))

        # Check if we already have analysis results to display
        if st.session_state.analysis_complete and hasattr(st.session_state, 'text_report') and st.session_state.text_report and hasattr(st.session_state, 'url') and st.session_state.url:
            
            st.success(language_manager.get_text("analysis_complete", lang))  
            # Show SEO Helper button prominently
            st.markdown(f"### {language_manager.get_text('next_steps', lang)}")
            st.markdown(language_manager.get_text("continue_optimizing", lang))
            
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_after_analysis", use_container_width=True):
                st.switch_page("pages/1_SEO_Helper.py")
            
            # Show additional tools in columns
            st.markdown(f"### {language_manager.get_text('content_generation_tools', lang)}")
            st.markdown(language_manager.get_text("create_optimized_content", lang))
            col1, col2 = st.columns(2)
        
            with col1:
                if st.button(language_manager.get_text("article_writer_button", lang), key="article_writer_button_results", use_container_width=True):
                    if 'update_page_history' in globals():
                        update_page_history("article")
                    st.switch_page("pages/2_Article_Writer.py")
                
            with col2:
                if st.button(language_manager.get_text("product_writer_button", lang), key="product_writer_button_results", use_container_width=True):
                    if 'update_page_history' in globals():
                        update_page_history("product")
                    st.switch_page("pages/3_Product_Writer.py")

            st.subheader(language_manager.get_text("analysis_results", lang, st.session_state.url))
            st.text_area("SEO Report", st.session_state.text_report, height=300)
                  

        else:
            # Only show welcome message and URL form if analysis is NOT complete
            st.markdown(f"""
            ## {language_manager.get_text("welcome_message", lang)}
            
            {language_manager.get_text("platform_description", lang)}
            
            ### {language_manager.get_text("getting_started", lang)}
            
            {language_manager.get_text("begin_by_analyzing", lang)}
            """)
            
            # URL input form - only appears if analysis is not complete
            with st.form("url_form"):
                website_url = st.text_input(language_manager.get_text("enter_url", lang), placeholder="https://example.com")
                analyze_button = st.form_submit_button(language_manager.get_text("analyze_button", lang))
        
                if analyze_button and website_url:
                    asyncio.run(process_url(website_url, lang))
            
            st.markdown(f"### {language_manager.get_text('analyze_with_ai', lang)}")
            # SEO Helper button - always visible but with context
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button"):
                st.switch_page("pages/1_SEO_Helper.py")
        
        # Logout button in sidebar
        if st.sidebar.button(language_manager.get_text("logout_button", lang), key="logout_button"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.messages = []
            if 'page_history' in st.session_state:
                st.session_state.page_history = {}
            st.session_state.analysis_complete = False
            for key in ['text_report', 'full_report', 'url']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
                
        # Display sidebar
        common_sidebar()

# Get environment variables from session state or reload if needed
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def process_url(url, lang="en"):
    try:
        # Normalize URL
        normalized_url = normalize_url(url)
        
        with st.spinner(language_manager.get_text("analyzing_website", lang)):
            # Check if we have a saved report
            saved_report = load_saved_report(normalized_url, supabase)
            
            if saved_report:
                st.info(language_manager.get_text("found_existing_report", lang))
                text_report, full_report = saved_report
            else:
                # Generate new report
                analysis_result = analyze_website(normalized_url, supabase)
                if analysis_result:
                    text_report, full_report = analysis_result
                else:
                    st.error(language_manager.get_text("analysis_failed", lang))
                    return
            
            # Display the report
            display_report(text_report, full_report, normalized_url)
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logging.error(f"Error processing URL: {str(e)}")

if __name__ == "__main__":
    main()