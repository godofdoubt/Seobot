#pages/3_Product_Writer.py
import streamlit as st
import asyncio
import os
import logging # Import logging
from dotenv import load_dotenv
from supabase import create_client, Client
# Ensure update_page_history is imported
from utils.shared_functions import init_shared_session_state, common_sidebar, update_page_history, load_saved_report
from utils.language_support import language_manager
# Ensure the generation function is importable
from buttons.generate_product_description import generate_product_description


# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Product Writer - Se10 AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="auto"
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

def check_auth():
    """Check if user is authenticated"""
    lang = st.session_state.language if "language" in st.session_state else "en"
    if not st.session_state.authenticated:
        st.warning(language_manager.get_text("authentication_required", lang))
        if st.button(language_manager.get_text("go_to_login", lang)): # Added a button to go to main
            st.switch_page("main.py")
        st.stop()

def format_product_details_for_textarea(details_dict, seo_keywords_list, lang="en"):
    """Formats structured product details and SEO keywords into a string for a textarea."""
    if not isinstance(details_dict, dict):
        details_dict = {}
    if not isinstance(seo_keywords_list, list):
        seo_keywords_list = []

    output_parts = []

    # Features
    features = details_dict.get("features", [])
    if features:
        output_parts.append(f"**{language_manager.get_text('features_label', lang, fallback='Features')}:**")
        for item in features:
            output_parts.append(f"- {item}")
        output_parts.append("")

    # Benefits
    benefits = details_dict.get("benefits", [])
    if benefits:
        output_parts.append(f"**{language_manager.get_text('benefits_label', lang, fallback='Benefits')}:**")
        for item in benefits:
            output_parts.append(f"- {item}")
        output_parts.append("")

    # Target Audience
    target_audience = details_dict.get("target_audience")
    if target_audience:
        output_parts.append(f"**{language_manager.get_text('target_audience_label', lang, fallback='Target Audience')}:**")
        output_parts.append(target_audience)
        output_parts.append("")
    
    # Competitive Advantage
    competitive_advantage = details_dict.get("competitive_advantage") # As per example structure
    if competitive_advantage:
        output_parts.append(f"**{language_manager.get_text('competitive_advantage_label', lang, fallback='Competitive Advantage')}:**")
        output_parts.append(competitive_advantage)
        output_parts.append("")

    # SEO Keywords
    if seo_keywords_list:
        output_parts.append(f"**{language_manager.get_text('suggested_seo_keywords_label', lang, fallback='Suggested SEO Keywords')}:**")
        output_parts.append(", ".join(seo_keywords_list))
        output_parts.append("")

    return "\n".join(output_parts).strip()

