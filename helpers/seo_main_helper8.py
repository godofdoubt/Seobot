#SeoTree/helpers/seo_main_helper8.py
import streamlit as st
import re
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Callable, Dict, Any
from utils.language_support import language_manager

language_names = {"en": "English", "tr": "Turkish"}

def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools."""
    
    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    async def process_question(prompt: str, context: str) -> str:
        """Process a question using Gemini."""
        try:
            # Include username in context if available
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
            language_instruction = f"Please respond in {language_names.get(st.session_state.language, 'English')}." if st.session_state.language != "en" else ""
            
            # Updated full_prompt to guide Gemini on using the potentially rich context
            full_prompt = f"""{language_instruction}
{username_context}You are an SEO expert assistant.
The context provided below contains a detailed SEO report for a website. This report may already include AI-generated strategic insights and recommendations.

Context:
{context}

Question: {prompt}

Please provide a helpful and comprehensive response based on the information in the provided context. If the report in the context already contains relevant suggestions or insights pertaining to the question, prioritize referencing or summarizing those. Only generate new insights if the question asks for something not covered or asks for alternatives.
"""
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"

    # Create tools dictionary with actual function implementations
    from buttons.generate_seo_suggestions import generate_seo_suggestions
    
    tools = {
        "process_question": Tool(
            description="Process a question using the chat context and analysis",
            function=process_question,
            parameters=["prompt", "context"],
            validation=True,
            prompt="Processing your question..."
        ),
        "generate_seo_suggestions": Tool(
            description="Provide SEO suggestions based on the llm_analysis_all data",
            function=generate_seo_suggestions,
            parameters=[], # No parameters needed - function will access session state
            validation=True,
            prompt="Generating SEO suggestions..."
        )
    }

    return tools

async def process_chat_input(
    prompt: str,
    process_url_from_main: Callable,
    MISTRAL_API_KEY: str = None,
    GEMINI_API_KEY: str = None,
    message_list: str = "messages"
):
    """Processes chat input. Uses process_url_from_main for URL analysis, 
    or question answering for other inputs.
    Supports both Gemini and Mistral API for chat responses.
    """
    lang = st.session_state.get("language", "en")

    # Check authentication before processing
    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"):
            st.markdown("You need to log in first to use this service.")
            return
    
    # Handle URL analysis by delegating to main.py's process_url
    if re.match(r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$', prompt):
        with st.chat_message("assistant"):
            st.markdown(f"Processing URL: {prompt}...")
        
        await process_url_from_main(prompt, lang)

    else:
        # Handle questions using appropriate model
        if st.session_state.get("text_report"):
            # Determine which model to use based on provided API keys
            if MISTRAL_API_KEY and (not GEMINI_API_KEY or st.session_state.get("use_mistral", False)):
                # Use Mistral API
                await process_with_mistral(prompt, MISTRAL_API_KEY, message_list)
            elif GEMINI_API_KEY:
                # Use Gemini API with tools
                await process_with_gemini(prompt, GEMINI_API_KEY, message_list)
            else:
                with st.chat_message("assistant"):
                    st.markdown("No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY.")
                st.session_state[message_list].append({"role": "assistant", "content": "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY."})
        else:
            with st.chat_message("assistant"):
                st.markdown("Please provide a website URL first so I can analyze it.")
            st.session_state[message_list].append({"role": "assistant", "content": "Please provide a website URL first so I can analyze it."})

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str, message_list: str = "messages"):
    """Process the chat input using Mistral API."""
    lang = st.session_state.get("language", "en")
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."

    with st.spinner(spinner_text):
        with st.chat_message("assistant"):
            try:
                history_context = ""
                num_history_turns = 5
                messages_to_process = st.session_state.get(message_list, [])
                start_index = max(0, len(messages_to_process) - num_history_turns)
                for message in messages_to_process[start_index:]:
                    history_context += f"{message['role'].capitalize()}: {message['content']}\n"
                
                username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
                
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {MISTRAL_API_KEY}"
                }
                language_info = f"Please respond in {language_names.get(lang, 'English')}. " if lang != "en" else ""
                
                # Prepare context - use llm_analysis_all if available, fallback to text_report
                context_data = ""
                if st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                    context_data = f"Detailed Analysis Data (llm_analysis_all): {st.session_state.full_report['llm_analysis_all']}"
                elif st.session_state.get("text_report"):
                    context_data = f"SEO Report: {st.session_state.text_report}"
                else:
                    context_data = "No SEO report available."
                
                system_prompt_content = f"""You are an SEO expert assistant. {language_info}
