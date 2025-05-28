# /SeoTree/main.py
import streamlit as st
import os
from dotenv import load_dotenv
import logging
import asyncio
import json # Already present, re-confirming
import re   # Added for data extraction
from datetime import datetime # Already present
import plotly.express as px # Added for Plotly Express
import plotly.graph_objects as go # Added for Plotly Graph Objects
# from plotly.subplots import make_subplots # Not used yet, can be added if complex subplots are needed
# import pandas as pd # Not strictly needed for these charts, can be added if complex data manipulation is required by Plotly

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
    st.session_state.url_being_analyzed = url
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
                
                # Get the report ID and detailed analysis status
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
                    
                    # FIXED LOGIC: Better status handling
                    if llm_analysis_completed:
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("full_site_analysis_complete", lang),
                            "status": "complete"
                        }
                        if llm_analysis_error:
                            logging.warning(f"Detailed analysis for report ID {report_id_for_detailed_analysis} (URL: {normalized_url}) is complete but has logged errors: {llm_analysis_error}")
                    elif llm_analysis_error:  # Error occurred and not completed
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_error_status", lang, llm_analysis_error),
                            "status": "error"
                        }
                    else:  # Not completed and no error (in progress or not started)
                        logging.info(f"Detailed analysis not complete for report ID {report_id_for_detailed_analysis}, triggering background process.")
                        st.session_state.detailed_analysis_info = {
                            "report_id": report_id_for_detailed_analysis,
                            "url": normalized_url,
                            "status_message": language_manager.get_text("detailed_analysis_inprogress", lang),
                            "status": "in_progress"
                        }
                        # FIXED: Use the correct function that exists
                        if not trigger_detailed_analysis_background_process(report_id_for_detailed_analysis):
                            st.session_state.detailed_analysis_info = {"report_id": None, "url": None, "status_message": "", "status": None}
                else:
                    logging.warning(f"Could not find report ID for existing report {normalized_url} to check detailed analysis status.")
            else:
                # New analysis case
                logging.info(f"Generating new report for {normalized_url}")
                st.info(language_manager.get_text("generating_new_analysis", lang))
                
                analysis_result = await analyze_website(normalized_url, supabase)
                
                if analysis_result and analysis_result[0] and analysis_result[1]:
                    text_report, full_report = analysis_result
                    logging.info("New analysis successfully generated")
                    
                    # Get the new report ID
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
                        # FIXED: Use the correct function that exists
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
                st.session_state.analysis_in_progress = False
                st.session_state.url_being_analyzed = None
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

# --- PRIORITY STYLING HELPER ---
PRIORITY_STYLES = {
    "critical": {"icon": "🚨", "class": "priority-high"},
    "high": {"icon": "🔥", "class": "priority-high"},
    "medium": {"icon": "⚠️", "class": "priority-medium"},
    "low": {"icon": "💡", "class": "priority-low"},
    "informational": {"icon": "ℹ️", "class": "priority-low"} 
}

def get_priority_styling_info(text_line_containing_priority):
    original_text = text_line_containing_priority
    priority_level_str = "medium" 
    normalized_line = original_text.lower()

    if "priority:" in normalized_line:
        try:
            temp_level = normalized_line.split("priority:", 1)[1].strip()
            priority_level_str = temp_level.split()[0].strip('*-.,:') # Clean up common trailing chars
        except IndexError:
            pass 

    best_match_key = "medium" 
    for key in PRIORITY_STYLES:
        if key in priority_level_str:
            best_match_key = key
            break
            
    style = PRIORITY_STYLES[best_match_key]
    # Return the full original text for display, not just the parsed level
    return style["icon"], style["class"], original_text


# --- Styled Report Display Functions (Modified) ---

