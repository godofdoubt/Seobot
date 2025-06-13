# /SeoBot/main.py
import streamlit as st
import os
from dotenv import load_dotenv
import logging
import asyncio
import json # Already present, re-confirming
import re   # Added for data extraction
from datetime import datetime # Already present
import time # Added for setting analysis_start_time
import plotly.express as px # Added for Plotly Express
import plotly.graph_objects as go # Added for Plotly Graph Objects
# from plotly.subplots import make_subplots # Not used yet, can be added if complex subplots are needed
# import pandas as pd # Not strictly needed for these charts, can be added if complex data manipulation is required by Plotly
from urllib.parse import urlparse # Added for URL validation

# Import update_page_history as well
from utils.shared_functions import analyze_website, load_saved_report, init_shared_session_state, common_sidebar , display_detailed_analysis_status_enhanced, trigger_detailed_analysis_background_process_with_callback, update_page_history
from utils.s10tools import normalize_url
from utils.language_support import language_manager
from supabase import create_client, Client
from analyzer.llm_report.llm_analysis_end_processor import LLMAnalysisEndProcessor



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

# Define a function to initialize the client and cache it
@st.cache_resource
def init_supabase_client():
    """Initializes and returns a Supabase client, cached for reuse."""
    logging.info("Initializing Supabase client.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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
        # Get the current language from Streamlit session state
        current_language = st.session_state.get("language", "en") # Default to 'en' if not set
        logging.info(f"Attempting to trigger detailed analysis for report ID {report_id} with language '{current_language}' via background thread.")

        # Instantiate the processor.
        # NOTE: This instance of processor is only used to call schedule_run_in_background.
        # The actual processing in the thread will use a NEW instance initialized with current_language.
        # We don't need to pass language_code here because schedule_run_in_background will create
        # a new instance with the correct language for the thread.
        processor = LLMAnalysisEndProcessor() # Instantiated with its default lang, but it's fine

        # Schedule the run method in a background thread, passing the current language
        # processor.run expects a list of strings for report_ids.
        processor.schedule_run_in_background(
            report_ids=[str(report_id)],
            language_code=current_language # Pass the determined language
        )

        logging.info(f"Successfully scheduled detailed analysis (background thread) for report ID {report_id} with language '{current_language}'")
        return True
    except ValueError as ve:
        error_msg = language_manager.get_text("detailed_analysis_init_error", st.session_state.get("language", "en"))
        logging.error(f"Failed to initialize LLMAnalysisEndProcessor for report ID {report_id}: {ve} - {error_msg}")
        st.error(error_msg)
        return False
    except RuntimeError as re_err:
        error_msg = language_manager.get_text("detailed_analysis_runtime_error", st.session_state.get("language", "en"))
        logging.error(f"Runtime error during LLMAnalysisEndProcessor initialization for report ID {report_id}: {re_err} - {error_msg}")
        st.error(error_msg)
        return False
    except Exception as e:
        error_msg = language_manager.get_text("detailed_analysis_trigger_error", st.session_state.get("language", "en"))
        logging.error(f"Failed to trigger detailed analysis for report ID {report_id} via background thread: {e} - {error_msg}", exc_info=True)
        st.error(error_msg)
        return False

# FIX: Added `supabase` client as a parameter
async def process_url(url, supabase, lang="en"):
    st.session_state.analysis_in_progress = True
    st.session_state.url_being_analyzed = url
    try:
        normalized_url = normalize_url(url)
        if not normalized_url:
            st.error(language_manager.get_text("invalid_url_format_warning", lang, fallback="Invalid URL format provided for processing."))
            st.session_state.analysis_in_progress = False
            st.session_state.url_being_analyzed = None
            return

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
                    report_id_for_detailed_analysis = report_data['id']
                    llm_analysis_completed = report_data.get('llm_analysis_all_completed', False)
                    llm_analysis_error = report_data.get('llm_analysis_all_error')
                    if llm_analysis_completed:
                        st.session_state.detailed_analysis_info = {"report_id": report_id_for_detailed_analysis, "url": normalized_url, "status_message": language_manager.get_text("full_site_analysis_complete", lang), "status": "complete"}
                        if llm_analysis_error: logging.warning(f"Detailed analysis for report ID {report_id_for_detailed_analysis} is complete but has errors: {llm_analysis_error}")
                    elif llm_analysis_error:
                        st.session_state.detailed_analysis_info = {"report_id": report_id_for_detailed_analysis, "url": normalized_url, "status_message": language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error=llm_analysis_error), "status": "error"}
                    else:
                        st.session_state.detailed_analysis_info = {"report_id": report_id_for_detailed_analysis, "url": normalized_url, "status_message": language_manager.get_text("detailed_analysis_inprogress", lang), "status": "in_progress"}
                        if trigger_detailed_analysis_background_process(report_id_for_detailed_analysis):
                            st.session_state[f"auto_refresh_{report_id_for_detailed_analysis}"] = True; st.session_state[f"last_check_{report_id_for_detailed_analysis}"] = 0; st.session_state[f"analysis_start_time_{report_id_for_detailed_analysis}"] = time.time()
                        else:
                            st.session_state.detailed_analysis_info["status"] = "error"
                            st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text("detailed_analysis_trigger_failed_status", lang, fallback="Failed to start detailed analysis process.")
            else:
                logging.info(f"Generating new report for {normalized_url}")
                st.info(language_manager.get_text("generating_new_analysis", lang))
                analysis_result = await analyze_website(normalized_url, supabase)
                if analysis_result and analysis_result[0] and analysis_result[1]:
                    text_report, full_report = analysis_result
                    report_response = await asyncio.to_thread(lambda: supabase.table('seo_reports').select('id').eq('url', normalized_url).order('timestamp', desc=True).limit(1).execute())
                    if report_response.data:
                        report_id_for_detailed_analysis = report_response.data[0]['id']
                        st.session_state.detailed_analysis_info = {"report_id": report_id_for_detailed_analysis, "url": normalized_url, "status_message": language_manager.get_text("detailed_analysis_inprogress", lang), "status": "in_progress"}
                        if trigger_detailed_analysis_background_process(report_id_for_detailed_analysis):
                             st.session_state[f"auto_refresh_{report_id_for_detailed_analysis}"] = True; st.session_state[f"last_check_{report_id_for_detailed_analysis}"] = 0; st.session_state[f"analysis_start_time_{report_id_for_detailed_analysis}"] = time.time()
                        else:
                            st.session_state.detailed_analysis_info["status"] = "error"
                            st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text("detailed_analysis_trigger_failed_status", lang, fallback="Failed to start detailed analysis process.")
                else:
                    st.error(language_manager.get_text("failed_to_analyze", lang)); logging.error(f"Analysis failed for {normalized_url}")
                    st.session_state.analysis_in_progress = False; st.session_state.url_being_analyzed = None; return

            if text_report and full_report: display_report(text_report, full_report, normalized_url)
            else:
                st.error(language_manager.get_text("report_data_unavailable", lang)); logging.error(f"Report data is None for {normalized_url}")
                st.session_state.analysis_in_progress = False; st.session_state.url_being_analyzed = None
    except Exception as e:
        st.error(f"Error in process_url: {str(e)}"); logging.error(f"Error in process_url: {str(e)}", exc_info=True)
        st.session_state.analysis_in_progress = False; st.session_state.url_being_analyzed = None

