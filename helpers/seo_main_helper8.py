#SeoTree/helpers/seo_main_helper8.py
import streamlit as st
import re
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Callable, Dict, Any
from utils.language_support import language_manager
from utils.shared_functions import analyze_website
language_names = {"en": "English", "tr": "Turkish"}

def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools."""
    
    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    async def process_question(prompt: str, context: str) -> str:
        """Process a question using o10."""
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
            parameters=["report"],
            validation=True,
            prompt="Generating SEO suggestions..."
        )
        # Add other tools here as needed
    }

    return tools

async def process_chat_input(
    prompt: str,
    analyze_website: Callable,
    load_saved_report: Callable,
    display_report_and_services: Callable,
    MISTRAL_API_KEY: str = None,
    GEMINI_API_KEY: str = None,
    message_list: str = "messages"
):
    """Processes chat input and handles URL analysis or question answering.
    Supports both Gemini and Mistral API for chat responses.
    """
    lang = st.session_state.get("language", "en")


    # Check authentication before processing
    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"):
            st.markdown("You need to log in first to use this service.")
            return
    
    # Handle URL analysis
    if re.match(r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$', prompt):
        normalized_url = normalize_url(prompt)
        text_report, full_report = load_saved_report(normalized_url)
        
        if text_report and full_report:
            display_report_and_services(text_report, full_report, normalized_url)
            st.session_state.analysis_complete = True  # Make sure this is set
        else:
            with st.chat_message("assistant"):
                st.markdown(f"Analyzing {normalized_url}...")
            with st.spinner("Analyzing website..."):
                text_report, full_report = await analyze_website(normalized_url)
                if text_report and full_report:
                    display_report_and_services(text_report, full_report, normalized_url)
                    st.session_state.analysis_complete = True  # Make sure this is set
                else:
                    with st.chat_message("assistant"):
                        st.markdown("Analysis completed, but no report was generated.")
                    st.session_state[message_list].append({"role": "assistant", "content": "Analysis completed, but no report was generated."})
                    

    else:
        # Handle questions using appropriate model
        if st.session_state.text_report:
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
    
    #await process_chat_input(...)
    
    #if st.session_state.analysis_complete:
     #   st.rerun()
            

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str, message_list: str = "messages"):
    """Process the chat input using Mistral API."""


    lang = st.session_state.get("language", "en")
    with st.spinner(language_manager.get_text("analyzing_website", lang)):
        with st.chat_message("assistant"):
            try:
                # Prepare conversation history context
                history_context = ""
                num_history_turns = 5
                messages = st.session_state[message_list]
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
{st.session_state.text_report}"""
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
    # Initialize tools
    lang = st.session_state.get("language", "en")
    tools = create_tools(GEMINI_API_KEY)
    
    with st.spinner(language_manager.get_text("analyzing_website", lang)):
        try:
            # Initialize used_tools in session state if it doesn't exist
            if "used_tools" not in st.session_state:
                st.session_state.used_tools = set()

            # --- Tool Selection Logic ---
            tool_used = False  # Flag to track if any tool was used

            if any(keyword in prompt.lower() for keyword in ["suggest", "recommendation", "improve", "seo"]) and "generate_seo_suggestions" not in st.session_state.used_tools:
                with st.chat_message("assistant"):
                    response = tools["generate_seo_suggestions"].function(st.session_state.text_report)
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})
                    st.session_state.used_tools.add("generate_seo_suggestions")
                    tool_used = True

            # Add other tool conditions here as needed

            if not tool_used: # Only use process_question if NO other tool was used
                # Use default question processing tool
                with st.chat_message("assistant"):
                    history_context = ""
                    num_history_turns = 5
                    messages = st.session_state[message_list]
                    start_index = max(0, len(messages) - num_history_turns)
                    for message in messages[start_index:]:
                        history_context += f"{message['role'].capitalize()}: {message['content']}\n"


                    # Add language information to system message
                    #language_info = f"Please respond in {language_names.get(lang, 'English')}. " if lang != "en" else ""
                    context = f"""
                    Username: {st.session_state.username if "username" in st.session_state else "Anonymous"}
                    SEO Report: {st.session_state.text_report}
                    Conversation History: {history_context}
                    """
                    response = await tools["process_question"].function(prompt, context)
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})

        except Exception as e:
            with st.chat_message("assistant"):
                error_msg = f"Error processing request: {str(e)}"
                st.error(error_msg)
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})

      