def _get_main_section_details(section_title):
    """Helper to determine icon and default expansion for main sections."""
    title_lower = section_title.lower()
    expanded_default = title_lower in [
        "overall seo score & summary", 
        "recommendations & action plan",
        "website analysis summary" # Common summary titles
    ]
    icon = "📂" 
    if "summary" in title_lower or "overview" in title_lower: icon = "📊"
    elif "recommendation" in title_lower or "action plan" in title_lower: icon = "🎯"
    elif "technical seo" in title_lower: icon = "⚙️"
    elif "content analysis" in title_lower: icon = "📝"
    elif "keyword analysis" in title_lower: icon = "🔑"
    elif "on-page seo" in title_lower : icon = "📄"
    elif "subpage analysis" in title_lower or "sub-page" in title_lower : icon = "📑"
    elif "backlink" in title_lower: icon = "🔗"
    elif "mobile" in title_lower: icon = "📱"
    elif "speed" in title_lower or "performance" in title_lower: icon = "🚀"
    elif "security" in title_lower: icon = "🛡️"
    return icon, expanded_default

def display_styled_report(text_report, lang):
    """Display the SEO report with enhanced styling, structure, expanders, and visualizations."""
    st.markdown("""
    <style>
    .report-container {
        background: linear-gradient(135deg, #f0f2f5 0%, #e9ecef 100%);
        padding: 1.5rem; 
        border-radius: 10px; 
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08); 
    }
    .report-header {
        background: white;
        padding: 1.5rem; 
        border-radius: 8px; 
        margin-bottom: 1rem; 
        text-align: center;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05); 
        border-bottom: 3px solid #667eea; 
    }
    .analysis-section { 
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-top: 4px solid #667eea; 
    }
    /* Style for analysis-section when inside an expander */
    .streamlit-expander > div > div > .analysis-section { /* Target .analysis-section more robustly */
        margin-top: 0.5rem !important; 
        margin-bottom: 0.5rem !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.07) !important; 
        border-top: 2px solid #8998f0 !important; 
        padding: 1rem !important;
    }
    .section-title {
        color: #667eea;
        font-size: 1.4rem; 
        font-weight: 600; 
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #dee2e6; 
    }
    .subsection-title {
        color: #764ba2;
        font-size: 1.15rem; 
        font-weight: 600;
        margin: 1.2rem 0 0.7rem 0; 
    }
    .metric-card { /* ... (other existing styles from original) ... */ }
    .metric-value { /* ... */ }
    .metric-label { /* ... */ }
    .status-good { color: #155724; font-weight: 500; padding: 0.75rem 1rem; background: #d4edda; border-radius: 6px; border-left: 4px solid #28a745; margin: 0.5rem 0; }
    .status-warning { color: #856404; font-weight: 500; padding: 0.75rem 1rem; background: #fff3cd; border-radius: 6px; border-left: 4px solid #ffc107; margin: 0.5rem 0; }
    .status-error { color: #721c24; font-weight: 500; padding: 0.75rem 1rem; background: #f8d7da; border-radius: 6px; border-left: 4px solid #dc3545; margin: 0.5rem 0; }
    .keyword-tag { background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 0.3rem 0.7rem; border-radius: 15px; margin: 0.2rem; display: inline-block; font-size: 0.85rem; font-weight: 500; box-shadow: 0 1px 3px rgba(0,0,0,0.15); }
    .priority-high { background: #ffebee; border-left: 4px solid #f44336; padding: 1rem; margin: 0.75rem 0; border-radius: 8px; box-shadow: 0 2px 6px rgba(244,67,54,0.15); color: #c62828; }
    .priority-medium { background: #fff3e0; border-left: 4px solid #ff9800; padding: 1rem; margin: 0.75rem 0; border-radius: 8px; box-shadow: 0 2px 6px rgba(255,152,0,0.15); color: #e65100; }
    .priority-low { background: #e8f5e9; border-left: 4px solid #4caf50; padding: 1rem; margin: 0.5rem 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(76,175,80,0.2); color: #1b5e20; }
    .content-block { background: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; margin: 0.5rem 0; border-left: 3px solid #ced4da; font-size: 0.95rem; }
    .highlight-box { background: #e3f2fd; padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #2196f3; color: #01579b; }
    </style>
    """, unsafe_allow_html=True)
    
    # Extract metrics and display dashboard
    metrics = extract_metrics_from_report(text_report)
    display_seo_dashboard(metrics, lang) # Pass lang for localized chart titles
    
    lines = text_report.split('\n')
    st.markdown('<div class="report-container">', unsafe_allow_html=True)
    
    report_header_title = language_manager.get_text("seo_report_main_header_title", lang, fallback="SEO Analysis Report")
    report_header_subtitle = language_manager.get_text("seo_report_generated_time", lang, datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    report_header_tag = language_manager.get_text("seo_report_comprehensive_tag", lang, fallback="Comprehensive Website Analysis")


    st.markdown(f'''
    <div class="report-header">
        <h1 style="color: #667eea; margin-bottom: 0.3rem; font-size: 2rem;">📊 {report_header_title}</h1>
        <p style="color: #5a5a5a; margin: 0; font-size: 1rem;">{report_header_subtitle}</p>
        <div style="margin-top: 0.8rem;">
            <span style="background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 0.4rem 0.8rem; border-radius: 15px; font-weight: 500; font-size: 0.9rem;">
                🚀 {report_header_tag}
            </span>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    i = 0
    current_section_content = []
    section_title = ""
    first_section_found = False
    while i < len(lines):
        if lines[i].strip().startswith('## '):
            first_section_found = True
            break
        i += 1
    
    if not first_section_found:
        st.warning(language_manager.get_text("report_parse_error_raw_display", lang, fallback="Could not parse the report into sections. Displaying raw content."))
        st.markdown(f"<pre>{text_report}</pre>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Main parsing loop, i is already at the first '##' line
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('## '):
            if section_title and current_section_content: # Render previous section
                icon, expanded = _get_main_section_details(section_title)
                with st.expander(f"{icon} {section_title}", expanded=expanded):
                    display_report_section(section_title, current_section_content)
            
            section_title = line[3:].strip() # Start new section
            current_section_content = []
        elif line: # Accumulate content for current section_title
            if line.startswith('### '):
                current_section_content.append(('subsection', line[4:].strip()))
            elif line.startswith('#### '):
                current_section_content.append(('subsubsection', line[5:].strip()))
            elif "✅" in line or "⚠️" in line or "❌" in line:
                current_section_content.append(('status', line))
            elif line.startswith('- '):
                current_section_content.append(('bullet', line[2:].strip()))
            elif line.startswith('**') and line.endswith('**') and len(line) > 4:
                current_section_content.append(('bold_kv', line[2:-2]))
            elif not line.startswith('#'): 
                current_section_content.append(('text', line))
        i += 1
    
    if section_title and current_section_content: # Display the last section
        icon, expanded = _get_main_section_details(section_title)
        with st.expander(f"{icon} {section_title}", expanded=expanded):
            display_report_section(section_title, current_section_content)
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_report_section(title, content_items):
    st.markdown(f'<div class="analysis-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title" style="margin-top:0;">{title}</div>', unsafe_allow_html=True)
    
    current_subsection_title = ""
    subsection_elements = []

    def render_subsection_if_needed():
        nonlocal current_subsection_title # Important for modifying outer scope var
        if current_subsection_title and subsection_elements:
            is_subpage_report = any(kw in current_subsection_title.lower() for kw in ["subpage:", "analysis for http", "analysis of /", "details for /", "page analysis:"]) and "/" in current_subsection_title

            if is_subpage_report and len(subsection_elements) > 0: 
                has_critical_issue = any(
                    ("❌" in el_text or any(p_key in el_text.lower() for p_key in ["priority: high", "priority: critical"]))
                    for _, el_text in subsection_elements
                )
                sub_expander_icon = "📃" 
                expanded_sub_default = False
                if has_critical_issue:
                    sub_expander_icon = "❗️"
                    expanded_sub_default = True
                elif len(subsection_elements) < 5: 
                    expanded_sub_default = True

                with st.expander(f"{sub_expander_icon} {current_subsection_title}", expanded=expanded_sub_default):
                    _display_elements_for_subsection(subsection_elements)
            else:
                st.markdown(f'<div class="subsection-title">{current_subsection_title}</div>', unsafe_allow_html=True)
                _display_elements_for_subsection(subsection_elements)
            
            subsection_elements.clear()
            current_subsection_title = "" 

    for item_type, item_text in content_items:
        if item_type == 'subsection':
            render_subsection_if_needed() 
            current_subsection_title = item_text 
        elif item_type == 'subsubsection': 
            if current_subsection_title: 
                subsection_elements.append((item_type, item_text))
            else: 
                st.markdown(f'<div class="subsection-title" style="font-size: 1.05rem; color: #5c4388;">{item_text}</div>', unsafe_allow_html=True)
        elif current_subsection_title: 
            subsection_elements.append((item_type, item_text))
        else: 
            _render_single_item(item_type, item_text, indent=False)

    render_subsection_if_needed() 
    st.markdown('</div>', unsafe_allow_html=True)

def _render_single_item(item_type, item_text, indent=False):
    """Helper to render individual content items with optional indent."""
    style_attr = 'style="margin-left: 1rem;"' if indent else ''

    if item_type == 'status':
        cls, icon_char = "", ""
        if "✅" in item_text: cls, icon_char = "status-good", "✅"
        elif "⚠️" in item_text: cls, icon_char = "status-warning", "⚠️"
        elif "❌" in item_text: cls, icon_char = "status-error", "❌"
        if cls:
            st.markdown(f'<div class="{cls}" {style_attr}>{icon_char} {item_text.replace(icon_char, "").strip()}</div>', unsafe_allow_html=True)
    elif item_type == 'bullet':
        base_style = "padding-left: 1.5rem; position: relative;"
        indent_style = "margin-left: 1rem;" if indent else ""
        st.markdown(f'<div class="content-block" style="{base_style} {indent_style}"><span style="position: absolute; left: 0.5rem; top: 0.8rem;">•</span>{item_text}</div>', unsafe_allow_html=True)
    elif item_type == 'bold_kv':
        if "priority:" in item_text.lower():
            icon, css_class, full_text = get_priority_styling_info(item_text)
            st.markdown(f'<div class="{css_class}" {style_attr}>{icon} <strong>{full_text}</strong></div>', unsafe_allow_html=True)
        elif ':' in item_text:
            key, value = item_text.split(':', 1)
            st.markdown(f'<div class="content-block" {style_attr}><strong>{key.strip()}:</strong> {value.strip()}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="content-block" {style_attr}><strong>{item_text}</strong></div>', unsafe_allow_html=True)
    elif item_type == 'text':
        if ':' in item_text and not item_text.startswith('http'):
            key, value = item_text.split(':', 1)
            st.markdown(f'<div class="content-block" {style_attr}><strong>{key.strip()}:</strong> {value.strip()}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="content-block" {style_attr}>{item_text}</div>', unsafe_allow_html=True)


def _display_elements_for_subsection(elements):
    """Renders a list of (item_type, item_text) elements, typically content of a subsection."""
    for item_type, item_text in elements:
        if item_type == 'subsubsection':
            st.markdown(f'<div class="subsection-title" style="font-size: 1.05rem; color: #5c4388; margin-left: 1rem; margin-top:1rem;">{item_text}</div>', unsafe_allow_html=True)
        elif item_type == 'bullet' and ('(' in item_text and ')' in item_text and any(k in item_text.lower() for k in ['found in', 'subpages', 'pages'])):
            parts = item_text.split('(', 1)
            keyword_name = parts[0].strip()
            details = "(" + parts[1].strip()
            st.markdown(f'<div><span class="keyword-tag" style="margin-right: 5px; margin-left: 1rem;">{keyword_name}</span> <span style="font-size:0.9em; color: #555;">{details}</span></div>', unsafe_allow_html=True)
        elif item_type == 'bold_kv' and "priority:" in item_text.lower(): # Priority lines within subsections
            icon, css_class, full_text = get_priority_styling_info(item_text)
            st.markdown(f'<div class="{css_class}" style="margin-left: 1rem;">{icon} <strong>{full_text}</strong></div>', unsafe_allow_html=True)
        elif item_type == 'bold_kv': # Other bold key-values
            if ':' in item_text: 
                key, value = item_text.split(':', 1)
                st.markdown(f'<div class="content-block" style="margin-top:0.8rem; margin-left: 1rem;"><strong>{key.strip()}:</strong> {value.strip()}</div>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<div class="content-block" style="margin-top:0.8rem; margin-left: 1rem;"><strong>{item_text}</strong></div>', unsafe_allow_html=True)
        elif item_type == 'text':
            if item_text.startswith('http'):
                st.markdown(f'<div class="content-block" style="margin-left: 1rem;">🔗 Target: <a href="{item_text}" target="_blank">{item_text}</a></div>', unsafe_allow_html=True)
            elif ':' in item_text:
                key, value = item_text.split(':', 1)
                key_lower, value_strip = key.strip().lower(), value.strip()
                if key_lower in ["summary", "keywords", "seo keyword suggestions", "overall tone", "target audience", "topic categories", "contact information & key mentions", "features", "benefits", "description", "focus keyword", "content length", "suggested title", "target page", "content gap addressed", "competitive advantage"]:
                    st.markdown(f'<div class="content-block" style="margin-bottom:0.3rem; margin-left: 1rem;"><strong>{key.strip()}:</strong></div>', unsafe_allow_html=True)
                    if key_lower in ["keywords", "seo keyword suggestions", "additional keywords", "topic categories"] and value_strip:
                        sub_items = [s.strip() for s in value_strip.split(',') if s.strip()]
                        if sub_items:
                            tags_html = "".join([f'<span class="keyword-tag" style="margin-left: 1.2rem; margin-right:0.2rem;">{s}</span>' for s in sub_items]) # slightly more indent for tags
                            st.markdown(tags_html, unsafe_allow_html=True)
                        elif value_strip:
                             st.markdown(f'<div style="padding-left:2rem;">{value_strip}</div>', unsafe_allow_html=True)
                    elif value_strip:
                        st.markdown(f'<div style="padding-left:2rem;">{value_strip}</div>', unsafe_allow_html=True)
                else: 
                    st.markdown(f'<div class="content-block" style="margin-left: 1rem;"><strong>{key.strip()}:</strong> {value_strip}</div>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<div class="content-block" style="margin-left: 1rem;">{item_text}</div>', unsafe_allow_html=True)
        else: # Fallback for other types if any, rendering with indent
             _render_single_item(item_type, item_text, indent=True)


# --- Main App ---

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
            # Filter out report display messages if we are showing a full styled report
            # For now, let's assume main.py doesn't use the chat interface itself, but other pages might.
            # If chat messages were to be shown here, they'd go here.
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
            
            # Use the new styled report display which now includes the dashboard
            display_styled_report(st.session_state.text_report, lang)
            
            # Optional: Add a collapsible raw report section for advanced users
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
            
            with st.form("url_form"):
                if st.session_state.analysis_in_progress and st.session_state.url_being_analyzed:
                    website_url = st.text_input(
                        language_manager.get_text("enter_url_placeholder", lang),
                        value=st.session_state.url_being_analyzed,
                        placeholder="https://example.com",
                        disabled=True
                    )
                    st.info(language_manager.get_text("analyzing_website", lang)) # This spinner is part of process_url
                    analyze_button = st.form_submit_button(
                        language_manager.get_text("analyze_button", lang),
                        disabled=True
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
        
        common_sidebar()

if __name__ == "__main__":
    run_main_app()