Your primary goal is to provide helpful responses based on the website analysis report provided in the 'Context from SEO Report' section.
This report is comprehensive and may already include AI-generated strategic insights, recommendations, keyword analysis, and subpage details.

When responding to the user:
1. First, check if the 'Context from SEO Report' directly answers or contains relevant information for the user's query.
2. If it does, prioritize using, summarizing, or referencing that information from the report.
3. If the report does not directly cover the query, or if the user asks for alternatives or further elaboration, then use your SEO expertise to generate a helpful response, still keeping the report's content in mind as the primary source of truth about the analyzed website.

User Information:
{username_context}

Conversation History (for context, but prioritize the SEO Report for site-specific questions):
{history_context}

Context from SEO Report:
{context_data}"""

                data = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt_content
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    response_json = response.json()
                    response_text = response_json['choices'][0]['message']['content']
                    st.markdown(response_text)
                    st.session_state[message_list].append({"role": "assistant", "content": response_text})
                else:
                    error_msg = f"Mistral API error: {response.status_code} - {response.text}"
                    st.markdown(error_msg)
                    st.session_state[message_list].append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_msg = f"Error connecting to Mistral API: {str(e)}"
                st.markdown(error_msg)
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})

async def process_with_gemini(prompt: str, GEMINI_API_KEY: str, message_list: str = "messages"):
    """Process the chat input using Gemini and tools."""
    lang = st.session_state.get("language", "en")
    tools = create_tools(GEMINI_API_KEY)
    
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."

    with st.spinner(spinner_text):
        try:
            if "used_tools" not in st.session_state:
                st.session_state.used_tools = set()

            tool_used = False

            # Check for suggestion keywords but ensure llm_analysis_all is available
            if any(keyword in prompt.lower() for keyword in ["suggest", "recommendation", "improve"]) and \
               "generate_seo_suggestions" not in st.session_state.used_tools and \
               st.session_state.get("full_report") and \
               st.session_state.full_report.get("llm_analysis_all"):
                with st.chat_message("assistant"):
                    # generate_seo_suggestions will now access llm_analysis_all directly from session state
                    response = tools["generate_seo_suggestions"].function()
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})
                    st.session_state.used_tools.add("generate_seo_suggestions")
                    tool_used = True
            elif any(keyword in prompt.lower() for keyword in ["suggest", "recommendation", "improve"]) and \
                 (not st.session_state.get("full_report") or not st.session_state.full_report.get("llm_analysis_all")):
                 with st.chat_message("assistant"):
                    msg = "To generate comprehensive SEO suggestions based on detailed page analysis, complete llm_analysis_all data is needed. Please analyze a URL first and wait for the detailed analysis to complete. I can still discuss any suggestions present in the current summary if available."
                    st.markdown(msg)
                    st.session_state[message_list].append({"role": "assistant", "content": msg})
                    tool_used = True

            if not tool_used:
                with st.chat_message("assistant"):
                    history_context = ""
                    num_history_turns = 5
                    messages_to_process = st.session_state.get(message_list, [])
                    start_index = max(0, len(messages_to_process) - num_history_turns)
                    for message in messages_to_process[start_index:]:
                        history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                    # Context for Gemini's process_question tool - prioritize llm_analysis_all
                    context_data = ""
                    if st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                        context_data = f"Detailed Analysis Data (llm_analysis_all): {st.session_state.full_report['llm_analysis_all']}"
                    elif st.session_state.get("text_report"):
                        context_data = f"SEO Report: {st.session_state.text_report}"
                    else:
                        context_data = "No SEO report available. Please analyze a URL first."

                    context_for_gemini = f"""
                    Username: {st.session_state.username if "username" in st.session_state and st.session_state.username else "Anonymous"}
                    {context_data}
                    Conversation History (for reference, prioritize the SEO Report for site-specific questions):
                    {history_context}
                    """
                    
                    response = await tools["process_question"].function(prompt, context_for_gemini)
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})

        except Exception as e:
            with st.chat_message("assistant"):
                error_msg = f"Error processing request with Gemini: {str(e)}"
                st.error(error_msg)
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})