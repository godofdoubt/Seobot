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
import subprocess

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
    st.rerun()

async def trigger_detailed_analysis_background_process(report_id):
    """Triggers the detailed analysis background script."""
    try:
        # Updated to call the new runner script
        script_path = os.path.join('analyzer', 'run_llm_analysis_end_class.py')
        if not os.path.exists(script_path):
            logging.error(f"Detailed analysis script not found at {script_path}")
            st.error(language_manager.get_text("detailed_analysis_script_missing", st.session_state.get("language", "en")))
            return False

        # Ensure report_id is a string for Popen
        subprocess.Popen(['python', script_path, str(report_id)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) # Hide console window on Windows
        logging.info(f"Successfully triggered {script_path} (background) for report ID {report_id}")
        return True
    except Exception as e:
        logging.error(f"Failed to run {script_path} in background: {e}")
        st.error(language_manager.get_text("detailed_analysis_trigger_error", st.session_state.get("language", "en")))
        return False

async def process_url(url, lang="en"):
    try:
        normalized_url = normalize_url(url)
        logging.info(f"Starting process_url for {normalized_url}")
        
        # Initialize with status
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
                    supabase.table('seo_reports').select('id, llm_analysis_all_completed, llm_analysis_all_error')
                    .eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute
                )
                
                if report_response.data:
                    report_id_for_detailed_analysis = report_response.data[0]['id']
                    llm_analysis_completed = report_response.data[0].get('llm_analysis_all_completed', False)
                    llm_analysis_error = report_response.data[0].get('llm_analysis_all_error')
                    logging.info(f"Existing report ID: {report_id_for_detailed_analysis}, completed: {llm_analysis_completed}, error: {llm_analysis_error}")
                    
                    if llm_analysis_error:
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error),
                            "status": "error"
                        }
                    elif not llm_analysis_completed:
                        logging.info(f"Detailed analysis not complete for report ID {report_id_for_detailed_analysis}, triggering background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        if not await trigger_detailed_analysis_background_process(report_id_for_detailed_analysis):
                            st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
                    else:  # Already completed
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("full_site_analysis_complete", lang),
                            "status": "complete"
                        }
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
                        supabase.table('seo_reports').select('id').eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute
                    )
                    if report_response.data:
                        report_id_for_detailed_analysis = report_response.data[0]['id']
                        logging.info(f"New report ID: {report_id_for_detailed_analysis}. Triggering detailed analysis background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        if not await trigger_detailed_analysis_background_process(report_id_for_detailed_analysis):
                            st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
                    else:
                        logging.warning(f"Could not find report ID for new analysis {normalized_url} to trigger detailed analysis.")
                else:
                    st.error(language_manager.get_text("failed_to_analyze", lang))
                    logging.error(f"Analysis failed for {normalized_url}")
                    return
            
            if text_report and full_report:
                logging.info(f"Displaying initial report for {normalized_url}")
                display_report(text_report, full_report, normalized_url)
            else:
                st.error(language_manager.get_text("report_data_unavailable", lang))
                logging.error(f"Report data (text_report or full_report) is None for {normalized_url} before display_report call.")
    
    except Exception as e:
        error_message = f"Error in process_url: {str(e)}"
        st.error(error_message)
        logging.error(error_message, exc_info=True)


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

    st.title("Se10 Web Servies")
    init_shared_session_state()

    if "language" not in st.session_state:
        st.session_state.language = "en"
    lang = st.session_state.language

    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "detailed_analysis_info" not in st.session_state: 
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}


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

    if not st.session_state.authenticated:
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
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    # Pass username as a positional argument for formatting
                    welcome_msg = language_manager.get_text("welcome_authenticated", lang, username) 
                    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]
                    st.rerun()
                else:
                    st.error(language_manager.get_text("login_failed", lang))
    else:
        # Pass username as a positional argument for formatting
        st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))

        if st.session_state.analysis_complete and hasattr(st.session_state, 'text_report') and st.session_state.text_report and hasattr(st.session_state, 'url') and st.session_state.url:
            
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

            detailed_info = st.session_state.detailed_analysis_info
            if detailed_info.get("report_id") and detailed_info.get("url") == st.session_state.url:
                st.info(detailed_info["status_message"])
                # Show button only if status is "in_progress"
                if detailed_info.get("status") == "in_progress":
                    if st.button(language_manager.get_text("check_report_update_button", lang), key="check_update_button"):
                        report_id_to_check = detailed_info["report_id"]
                        
                        completion_check_response = supabase.table('seo_reports').select('llm_analysis_all_completed, text_report, report, llm_analysis_all_error').eq('id', report_id_to_check).single().execute()

                        if completion_check_response.data:
                            llm_all_completed = completion_check_response.data.get('llm_analysis_all_completed')
                            llm_all_error = completion_check_response.data.get('llm_analysis_all_error')

                            if llm_all_error:
                                st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text("detailed_analysis_error_status", lang, llm_all_error)
                                st.session_state.detailed_analysis_info["status"] = "error"
                            elif llm_all_completed:
                                st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text("full_site_analysis_complete", lang)
                                st.session_state.detailed_analysis_info["status"] = "complete"
                                st.session_state.text_report = completion_check_response.data.get('text_report')
                                st.session_state.full_report = completion_check_response.data.get('report')
                                st.session_state.analysis_complete = True
                                st.success(language_manager.get_text("full_site_analysis_complete", lang))
                            else:
                                st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text("detailed_analysis_still_inprogress", lang)
                                st.session_state.detailed_analysis_info["status"] = "in_progress"
                            st.rerun()
                        else:
                            st.error(language_manager.get_text("error_checking_report_status", lang))
            
            # Pass URL as a positional argument for formatting
            st.subheader(language_manager.get_text("analysis_results_for_url", lang, st.session_state.url))
            st.text_area(language_manager.get_text("seo_report_label", lang), st.session_state.text_report, height=300)
                  
        else: 
            st.markdown(f"""
            ## {language_manager.get_text("welcome_message", lang)}
            {language_manager.get_text("platform_description", lang)}
            ### {language_manager.get_text("getting_started", lang)}
            {language_manager.get_text("begin_by_analyzing", lang)}
            """)
            
            with st.form("url_form"):
                website_url = st.text_input(language_manager.get_text("enter_url_placeholder", lang), placeholder="https://example.com")
                analyze_button = st.form_submit_button(language_manager.get_text("analyze_button", lang))
        
                if analyze_button and website_url:
                    asyncio.run(process_url(website_url, lang))
            
            st.markdown(f"### {language_manager.get_text('analyze_with_ai', lang)}")
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_before_analysis"): 
                st.switch_page("pages/1_SEO_Helper.py")
        
        if st.sidebar.button(language_manager.get_text("logout_button", lang), key="logout_button_main"): 
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.messages = []
            if 'page_history' in st.session_state:
                st.session_state.page_history = {}
            st.session_state.analysis_complete = False
            st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
            for key_to_del in ['text_report', 'full_report', 'url', 'main_page_analysis', 'other_pages_analysis']: 
                if key_to_del in st.session_state:
                    del st.session_state[key_to_del]
            st.rerun()
                
        common_sidebar()

if __name__ == "__main__":
    run_main_app()