# --- DATA EXTRACTION AND VISUALIZATION FUNCTIONS ---

def extract_metrics_from_report(full_report_json):
    """
    Extract key metrics from the SEO report for visualization.
    Prioritizes data from full_report_json. SEO score is calculated
    based on a detailed heuristic reflecting common SEO best practices.
    """
    metrics = {
        'seo_score': 0, # Default to 0, will be calculated
        'issues_by_priority': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}, # Still extracted for score, not charted
        'page_metrics': { # For homepage primarily
            'word_count': 0,
            'images': 0,
            'headings': 0,
            'missing_alt_tags': 0, # Specifically for homepage if available
            'internal_links': None, # Now populated from JSON if available
            'external_links': None  # Now populated from JSON if available
        },
        'technical_metrics': { # Site-wide technical indicators
            'robots_txt_status': 'error',
            'sitemap_status': 'error',
            'ssl_secure': 'error',
            'mobile_friendly': 'error', # Derived from site_health_indicators
            'title_tag': 'error', # Homepage title status
            'internal_404_count': 0, # Populated from site_health_indicators
            'page_speed': None # Derived from crawl time
        },
        'site_health_indicators': { # Detailed site-wide health data for scoring
            'thin_content_page_count': 0,
            'bad_format_title_page_count': 0,
            'internal_404_page_count': 0, # Will be 0 if no status_code in page_statistics
            'mobile_optimization_percentage': 0.0,
            'alt_text_coverage_percentage': 0.0,
            'average_content_length_chars': 0,
            'homepage_content_length_chars': 0,
            'homepage_title_status': 'error',
            'avg_crawl_time_per_page': None,
            'crawled_pages_count': 0 # Added for direct access in scoring
        }
    }

    if not full_report_json or not isinstance(full_report_json, dict):
        logging.warning("extract_metrics_from_report: full_report_json is None or not a dict. Metrics will be very limited.")
        return metrics # Return early with default/empty metrics

    main_url_from_json = full_report_json.get('url')

    # 1. Populate Issues by Priority (for score calculation)
    if 'issues_summary' in full_report_json and isinstance(full_report_json['issues_summary'], dict):
        for prio, count in full_report_json['issues_summary'].items():
            prio_lower = prio.lower()
            if prio_lower in metrics['issues_by_priority'] and isinstance(count, int):
                metrics['issues_by_priority'][prio_lower] = count

    # 2. Populate Site Health Indicators & some Technical Metrics
    health = metrics['site_health_indicators']
    tech_metrics = metrics['technical_metrics']

    health['crawled_pages_count'] = full_report_json.get('crawled_internal_pages_count', 0)

    tech_metrics['robots_txt_status'] = 'good' if full_report_json.get('robots_txt_found') else 'error'
    tech_metrics['sitemap_status'] = 'good' if full_report_json.get('sitemap_found') else 'error'

    ssl_valid = full_report_json.get('ssl_is_valid')
    if ssl_valid is True: tech_metrics['ssl_secure'] = 'good'
    elif ssl_valid is False: tech_metrics['ssl_secure'] = 'error'
    elif main_url_from_json and main_url_from_json.startswith("https://"): tech_metrics['ssl_secure'] = 'good'
    # else it remains 'error' (default)

    mobile_viewport_pages = full_report_json.get('pages_with_mobile_viewport_count', 0)
    if health['crawled_pages_count'] > 0:
        health['mobile_optimization_percentage'] = (mobile_viewport_pages / health['crawled_pages_count']) * 100

    total_imgs = full_report_json.get('total_images_count', 0)
    total_missing_alts = full_report_json.get('total_missing_alt_tags_count', 0)
    if total_imgs > 0:
        health['alt_text_coverage_percentage'] = ((total_imgs - total_missing_alts) / total_imgs) * 100
    elif total_imgs == 0: # No images means 100% coverage (no missing alts for non-existent images)
        health['alt_text_coverage_percentage'] = 100.0

    health['average_content_length_chars'] = full_report_json.get('average_cleaned_content_length_per_page', 0)

    analysis_duration = full_report_json.get('analysis_duration_seconds')
    if isinstance(analysis_duration, (int, float)) and health['crawled_pages_count'] > 0:
        avg_crawl_time = analysis_duration / health['crawled_pages_count']
        health['avg_crawl_time_per_page'] = avg_crawl_time
        if avg_crawl_time < 2: tech_metrics['page_speed'] = 'good'
        elif avg_crawl_time <= 4: tech_metrics['page_speed'] = 'warning'
        else: tech_metrics['page_speed'] = 'error'

    # Homepage specific data (from llm_analysis if available, or page_statistics for main_url)
    hp_data_source = None
    llm_analysis_data = full_report_json.get('llm_analysis', {})
    if isinstance(llm_analysis_data, dict) and llm_analysis_data.get('url') == main_url_from_json:
        if 'tech_stats' in llm_analysis_data and isinstance(llm_analysis_data['tech_stats'], dict):
            hp_data_source = llm_analysis_data['tech_stats']

    if not hp_data_source and main_url_from_json: # Fallback to page_statistics for homepage
        page_stats = full_report_json.get('page_statistics', {})
        if isinstance(page_stats, dict) and main_url_from_json in page_stats:
            if isinstance(page_stats[main_url_from_json], dict):
                 hp_data_source = page_stats[main_url_from_json]

    if hp_data_source:
        hp_len_chars = hp_data_source.get('cleaned_content_length')
        if isinstance(hp_len_chars, (int, float)):
            health['homepage_content_length_chars'] = int(hp_len_chars)
            if health['homepage_content_length_chars'] > 0 :
                metrics['page_metrics']['word_count'] = int(health['homepage_content_length_chars'] / 5.5)

        hp_title_text = hp_data_source.get('title', '')
        if isinstance(hp_title_text, str):
            hp_title_text = hp_title_text.strip()
            if not hp_title_text: health['homepage_title_status'] = 'error'
            elif "<br" in hp_title_text.lower(): health['homepage_title_status'] = 'error' # Bad format
            elif not (10 <= len(hp_title_text) <= 70): health['homepage_title_status'] = 'warning'
            else: health['homepage_title_status'] = 'good'
        tech_metrics['title_tag'] = health['homepage_title_status'] # For technical chart

        # Populate homepage metrics for bar chart
        metrics['page_metrics']['images'] = hp_data_source.get('images_count', 0)
        headings_count_data = hp_data_source.get('headings_count') # Could be int or dict
        if isinstance(headings_count_data, int):
            metrics['page_metrics']['headings'] = headings_count_data
        elif isinstance(headings_count_data, dict): # e.g. {'h1':1, 'h2':3}
            metrics['page_metrics']['headings'] = sum(v for v in headings_count_data.values() if isinstance(v, int))

        metrics['page_metrics']['missing_alt_tags'] = hp_data_source.get('missing_alt_tags_count',0)
        metrics['page_metrics']['internal_links'] = hp_data_source.get('internal_links_count')
        metrics['page_metrics']['external_links'] = hp_data_source.get('external_links_count')


    # Iterate all page_statistics for thin content, bad titles, 404s
    page_statistics_dict = full_report_json.get('page_statistics', {})
    if isinstance(page_statistics_dict, dict):
        for url, page_data in page_statistics_dict.items():
            if not isinstance(page_data, dict): continue

            content_len_chars = page_data.get('cleaned_content_length', 0)
            if isinstance(content_len_chars, (int,float)) and content_len_chars < 1200: # Approx < 220 words
                health['thin_content_page_count'] += 1

            title_text = page_data.get('title', '')
            if isinstance(title_text, str) and "<br" in title_text.lower():
                health['bad_format_title_page_count'] += 1

            status_code = page_data.get('status_code')
            if isinstance(status_code, int) and status_code == 404:
                health['internal_404_page_count'] +=1

    tech_metrics['internal_404_count'] = health['internal_404_page_count']


    # 3. Calculate SEO Score
    score_a, score_b, score_c, score_d_base = 0, 0, 0, 10

    # A. Technical Foundation (Max 20 points)
    if tech_metrics['robots_txt_status'] == 'good': score_a += 5
    if tech_metrics['ssl_secure'] == 'good': score_a += 5
    if tech_metrics['sitemap_status'] == 'good': score_a += 5
    if health['avg_crawl_time_per_page'] is not None:
        if health['avg_crawl_time_per_page'] < 2: score_a += 5
        elif health['avg_crawl_time_per_page'] <= 3: score_a += 3
        elif health['avg_crawl_time_per_page'] <= 4: score_a += 1
    # else: 0 points for speed if N/A or > 4s

    # B. Mobile Friendliness (Max 15 points)
    if health['mobile_optimization_percentage'] >= 99.0: score_b = 15
    elif health['mobile_optimization_percentage'] >= 90.0: score_b = 10
    elif health['mobile_optimization_percentage'] >= 80.0: score_b = 5

    # Set technical_metrics['mobile_friendly'] for chart based on percentage
    if health['mobile_optimization_percentage'] >= 90.0: tech_metrics['mobile_friendly'] = 'good'
    elif health['mobile_optimization_percentage'] >= 70.0: tech_metrics['mobile_friendly'] = 'warning'
    else: tech_metrics['mobile_friendly'] = 'error'


    # C. Content Quality & Structure (Max 35 points)
    # C.1 Homepage Title Status
    if health['homepage_title_status'] == 'good': score_c += 5
    elif health['homepage_title_status'] == 'warning': score_c += 2
    # C.2 Site-wide Title Quality (Bad Format)
    if health['crawled_pages_count'] > 0:
        bad_title_ratio = health['bad_format_title_page_count'] / health['crawled_pages_count']
        if health['bad_format_title_page_count'] == 0: score_c += 5
        elif bad_title_ratio < 0.1: score_c += 3
        elif bad_title_ratio < 0.25: score_c += 1
    elif health['bad_format_title_page_count'] == 0 : # No pages crawled, no bad titles
        score_c += 5

    # C.3 Homepage Content Length (Max 10 points)
    hp_words_approx = health['homepage_content_length_chars'] / 5.5 if health['homepage_content_length_chars'] else 0
    if hp_words_approx >= 800: score_c += 10
    elif hp_words_approx >= 600: score_c += 7
    elif hp_words_approx >= 400: score_c += 4

    # C.4 Average Content Length (Max 10 points)
    avg_words_approx = health['average_content_length_chars'] / 5.5 if health['average_content_length_chars'] else 0
    if avg_words_approx >= 800: score_c += 10
    elif avg_words_approx >= 600: score_c += 6
    elif avg_words_approx >= 350: score_c += 3

    # C.5 Alt Text Coverage (Max 5 points)
    if health['alt_text_coverage_percentage'] >= 95.0: score_c += 5
    elif health['alt_text_coverage_percentage'] >= 85.0: score_c += 3
    elif health['alt_text_coverage_percentage'] >= 75.0: score_c += 1

    # D. Issues & Penalties (Base `score_d_base`, deduct, min score 0)
    issue_penalty = 0
    issue_penalty += metrics['issues_by_priority']['critical'] * 10
    issue_penalty += metrics['issues_by_priority']['high'] * 5
    issue_penalty += metrics['issues_by_priority']['medium'] * 2
    issue_penalty += metrics['issues_by_priority']['low'] * 1

    thin_content_penalty = 0
    if health['thin_content_page_count'] > 0:
        penalty_per_thin_page = 3

        if health['crawled_pages_count'] > 0 and health['crawled_pages_count'] <= 10:
             thin_content_penalty_cap = health['crawled_pages_count']
        else:
             thin_content_penalty_cap = 10

        thin_content_penalty = min(health['thin_content_page_count'] * penalty_per_thin_page, thin_content_penalty_cap)

    score_d = max(0, score_d_base - issue_penalty - thin_content_penalty)

    final_s_a, final_s_b, final_s_c, final_s_d = 0, 0, 0, 0
    try:
        final_s_a = score_a if isinstance(score_a, (int, float)) else 0
        final_s_b = score_b if isinstance(score_b, (int, float)) else 0
        final_s_c = score_c if isinstance(score_c, (int, float)) else 0
        final_s_d = score_d if isinstance(score_d, (int, float)) else 0

        current_sum = final_s_a + final_s_b + final_s_c + final_s_d

        rounded_sum = round(current_sum)
        int_sum = int(rounded_sum)
        final_seo_score = min(100, int_sum)
        metrics['seo_score'] = final_seo_score
    except (TypeError, ValueError, OverflowError) as e:
        logging.error(
            f"Error calculating final SEO score. Components: a={score_a}, b={score_b}, c={score_c}, d={score_d}. Error: {e}",
            exc_info=True
        )

    logging.info(f"Calculated SEO score for {main_url_from_json or 'report'}: {metrics['seo_score']}")
    logging.info(f"Score breakdown: Tech(A)={score_a}, Mobile(B)={score_b}, Content(C)={score_c}, Issues/Penalties(D)={score_d} (Base: {score_d_base}, IssuePen: {issue_penalty}, ThinPen: {thin_content_penalty})")
    logging.info(f"Health Indicators: {health}")

    return metrics


