

# /SeoTree/main.py
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
    except RuntimeError as re_err: # Renamed re to re_err to avoid conflict with re module
        error_msg = language_manager.get_text("detailed_analysis_runtime_error", st.session_state.get("language", "en"))
        logging.error(f"Runtime error during LLMAnalysisEndProcessor initialization for report ID {report_id}: {re_err} - {error_msg}")
        st.error(error_msg)
        return False
    except Exception as e:
        error_msg = language_manager.get_text("detailed_analysis_trigger_error", st.session_state.get("language", "en"))
        logging.error(f"Failed to trigger detailed analysis for report ID {report_id} via background thread: {e} - {error_msg}", exc_info=True)
        st.error(error_msg)
        return False

async def process_url(url, lang="en"):
    st.session_state.analysis_in_progress = True
    st.session_state.url_being_analyzed = url # Set the URL being analyzed early
    try:
        normalized_url = normalize_url(url) # normalize_url from s10tools
        # This initial normalization is primarily for logging and consistency.
        # If the URL was invalid and slipped past the UI check, it might still cause issues here or downstream.
        # However, the UI check added should prevent most structurally invalid URLs.
        if not normalized_url: # Defensive check, though UI should catch this
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
                    logging.info(f"Existing report ID: {report_id_for_detailed_analysis}, completed: {llm_analysis_completed}, error: {llm_analysis_error}")

                    if llm_analysis_completed:
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("full_site_analysis_complete", lang),
                            "status": "complete"
                        }
                        if llm_analysis_error:
                            logging.warning(f"Detailed analysis for report ID {report_id_for_detailed_analysis} (URL: {normalized_url}) is complete but has logged errors: {llm_analysis_error}")
                    elif llm_analysis_error:
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error),
                            "status": "error"
                        }
                    else:
                        logging.info(f"Detailed analysis not complete for report ID {report_id_for_detailed_analysis}, triggering background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        triggered_successfully = trigger_detailed_analysis_background_process(report_id_for_detailed_analysis)
                        if triggered_successfully:
                            st.session_state[f"auto_refresh_{report_id_for_detailed_analysis}"] = True
                            st.session_state[f"last_check_{report_id_for_detailed_analysis}"] = 0
                            st.session_state[f"analysis_start_time_{report_id_for_detailed_analysis}"] = time.time()
                        else:
                            st.session_state.detailed_analysis_info["status"] = "error"
                            st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text(
                                "detailed_analysis_trigger_failed_status", lang,
                                fallback="Failed to start detailed analysis process."
                            )
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
                        report_id_for_detailed_analysis = report_response.data[0]['id']
                        logging.info(f"New report ID: {report_id_for_detailed_analysis}. Triggering detailed analysis background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        triggered_successfully = trigger_detailed_analysis_background_process(report_id_for_detailed_analysis)
                        if triggered_successfully:
                            st.session_state[f"auto_refresh_{report_id_for_detailed_analysis}"] = True
                            st.session_state[f"last_check_{report_id_for_detailed_analysis}"] = 0
                            st.session_state[f"analysis_start_time_{report_id_for_detailed_analysis}"] = time.time()
                        else:
                            st.session_state.detailed_analysis_info["status"] = "error"
                            st.session_state.detailed_analysis_info["status_message"] = language_manager.get_text(
                                "detailed_analysis_trigger_failed_status", lang,
                                fallback="Failed to start detailed analysis process."
                            )
                    else:
                        logging.warning(f"Could not find report ID for new analysis {normalized_url} to trigger detailed analysis.")
                else:
                    st.error(language_manager.get_text("failed_to_analyze", lang))
                    logging.error(f"Analysis failed for {normalized_url}")
                    # Clear analysis_in_progress states as the core analysis failed
                    st.session_state.analysis_in_progress = False
                    st.session_state.url_being_analyzed = None
                    return

            if text_report and full_report:
                logging.info(f"Displaying initial report for {normalized_url}")
                # display_report will set analysis_in_progress = False and url_being_analyzed = None
                display_report(text_report, full_report, normalized_url)
            else:
                st.error(language_manager.get_text("report_data_unavailable", lang))
                logging.error(f"Report data (text_report or full_report) is None for {normalized_url} before display_report call.")
                st.session_state.analysis_in_progress = False
                st.session_state.url_being_analyzed = None

    except Exception as e:
        error_message = f"Error in process_url: {str(e)}"
        st.error(error_message)
        logging.error(error_message, exc_info=True)
        st.session_state.analysis_in_progress = False
        st.session_state.url_being_analyzed = None

# --- DATA EXTRACTION AND VISUALIZATION FUNCTIONS ---

def extract_metrics_from_report(text_report):
    """Extract key metrics from the SEO report for visualization."""
    metrics = {
        'seo_score': None,
        'issues_by_priority': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
        'page_metrics': {}, # e.g., word_count, images, internal_links, external_links, headings
        'technical_metrics': {'robots_txt_status': None} # e.g., mobile_friendly, ssl_secure, page_speed, meta_description, title_tag, robots_txt_status
    }

    if not text_report: # Handle empty report
        return metrics

    lines = text_report.split('\n')

    # Extract SEO Score
    for line in lines:
        if 'seo score' in line.lower() or 'overall score' in line.lower():
            score_match = re.search(r'(\d+)(?:/100|\%)?', line) # Made /100 or % optional
            if score_match:
                try:
                    metrics['seo_score'] = int(score_match.group(1))
                    break
                except ValueError:
                    logging.warning(f"Could not parse SEO score from: {line}")

    # Count issues by priority
    for line in lines:
        line_lower = line.lower()
        if 'priority:' in line_lower: # This should catch "**Priority**: High" as well
            if 'critical' in line_lower:
                metrics['issues_by_priority']['critical'] += 1
            elif 'high' in line_lower:
                metrics['issues_by_priority']['high'] += 1
            elif 'medium' in line_lower:
                metrics['issues_by_priority']['medium'] += 1
            elif 'low' in line_lower:
                metrics['issues_by_priority']['low'] += 1

    # Extract page metrics
    for line in lines:
        if ':' in line and not line.startswith('#'): # Avoid section titles
            key_value = line.split(':', 1)
            if len(key_value) == 2:
                key, value_str = key_value[0].strip().lower(), key_value[1].strip()

                number_match = re.search(r'(\d+)', value_str)
                if number_match:
                    try:
                        num_value = int(number_match.group(1))

                        if 'word count' in key:
                            metrics['page_metrics']['word_count'] = num_value
                        elif ('image' in key or 'images' in key) and ('number of' in key or 'count' in key or 'total' in key or 'found' in key): # More robust image count
                            metrics['page_metrics']['images'] = num_value
                        elif 'internal link' in key:
                            metrics['page_metrics']['internal_links'] = num_value
                        elif 'external link' in key:
                            metrics['page_metrics']['external_links'] = num_value
                        # More robust headings count
                        elif ('heading' in key or 'headings' in key or 'h1 tag' in key) and \
                             ('count' in key or 'number of' in key or 'total' in key or 'found' in key or 'tags:' in key_value[0].strip()):
                            metrics['page_metrics']['headings'] = num_value
                    except ValueError:
                        logging.warning(f"Could not parse number for page metric '{key}' from: {value_str}")

    # Extract technical performance indicators
    for line in lines:
        line_lower = line.lower()
        status_category = None
        if '✅' in line: status_category = 'good'
        elif '⚠️' in line: status_category = 'warning'
        elif '❌' in line: status_category = 'error'
        else: continue

        # More robust mobile friendly check
        if 'mobile-friendly' in line_lower or \
           'mobile usability' in line_lower or \
           'mobile optimization' in line_lower or \
           ('mobile' in line_lower and 'optimized' in line_lower):
            metrics['technical_metrics']['mobile_friendly'] = status_category
        elif ('ssl certificate' in line_lower or 'https' in line_lower) and ('secure' in line_lower or 'active' in line_lower):
            metrics['technical_metrics']['ssl_secure'] = status_category
        elif 'page speed' in line_lower or 'loading time' in line_lower or 'performance' in line_lower and not 'score' in line_lower: # Avoid performance score line
            metrics['technical_metrics']['page_speed'] = status_category
        elif 'meta description' in line_lower and ('present' in line_lower or 'length' in line_lower or 'missing' in line_lower):
            metrics['technical_metrics']['meta_description'] = status_category
        elif 'title tag' in line_lower and ('length' in line_lower or 'present' in line_lower or 'missing' in line_lower):
            metrics['technical_metrics']['title_tag'] = status_category
        elif 'robots.txt' in line_lower and ('file' in line_lower or 'found' in line_lower or 'status' in line_lower): # New: Robots.txt status
            metrics['technical_metrics']['robots_txt_status'] = status_category

    return metrics

def create_seo_score_gauge(score, lang="en"):
    """Create a gauge chart for SEO score."""
    if score is None:
        score = 0 # Default to 0 if no score is found

    title_text = language_manager.get_text("seo_score_gauge_title", lang, fallback="SEO Score")

    fig = go.Figure(go.Indicator(
        mode = "gauge+number", # Removed delta as it might be confusing without clear context
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title_text, 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#667eea"}, # Main bar color
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': '#f8d7da'},  # Light red for poor
                {'range': [50, 80], 'color': '#fff3cd'}, # Light yellow for average
                {'range': [80, 100], 'color': '#d4edda'} # Light green for good
            ],
            'threshold': { # Example threshold line
                'line': {'color': "red", 'width': 3},
                'thickness': 0.75,
                'value': score # Shows current value on threshold line (can be static like 90)
            }
        }
    ))

    fig.update_layout(
        height=280, # Adjusted height
        margin=dict(l=20, r=20, t=50, b=20),
        font={'color': "#333", 'family': "Arial, sans-serif"}
    )

    return fig

