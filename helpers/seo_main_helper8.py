#SeoTree/helpers/seo_main_helper8.py
import streamlit as st
import re
import json
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Callable, Dict, Any
from utils.language_support import language_manager
import logging

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
You are SEO Helper, an expert SEO strategist and content architect.

Your primary goal is to answer the user's questions by providing SEO-optimized and creative content strategies, drawing from the website analysis report and other information provided in the 'User Information and Context' section below. This context is comprehensive and may already include AI-generated strategic insights, recommendations, keyword analysis, and subpage details from an SEO report.

When responding to the user's question:
1.  **Prioritize the Provided Context**: Thoroughly analyze the 'User Information and Context' (which includes any available SEO Report/Detailed Analysis, conversation history, and user information) to understand the user's query and the website's current SEO status.
2.  **Strategic Planning, Not Just Answers**: Your aim is to help the user decide on the best strategies considering the report and their question, and then to help them form a plan for implementation.
    * **Do NOT create full content directly.** Instead, guide the user by suggesting focus keywords, relevant long-tail and potentially low-competition keywords, ideas for content structure, content length considerations, overall tone, and other necessary details for content creation.
    * Explicitly mention that after your strategic advice, they can use tools like "Article Writer / Makale Yazarı" or "Product Writer / Ürün Yazarı " to generate the actual content based on your plan.