def render_product_writer_sidebar_options():
    """Renders product-specific options in the sidebar."""
    lang = st.session_state.language
    st.sidebar.markdown(f"### {language_manager.get_text('product_options_title', lang, fallback='Product Options')}") 

    if "product_options" not in st.session_state or not isinstance(st.session_state.product_options, dict):
        st.session_state.product_options = {
            "product_name": "",
            "product_details": "",
            "tone": "Professional", 
            "length": "Medium"      
        }

    st.session_state.product_options["product_name"] = st.sidebar.text_input(
        label=language_manager.get_text("product_name", lang, fallback="Product Name"),
        value=st.session_state.product_options.get("product_name", ""),
        placeholder=language_manager.get_text("product_name_placeholder", lang, fallback="Enter the name of the product")
    )

    st.session_state.product_options["product_details"] = st.sidebar.text_area(
        label=language_manager.get_text("product_details", lang, fallback="Product Details"),
        value=st.session_state.product_options.get("product_details", ""),
        placeholder=language_manager.get_text("product_details_placeholder", lang, fallback="Enter product features, benefits, specifications, target audience, etc."),
        height=250 # Increased height for potentially longer pre-filled content
    )

    tone_keys = ["tone_professional", "tone_casual", "tone_enthusiastic", "tone_technical", "tone_friendly"]
    tone_display_options = [language_manager.get_text(key, lang) for key in tone_keys]
    internal_to_display_map_tone = {
        "Professional": language_manager.get_text("tone_professional", lang),
        "Casual": language_manager.get_text("tone_casual", lang),
        "Enthusiastic": language_manager.get_text("tone_enthusiastic", lang),
        "Technical": language_manager.get_text("tone_technical", lang),
        "Friendly": language_manager.get_text("tone_friendly", lang),
    }
    current_tone_internal = st.session_state.product_options.get("tone", "Professional")
    current_display_value_tone = internal_to_display_map_tone.get(current_tone_internal, tone_display_options[0]) 
    try:
        current_index_tone = tone_display_options.index(current_display_value_tone)
    except ValueError:
            logging.warning(f"Product Writer: Tone '{current_display_value_tone}' (internal: '{current_tone_internal}') not in display options. Defaulting index.")
            current_index_tone = 0 

    selected_tone_display = st.sidebar.selectbox(
        label=language_manager.get_text("product_tone", lang, fallback="Tone"), 
        options=tone_display_options,
        index=current_index_tone
    )
    display_to_internal_map_tone = {v: k for k, v in internal_to_display_map_tone.items()}
    st.session_state.product_options["tone"] = display_to_internal_map_tone.get(selected_tone_display, "Professional")

    length_keys = ["product_length_short", "product_length_medium", "product_length_long"]
    length_display_options = [language_manager.get_text(key, lang) for key in length_keys]
    internal_to_display_map_length = {
        "Short": language_manager.get_text("product_length_short", lang),
        "Medium": language_manager.get_text("product_length_medium", lang),
        "Long": language_manager.get_text("product_length_long", lang),
    }
    current_length_internal = st.session_state.product_options.get("length", "Medium")
    current_display_value_length = internal_to_display_map_length.get(current_length_internal, length_display_options[1]) 
    try:
        current_index_length = length_display_options.index(current_display_value_length)
    except ValueError:
            logging.warning(f"Product Writer: Length '{current_display_value_length}' (internal: '{current_length_internal}') not in display options. Defaulting index.")
            current_index_length = 1 

    selected_length_display = st.sidebar.selectbox(
        label=language_manager.get_text("product_length", lang, fallback="Description Length"),
        options=length_display_options,
        index=current_index_length
    )
    display_to_internal_map_length = {v: k for k, v in internal_to_display_map_length.items()}
    st.session_state.product_options["length"] = display_to_internal_map_length.get(selected_length_display, "Medium")

    if st.sidebar.button(language_manager.get_text("generate_product_description", lang, fallback="Generate Product Description")):
        st.session_state.product_description_requested = True
        # No st.rerun() here, let the flag be processed in the main flow