def create_seo_score_gauge(score, lang="en"):
    """Create a gauge chart for SEO score."""
    if score is None:
        score = 0

    title_text = language_manager.get_text("seo_score_gauge_title", lang, fallback="SEO Score")

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title_text, 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#667eea"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': '#f8d7da'},
                {'range': [50, 80], 'color': '#fff3cd'},
                {'range': [80, 100], 'color': '#d4edda'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 3},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20), font={'color': "#333", 'family': "Arial, sans-serif"})
    return fig

def create_content_quality_overview_chart(site_health_indicators, lang="en"):
    """Create a chart summarizing key content quality metrics."""
    if not site_health_indicators: return None

    chart_labels = []
    chart_values = []
    chart_tooltips = []

    # Metric 1: Thin Content Pages
    thin_pages_count = site_health_indicators.get('thin_content_page_count', 0)
    chart_labels.append(language_manager.get_text("metric_thin_content_pages", lang, fallback="Thin Content Pages"))
    chart_values.append(thin_pages_count)
    chart_tooltips.append(language_manager.get_text("tooltip_thin_content_pages", lang, thin_pages_count=thin_pages_count, fallback=f"{thin_pages_count} pages found with less than ~220 words. These may be seen as low-value by search engines."))

    # Metric 2: Pages with Title Format Issues
    bad_titles_count = site_health_indicators.get('bad_format_title_page_count', 0)
    chart_labels.append(language_manager.get_text("metric_bad_format_titles", lang, fallback="Pages with Title Format Issues"))
    chart_values.append(bad_titles_count)
    chart_tooltips.append(language_manager.get_text("tooltip_bad_format_titles", lang, bad_titles_count=bad_titles_count, fallback=f"{bad_titles_count} pages found with title formatting problems (e.g., <br> tags). Ensure titles are clean and descriptive."))

    if not chart_labels: return None

    fig = go.Figure()
    for i in range(len(chart_labels)):
        fig.add_trace(go.Bar(
            y=[chart_labels[i]],
            x=[chart_values[i]],
            orientation='h',
            text=str(chart_values[i]),
            textposition="inside",
            insidetextanchor="middle",
            marker_color='#ff7f0e' if chart_values[i] > 0 else '#2ca02c', # Orange for issues, green if zero
            hovertext=chart_tooltips[i],
            hoverinfo="text"
        ))

    fig.update_layout(
        title_text=language_manager.get_text("content_quality_overview_title", lang, fallback="Content Quality Overview"),
        xaxis=dict(title=language_manager.get_text("xaxis_label_num_pages", lang, fallback="Number of Pages")),
        yaxis=dict(autorange="reversed"), # Puts first item at the top
        height=max(200, len(chart_labels) * 70 + 60), # Dynamic height: base + per label
        showlegend=False,
        margin=dict(l=220, r=20, t=50, b=50), # Increased left margin for long labels
        font={'family': "Arial, sans-serif"}
    )
    return fig


