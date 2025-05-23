# utils/shared_functions.py
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
        st.session_state.use_mistral = False # Default to Gemini (o10)
    if "current_page" not in st.session_state:
        st.session_state.current_page = "seo" # Or a more generic default like "home"
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
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
    # For keeping track of URL being analyzed even when switching pages
    if "url_being_analyzed" not in st.session_state:
        st.session_state.url_being_analyzed = None
    if "analysis_in_progress" not in st.session_state:
        st.session_state.analysis_in_progress = False

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
        # Ensure language_manager is available or handle gracefully
        lang = st.session_state.get("language", "en")
        welcome_base = "Welcome to the {page_name} page."
        try:
            # Example: you might want a generic welcome key
            # welcome_base = language_manager.get_text("generic_page_welcome", lang, page_name=page_name.capitalize())
            pass # Placeholder if not using language_manager here for generic messages
        except Exception: # Fallback
             pass
        welcome_message = welcome_base.format(page_name=page_name.capitalize())

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
        
    report_message = {"role": "assistant", "content": f"Report for {normalized_url}:\n{text_report}"}
    st.session_state[message_list].append(report_message)
    
    st.rerun()
    
# Common sidebar layout
def common_sidebar():
    """Common sidebar content across all pages"""
    lang = st.session_state.get("language", "en")
    st.sidebar.title(language_manager.get_text("main_settings_title", lang))

    is_analysis_in_progress = st.session_state.get("analysis_in_progress", False)

    # --- Navigation Links ---
    st.sidebar.page_link("main.py", label=language_manager.get_text("home_page_label", lang))
    st.sidebar.page_link("pages/1_SEO_Helper.py", label=language_manager.get_text("seo_helper_button", lang)) # Always enabled
    

    # Define paths for other pages
    # Ensure these paths are correct relative to your project root where streamlit run is executed
    article_writer_path = "pages/2_Article_Writer.py"
    product_writer_path = "pages/3_Product_Writer.py"

    if os.path.exists(article_writer_path): # Check if file exists before creating link
        st.sidebar.page_link(
            article_writer_path,
            label=language_manager.get_text("article_writer_button", lang),
            disabled=is_analysis_in_progress
        )
    
    if os.path.exists(product_writer_path): # Check if file exists
        st.sidebar.page_link(
            product_writer_path,
            label=language_manager.get_text("product_writer_button", lang),
            disabled=is_analysis_in_progress
        )
    
    st.sidebar.divider()

    # --- Other Sidebar Elements (Language, Model, Report) ---
    disable_interactive_elements = is_analysis_in_progress

    # Language selector
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
        st.rerun()   
    
    # Model selection
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
                    # st.rerun() # Optional: rerun if model change needs immediate global UI effect
    
    with st.sidebar.expander(language_manager.get_text("view_seo_report_expander_label", lang), expanded=False):
        if st.session_state.text_report and st.session_state.url:
            # MODIFIED LINE: Pass st.session_state.url as a positional argument
            report_label = language_manager.get_text("your_website_report_label", lang, st.session_state.url)
            st.sidebar.text_area(
                report_label, 
                st.session_state.text_report, 
                height=200,
                disabled=disable_interactive_elements
            )
        else:
            st.sidebar.write(language_manager.get_text("no_text_report_available", lang))

    if is_analysis_in_progress:
        st.sidebar.info(language_manager.get_text("analysis_running_sidebar_info", lang))
    
    st.sidebar.divider()

    # Logout Button
    if st.sidebar.button(
        language_manager.get_text("logout_button", lang), 
        key="common_sidebar_logout_button",
        disabled=is_analysis_in_progress # Disable logout during analysis
    ):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.messages = []
        if 'page_history' in st.session_state:
            st.session_state.page_history = {}
        st.session_state.analysis_complete = False
        st.session_state.analysis_in_progress = False # Reset this
        st.session_state.url_being_analyzed = None    # Reset this
        st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
        
        keys_to_clear_on_logout = [
            'text_report', 'full_report', 'url', 
            'main_page_analysis', 'other_pages_analysis',
        ]
        for key_to_del in keys_to_clear_on_logout:
            if key_to_del in st.session_state:
                del st.session_state[key_to_del]
        
        st.query_params.clear() 
        st.switch_page("main.py")


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
                logging.info(f"Report succesfully created {url}.")
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