3.  **Leverage and Enhance Existing Insights**:
    * If the 'User Information and Context' (especially within an SEO report section) contains pre-existing suggestions (e.g., 'suggested_keywords_for_seo', 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS', 'Site-Wide Subpage SEO Suggestions'), do not just repeat them.
    * Instead, *integrate, build upon, refine, or offer alternatives* to these existing insights in direct response to the user's question. Help the user understand how those suggestions apply to their current query, how they could be prioritized, or what a practical next step would be.
4.  **Incorporate Strategic SEO Elements (where relevant and helpful to the user's question)**:
    * **Keyword Strategy**: If the question relates to content ideas, improvement, or ranking, suggest relevant primary, secondary, and potentially low-competition keywords. Explain the rationale.
    * **Content Opportunities**: If appropriate for the question, identify potential new content topics, alternative page ideas (e.g., supporting articles, FAQ sections, cornerstone content) that could fill content gaps, target new keyword opportunities, or build site authority related to the user's query.
    * **Tone and Audience Alignment**: If the question touches upon content creation, refinement, or audience engagement, advise on aligning content tone with the target audience identified in the analysis or help define it.
    * **Actionable Steps**: Provide clear, actionable steps or considerations that the user can take forward.
5.  **Be Specific and Practical**: Offer high-priority, easy-to-implement strategies where possible. If relevant to the question and strategy, you can include considerations for internal linking, backlinks, social media posts, or video content to support the core content strategies.

User Information and Context (includes SEO report data and conversation history):
{context}

User's Current Question: {prompt}

Please provide a helpful, comprehensive, and strategic response to the user's question, keeping the above guidelines in mind. Focus on empowering the user to make informed decisions and effectively plan their content.

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
            description="Provide comprehensive SEO suggestions based on the llm_analysis_all data",
            function=generate_seo_suggestions,
            parameters=[], # No parameters needed - function will access session state
            validation=True,
            prompt="Generating comprehensive SEO suggestions..."
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
        if st.session_state.get("text_report") or (st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all")):
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
                st.markdown("Please provide a website URL first so I can analyze it and generate a comprehensive report.")
            st.session_state[message_list].append({"role": "assistant", "content": "Please provide a website URL first so I can analyze it and generate a comprehensive report."})

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str, message_list: str = "messages"):
    """Process the chat input using Mistral API."""
    lang = st.session_state.get("language", "en")
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."

    with st.spinner(spinner_text):
        with st.chat_message("assistant"):
            try:
                # Build conversation history context
                history_context = ""
                num_history_turns = 5 
                messages_to_process = st.session_state.get(message_list, [])
                # Ensure we don't go out of bounds and take up to num_history_turns of CONVERSATION history
                actual_history = [m for m in messages_to_process if m.get('role') != 'system'] # Exclude any system messages if they exist
                start_index = max(0, len(actual_history) - num_history_turns) # Get last N turns before current prompt
                for message in actual_history[start_index:]:
                    history_context += f"{message['role'].capitalize()}: {message['content']}\n"
                
                username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
                
                # Prepare context data from SEO analysis
                context_data = ""
                if st.session_state.get("text_report"):
                    context_data = f"SEO Report (Summary): {st.session_state.text_report}"
                elif st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                    # Safely format JSON data
                    llm_analysis_content = st.session_state.full_report['llm_analysis_all']
                    if isinstance(llm_analysis_content, dict):
                        try:
                            context_data = f"Detailed Analysis Data (llm_analysis_all):\n{json.dumps(llm_analysis_content, indent=2, ensure_ascii=False)}"
                        except Exception as e:
                            context_data = f"Detailed Analysis Data (llm_analysis_all):\n{str(llm_analysis_content)}"
                    else:
                        context_data = f"Detailed Analysis Data (llm_analysis_all):\n{str(llm_analysis_content)}"
                else:
                    context_data = "No SEO report or detailed analysis data is currently available."
                
                # Mistral API request
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {MISTRAL_API_KEY}"
                }
                
                language_info = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "
                
                system_prompt_content = f"""You are an SEO expert assistant and content strategist. {language_info}

Your primary role is to help users develop effective SEO and content strategies based on the website analysis data provided and their specific questions. You should guide them in planning content that they can later create using tools like "Article Writer" or "Product Writer".

Key Principles for Your Responses:
1.  **Context is Key**: Always ground your advice in the provided "Context from SEO Report" (which could be a summary or detailed analysis) and "Conversation History". This context may include detailed site analysis, AI-generated recommendations, and previous interactions.
2.  **Strategic Guidance over Direct Content Creation**:
    * Your goal is to help the user strategize. This means suggesting keywords (including low-competition ones if relevant and asked for or clearly beneficial), content structures or outlines, target audience considerations, optimal tone, and content length estimates.
    * Do NOT write full articles or product descriptions. Explicitly state that the user can take your strategic plan to tools like "Article Writer" or "Product Writer" for the actual content generation.
3.  **Build Upon, Don't Just Repeat**: If the provided "Context from SEO Report" already contains strategic advice, keyword suggestions (e.g., 'AI-POWERED STRATEGIC INSIGHTS', 'suggested_keywords_for_seo', 'Site-Wide Subpage SEO Suggestions'), your role when answering a related question is to:
    * Help the user understand how these existing suggestions apply to their current question.
    * Refine, elaborate on, or offer alternatives or complementary ideas to these existing points.
    * Help prioritize actions based on these insights if the user is asking for direction.
4.  **Incorporate Advanced SEO Concepts (When Relevant to the Question)**:
    * When a user's question opens the door for it, discuss opportunities like identifying content gaps, proposing new pages/topics to build topical authority, or refining content for better E-E-A-T signals.
    * Suggest practical, actionable steps.
5.  **Prioritization and Clarity**: Focus on high-impact, actionable advice. If suggesting multiple actions, try to indicate priorities (e.g., High, Medium, Low) where appropriate, especially if the user seems unsure where to start.

When responding to the user's prompt (which will be provided along with the context data in the user message):
- First, thoroughly analyze their question in light of all available context (SEO report data, conversation history, user info).
- If the existing report data directly addresses or is highly relevant to the query, synthesize and explain it strategically, offering next steps or deeper insights.
- If the query requires new analysis or elaboration beyond what's explicitly in the report, provide your expert strategic advice following the principles above.
- Ensure your entire response is in the requested language ({language_names.get(lang, 'English')}).
"""
                
                # Construct the user message with all context
                user_content_for_mistral = f"""User Information:
{username_context}

Conversation History (most recent turns for context):
{history_context}

Context from SEO Report (prioritize this for site-specific information):
{context_data}

Based on all the above information and my system persona (SEO expert assistant and content strategist), please answer the following user question. Focus on providing strategic advice and a plan, not generating full content. Guide me on how I can use tools like "Article Writer" or "Product Writer" with your strategy.

User Question: {prompt}
"""

                data = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt_content
                        },
                        {
                            "role": "user",
                            "content": user_content_for_mistral
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    response_json = response.json()
                    if response_json.get('choices') and len(response_json['choices']) > 0 and response_json['choices'][0].get('message'):
                        response_text = response_json['choices'][0]['message']['content']
                        st.markdown(response_text)
                        st.session_state[message_list].append({"role": "assistant", "content": response_text})
                    else:
                        error_msg = f"Mistral API response format error: 'choices' or 'message' structure not as expected. Response: {response.text}"
                        logging.error(error_msg)
                        st.markdown("I encountered an issue processing your request. Please try again.")
                        st.session_state[message_list].append({"role": "assistant", "content": "Mistral API response error. Please try again."})
                else:
                    error_msg = f"Mistral API error: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    st.markdown(f"I encountered an API error (Status: {response.status_code}). Please try again.")
                    st.session_state[message_list].append({"role": "assistant", "content": f"Mistral API error: {response.status_code}. Please try again."})
            except Exception as e:
                error_msg = f"Error connecting to Mistral API: {str(e)}"
                logging.error(error_msg)
                st.markdown("I encountered an error processing your request. Please try again.")
                st.session_state[message_list].append({"role": "assistant", "content": "Error processing request. Please try again."})


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
            suggestion_keywords = ["suggest", "recommendation", "improve", "optimize", "enhance", "strategy", "plan"]
            if any(keyword in prompt.lower() for keyword in suggestion_keywords) and \
               "generate_seo_suggestions" not in st.session_state.used_tools and \
               st.session_state.get("full_report") and \
               st.session_state.full_report.get("llm_analysis_all"):
                with st.chat_message("assistant"):
                    # generate_seo_suggestions will access llm_analysis_all directly from session state
                    response = tools["generate_seo_suggestions"].function()
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})
                    st.session_state.used_tools.add("generate_seo_suggestions")
                    tool_used = True
            elif any(keyword in prompt.lower() for keyword in suggestion_keywords) and \
                 (not st.session_state.get("full_report") or not st.session_state.full_report.get("llm_analysis_all")):
                with st.chat_message("assistant"):
                    msg = "To generate comprehensive SEO suggestions based on detailed page analysis, complete llm_analysis_all data is needed. Please analyze a URL first and wait for the detailed analysis to complete. I can still discuss any suggestions present in the current summary if available."
                    st.markdown(msg)
                    st.session_state[message_list].append({"role": "assistant", "content": msg})
                    tool_used = True

            if not tool_used:
                with st.chat_message("assistant"):
                    # Build conversation history
                    history_context = ""
                    num_history_turns = 5
                    messages_to_process = st.session_state.get(message_list, [])
                    start_index = max(0, len(messages_to_process) - num_history_turns)
                    for message in messages_to_process[start_index:]:
                        history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                    # Prepare context data - prioritize text_report, fallback to llm_analysis_all
                    context_data = ""
                    if st.session_state.get("text_report"):
                        context_data = f"SEO Report: {st.session_state.text_report}"
                    elif st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                        llm_analysis_content = st.session_state.full_report['llm_analysis_all']
                        if isinstance(llm_analysis_content, dict):
                            try:
                                context_data = f"Detailed Analysis Data (llm_analysis_all): {json.dumps(llm_analysis_content, indent=2, ensure_ascii=False)}"
                            except Exception as e:
                                context_data = f"Detailed Analysis Data (llm_analysis_all): {str(llm_analysis_content)}"
                        else:
                            context_data = f"Detailed Analysis Data (llm_analysis_all): {str(llm_analysis_content)}"
                    else:
                        context_data = "No SEO report available. Please analyze a URL first."

                    # Assemble context for Gemini
                    context_for_gemini = f"""Username: {st.session_state.username if "username" in st.session_state and st.session_state.username else "Anonymous"}

{context_data}

Conversation History (for reference, prioritize the SEO Report for site-specific questions):
{history_context}"""
                    
                    response = await tools["process_question"].function(prompt, context_for_gemini)
                    st.markdown(response)
                    st.session_state[message_list].append({"role": "assistant", "content": response})

        except Exception as e:
            with st.chat_message("assistant"):
                error_msg = f"Error processing request with Gemini: {str(e)}"
                logging.error(error_msg)
                st.markdown("I encountered an error processing your request. Please try again.")
                st.session_state[message_list].append({"role": "assistant", "content": "Error processing request. Please try again."})