def create_page_metrics_bar_chart(page_metrics_data, lang="en"):
    """Create a bar chart for page metrics (primarily for homepage)."""
    if not page_metrics_data: return None
    metric_names_map = {
        'word_count': language_manager.get_text("metric_word_count", lang, fallback="Word Count"),
        'images': language_manager.get_text("metric_images", lang, fallback="Images"),
        'internal_links': language_manager.get_text("metric_internal_links", lang, fallback="Internal Links"),
        'external_links': language_manager.get_text("metric_external_links", lang, fallback="External Links"),
        'headings': language_manager.get_text("metric_headings", lang, fallback="Headings")
        # 'missing_alt_tags' is part of score calculation, not typically charted directly here.
    }
    metrics_list = []; values = []
    # Explicit order for the bar chart
    ordered_keys = ['word_count', 'images', 'headings', 'internal_links', 'external_links']

    for metric_key in ordered_keys:
        value = page_metrics_data.get(metric_key)
        if value is not None and metric_key in metric_names_map:
            metrics_list.append(metric_names_map[metric_key])
            values.append(value)

    if not metrics_list: return None # No valid data to plot

    fig = go.Figure(data=[go.Bar(
        x=metrics_list,
        y=values,
        text=values,
        textposition='auto',
        marker_color=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'] * (len(metrics_list)//5 + 1)
    )])
    fig.update_layout(
        title_text=language_manager.get_text("page_content_metrics_bar_title_hp", lang, fallback="Page Content Metrics (Homepage)"),
        xaxis_title=language_manager.get_text("metrics_axis_label", lang, fallback="Metrics"),
        yaxis_title=language_manager.get_text("count_axis_label", lang, fallback="Count"),
        height=380,
        margin=dict(l=20, r=20, t=50, b=20),
        font={'family': "Arial, sans-serif"}
    )
    return fig