def create_issues_pie_chart(issues_data, lang="en"):
    """Create a pie chart for issues by priority."""
    labels = []
    values = []
    colors = []

    priority_map = {
        'critical': language_manager.get_text("priority_critical", lang, fallback="Critical"),
        'high': language_manager.get_text("priority_high", lang, fallback="High"),
        'medium': language_manager.get_text("priority_medium", lang, fallback="Medium"),
        'low': language_manager.get_text("priority_low", lang, fallback="Low")
    }
    color_map = {
        'critical': '#dc3545', # Red
        'high': '#fd7e14',     # Orange
        'medium': '#ffc107',   # Yellow
        'low': '#28a745'       # Green
    }

    for priority_key, count in issues_data.items():
        if count > 0:
            labels.append(f'{priority_map.get(priority_key, priority_key.title())} ({count})')
            values.append(count)
            colors.append(color_map.get(priority_key, '#cccccc')) # Default color

    if not values: # No issues found
        labels = [language_manager.get_text("no_issues_found_pie", lang, fallback="No Issues Found")]
        values = [1]
        colors = ['#17a2b8'] # Info color

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4, # Donut chart
        marker_colors=colors,
        textinfo='percent+label',
        insidetextorientation='radial'
    )])

    fig.update_layout(
        title_text=language_manager.get_text("issues_by_priority_pie_title", lang, fallback="Issues by Priority"),
        height=380, # Adjusted height
        showlegend=False, # Legend can be redundant with textinfo
        margin=dict(l=20, r=20, t=50, b=20),
        font={'family': "Arial, sans-serif"}
    )

    return fig

