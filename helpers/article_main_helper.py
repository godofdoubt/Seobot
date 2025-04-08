#/mnt/data/Max/Seo12/helpers/article_main_helper.py
import streamlit as st
import re
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Dict
from utils.language_support import language_manager
language_names = {"en": "English", "tr": "Turkish"}

def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools specific to article writing."""

    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    async def process_question(prompt: str, context: str) -> str:
        """Process a question using Gemini with focus on article writing."""
        try:
            # Include username in context if available
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""

            lang = st.session_state.get("language", "en")
            language_instruction = f"Please respond in {language_names.get(lang, 'English')}." if lang != "en" else ""

            full_prompt = f"""{language_instruction}
            {username_context}Context: {context}
            Question: {prompt}

            Please provide a helpful response focused on article writing and content strategy.
            Consider the SEO analysis when providing guidance about content creation.
            """
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"

    # Import only the necessary tool for article writing
    from buttons.generate_article import generate_article

    tools = {
        "process_question": Tool(
            description="Process a question using the chat context and SEO report with focus on article writing",
            function=process_question,
            parameters=["prompt", "context"],
            validation=True,
            prompt="Processing your article-related question..."
        ),
        "generate_article": Tool(
            description="Generate an article based on the SEO report and URL",
            function=lambda text_report, url: generate_article(text_report, url, st.session_state.get("article_options", None)),
            parameters=["text_report", "url"],
            validation=True,
            prompt="Generating article..."
        )
    }

    return tools

async def process_with_gemini(prompt: str, GEMINI_API_KEY: str):
    """Process the chat input using Gemini with a focus on article generation."""
    # Initialize tools
    tools = create_tools(GEMINI_API_KEY)

    with st.spinner("Processing your question..."):
        try:
            # Initialize used_tools in session state if it doesn't exist
            if "used_tools" not in st.session_state:
                st.session_state.used_tools = set()

            # --- Tool Selection Logic ---
            tool_used = False  # Flag to track if any tool was used

            # Check for explicit random article generation requests
            if prompt.lower() == "random article" or prompt.lower() == "rastgele makale":
                with st.chat_message("assistant"):
                    try:
                        response = tools["generate_article"].function(st.session_state.text_report, st.session_state.url)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        tool_used = True
                    except Exception as article_error:
                        st.error(f"Could not generate article: {article_error}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Could not generate article: {article_error}"})

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
                    Focus: Article writing and content strategy
                    """
                    response = await tools["process_question"].function(prompt, context)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            with st.chat_message("assistant"):
                error_msg = f"Error processing request: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str):
    """Process the chat input using Mistral API with focus on article writing."""

    lang = st.session_state.get("language", "en")
    language_instruction = f"Please respond in {language_names.get(lang, 'English')}." if lang != "en" else ""

    with st.spinner("Generating response with Article Writer..."):
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

                # Check if the prompt is asking for article generation
                if any(keyword in prompt.lower() for keyword in ["article", "content", "write", "blog", "post", "generate", "create"]):
                    system_content = f"""{language_instruction}
You are an expert content writer and SEO specialist. Generate a well-structured, SEO-optimized article based on the provided website analysis.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.text_report}

Website URL: {st.session_state.url}

Instructions for article generation:
1. Create a compelling headline that includes relevant keywords
2. Structure the article with clear headings and subheadings
3. Aim for approximately 1000-1500 words of high-quality content
4. Include an introduction, main body with 3-5 sections, and conclusion
5. Optimize for SEO while maintaining readability and engagement
6. Use a conversational but authoritative tone
7. Include calls-to-action where appropriate
"""
                else:
                    system_content = f"""{language_instruction}
You are an expert in content writing and SEO strategy. Provide helpful responses about article writing, content strategy, and SEO optimization.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.text_report}

Website URL: {st.session_state.url}

Please provide specific, actionable advice related to content creation and article writing based on the SEO report.
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
                    "max_tokens": 2000 if any(keyword in prompt.lower() for keyword in ["article", "content", "write", "blog", "post", "generate", "create"]) else 1000
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

async def process_chat_input(
    prompt: str,
    MISTRAL_API_KEY: str = None,
    GEMINI_API_KEY: str = None,
    message_list: str = "messages"
):
    """Processes chat input and handles article writing-related questions.
    Supports both Gemini and Mistral API for chat responses.
    """
    # Check authentication before processing
    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"):
            lang = st.session_state.get("language", "en")
            st.markdown(language_manager.get_text("need_to_login", lang))
            return

    # Check if SEO report is available
    if not st.session_state.text_report:
        with st.chat_message("assistant"):
            lang = st.session_state.get("language", "en")
            message = language_manager.get_text("analyze_website_first", lang)
            st.markdown(message)
            st.session_state.messages.append({"role": "assistant", "content": message})
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
            st.markdown("No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY.")
            st.session_state.messages.append({"role": "assistant", "content": "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY."})