def create_technical_status_chart(technical_metrics_data, lang="en"):
    """Create a status chart for technical SEO factors."""
    if not technical_metrics_data: return None

    tech_factor_map = {
        'mobile_friendly': language_manager.get_text("tech_mobile_friendly", lang, fallback="Mobile Friendly"),
        'ssl_secure': language_manager.get_text("tech_ssl_secure", lang, fallback="SSL Secure"),
        'page_speed': language_manager.get_text("tech_page_speed", lang, fallback="Page Speed (Est.)"),
        'title_tag': language_manager.get_text("tech_title_tag_hp", lang, fallback="Title Tag (Homepage)"),
        'robots_txt_status': language_manager.get_text("tech_robots_txt", lang, fallback="Robots.txt Status"),
        'sitemap_status': language_manager.get_text("tech_sitemap_status", lang, fallback="Sitemap Status"),
        'internal_404_count': language_manager.get_text("tech_internal_404s", lang, fallback="Internal 404s")
    }
    status_color_map = {'good': '#28a745', 'warning': '#ffc107', 'error': '#dc3545', 'info': '#17a2b8'}
    status_text_map = {
        'good': language_manager.get_text("status_good", lang, fallback="Good"),
        'warning': language_manager.get_text("status_warning", lang, fallback="Warning"),
        'error': language_manager.get_text("status_error", lang, fallback="Error"),
        # 'info' text is handled directly for counts
    }
    categories = []; status_texts_display = []; colors = []

    # Explicit order for technical status chart
    ordered_tech_keys = [
        'ssl_secure', 'robots_txt_status', 'sitemap_status',
        'mobile_friendly', 'title_tag', 'page_speed', 'internal_404_count'
    ]

    for category_key in ordered_tech_keys:
        status_val = technical_metrics_data.get(category_key)
        if status_val is not None and category_key in tech_factor_map:
            categories.append(tech_factor_map[category_key])

            current_status_text = ""
            current_color = '#cccccc' # Default

            if category_key == 'internal_404_count':
                count_val = int(status_val)
                current_status_text = f"{count_val} {language_manager.get_text('found_suffix', lang, fallback='Found')}" # Added localization
                current_color = status_color_map['good'] if count_val == 0 else status_color_map['error']
            else: # For good/warning/error type statuses
                status_str_lower = str(status_val).lower()
                current_status_text = status_text_map.get(status_str_lower, str(status_val).title())
                current_color = status_color_map.get(status_str_lower, '#cccccc')

            status_texts_display.append(current_status_text)
            colors.append(current_color)

    if not categories: return None

    fig = go.Figure()
    for i in range(len(categories)):
        fig.add_trace(go.Bar(
            y=[categories[i]],
            x=[1], # All bars have a "length" of 1 for visual representation
            name=status_texts_display[i], # Use for hover/legend if enabled
            orientation='h',
            marker_color=colors[i],
            text=status_texts_display[i],
            textposition="inside",
            insidetextanchor="middle"
        ))

    fig.update_layout(
        title_text=language_manager.get_text("technical_seo_status_title", lang, fallback="Technical SEO Status"),
        barmode='stack',
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0,1]),
        yaxis=dict(autorange="reversed"),
        height=max(300, len(categories) * 60), # Dynamic height
        showlegend=False,
        margin=dict(l=160, r=20, t=50, b=20), # Increased left margin for longer labels
        font={'family': "Arial, sans-serif"}
    )
    return fig


