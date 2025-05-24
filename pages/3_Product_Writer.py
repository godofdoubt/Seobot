#pages/3_Product_Writer.py
import streamlit as st
import asyncio
import os
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
    # This logic ensures the correct welcome message for the Product Writer page,
    # updating the first message in the chat if necessary.
    target_welcome_message_product = ""
    if st.session_state.get("url") and st.session_state.get("text_report"):
        target_welcome_message_product = language_manager.get_text(
            "welcome_product_writer_analyzed",
            lang,
            st.session_state.url,  # Pass URL as an argument for formatting
            fallback=f"Welcome to the Product Writer page.\nUsing analysis for: **{st.session_state.url}**"
        )
    else:
        target_welcome_message_product = language_manager.get_text(
            "welcome_product_writer_not_analyzed",
            lang,
            fallback="Welcome to the Product Writer page. Please analyze a website in the SEO Helper page first to proceed."
        )

    if "messages" not in st.session_state or not st.session_state.messages:
        # If messages list doesn't exist or is empty, initialize with the welcome message.
        st.session_state.messages = [{"role": "assistant", "content": target_welcome_message_product}]
    elif st.session_state.messages and st.session_state.messages[0].get("role") == "assistant":
        # If the first message is an assistant message but not the correct current welcome message, update it.
        if st.session_state.messages[0].get("content") != target_welcome_message_product:
            st.session_state.messages[0]["content"] = target_welcome_message_product
    # --- END: Fix for Product Writer Welcome Message ---


    # --- NEW Right Sidebar for Product Description Options ---
    if st.session_state.full_report and st.session_state.url:
        with st.sidebar:
            #st.markdown(f"### {language_manager.get_text('product_options_title', lang)}") 

            if "product_options" not in st.session_state:
                st.session_state.product_options = {
                    "product_name": "",
                    "product_details": "",
                    "tone": "Professional", 
                    "length": "Medium"      
                }

            st.session_state.product_options["product_name"] = st.text_input(
                label=language_manager.get_text("product_name", lang, fallback="Product Name"),
                value=st.session_state.product_options.get("product_name", ""),
                placeholder=language_manager.get_text("product_name_placeholder", lang, fallback="Enter the name of the product")
            )

            st.session_state.product_options["product_details"] = st.text_area(
                label=language_manager.get_text("product_details", lang, fallback="Product Details"),
                value=st.session_state.product_options.get("product_details", ""),
                placeholder=language_manager.get_text("product_details_placeholder", lang, fallback="Enter product features, benefits, specifications, target audience, etc."),
                height=150
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
            current_display_value_tone = internal_to_display_map_tone.get(st.session_state.product_options["tone"], tone_display_options[0]) 
            try:
                current_index_tone = tone_display_options.index(current_display_value_tone)
            except ValueError:
                 current_index_tone = 0 

            selected_tone_display = st.selectbox(
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
            current_display_value_length = internal_to_display_map_length.get(st.session_state.product_options["length"], length_display_options[1]) 
            try:
                current_index_length = length_display_options.index(current_display_value_length)
            except ValueError:
                 current_index_length = 1 

            selected_length_display = st.selectbox(
                label=language_manager.get_text("product_length", lang, fallback="Description Length"),
                options=length_display_options,
                index=current_index_length
            )
            display_to_internal_map_length = {v: k for k, v in internal_to_display_map_length.items()}
            st.session_state.product_options["length"] = display_to_internal_map_length.get(selected_length_display, "Medium")

            if st.sidebar.button(language_manager.get_text("generate_product_description", lang, fallback="Generate Product Description")):
                if not st.session_state.product_options.get("product_name"):
                    st.sidebar.warning("Please enter a Product Name.")
                elif not st.session_state.product_options.get("product_details"):
                     st.sidebar.warning("Please enter Product Details.")
                else:
                    st.session_state.product_description_requested = True
                    st.rerun()

        if st.session_state.product_description_requested:
            if "product_options" in st.session_state:
                with st.spinner(language_manager.get_text("generating_product_description", lang, fallback="Generating product description...")):
                    try:
                        description = generate_product_description(
                            st.session_state.text_report, 
                            st.session_state.product_options 
                        )
                        st.session_state.messages.append({"role": "assistant", "content": description})
                    except Exception as e:
                        st.error(f"{language_manager.get_text('error_processing_request', lang)}: {e}")
                        st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text('could_not_generate_description', lang)})

                st.session_state.product_description_requested = False
                st.rerun() 
            else:
                 st.error("Product options not found. Cannot generate description.")
                 st.session_state.product_description_requested = False


    st.markdown(language_manager.get_text("logged_in_as", lang, st.session_state.username))
    common_sidebar()

    if "messages" in st.session_state:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if not st.session_state.text_report:
        st.warning(language_manager.get_text("analyze_website_first_product", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with product descriptions."))
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(language_manager.get_text("seo_helper_button", lang, fallback="SEO Helper"), key="seo_helper_button"):
                update_page_history("seo")
                st.switch_page("pages/1_SEO_Helper.py")

    if prompt := st.chat_input(language_manager.get_text("product_description_prompt", lang, fallback="What kind of product description would you like to write?")):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not st.session_state.text_report:
            with st.chat_message("assistant"):
                response = language_manager.get_text("analyze_website_first_chat_product", lang, fallback="Please analyze a website first in the SEO Helper page before I can help with product writing.")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            from helpers.product_main_helper import process_chat_input 

            await process_chat_input(
                prompt,
                MISTRAL_API_KEY=st.session_state.MISTRAL_API_KEY,
                GEMINI_API_KEY=st.session_state.GEMINI_API_KEY,
                message_list="messages" 
            )

if __name__ == "__main__":
    asyncio.run(main())