# Add these new functions to your existing shared_functions.py file
# Add this function to your shared_functions.py file, 
# place it before the display_detailed_analysis_status_enhanced function
def check_and_update_report_status(supabase: Client, report_id: int, lang: str = "en"):
    """
    Check the database for the current status of detailed analysis and update session state
    Returns: (status_changed: bool, new_status: str, message: str)
    """
    try:
        # Query the database for current status AND the updated reports
        response = supabase.table('seo_reports').select(
            'llm_analysis_all_completed, llm_analysis_all_error, text_report, report, url'
        ).eq('id', report_id).execute()
        
        if not response.data:
            logging.warning(f"No report found with ID {report_id}")
            return False, "error", "Report not found"
        
        report_data = response.data[0]
        llm_analysis_completed = report_data.get('llm_analysis_all_completed', False)
        llm_analysis_error = report_data.get('llm_analysis_all_error')
        
        # Get the current status before updating
        current_status = st.session_state.detailed_analysis_info.get("status")
        
        # Determine new status based on database values
        if llm_analysis_completed:
            new_status = "complete"
            new_message = language_manager.get_text("full_site_analysis_complete", lang)
            
            # CRITICAL FIX: Update session state with the new comprehensive report
            # Only update if we're transitioning to complete status or if reports are different
            db_text_report = report_data.get('text_report', '')
            db_full_report = report_data.get('report', {})
            db_url = report_data.get('url', '')
            
            should_update_reports = (
                current_status != "complete" or  # Status is changing to complete
                st.session_state.text_report != db_text_report or  # Text report is different
                st.session_state.url == db_url  # Same URL (safety check)
            )
            
            if should_update_reports and db_text_report and db_full_report:
                logging.info(f"Updating session state with comprehensive report for {db_url}")
                st.session_state.text_report = db_text_report
                st.session_state.full_report = db_full_report
                st.session_state.url = db_url
                logging.info(f"Session state updated with comprehensive report (length: {len(db_text_report)} chars)")
            
            if llm_analysis_error:
                logging.warning(f"Report {report_id} completed but has errors: {llm_analysis_error}")
                
        elif llm_analysis_error:
            new_status = "error"
            new_message = language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error)
        else:
            new_status = "in_progress"
            new_message = language_manager.get_text("detailed_analysis_inprogress", lang)
        
        # Check if status changed
        status_changed = current_status != new_status
        
        if status_changed:
            # Update session state
            st.session_state.detailed_analysis_info.update({
                "status": new_status,
                "status_message": new_message
            })
            logging.info(f"Status changed for report {report_id}: {current_status} -> {new_status}")
        
        return status_changed, new_status, new_message
        
    except Exception as e:
        error_msg = f"Error checking report status: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return False, "error", error_msg