def display_seo_dashboard(metrics, lang="en"):
    st.markdown(f"### {language_manager.get_text('seo_dashboard_main_title', lang, fallback='📊 SEO Analysis Dashboard')}")
    col1, col2 = st.columns(2)
    with col1:
        # SEO Score Gauge
        fig_gauge = create_seo_score_gauge(metrics['seo_score'], lang)
        st.plotly_chart(fig_gauge, use_container_width=True)
        if metrics.get('site_health_indicators',{}).get('crawled_pages_count', 0) == 0:
             st.caption(language_manager.get_text("seo_score_not_available_caption", lang, fallback="SEO Score might be 0 due to limited data for calculation."))

        # Page Content Metrics (Homepage)
        page_metrics_for_chart = {k: v for k,v in metrics.get('page_metrics', {}).items() if v is not None and k != 'missing_alt_tags'}
        if page_metrics_for_chart:
            fig_bar = create_page_metrics_bar_chart(page_metrics_for_chart, lang)
            if fig_bar: st.plotly_chart(fig_bar, use_container_width=True)
            else: st.info(language_manager.get_text("page_metrics_not_available_hp", lang, fallback="Page Content Metrics (Homepage) not available."))
        else: st.info(language_manager.get_text("page_metrics_not_available_hp", lang, fallback="Page Content Metrics (Homepage) not available."))

    with col2:
        # Content Quality Overview Chart (New)
        site_health_indicators = metrics.get('site_health_indicators', {})
        fig_content_quality = create_content_quality_overview_chart(site_health_indicators, lang)
        if fig_content_quality:
            st.plotly_chart(fig_content_quality, use_container_width=True)
        else:
            st.info(language_manager.get_text("content_quality_overview_not_available", lang, fallback="Content Quality Overview data not available."))

        # Textual summary for content quality and SEO score
        crawled_pages_count = site_health_indicators.get('crawled_pages_count', 0)
        # Only show this advice if an analysis with crawled pages was actually performed.
        if crawled_pages_count > 0 and metrics['seo_score'] < 70:
            thin_pages = site_health_indicators.get('thin_content_page_count', 0)
            bad_titles = site_health_indicators.get('bad_format_title_page_count', 0)

            message_parts = []
            if thin_pages > 0:
                message_parts.append(
                    language_manager.get_text(
                        "content_issue_thin_pages_found", lang, count=thin_pages,
                        fallback=f"{thin_pages} page(s) with potentially thin content"
                    )
                )
            if bad_titles > 0:
                message_parts.append(
                    language_manager.get_text(
                        "content_issue_bad_titles_found", lang, count=bad_titles,
                        fallback=f"{bad_titles} page(s) with title format issues"
                    )
                )

            if message_parts:
                issues_string = " and ".join(message_parts) if len(message_parts) > 1 else message_parts[0]
                full_message = language_manager.get_text(
                    "low_score_content_advice", lang, issues=issues_string,
                    fallback=f"Your SEO score may be affected by content quality. Consider addressing: {issues_string}. Improving these areas can enhance your site's performance."
                )
                st.warning(full_message)
            else: # Score is low, but these specific content issues were not detected
                st.info(language_manager.get_text(
                    "low_score_other_factors", lang,
                    fallback="Your SEO score is below the optimal range. While major thin content or title format issues weren't detected site-wide from this scan, review other technical aspects, content relevance, and user experience to identify areas for improvement."
                ))
        st.markdown("<br>", unsafe_allow_html=True) # Add some spacing before the next chart


        # Technical SEO Status Chart
        technical_metrics_for_chart = {k:v for k,v in metrics.get('technical_metrics', {}).items() if v is not None}
        if technical_metrics_for_chart:
            fig_tech = create_technical_status_chart(technical_metrics_for_chart, lang)
            if fig_tech: st.plotly_chart(fig_tech, use_container_width=True)
            else: st.info(language_manager.get_text("technical_seo_status_not_available", lang, fallback="Technical SEO Status not available."))
        else: st.info(language_manager.get_text("technical_seo_status_not_available", lang, fallback="Technical SEO Status not available."))
    st.markdown("---")