async def main():
    # Initialize shared session state
    init_shared_session_state()

    # Get current language
    lang = st.session_state.language if "language" in st.session_state else "en"

    st.title(language_manager.get_text("product_writer_button", lang, fallback="Product Writer"))

    # Initialize product description generation flag if not present
    if "product_description_requested" not in st.session_state:
        st.session_state.product_description_requested = False

    # Set current page to product and update history - THIS IS THE KEY CALL
    if st.session_state.current_page != "product":
        update_page_history("product") # This will set the welcome message or restore history

    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Check if user is authenticated
    check_auth()

    # --- START: Fix for Product Writer Welcome Message ---
    target_welcome_message_product = ""
    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message_product = language_manager.get_text(
            "welcome_product_writer_analyzed",
            lang,
            st.session_state.url,
            fallback=f"Welcome to the Product Writer page.\nUsing analysis for: **{st.session_state.url}**"
        )
    else:
        target_welcome_message_product = language_manager.get_text(
            "welcome_product_writer_not_analyzed",
            lang,
            fallback="Welcome to the Product Writer page. Please analyze a website in the SEO Helper page first to proceed."
        )

    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_product}]
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
        # Only update if the content is different, to avoid unnecessary reruns if already correct
        if st.session_state.messages[0].get("content") != target_welcome_message_product:
            st.session_state.messages[0]["content"] = target_welcome_message_product
    # --- END: Fix for Product Writer Welcome Message ---

    # --- NEW BLOCK START: Process list/item(s) of product descriptions from SEO Helper ---
    products_processed_in_this_run = False
    products_to_add_to_chat = []
    processed_product_names_this_run = set() # To help de-duplicate within this run

    # Process the primary state: products_pending_display_on_pw (list of dicts)
    # Use pop to get and remove the data, ensuring it's processed once.
    pending_products_data = st.session_state.pop("products_pending_display_on_pw", None) 

    if pending_products_data:
        # Ensure pending_products_data is treated as a list
        if not isinstance(pending_products_data, list):
            logging.warning(f"Product Writer: 'products_pending_display_on_pw' was not a list (type: {type(pending_products_data)}). Wrapping in a list. Data: {str(pending_products_data)[:200]}")
            pending_products_data = [pending_products_data]

        logging.info(f"Product Writer: Processing {len(pending_products_data)} item(s) from 'products_pending_display_on_pw' state.")
        for product_details in pending_products_data:
            if isinstance(product_details, dict) and "name" in product_details and "description" in product_details:
                products_to_add_to_chat.append(product_details)
                processed_product_names_this_run.add(product_details.get("name"))
            else:
                logging.warning(f"Product Writer: Skipping invalid product_details from 'products_pending_display_on_pw' source: {product_details}")
    
    # No legacy state to check for products like in Article Writer.

    if products_to_add_to_chat:
        if "messages" not in st.session_state: # Ensure messages list exists
            st.session_state.messages = []

        for i, product_info in enumerate(products_to_add_to_chat):
            product_name = product_info.get("name", f"Generated Product {i+1}") # Fallback name
            description = product_info.get("description", "No description.")
            
            product_display_message_content = f"**{language_manager.get_text('generated_product_from_seo_helper_title', lang, product_name=product_name, fallback=f'Generated Product Description (from SEO Helper): {product_name}')}**\n\n{description}"
            
            # Basic check to prevent adding the exact same message if it's already the last one.
            is_already_last_message = False
            if st.session_state.messages and \
               st.session_state.messages[-1].get("role") == "assistant" and \
               st.session_state.messages[-1].get("content") == product_display_message_content:
                is_already_last_message = True
            
            if not is_already_last_message:
                st.session_state.messages.append({"role": "assistant", "content": product_display_message_content})
                logging.info(f"Product Writer: Appended product description for '{product_name}' (from SEO Helper transfer) to messages. Total messages: {len(st.session_state.messages)}")
                products_processed_in_this_run = True
            else:
                logging.info(f"Product Writer: Product description for '{product_name}' (from SEO Helper transfer) appears to be a duplicate of the last message. Skipping append.")
                
    if products_processed_in_this_run: # If any new product descriptions were actually added to chat
        st.rerun() 
    # --- NEW BLOCK END ---

    # --- Sidebar Setup ---
    def render_sidebar_options_conditionally():
        # Only show product options if a report is loaded
        if st.session_state.get("full_report") and st.session_state.get("url"):
            render_product_writer_sidebar_options()
        # else:
            # Optionally, show a message if report not loaded
            # st.sidebar.info(language_manager.get_text("analyze_site_for_product_options", lang, 
            # fallback="Analyze a site in SEO Helper to see product options."))

    common_sidebar(page_specific_content_func=render_sidebar_options_conditionally)


    # --- NEW: Automated Product Suggestion Tasks ---
    display_suggestions_condition = (
        st.session_state.get("url") and
        st.session_state.get("text_report") and
        st.session_state.get("auto_suggestions_data") and
        st.session_state.get("current_report_url_for_suggestions") == st.session_state.get("url")
    )

    if display_suggestions_condition:
        auto_suggestions = st.session_state.auto_suggestions_data
        product_tasks = []

        if auto_suggestions and \
           isinstance(auto_suggestions, dict) and \
           "content_creation_ideas" in auto_suggestions and \
           isinstance(auto_suggestions.get("content_creation_ideas"), dict) and \
           "product_content_tasks" in auto_suggestions.get("content_creation_ideas", {}) and \
           isinstance(auto_suggestions.get("content_creation_ideas", {}).get("product_content_tasks"), list):
            product_tasks = auto_suggestions["content_creation_ideas"]["product_content_tasks"]
        
        if product_tasks:
            st.subheader(language_manager.get_text("suggested_product_tasks_title", lang, fallback="Suggested Product Tasks"))
            st.markdown(language_manager.get_text("suggested_product_tasks_intro", lang, fallback="We found some product description suggestions based on the SEO analysis. Select one to pre-fill the product options:"))

            if "last_url_for_product_suggestion_selection" not in st.session_state or \
               st.session_state.last_url_for_product_suggestion_selection != st.session_state.url:
                st.session_state.selected_auto_suggestion_product_task_index = None
                st.session_state.last_url_for_product_suggestion_selection = st.session_state.url

            for i, task in enumerate(product_tasks):
                if not isinstance(task, dict):
                    logging.warning(f"Product Writer: Skipping non-dict product task at index {i}: {task}")
                    continue
                
                task_product_name = task.get('product_name', language_manager.get_text('untitled_suggestion', lang, fallback='Untitled Suggestion'))
                if not task_product_name: task_product_name = language_manager.get_text('untitled_suggestion', lang, fallback='Untitled Suggestion')

                with st.expander(f"{language_manager.get_text('suggestion_task_label', lang, fallback='Suggestion')} {i+1}: {task_product_name}",
                                 expanded=(st.session_state.selected_auto_suggestion_product_task_index == i)):
                    
                    st.markdown(f"**{language_manager.get_text('product_name_label', lang, fallback='Product Name')}:** {task.get('product_name', 'N/A')}")
                    st.markdown(f"**{language_manager.get_text('product_description_length_label', lang, fallback='Description Length')}:** {task.get('description_length', 'N/A')}")
                    st.markdown(f"**{language_manager.get_text('tone_label', lang, fallback='Tone')}:** {task.get('tone', 'N/A')}")
                    
                    seo_keywords_display = task.get('seo_keywords', [])
                    if isinstance(seo_keywords_display, list):
                        seo_keywords_display = ", ".join(seo_keywords_display) if seo_keywords_display else language_manager.get_text('none_value', lang, fallback="None")
                    elif not seo_keywords_display:
                        seo_keywords_display = language_manager.get_text('none_value', lang, fallback="None")
                    st.markdown(f"**{language_manager.get_text('seo_keywords_label', lang, fallback='SEO Keywords')}:** {seo_keywords_display}")

                    product_details_summary = format_product_details_for_textarea(task.get('product_details', {}), [], lang) 
                    if product_details_summary:
                        st.markdown(f"**{language_manager.get_text('product_details_summary_label', lang, fallback='Product Details Summary')}:**")
                        st.markdown(f"> {product_details_summary.replace(chr(10), chr(10) + '> ')}") 

                    if st.button(language_manager.get_text("use_this_suggestion_button", lang, fallback="Use This Suggestion"), key=f"use_product_suggestion_{i}"):
                        if "product_options" not in st.session_state:
                            st.session_state.product_options = {}

                        st.session_state.product_options["product_name"] = task.get("product_name", "")
                        
                        valid_lengths = ["Short", "Medium", "Long"]
                        task_length_val = task.get("description_length")
                        if task_length_val in valid_lengths:
                            st.session_state.product_options["length"] = task_length_val
                        else:
                            st.warning(language_manager.get_text(
                                "invalid_length_in_suggestion_warning", lang, task_length_val, "Medium", # Pass as positional args
                                fallback=f"Warning: The suggested length '{task_length_val}' is invalid. Defaulting to 'Medium'."
                            ))
                            logging.warning(f"Product Writer: Invalid length '{task_length_val}' in suggestion for task {i}. Defaulting to Medium.")
                            st.session_state.product_options["length"] = "Medium"

                        valid_tones = ["Professional", "Casual", "Enthusiastic", "Technical", "Friendly"]
                        task_tone_val = task.get("tone")
                        if task_tone_val in valid_tones:
                            st.session_state.product_options["tone"] = task_tone_val
                        else:
                            st.warning(language_manager.get_text(
                                "invalid_tone_in_suggestion_warning", lang, task_tone_val, "Professional", # Pass as positional args
                                fallback=f"Warning: The suggested tone '{task_tone_val}' is invalid. Defaulting to 'Professional'."
                            ))
                            logging.warning(f"Product Writer: Invalid tone '{task_tone_val}' in suggestion for task {i}. Defaulting to Professional.")
                            st.session_state.product_options["tone"] = "Professional"
                        
                        product_details_dict = task.get("product_details", {})
                        seo_keywords_list = task.get("seo_keywords", [])
                        st.session_state.product_options["product_details"] = format_product_details_for_textarea(product_details_dict, seo_keywords_list, lang)
                        
                        st.session_state.selected_auto_suggestion_product_task_index = i
                        
                        # --- MODIFICATION START: Auto-request generation if inputs are valid ---
                        populated_name = st.session_state.product_options.get("product_name", "").strip()
                        populated_details = st.session_state.product_options.get("product_details", "").strip()
                        can_auto_generate = True

                        if not populated_name:
                            st.warning(language_manager.get_text("product_name_missing_in_suggestion_for_auto_gen", lang, 
                                                                fallback="Product name is missing in this suggestion. Please provide one in the sidebar to generate."))
                            logging.warning(f"Product Writer: Suggestion used, but product name from task is missing. Not auto-requesting generation.")
                            can_auto_generate = False
                        
                        # Check details only if name was present, to avoid multiple primary warnings
                        if can_auto_generate and not populated_details:
                            st.warning(language_manager.get_text("product_details_missing_in_suggestion_for_auto_gen", lang, 
                                                                fallback="Product details are missing or effectively empty in this suggestion. Please review in the sidebar to generate."))
                            logging.warning(f"Product Writer: Suggestion used (name: '{populated_name}'), but formatted product details are empty. Not auto-requesting generation.")
                            can_auto_generate = False
                        
                        if can_auto_generate:
                            st.session_state.product_description_requested = True
                            logging.info(f"Product Writer: Suggestion for '{populated_name}' used. Auto-requesting description generation.")
                        # --- MODIFICATION END ---
                        
                        st.rerun() # Rerun to update sidebar with pre-filled options & potentially trigger generation
            st.divider()
        elif display_suggestions_condition: # Condition met but no product_tasks
            st.info(language_manager.get_text("no_product_suggestions_found", lang, fallback="No specific product suggestions found in the current report, or the data format is unrecognized."))
    # --- END Automated Product Suggestion Tasks ---


    # --- Product Description Generation Logic ---
    if st.session_state.product_description_requested:
        current_product_options = st.session_state.get("product_options", {})
        if not isinstance(current_product_options, dict):
            logging.error("Product Writer: product_options is not a dict. Resetting to default for generation.")
            current_product_options = {
                "product_name": "", "product_details": "", "tone": "Professional", "length": "Medium"
            }
            st.session_state.product_options = current_product_options

        product_name_valid = current_product_options.get("product_name", "").strip()
        product_details_valid = current_product_options.get("product_details", "").strip()

        if not product_name_valid:
            st.warning(language_manager.get_text("product_name_required_warning", lang, fallback="Product Name is required. Please fill it in the sidebar options."))
            st.session_state.product_description_requested = False 
        elif not product_details_valid:
            st.warning(language_manager.get_text("product_details_required_warning", lang, fallback="Product Details are required. Please fill them in the sidebar options."))
            st.session_state.product_description_requested = False
        elif not st.session_state.get("text_report"): # Added check for text_report before attempting generation
            st.warning(language_manager.get_text("analyze_website_first_product_gen", lang, fallback="Please analyze a website in SEO Helper before generating product descriptions."))
            st.session_state.product_description_requested = False
        else:
            with st.spinner(language_manager.get_text("generating_product_description", lang, fallback="Generating product description...")):
                try:
                    description = generate_product_description(
                        st.session_state.text_report, 
                        current_product_options
                    )
                    if "messages" not in st.session_state: st.session_state.messages = [] # Defensive
                    st.session_state.messages.append({"role": "assistant", "content": description})
                except Exception as e:
                    logging.error(f"Error generating product description: {e}", exc_info=True)
                    error_msg = language_manager.get_text('error_processing_request', lang, error=str(e))
                    st.error(error_msg)
                    if "messages" not in st.session_state: st.session_state.messages = [] # Defensive
                    st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text('could_not_generate_description', lang)})

            st.session_state.product_description_requested = False
            st.rerun() # Rerun to display the new description or error


    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    
    if "messages" in st.session_state:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if not st.session_state.get("text_report"):
        st.warning(language_manager.get_text("analyze_website_first_product", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with product descriptions."))
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(language_manager.get_text("seo_helper_button", lang, fallback="SEO Helper"), key="seo_helper_button_redirect_product"):
                update_page_history("seo")
                st.switch_page("pages/1_SEO_Helper.py")

    if prompt := st.chat_input(language_manager.get_text("product_description_prompt", lang, fallback="What kind of product description would you like to write?")):
        if "messages" not in st.session_state: st.session_state.messages = [] # Ensure messages exists
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not st.session_state.get("text_report"):
            with st.chat_message("assistant"):
                response = language_manager.get_text("analyze_website_first_chat_product", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with article writing.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            from helpers.product_main_helper import process_chat_input 
            await process_chat_input(
                prompt,
                MISTRAL_API_KEY=st.session_state.get("MISTRAL_API_KEY"),
                GEMINI_API_KEY=st.session_state.get("GEMINI_API_KEY"),
                message_list="messages" 
            )
            st.rerun()

if __name__ == "__main__":
    asyncio.run(main())