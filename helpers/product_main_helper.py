# helpers/product_main_helper.py
import streamlit as st
import re
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Callable, Dict, Any
from utils.language_support import language_manager

language_names = {"en": "English", "tr": "Turkish"}

def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools specific to product writing."""

    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    async def process_question(prompt: str, context: str) -> str:
        """Process a question using Gemini with language support."""
        try:
            # Include username in context if available
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
            language_instruction = f"Please respond in {language_names.get(st.session_state.language, 'English')}." if st.session_state.language != "en" else ""

            full_prompt = f"""{language_instruction}
            {username_context}Context: {context}
            Question: {prompt}

            Please provide a helpful response focused on product descriptions and product writing.
            Think about how to use web site analysis to create effective product copy.
            """
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"

    # Import only the necessary tool for product writing
    from buttons.generate_product_description import generate_product_description

    tools = {
        "process_question": Tool(
            description="Process a question using the chat context and SEO report with focus on product writing",
            function=process_question,
            parameters=["prompt", "context"],
            validation=True,
            prompt="Processing your product-related question..."
        ),
        "generate_product_description": Tool(
            description="Generate a product description based on the SEO report",
            function=lambda text_report, url: generate_product_description(text_report, url, st.session_state.get("product_options", None)),
            parameters=["text_report"],
            validation=True,
            prompt="Generating product description..."
        )
    }

    return tools

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str):
    """Process the chat input using Mistral API with focus on product writing and language support."""
    lang = st.session_state.get("language", "en")
    with st.spinner(language_manager.get_text("generating_response", lang) + " (Product Writer)..."):
        with st.chat_message("assistant"):
            try:
                # Prepare conversation history context
                history_context = ""
                num_history_turns = 5
                messages = st.session_state.messages
                start_index = max(0, len(messages) - num_history_turns)
                for message in messages[start_index:]:
                    history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                # Include username in context if available
                username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""

                # Send request to Mistral API
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {MISTRAL_API_KEY}"
                }

                # Add language information to system message
                language_info = f"Please respond in {language_names.get(lang, 'English')}. " if lang != "en" else ""

                # Check if the prompt is asking for product description generation
                if any(keyword in prompt.lower() for keyword in ["product", "description", "feature", "generate", "create", "write"]):
                    system_content = f"""You are an expert product copywriter and SEO specialist. {language_info}Generate a well-structured, SEO-optimized product description based on the provided website analysis.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.text_report}

Instructions for product description generation:
1. Create a compelling product headline that includes relevant keywords
2. Structure the description with clear features and benefits
3. Aim for approximately 300-500 words of high-quality content
4. Include specifications and technical details where appropriate
5. Optimize for SEO while maintaining persuasive sales copy
6. Use a professional but engaging tone
7. Include a strong call-to-action
"""
                else:
                    system_content = f"""You are an expert in product copywriting and SEO strategy. {language_info}Provide helpful responses about product descriptions, feature highlights, and SEO optimization for product pages.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.text_report}

Please provide specific, actionable advice related to product content creation and copywriting based on the SEO report.
"""

                data = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_content
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500 if any(keyword in prompt.lower() for keyword in ["product", "description", "feature", "generate", "create", "write"]) else 800
                }

                response = requests.post(url, headers=headers, json=data)

                if response.status_code == 200:
                    response_json = response.json()
                    response_text = response_json['choices'][0]['message']['content']
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    error_msg = f"Mistral API error: {response.status_code} - {response.text}"
                    st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_msg = f"Error connecting to Mistral API: {str(e)}"
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

async def process_with_gemini(prompt: str, GEMINI_API_KEY: str):
    """Process the chat input using Gemini with a focus on product descriptions and language support."""
    lang = st.session_state.get("language", "en")
    # Initialize tools
    tools = create_tools(GEMINI_API_KEY)

    with st.spinner(language_manager.get_text("processing_question", lang) + "..."):
        try:
            # Initialize used_tools in session state if it doesn't exist
            if "used_tools" not in st.session_state:
                st.session_state.used_tools = set()

            # --- Tool Selection Logic ---
            tool_used = False  # Flag to track if any tool was used

            # Check for explicit random product description requests
            if prompt.lower() == "write random product description" or prompt.lower() == "rastgele ürün açıklaması oluştur":
                with st.chat_message("assistant"):
                    try:
                        response = tools["generate_product_description"].function(st.session_state.text_report)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        tool_used = True
                    except Exception as product_desc_error:
                        st.error(language_manager.get_text("could_not_generate_description", lang) + f": {product_desc_error}")
                        st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text("could_not_generate_description", lang) + f": {product_desc_error}"})

            if not tool_used:  # Use process_question if no other tool was used
                with st.chat_message("assistant"):
                    history_context = ""
                    num_history_turns = 5
                    start_index = max(0, len(st.session_state.messages) - num_history_turns)
                    for message in st.session_state.messages[start_index:]:
                        history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                    context = f"""
                    Username: {st.session_state.username if "username" in st.session_state else "Anonymous"}
                    SEO Report: {st.session_state.text_report}
                    Conversation History: {history_context}
                    Focus: Product descriptions and product content
                    """
                    response = await tools["process_question"].function(prompt, context)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            with st.chat_message("assistant"):
                error_msg = language_manager.get_text("error_processing_request", lang) + f": {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

async def process_chat_input(
    prompt: str,
    analyze_website: Callable = None,
    load_saved_report: Callable = None,
    display_report_and_services: Callable = None,
    MISTRAL_API_KEY: str = None,
    GEMINI_API_KEY: str = None,
    message_list: str = "messages",
):
    """Processes chat input for the Product Writer page with language support."""
    lang = st.session_state.get("language", "en")

    # Check authentication before processing
    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"):
            st.markdown(language_manager.get_text("login_required", lang))
            return

    # Handle URL analysis (keeping this part for compatibility, but not focusing on it as per request)
    if re.match(r'^(https?://)?[\w.-]+\.[a-z]{2,}$', prompt) and analyze_website and load_saved_report and display_report_and_services:
        normalized_url = normalize_url(prompt)
        text_report, full_report = load_saved_report(normalized_url)

        if text_report and full_report:
            display_report_and_services(text_report, full_report, normalized_url)
        else:
            with st.chat_message("assistant"):
                st.markdown(language_manager.get_text("analyzing", lang) + f" {normalized_url}...")
            with st.spinner(language_manager.get_text("analyzing_website", lang) + "..."):
                text_report, full_report = await analyze_website(normalized_url)
                if text_report and full_report:
                    display_report_and_services(text_report, full_report, normalized_url)
                else:
                    with st.chat_message("assistant"):
                        st.markdown(language_manager.get_text("analysis_completed_no_report", lang))
    else:
        # Check if SEO report is available
        if not st.session_state.text_report:
            with st.chat_message("assistant"):
                st.markdown(language_manager.get_text("analyze_website_first_product", lang))
                st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text("analyze_website_first_product", lang)})
            return

        # Determine which model to use based on provided API keys
        if MISTRAL_API_KEY and (not GEMINI_API_KEY or st.session_state.get("use_mistral", False)):
            # Use Mistral API
            await process_with_mistral(prompt, MISTRAL_API_KEY)
        elif GEMINI_API_KEY:
            # Use Gemini API with tools
            await process_with_gemini(prompt, GEMINI_API_KEY)
        else:
            with st.chat_message("assistant"):
                st.markdown(language_manager.get_text("no_ai_model_configured", lang))
                st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text("no_ai_model_configured", lang)})
