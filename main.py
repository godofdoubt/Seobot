

#/SeoTree/main.py
import streamlit as st
import os
from dotenv import load_dotenv
import logging
import asyncio
from utils.shared_functions import analyze_website, load_saved_report, init_shared_session_state, common_sidebar , display_detailed_analysis_status_enhanced, trigger_detailed_analysis_background_process_with_callback
from utils.s10tools import normalize_url
from utils.language_support import language_manager
from supabase import create_client, Client
from analyzer.llm_analysis_end_processor import LLMAnalysisEndProcessor 

# --- Configuration & Setup ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

if "GEMINI_API_KEY" not in st.session_state:
    st.session_state.GEMINI_API_KEY = GEMINI_API_KEY
if "MISTRAL_API_KEY" not in st.session_state:
    st.session_state.MISTRAL_API_KEY = MISTRAL_API_KEY

USER_API_KEYS = {}
for key, value in os.environ.items():
    if key.startswith('USER') and key.endswith('_API_KEY'):
        USER_API_KEYS[value] = key.replace('_API_KEY', '')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def authenticate_user(api_key):
    if api_key in USER_API_KEYS:
        return True, USER_API_KEYS[api_key]
    return False, None

def display_report(text_report, full_report, normalized_url):
    st.session_state.text_report = text_report
    st.session_state.full_report = full_report
    st.session_state.url = normalized_url
    st.session_state.analysis_complete = True
    st.session_state.analysis_in_progress = False  # Clear the in-progress flag
    st.session_state.url_being_analyzed = None     # Clear the URL being analyzed
    st.rerun() # This can now stay

# Changed to a synchronous function
def trigger_detailed_analysis_background_process(report_id: int): # report_id is int from DB
    """Triggers the detailed analysis by scheduling it in a background thread."""
    try:
        logging.info(f"Attempting to trigger detailed analysis for report ID {report_id} via background thread.")
        
        # Instantiate the processor.
        processor = LLMAnalysisEndProcessor() 
        
        # Schedule the run method in a background thread.
        # processor.run expects a list of strings for report_ids.
        processor.schedule_run_in_background(report_ids=[str(report_id)])
        
        # The task_done_callback is removed as it's specific to asyncio.Task.
        # The background thread will log its own completion/errors.
        # The Streamlit app relies on polling the database for status updates.
        
        logging.info(f"Successfully scheduled detailed analysis (background thread) for report ID {report_id}")
        return True
    except ValueError as ve: 
        error_msg = language_manager.get_text("detailed_analysis_init_error", st.session_state.get("language", "en"))
        logging.error(f"Failed to initialize LLMAnalysisEndProcessor for report ID {report_id}: {ve} - {error_msg}")
        st.error(error_msg)
        return False
    except RuntimeError as re: 
        error_msg = language_manager.get_text("detailed_analysis_runtime_error", st.session_state.get("language", "en"))
        logging.error(f"Runtime error during LLMAnalysisEndProcessor initialization for report ID {report_id}: {re} - {error_msg}")
        st.error(error_msg)
        return False
    except Exception as e:
        error_msg = language_manager.get_text("detailed_analysis_trigger_error", st.session_state.get("language", "en"))
        logging.error(f"Failed to trigger detailed analysis for report ID {report_id} via background thread: {e} - {error_msg}", exc_info=True)
        st.error(error_msg)
        return False