def display_detailed_analysis_status_enhanced(supabase: Client, lang: str = "en"):
    """
    Enhanced display with smart auto-refresh that detects background completion
    """
    detailed_info = st.session_state.detailed_analysis_info
    
    if not (detailed_info.get("report_id") and detailed_info.get("url") == st.session_state.url):
        return
    
    report_id = detailed_info["report_id"]
    current_status = detailed_info.get("status")
    
    # Display current status
    if current_status == "complete":
        st.success(f"✅ {detailed_info['status_message']}")
        # Show a refresh button to manually reload the comprehensive report
        if st.button(
            language_manager.get_text("refresh_comprehensive_report", lang, "🔄 Refresh Comprehensive Report"), 
            key=f"refresh_comprehensive_{report_id}",
            help="Click to ensure you're seeing the latest comprehensive analysis"
        ):
            # Force refresh the report from database
            status_changed, new_status, message = check_and_update_report_status(supabase, report_id, lang)
            if new_status == "complete":
                st.success("Report refreshed with latest comprehensive analysis!")
                st.rerun()
            
    elif current_status == "error":
        st.warning(f"⚠️ {detailed_info['status_message']}")
    else:  # in_progress
        st.info(f"🔄 {detailed_info['status_message']}")
    
    # Enhanced auto-refresh for in-progress reports
    if current_status == "in_progress":
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button(
                language_manager.get_text("check_report_update_button", lang), 
                key=f"manual_check_{report_id}"
            ):
                status_changed, new_status, message = check_and_update_report_status(supabase, report_id, lang)
                if status_changed:
                    if new_status == "complete":
                        st.success("🎉 Comprehensive analysis complete! Report updated.")
                    st.rerun()
        
        with col2:
            auto_refresh_enabled = st.checkbox(
                "🔄 Smart auto-check", 
                value=st.session_state.get(f"auto_refresh_{report_id}", True),
                key=f"auto_refresh_toggle_{report_id}",
                help="Automatically checks for completion every 5 seconds"
            )
            st.session_state[f"auto_refresh_{report_id}"] = auto_refresh_enabled
        
        # Enhanced auto-refresh with completion detection
        if auto_refresh_enabled:
            status_changed, new_status, message = enhanced_auto_refresh_with_completion_detection(
                supabase, report_id, lang
            )
            
            if status_changed and new_status in ["complete", "error"]:
                # Show completion message and refresh
                if new_status == "complete":
                    st.success(f"🎉 Comprehensive analysis completed! Report updated with detailed insights.")
                else:
                    st.error(f"❌ Analysis failed: {message}")
                time.sleep(2)  # Brief pause to show the message
                st.rerun()
            else:
                # Show live countdown
                next_check_in = 5 - (time.time() - st.session_state.get(f"last_check_{report_id}", 0))
                if next_check_in > 0:
                    st.info(f"⏱️ Next auto-check in {int(next_check_in)} seconds...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.info("🔍 Checking status now...")
                    st.rerun()



def enhanced_auto_refresh_with_completion_detection(supabase: Client, report_id: int, lang: str = "en"):
    """
    Enhanced auto-refresh that tries to detect when background process completes
    """
    # Check if we should be auto-refreshing
    if not st.session_state.get(f"auto_refresh_{report_id}", False):
        return False, None, "Auto-refresh disabled"
    
    current_time = time.time()
    last_check = st.session_state.get(f"last_check_{report_id}", 0)
    
    # More frequent checks (every 5 seconds) when analysis is in progress
    check_interval = 5
    
    if current_time - last_check >= check_interval:
        st.session_state[f"last_check_{report_id}"] = current_time
        
        # Check database status
        status_changed, new_status, message = check_and_update_report_status(supabase, report_id, lang)
        
        if status_changed and new_status in ["complete", "error"]:
            # Analysis finished - stop auto-refresh
            st.session_state[f"auto_refresh_{report_id}"] = False
            logging.info(f"Auto-refresh detected completion for report {report_id}")
            return True, new_status, message
        
        return status_changed, new_status, message
    
    return False, None, "Not time to check yet"


def trigger_detailed_analysis_background_process_with_callback(report_id: int, supabase: Client):
    """
    Triggers the detailed analysis and sets up auto-refresh detection
    """
    try:
        logging.info(f"Triggering detailed analysis for report ID {report_id}")
        
        # Store the start time to detect completion
        st.session_state[f"analysis_start_time_{report_id}"] = time.time()
        st.session_state[f"auto_refresh_{report_id}"] = True
        
        # Import and use your existing trigger logic
        from analyzer.llm_analysis_end_processor import LLMAnalysisEndProcessor
        processor = LLMAnalysisEndProcessor() 
        processor.schedule_run_in_background(report_ids=[str(report_id)])
        
        logging.info(f"Successfully scheduled detailed analysis for report ID {report_id}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to trigger detailed analysis for report ID {report_id}: {e}")
        return False