# TWEAK 1: Added cached function for performance
@st.cache_data
def cached_extract_metrics(full_report_json):
    """Caches the metric extraction from the full report JSON to improve performance."""
    logging.info("Running metric extraction (will be cached on subsequent runs with same input).")
    return extract_metrics_from_report(full_report_json)

def display_styled_report(full_report_json, lang):
    # Use the cached function to extract metrics
    metrics = cached_extract_metrics(full_report_json)
    display_seo_dashboard(metrics, lang)

def run_main_app():
    # --- STEP 1: Initial Page Configuration ---
    # Configure the page and inject CSS immediately. This is critical to prevent the
    # default Streamlit navigation from flashing on screen (FOUC - Flash of Unstyled Content).
    st.set_page_config(
        page_title="RICAS Beta", 
        page_icon="📊", 
        layout="wide", 
        initial_sidebar_state="collapsed", 
        menu_items={'Get Help': 'https://www.seo1.com/help', 'Report a bug': "https://www.se10.com/bug", 'About': "# Raven Web Services"}
    )
    hide_pages_nav = """<style> div[data-testid="stSidebarNav"] {display: none !important;} </style>"""
    st.markdown(hide_pages_nav, unsafe_allow_html=True)

    # --- STEP 2: Render Initial UI & Basic Setup ---
    # Display the title and initialize session state right away. These are fast operations
    # and give the user immediate visual feedback that the app is loading.
    
    # --- NEW CODE START ---
    # Display the logo at the top of the page.
    # It assumes you have a folder named 'assets' in your root directory
    # with the logo file 'logo.png' inside it.
    try:
        st.image('assets/logo.png', width=200) # Adjust the width as needed
    except FileNotFoundError:
        # This will log a warning to your console if the file is not found,
        # but the app will continue to run without crashing.
        logging.warning("Logo file not found at 'assets/logo.png'. Skipping logo display.")
    # --- NEW CODE END ---

    st.title("Raven Intelligent Content Automation Solutions")
    init_shared_session_state()
    lang = st.session_state.language

    # --- STEP 3: Validate Configuration ---
    # Check for essential environment variables. This is a quick check.
    for config_name, config_value in {'Supabase URL': SUPABASE_URL, 'Supabase Key': SUPABASE_KEY}.items():
        if not config_value: st.error(f"{config_name} is missing."); st.stop()
    if not GEMINI_API_KEY and not MISTRAL_API_KEY: st.error(language_manager.get_text("no_ai_model", lang)); st.stop()

    # --- STEP 4: Initialize External Services & Dependent Logic ---
    # Now, initialize the Supabase client. This might be a slightly slower operation
    # (especially on the very first page load), so we do it after the initial UI is visible.
    supabase = init_supabase_client()
    
    # This function might depend on the supabase client, so it's placed here.
    if st.session_state.get("current_page") != "main":
        update_page_history("main")

    # --- STEP 5: Main Application Logic ---
    # Initialize remaining session state flags and then run the main app router.
    if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
    if "detailed_analysis_info" not in st.session_state: st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}

    if not st.session_state.authenticated:
        st.markdown(language_manager.get_text("welcome_seo", lang)); st.markdown(language_manager.get_text("enter_api_key", lang))
        languages = language_manager.get_available_languages(); language_names = {"en": "English", "tr": "Türkçe"}
        selected_language = st.selectbox("Language / Dil", languages, format_func=lambda x: language_names.get(x, x), index=languages.index(st.session_state.language))
        if selected_language != st.session_state.language: st.session_state.language = selected_language; st.rerun()
        with st.form("login_form"):
            api_key = st.text_input(language_manager.get_text("enter_api_key_label", lang), type="password")
            if st.form_submit_button(language_manager.get_text("login_button", lang)):
                is_authenticated, username = authenticate_user(api_key)
                if is_authenticated: st.session_state.authenticated = True; st.session_state.username = username; st.rerun()
                else: st.error(language_manager.get_text("login_failed", lang))
    else:
        st.markdown(language_manager.get_text("logged_in_as", lang, username=st.session_state.username))
        if st.session_state.analysis_complete and hasattr(st.session_state, 'full_report') and st.session_state.full_report and hasattr(st.session_state, 'url') and st.session_state.url: # Check full_report
            st.success(language_manager.get_text("analysis_complete_message", lang))
            st.markdown(f"### {language_manager.get_text('next_steps', lang)}"); st.markdown(language_manager.get_text("continue_optimizing", lang))
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_after_analysis", use_container_width=True): st.switch_page("pages/1_SEO_Helper.py")
            st.markdown(f"### {language_manager.get_text('content_generation_tools', lang)}"); st.markdown(language_manager.get_text("create_optimized_content", lang))
            col1, col2 = st.columns(2)
            with col1:
                if st.button(language_manager.get_text("article_writer_button", lang), key="article_writer_button_results", use_container_width=True): st.switch_page("pages/2_Article_Writer.py")
            with col2:
                if st.button(language_manager.get_text("product_writer_button", lang), key="product_writer_button_results", use_container_width=True): st.switch_page("pages/3_Product_Writer.py")
            display_detailed_analysis_status_enhanced(supabase, lang)
            st.subheader(language_manager.get_text("analysis_results_for_url", lang, url=st.session_state.url))
            display_styled_report(st.session_state.full_report, lang)

            if hasattr(st.session_state, 'text_report') and st.session_state.text_report: # Ensure text_report exists for raw data expander
                with st.expander(f"📄 {language_manager.get_text('raw_report_data_label', lang)}", expanded=False):
                    st.text_area(label=language_manager.get_text('seo_report_label', lang), value=st.session_state.text_report, height=300, help=language_manager.get_text('raw_report_help', lang))

            # Option to display full JSON report for debugging/advanced users
            if st.checkbox(language_manager.get_text("show_full_json_report", lang, fallback="Show Full JSON Report Data (for debugging)"), key="show_json_debug"):
                 with st.expander(f"🧬 {language_manager.get_text('full_json_report_label', lang, fallback='Full JSON Report')}", expanded=False):
                    st.json(st.session_state.full_report, expanded=False)

        else:
            st.markdown(f" {language_manager.get_text('platform_description', lang)}\n### {language_manager.get_text('getting_started', lang)}\n{language_manager.get_text('begin_by_analyzing', lang)}") #{## language_manager.get_text('welcome_message', lang)}\n
            if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
                with st.form("url_form_disabled"):
                    st.text_input(language_manager.get_text("enter_url_placeholder", lang), value=st.session_state.url_being_analyzed, placeholder="https://example.com", disabled=True)
                    st.info(language_manager.get_text("analyzing_website_main_page_info", lang, url=st.session_state.url_being_analyzed, fallback=f"Analysis for {st.session_state.url_being_analyzed} is in progress..."))
                    st.form_submit_button(language_manager.get_text("analyze_button", lang), disabled=True)
            else:
                with st.form("url_form_active"):
                    website_url_input = st.text_input(language_manager.get_text("enter_url_placeholder", lang), placeholder="https://example.com", key="main_url_input_active")
                    if st.form_submit_button(language_manager.get_text("analyze_button", lang)):
                        url_to_analyze = website_url_input.strip()
                        if not url_to_analyze: st.warning(language_manager.get_text("please_enter_url", lang, fallback="Please enter a URL."))
                        else:
                            normalized_url_attempt = normalize_url(url_to_analyze); valid_for_processing = False
                            if normalized_url_attempt:
                                try:
                                    parsed = urlparse(normalized_url_attempt)
                                    if parsed.scheme in ['http', 'https'] and parsed.hostname and ('.' in parsed.hostname or parsed.hostname.lower() == 'localhost' or re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", parsed.hostname)):
                                        valid_for_processing = True
                                except ValueError: pass # Error during parsing means invalid
                            # FIX: Pass the supabase client to the processing function
                            if valid_for_processing: asyncio.run(process_url(url_to_analyze, supabase, lang))
                            else: st.warning(language_manager.get_text("invalid_url_format_warning", lang, fallback="Invalid URL format. Please enter a valid website address (e.g., https://example.com)."))
            st.markdown(f"### {language_manager.get_text('analyze_with_ai', lang)}")
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_before_analysis"): st.switch_page("pages/1_SEO_Helper.py")
        common_sidebar()

if __name__ == "__main__":
    run_main_app()