def create_page_metrics_bar_chart(page_metrics_data, lang="en"):
    """Create a bar chart for page metrics."""
    if not page_metrics_data:
        return None # Or a message saying "No page metrics available"

    metric_names_map = {
        'word_count': language_manager.get_text("metric_word_count", lang, fallback="Word Count"),
        'images': language_manager.get_text("metric_images", lang, fallback="Images"),
        'internal_links': language_manager.get_text("metric_internal_links", lang, fallback="Internal Links"),
        'external_links': language_manager.get_text("metric_external_links", lang, fallback="External Links"),
        'headings': language_manager.get_text("metric_headings", lang, fallback="Headings")
    }

    metrics = []
    values = []

    for metric_key, value in page_metrics_data.items():
        if value is not None: # Only include metrics that have a value
            metrics.append(metric_names_map.get(metric_key, metric_key.replace('_', ' ').title()))
            values.append(value)

    if not metrics: return None

    fig = go.Figure(data=[
        go.Bar(
            x=metrics,
            y=values,
            text=values,
            textposition='auto',
            marker_color=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'] * (len(metrics)//5 + 1) # Cycle colors
        )
    ])

    fig.update_layout(
        title_text=language_manager.get_text("page_content_metrics_bar_title", lang, fallback="Page Content Metrics"),
        xaxis_title=language_manager.get_text("metrics_axis_label", lang, fallback="Metrics"),
        yaxis_title=language_manager.get_text("count_axis_label", lang, fallback="Count"),
        height=380, # Adjusted height
        margin=dict(l=20, r=20, t=50, b=20),
        font={'family': "Arial, sans-serif"}
    )

    return fig