async def process_url(url, lang="en"):
    st.session_state.analysis_in_progress = True
    st.session_state.url_being_analyzed = url  # Store the URL being analyzed
    try:
        normalized_url = normalize_url(url)
        logging.info(f"Starting process_url for {normalized_url}")
        
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}

        with st.spinner(language_manager.get_text("analyzing_website", lang)):
            saved_report_data = await asyncio.to_thread(load_saved_report, normalized_url, supabase)
            
            text_report, full_report = None, None
            report_id_for_detailed_analysis = None

            if saved_report_data and saved_report_data[0] and saved_report_data[1]:
                text_report, full_report = saved_report_data
                st.info(language_manager.get_text("found_existing_report", lang))
                logging.info(f"Found existing report for {normalized_url}")
                
                report_response = await asyncio.to_thread(
                    lambda: supabase.table('seo_reports').select('id, llm_analysis_all_completed, llm_analysis_all_error')
                    .eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute()
                )
                
                if report_response.data:
                    report_data = report_response.data[0]
                    report_id_for_detailed_analysis = report_data['id'] # This is an int
                    llm_analysis_completed = report_data.get('llm_analysis_all_completed', False)
                    llm_analysis_error = report_data.get('llm_analysis_all_error')
                    logging.info(f"Existing report ID: {report_id_for_detailed_analysis}, completed: {llm_analysis_completed}, error: {llm_analysis_error}")
                    
                    # MODIFIED LOGIC: Prioritize llm_analysis_completed
                    if llm_analysis_completed:
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("full_site_analysis_complete", lang),
                            "status": "complete"
                        }
                        if llm_analysis_error: # Log error if present, but status is still complete
                             logging.warning(f"Detailed analysis for report ID {report_id_for_detailed_analysis} (URL: {normalized_url}) is complete but has logged errors: {llm_analysis_error}")
                    elif llm_analysis_error: # This means completed is False and there is an error
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error),
                            "status": "error"
                        }
                    elif not llm_analysis_completed: # Not completed and no error reported yet (implies in progress)
                        logging.info(f"Detailed analysis not complete for report ID {report_id_for_detailed_analysis}, triggering background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        # Call the synchronous version, no await
                        if not trigger_detailed_analysis_background_process_with_callback(report_id_for_detailed_analysis, supabase):
                            st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
                else:
                    logging.warning(f"Could not find report ID for existing report {normalized_url} to check detailed analysis status.")
            else:
                logging.info(f"Generating new report for {normalized_url}")
                st.info(language_manager.get_text("generating_new_analysis", lang))
                
                analysis_result = await analyze_website(normalized_url, supabase)
                
                if analysis_result and analysis_result[0] and analysis_result[1]:
                    text_report, full_report = analysis_result
                    logging.info("New analysis successfully generated")
                    
                    report_response = await asyncio.to_thread(
                        lambda: supabase.table('seo_reports').select('id').eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute()
                    )
                    if report_response.data:
                        report_id_for_detailed_analysis = report_response.data[0]['id'] # This is an int
                        logging.info(f"New report ID: {report_id_for_detailed_analysis}. Triggering detailed analysis background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        # Call the synchronous version, no await
                        if not trigger_detailed_analysis_background_process(report_id_for_detailed_analysis):
                            st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
                    else:
                        logging.warning(f"Could not find report ID for new analysis {normalized_url} to trigger detailed analysis.")
                else:
                    st.error(language_manager.get_text("failed_to_analyze", lang))
                    logging.error(f"Analysis failed for {normalized_url}")
                    return 
            
            if text_report and full_report:
                logging.info(f"Displaying initial report for {normalized_url}")
                st.session_state.analysis_in_progress = False # Reset on successful completion (before display)
                st.session_state.url_being_analyzed = None    # Clear the URL being analyzed
                display_report(text_report, full_report, normalized_url)
            else:
                st.error(language_manager.get_text("report_data_unavailable", lang))
                logging.error(f"Report data (text_report or full_report) is None for {normalized_url} before display_report call.")
                st.session_state.analysis_in_progress = False # Reset if report data is unexpectedly unavailable
                st.session_state.url_being_analyzed = None    # Clear the URL being analyzed
    
    except Exception as e:
        error_message = f"Error in process_url: {str(e)}"
        st.error(error_message) 
        logging.error(error_message, exc_info=True)
        st.session_state.analysis_in_progress = False # Reset on any exception
        st.session_state.url_being_analyzed = None    # Clear the URL being analyzed

# --- Main App ---

def run_main_app():
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

    st.title("Se10 Web Servies")
    init_shared_session_state() #

    if "language" not in st.session_state:
        st.session_state.language = "en" #
    lang = st.session_state.language

    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False #
    if "detailed_analysis_info" not in st.session_state: 
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None} #


    for config_name, config_value in {
        'Supabase URL': SUPABASE_URL,
        'Supabase Key': SUPABASE_KEY
    }.items():
        if not config_value:
            st.error(f"{config_name} is missing.")
            st.stop()

    if not GEMINI_API_KEY and not MISTRAL_API_KEY: 
        st.error(language_manager.get_text("no_ai_model", lang))
        st.stop()

    if not st.session_state.authenticated: #
        st.markdown(language_manager.get_text("welcome_seo", lang))
        st.markdown(language_manager.get_text("enter_api_key", lang))
        
        languages = language_manager.get_available_languages()
        language_names = {"en": "English", "tr": "Türkçe"}

        selected_language = st.selectbox(
            "Language / Dil",
            languages,
            format_func=lambda x: language_names.get(x, x),
            index=languages.index(st.session_state.language)
        )
        
        if selected_language != st.session_state.language:
            st.session_state.language = selected_language
            st.rerun()
        
        with st.form("login_form"):
            api_key = st.text_input(language_manager.get_text("enter_api_key_label", lang), type="password")
            submit_button = st.form_submit_button(language_manager.get_text("login_button", lang))
            
            if submit_button:
                is_authenticated, username = authenticate_user(api_key)
                if is_authenticated:
                    st.session_state.authenticated = True #
                    st.session_state.username = username #
                    welcome_msg = language_manager.get_text("welcome_authenticated", lang, username) 
                    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}] #
                    st.rerun()
                else:
                    st.error(language_manager.get_text("login_failed", lang))
    else:
        st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))

        if st.session_state.analysis_complete and hasattr(st.session_state, 'text_report') and st.session_state.text_report and hasattr(st.session_state, 'url') and st.session_state.url: #
            
            st.success(language_manager.get_text("analysis_complete_message", lang)) 
            st.markdown(f"### {language_manager.get_text('next_steps', lang)}")
            st.markdown(language_manager.get_text("continue_optimizing", lang))
            
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_after_analysis", use_container_width=True):
                st.switch_page("pages/1_SEO_Helper.py")
            
            st.markdown(f"### {language_manager.get_text('content_generation_tools', lang)}")
            st.markdown(language_manager.get_text("create_optimized_content", lang))
            col1, col2 = st.columns(2)
        
            with col1:
                if st.button(language_manager.get_text("article_writer_button", lang), key="article_writer_button_results", use_container_width=True):
                    st.switch_page("pages/2_Article_Writer.py")
                
            with col2:
                if st.button(language_manager.get_text("product_writer_button", lang), key="product_writer_button_results", use_container_width=True):
                    st.switch_page("pages/3_Product_Writer.py")

               
                
                # Replace the entire section above with this single line:
                display_detailed_analysis_status_enhanced(supabase, lang) 
            
            st.subheader(language_manager.get_text("analysis_results_for_url", lang, st.session_state.url))
            st.text_area(language_manager.get_text("seo_report_label", lang), st.session_state.text_report, height=300) #
                  
        else: 
            st.markdown(f"""
            ## {language_manager.get_text("welcome_message", lang)}
            {language_manager.get_text("platform_description", lang)}
            ### {language_manager.get_text("getting_started", lang)}
            {language_manager.get_text("begin_by_analyzing", lang)}
            """)
            
            with st.form("url_form"):
                # If analysis is in progress, show the URL being analyzed
                if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
                    website_url = st.text_input(
                        language_manager.get_text("enter_url_placeholder", lang),
                        value=st.session_state.url_being_analyzed,
                        placeholder="https://example.com",
                        disabled=True  # Disable while analysis is running
                    )
                    st.info(language_manager.get_text("analyzing_website", lang))  # Show analyzing message
                    analyze_button = st.form_submit_button(
                        language_manager.get_text("analyze_button", lang),
                        disabled=True  # Disable button while analysis is running
                    )
                else:
                    website_url = st.text_input(
                        language_manager.get_text("enter_url_placeholder", lang),
                        placeholder="https://example.com"
                    )
                    analyze_button = st.form_submit_button(language_manager.get_text("analyze_button", lang))
            
                if analyze_button and website_url and not st.session_state.analysis_in_progress:
                    asyncio.run(process_url(website_url, lang))
            
            st.markdown(f"### {language_manager.get_text('analyze_with_ai', lang)}")
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_before_analysis"): 
                st.switch_page("pages/1_SEO_Helper.py")
        
       # if st.sidebar.button(language_manager.get_text("logout_button", lang), key="logout_button_main"): 
        #    st.session_state.authenticated = False #
         #   st.session_state.username = None #
          #  st.session_state.messages = [] #
           # if 'page_history' in st.session_state:
            #    st.session_state.page_history = {} #
            #st.session_state.analysis_complete = False #
            #st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None} #
            #for key_to_del in ['text_report', 'full_report', 'url', 'main_page_analysis', 'other_pages_analysis']: 
             #   if key_to_del in st.session_state:
              #      del st.session_state[key_to_del]
            #st.rerun() we already have a logout button in the sidebar
                
        common_sidebar() # shared sidebar with all pages.

if __name__ == "__main__":
    run_main_app()