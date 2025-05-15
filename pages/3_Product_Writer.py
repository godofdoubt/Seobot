#pages/3_Product_Writer.py
import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
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
    initial_sidebar_state="expanded"
)

def check_auth():
    """Check if user is authenticated"""
    lang = st.session_state.language if "language" in st.session_state else "en"
    if not st.session_state.authenticated:
        st.warning(language_manager.get_text("authentication_required", lang))
        st.stop()

async def main():
    # Initialize shared session state
    init_shared_session_state()

    # Get current language
    lang = st.session_state.language if "language" in st.session_state else "en"

    st.title(language_manager.get_text("product_writer_button", lang, fallback="Product Writer"))

    # Initialize product description generation flag if not present
    if "product_description_requested" not in st.session_state:
        st.session_state.product_description_requested = False

    # Set current page to product
    if st.session_state.current_page != "product":
        update_page_history("product")

    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Check if user is authenticated
    check_auth()

    # --- Welcome Message Logic ---
    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message = language_manager.get_text("welcome_product_writer_analyzed", lang, st.session_state.url, fallback="Welcome to the Product Writer page.\nUsing analysis for: **{}**")
    else:
        target_welcome_message = language_manager.get_text("welcome_product_writer_not_analyzed", lang, fallback="Welcome to the Product Writer page. Please analyze a website in the SEO Helper page first to proceed.")

    # Adjust message update logic if needed, maybe move welcome message display after sidebar
    # For simplicity, keeping it here for now.

    # --- NEW Right Sidebar for Product Description Options ---
    if st.session_state.full_report and st.session_state.url:
        with st.sidebar:
            st.markdown(f"### {language_manager.get_text('product_options_title', lang)}")

            # Initialize product options in session state if not present
            if "product_options" not in st.session_state:
                st.session_state.product_options = {
                    "product_name": "",
                    "product_details": "",
                    "tone": "Professional", # Default internal value
                    "length": "Medium"      # Default internal value
                }

            # Product Name
            st.session_state.product_options["product_name"] = st.text_input(
                label=language_manager.get_text("product_name", lang, fallback="Product Name"),
                value=st.session_state.product_options.get("product_name", ""),
                placeholder=language_manager.get_text("product_name_placeholder", lang, fallback="Enter the name of the product")
            )

            # Product Details
            st.session_state.product_options["product_details"] = st.text_area(
                label=language_manager.get_text("product_details", lang, fallback="Product Details"),
                value=st.session_state.product_options.get("product_details", ""),
                placeholder=language_manager.get_text("product_details_placeholder", lang, fallback="Enter product features, benefits, specifications, target audience, etc."),
                height=150
            )

            # --- Dynamic Tone Options --- (Reusing logic from Article Writer)
            tone_keys = ["tone_professional", "tone_casual", "tone_enthusiastic", "tone_technical", "tone_friendly"]
            tone_display_options = [language_manager.get_text(key, lang) for key in tone_keys]
            internal_to_display_map_tone = {
                "Professional": language_manager.get_text("tone_professional", lang),
                "Casual": language_manager.get_text("tone_casual", lang),
                "Enthusiastic": language_manager.get_text("tone_enthusiastic", lang),
                "Technical": language_manager.get_text("tone_technical", lang),
                "Friendly": language_manager.get_text("tone_friendly", lang),
            }
            current_display_value_tone = internal_to_display_map_tone.get(st.session_state.product_options["tone"], tone_display_options[0]) # Default to professional display value
            try:
                current_index_tone = tone_display_options.index(current_display_value_tone)
            except ValueError:
                 current_index_tone = 0 # Default index

            selected_tone_display = st.selectbox(
                label=language_manager.get_text("product_tone", lang, fallback="Tone"), # Use specific product tone key
                options=tone_display_options,
                index=current_index_tone
            )
            # Store the internal English value based on selection
            display_to_internal_map_tone = {v: k for k, v in internal_to_display_map_tone.items()}
            st.session_state.product_options["tone"] = display_to_internal_map_tone.get(selected_tone_display, "Professional")


            # --- Dynamic Length Options ---
            length_keys = ["product_length_short", "product_length_medium", "product_length_long"]
            length_display_options = [language_manager.get_text(key, lang) for key in length_keys]
            # Define mapping for length (using simple keys 'Short', 'Medium', 'Long' internally)
            internal_to_display_map_length = {
                "Short": language_manager.get_text("product_length_short", lang),
                "Medium": language_manager.get_text("product_length_medium", lang),
                "Long": language_manager.get_text("product_length_long", lang),
            }
            current_display_value_length = internal_to_display_map_length.get(st.session_state.product_options["length"], length_display_options[1]) # Default to medium display value
            try:
                current_index_length = length_display_options.index(current_display_value_length)
            except ValueError:
                 current_index_length = 1 # Default index

            selected_length_display = st.selectbox(
                label=language_manager.get_text("product_length", lang, fallback="Description Length"),
                options=length_display_options,
                index=current_index_length
            )
             # Store the internal simple key based on selection
            display_to_internal_map_length = {v: k for k, v in internal_to_display_map_length.items()}
            st.session_state.product_options["length"] = display_to_internal_map_length.get(selected_length_display, "Medium")

            # --- Generation Button and Logic ---
            # Add Product Writer-specific button to sidebar
            if st.sidebar.button(language_manager.get_text("generate_product_description", lang, fallback="Generate Product Description")):
                # Basic validation (optional but recommended)
                if not st.session_state.product_options.get("product_name"):
                    st.sidebar.warning("Please enter a Product Name.")
                elif not st.session_state.product_options.get("product_details"):
                     st.sidebar.warning("Please enter Product Details.")
                else:
                    st.session_state.product_description_requested = True
                    st.rerun()  # Rerun to process the flag

        # Handle product description generation if requested outside the sidebar definition
        if st.session_state.product_description_requested:
             # Ensure options exist before trying to generate
            if "product_options" in st.session_state:
                with st.spinner(language_manager.get_text("generating_product_description", lang, fallback="Generating product description...")):
                    try:
                        # *** IMPORTANT: Update the function call to pass options ***
                        description = generate_product_description(
                            st.session_state.text_report, # Original SEO report
                            st.session_state.product_options # NEW: Pass the collected options
                        )
                        # Add the description to session state messages
                        st.session_state.messages.append({"role": "assistant", "content": description})
                    except Exception as e:
                        st.error(f"{language_manager.get_text('error_processing_request', lang)}: {e}")
                        st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text('could_not_generate_description', lang)})

                # Reset the flag regardless of success or failure
                st.session_state.product_description_requested = False
                st.rerun() # Rerun again after generation to display the new message immediately
            else:
                 # Handle case where options somehow disappeared (shouldn't happen with above logic)
                 st.error("Product options not found. Cannot generate description.")
                 st.session_state.product_description_requested = False


    # Display username
    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))

    # Display common sidebar elements (like language selection)
    # Place this after the product-specific sidebar elements if you want them grouped.
    common_sidebar()

    # --- Display Welcome/Chat Messages ---
    # Moved welcome message display here to potentially reflect sidebar state better
    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message}]
    # Update first message if needed (ensure this logic is sound)
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
         if st.session_state.messages[0].get("content") != target_welcome_message:
              st.session_state.messages[0]["content"] = target_welcome_message


    # Display chat messages from shared session state
    if "messages" in st.session_state:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Add a check for SEO data (if not analyzed yet)
    if not st.session_state.text_report:
        st.warning(language_manager.get_text("analyze_website_first_product", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with product descriptions.")) # Use specific message key
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(language_manager.get_text("seo_helper_button", lang, fallback="SEO Helper"), key="seo_helper_button"):
                update_page_history("seo")
                st.switch_page("pages/1_SEO_Helper.py")

    # Handle chat input (remains largely the same)
    if prompt := st.chat_input(language_manager.get_text("product_description_prompt", lang, fallback="What kind of product description would you like to write?")):
        # Add user message to shared session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Check if URL has been analyzed
        if not st.session_state.text_report:
            with st.chat_message("assistant"):
                response = language_manager.get_text("analyze_website_first_chat_product", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with product writing.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            # Process the input using the enhanced helper - *ensure this helper can handle product context*
            from helpers.product_main_helper import process_chat_input # Assuming this exists and is appropriate

            # Process with available API keys
            await process_chat_input(
                prompt,
                MISTRAL_API_KEY=st.session_state.MISTRAL_API_KEY,
                GEMINI_API_KEY=st.session_state.GEMINI_API_KEY,
                # Pass message list if needed by helper
                # message_list="messages" # Example if needed
            )

if __name__ == "__main__":
    asyncio.run(main())