def create_technical_status_chart(technical_metrics_data, lang="en"):
    """Create a status chart for technical SEO factors."""
    if not technical_metrics_data:
        return None

    tech_factor_map = {
        'mobile_friendly': language_manager.get_text("tech_mobile_friendly", lang, fallback="Mobile Friendly"),
        'ssl_secure': language_manager.get_text("tech_ssl_secure", lang, fallback="SSL Secure"),
        'page_speed': language_manager.get_text("tech_page_speed", lang, fallback="Page Speed"),
        'meta_description': language_manager.get_text("tech_meta_description", lang, fallback="Meta Description"),
        'title_tag': language_manager.get_text("tech_title_tag", lang, fallback="Title Tag"),
        'robots_txt_status': language_manager.get_text("tech_robots_txt", lang, fallback="Robots.txt Status") # Added new metric
    }

    categories = []
    status_texts = [] # Good, Warning, Error
    colors = []

    status_color_map = {
        'good': '#28a745',    # Green
        'warning': '#ffc107', # Yellow
        'error': '#dc3545'    # Red
    }
    status_text_map = {
        'good': language_manager.get_text("status_good", lang, fallback="Good"),
        'warning': language_manager.get_text("status_warning", lang, fallback="Warning"),
        'error': language_manager.get_text("status_error", lang, fallback="Error")
    }

    for category_key, status_val in technical_metrics_data.items():
        if status_val is not None: # Only include metrics that have a status
            categories.append(tech_factor_map.get(category_key, category_key.replace('_', ' ').title()))
            status_texts.append(status_text_map.get(status_val, str(status_val).title())) # Ensure status_val is a string for .title()
            colors.append(status_color_map.get(status_val, '#cccccc'))

    if not categories: return None

    # Using horizontal bar chart for better readability of categories
    fig = go.Figure()
    for i in range(len(categories)):
        fig.add_trace(go.Bar(
            y=[categories[i]], # Category names on y-axis
            x=[1],             # All bars have a "length" of 1 for visual representation
            name=status_texts[i],
            orientation='h',
            marker_color=colors[i],
            text=status_texts[i], # Display status text on bar
            textposition="inside",
            insidetextanchor="middle"
        ))

    fig.update_layout(
        title_text=language_manager.get_text("technical_seo_status_title", lang, fallback="Technical SEO Status"),
        barmode='stack', # Though we add traces one by one, this is good practice for categorical bars
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0,1]), # Hide X-axis numbers
        yaxis=dict(autorange="reversed"), # Optional: reverse order if needed
        height=max(300, len(categories) * 60), # Dynamic height
        showlegend=False,
        margin=dict(l=150, r=20, t=50, b=20), # Adjust left margin for category names
        font={'family': "Arial, sans-serif"}
    )
    return fig

def display_seo_dashboard(metrics, lang="en"):
    """Display the SEO dashboard with various charts."""

    st.markdown(f"### {language_manager.get_text('seo_dashboard_main_title', lang, fallback='📊 SEO Analysis Dashboard')}")

    # Create columns for layout
    col1, col2 = st.columns(2)

    with col1:
        if metrics['seo_score'] is not None:
            fig_gauge = create_seo_score_gauge(metrics['seo_score'], lang)
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            # Display gauge at 0 if score is None, as per create_seo_score_gauge logic
            fig_gauge = create_seo_score_gauge(None, lang)
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.caption(language_manager.get_text("seo_score_not_available_caption", lang, fallback="SEO Score not explicitly found in report."))

        page_metrics_chart_data = {k: v for k, v in metrics.get('page_metrics', {}).items() if v is not None}
        if page_metrics_chart_data:
            fig_bar = create_page_metrics_bar_chart(page_metrics_chart_data, lang)
            if fig_bar:
                st.plotly_chart(fig_bar, use_container_width=True)
            else: # Should not happen if page_metrics_chart_data is not empty
                 st.info(language_manager.get_text("page_metrics_not_available", lang, fallback="Page Content Metrics not available."))
        else:
            st.info(language_manager.get_text("page_metrics_not_available", lang, fallback="Page Content Metrics not available."))

    with col2:
        # issues_by_priority will always exist, even if all counts are 0
        fig_pie = create_issues_pie_chart(metrics['issues_by_priority'], lang)
        st.plotly_chart(fig_pie, use_container_width=True)

        technical_metrics_chart_data = {k: v for k, v in metrics.get('technical_metrics', {}).items() if v is not None}
        if technical_metrics_chart_data:
            fig_tech = create_technical_status_chart(technical_metrics_chart_data, lang)
            if fig_tech:
                st.plotly_chart(fig_tech, use_container_width=True)
            else: # Should not happen if technical_metrics_chart_data is not empty
                st.info(language_manager.get_text("technical_seo_status_not_available", lang, fallback="Technical SEO Status not available."))
        else:
            st.info(language_manager.get_text("technical_seo_status_not_available", lang, fallback="Technical SEO Status not available."))
    st.markdown("---") # Add a separator


def display_styled_report(text_report, lang):
    """Display the SEO report with enhanced styling, structure, expanders, and visualizations."""

    metrics = extract_metrics_from_report(text_report)
    display_seo_dashboard(metrics, lang) # Pass lang for localized chart titles


