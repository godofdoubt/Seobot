#SeoTree/helpers/seo_main_helper8.py
import streamlit as st
import re
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Callable, Dict, Any
from utils.language_support import language_manager
# utils.shared_functions.analyze_website is not directly used here anymore for URL processing
# if process_url_from_main handles it all.
language_names = {"en": "English", "tr": "Turkish"}

def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools."""
    
    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # Updated to a generally available model

    async def process_question(prompt: str, context: str) -> str:
        """Process a question using Gemini.""" # Changed o10 to Gemini for clarity
        try:
            # Include username in context if available
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
            language_instruction = f"Please respond in {language_names.get(st.session_state.language, 'English')}." if st.session_state.language != "en" else ""
            
            full_prompt = f"""{language_instruction}
            {username_context}Context: {context}
            Question: {prompt}
            
            Please provide a helpful response based on the context.
            """
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"

    # Create tools dictionary with actual function implementations
    from buttons.generate_seo_suggestions import generate_seo_suggestions
    # Import other tool functions as needed
    
    tools = {
        "process_question": Tool(
            description="Process a question using the chat context and SEO report",
            function=process_question,
            parameters=["prompt", "context"],
            validation=True,
            prompt="Processing your question..."
        ),
        "generate_seo_suggestions": Tool(
            description="Provide SEO suggestions based on the full SEO report",
            function=generate_seo_suggestions,
            parameters=["report"], # This expects the full_report, not text_report
            validation=True,
            prompt="Generating SEO suggestions..."
        )
        # Add other tools here as needed
    }

    return tools

async def process_chat_input(
    prompt: str,
    process_url_from_main: Callable, # MODIFIED: New parameter to call main.py's process_url
    MISTRAL_API_KEY: str = None,
    GEMINI_API_KEY: str = None,
    message_list: str = "messages"
    # analyze_website, load_saved_report, display_report_and_services are no longer needed here
    # if process_url_from_main handles all URL processing aspects.
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
        with st.chat_message("assistant"): # Provide immediate feedback in chat
            st.markdown(f"Processing URL: {prompt}...")
        # Add user prompt to message list before calling process_url, 
        # as process_url might rerun and clear current chat display if not careful
        # St.session_state[message_list].append({"role": "user", "content": prompt}) # Already done by caller
        
        await process_url_from_main(prompt, lang)
        # process_url_from_main (main.py's process_url) is expected to handle:
        # - Normalization
        # - Checking saved reports (via load_saved_report)
        # - Analyzing new sites (via analyze_website)
        # - Saving reports
        # - Triggering background tasks (llm_analysis_end.py)
        # - Updating session_state (text_report, full_report, url, analysis_complete)
        # - Calling main.py's display_report which does st.rerun()
        # - Displaying relevant messages during its execution (e.g., "Analyzing...", "Found existing report...")
        # No need to explicitly call display_report_and_services or set analysis_complete here.
        # The st.rerun() from main.py's display_report will refresh the UI.

    else:
        # Handle questions using appropriate model
        if st.session_state.get("text_report"): # Check .get("text_report") for safety
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
    
    # The st.rerun() if a URL was processed will happen due to main.py's display_report.
    # If it was a question, the UI updates messages directly.

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str, message_list: str = "messages"):
    """Process the chat input using Mistral API."""
    lang = st.session_state.get("language", "en")
    # Using language_manager for spinner text
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."


    with st.spinner(spinner_text):
        with st.chat_message("assistant"):
            try:
                history_context = ""
                num_history_turns = 5
                messages_to_process = st.session_state.get(message_list, []) # Use .get for safety
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
                
                data = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""You are an SEO expert assistant. {language_info}Provide helpful responses based on the website analysis report.
                            
User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.get("text_report", "No SEO report available.")}""" # Use .get for safety
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

            # Ensure full_report exists for generate_seo_suggestions
            if any(keyword in prompt.lower() for keyword in ["suggest", "recommendation", "improve", "seo"]) and \
               "generate_seo_suggestions" not in st.session_state.used_tools and \
               st.session_state.get("full_report"): # Check for full_report
                with st.chat_message("assistant"):
                    # generate_seo_suggestions expects the full_report dictionary
                    response = tools["generate_seo_suggestions"].function(st.session_state.full_report)
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})
                    st.session_state.used_tools.add("generate_seo_suggestions")
                    tool_used = True
            elif any(keyword in prompt.lower() for keyword in ["suggest", "recommendation", "improve", "seo"]) and \
                 not st.session_state.get("full_report"):
                 with st.chat_message("assistant"):
                    msg = "SEO suggestions require a full analysis report, which is not available. Please analyze a URL first."
                    st.markdown(msg)
                    st.session_state[message_list].append({"role": "assistant", "content": msg})
                    tool_used = True # Technically a response was given, not a tool use.

            if not tool_used:
                with st.chat_message("assistant"):
                    history_context = ""
                    num_history_turns = 5
                    messages_to_process = st.session_state.get(message_list, [])
                    start_index = max(0, len(messages_to_process) - num_history_turns)
                    for message in messages_to_process[start_index:]:
                        history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                    context = f"""
                    Username: {st.session_state.username if "username" in st.session_state else "Anonymous"}
                    SEO Report: {st.session_state.get("text_report", "No SEO report available.")}
                    Conversation History: {history_context}
                    """
                    response = await tools["process_question"].function(prompt, context)
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})

        except Exception as e:
            with st.chat_message("assistant"):
                error_msg = f"Error processing request: {str(e)}"
                st.error(error_msg) # Use st.error for better visibility of actual errors
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})