def run_main_app():
    st.set_page_config(
        page_title="Raven Web Services Beta",
        page_icon="📊", # Changed icon to reflect dashboard
        layout="wide",
        initial_sidebar_state="collapsed",
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

    st.title("Raven Web Servies")
    init_shared_session_state() #

    if "language" not in st.session_state:
        st.session_state.language = "en" #
    lang = st.session_state.language

    # Call update_page_history for the main page
    if st.session_state.current_page != "main":
        update_page_history("main")

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
                    st.rerun()
                else:
                    st.error(language_manager.get_text("login_failed", lang))
    else:
        st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))

        if "messages" in st.session_state: # This is for chat messages, typically not used on main page report view
            pass


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

            display_detailed_analysis_status_enhanced(supabase, lang)

            st.subheader(language_manager.get_text("analysis_results_for_url", lang, st.session_state.url))

            display_styled_report(st.session_state.text_report, lang)

            with st.expander(f"📄 {language_manager.get_text('raw_report_data_label', lang)}", expanded=False):
                st.text_area(
                    label=language_manager.get_text('seo_report_label', lang),
                    value=st.session_state.text_report,
                    height=300,
                    help=language_manager.get_text('raw_report_help', lang)
                )

        else:
            st.markdown(f"""
            ## {language_manager.get_text("welcome_message", lang)}
            {language_manager.get_text("platform_description", lang)}
            ### {language_manager.get_text("getting_started", lang)}
            {language_manager.get_text("begin_by_analyzing", lang)}
            """)

            if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
                # Display a disabled form while analysis is in progress
                with st.form("url_form_disabled"):
                    st.text_input(
                        language_manager.get_text("enter_url_placeholder", lang),
                        value=st.session_state.url_being_analyzed,
                        placeholder="https://example.com",
                        disabled=True
                    )
                    # The spinner is primarily handled within process_url.
                    # An additional info message here confirms the state.
                    st.info(language_manager.get_text("analyzing_website_main_page_info", lang,
                                                    url=st.session_state.url_being_analyzed,
                                                    fallback=f"Analysis for {st.session_state.url_being_analyzed} is in progress..."))
                    st.form_submit_button(
                        language_manager.get_text("analyze_button", lang),
                        disabled=True
                    )
            else:
                # Display active form for new URL input
                with st.form("url_form_active"):
                    website_url_input = st.text_input(
                        language_manager.get_text("enter_url_placeholder", lang),
                        placeholder="https://example.com", 
                        key="main_url_input_active"
                    )
                    analyze_button_active = st.form_submit_button(language_manager.get_text("analyze_button", lang))

                    if analyze_button_active:
                        url_to_analyze = website_url_input.strip()
                        if not url_to_analyze:
                            st.warning(language_manager.get_text("please_enter_url", lang, fallback="Please enter a URL."))
                        else:
                            # Attempt to normalize the URL. s10tools.normalize_url handles basic corrections.
                            normalized_url_attempt = normalize_url(url_to_analyze)

                            valid_for_processing = False
                            if normalized_url_attempt:
                                try:
                                    parsed = urlparse(normalized_url_attempt)
                                    # A valid URL for web analysis must have http/https scheme and a valid hostname.
                                    if parsed.scheme in ['http', 'https'] and parsed.hostname:
                                        hostname = parsed.hostname
                                        # Check if hostname contains a dot (common for FQDNs),
                                        # or is 'localhost', or is a simple IP address.
                                        # This filters out inputs like "http://sometext" where "sometext" becomes hostname.
                                        if '.' in hostname or \
                                           hostname.lower() == 'localhost' or \
                                           re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
                                            valid_for_processing = True
                                except ValueError:
                                    # urlparse might fail for extremely malformed strings, though normalize_url should prevent this.
                                    pass # Treat as invalid if any error occurs during parsing

                            if valid_for_processing:
                                # The original url_to_analyze is passed. process_url will normalize it again.
                                asyncio.run(process_url(url_to_analyze, lang))
                            else:
                                st.warning(language_manager.get_text("invalid_url_format_warning", lang,
                                                                   fallback="Invalid URL format. Please enter a valid website address (e.g., https://example.com or http://localhost:8080)."))
                                                                   
            st.markdown(f"### {language_manager.get_text('analyze_with_ai', lang)}")
            if st.button(language_manager.get_text("seo_helper_button", lang), key="seo_helper_button_before_analysis"):
                st.switch_page("pages/1_SEO_Helper.py")

        common_sidebar()

if __name__ == "__main__":
    run_main_app()
