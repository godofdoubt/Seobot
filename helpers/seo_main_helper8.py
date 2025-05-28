#SeoTree/helpers/seo_main_helper8.py
import streamlit as st
import re
import json
import google.generativeai as genai
import requests
from utils.s10tools import normalize_url, Tool
from typing import Callable, Dict, Any, List
from utils.language_support import language_manager
import logging
from datetime import datetime

try:
    from buttons.generate_article import generate_article
except ImportError:
    logging.error("Failed to import generate_article from buttons.generate_article.py in seo_main_helper8.py")
    generate_article = None

language_names = {"en": "English", "tr": "Turkish"}


async def handle_seo_helper_cta_response(prompt: str, message_list: str, lang: str) -> bool:
    """Handles the user's response to a CTA from SEO Helper, with direct article generation and storage."""
    if not st.session_state.get("awaiting_seo_helper_cta_response", False):
        return False

    prompt_lower = prompt.lower().strip()
    
    yes_keywords_list = language_manager.get_text("yes_keywords_list", lang, fallback="yes,evet,ok,okay,proceed,yep,yeah,do it,start,affirmative,please do").split(',')
    no_keywords_list = language_manager.get_text("no_keywords_list", lang, fallback="no,hayır,nope,stop,cancel,don't,negative,not now,later").split(',')

    is_affirmative = False
    for kw in yes_keywords_list:
        kw_stripped = kw.strip()
        if kw_stripped == prompt_lower or (f" {kw_stripped} " in f" {prompt_lower} ") or \
           prompt_lower.startswith(kw_stripped + " ") or prompt_lower.endswith(" " + kw_stripped):
            is_affirmative = True
            break
    
    is_negative = False
    if not is_affirmative: 
        for kw in no_keywords_list:
            kw_stripped = kw.strip()
            if kw_stripped == prompt_lower or (f" {kw_stripped} " in f" {prompt_lower} ") or \
               prompt_lower.startswith(kw_stripped + " ") or prompt_lower.endswith(" " + kw_stripped):
                is_negative = True
                break
    
    logging.info(f"CTA Response Handling: Prompt='{prompt}', Affirmative={is_affirmative}, Negative={is_negative}")

    cta_context = st.session_state.get("seo_helper_cta_context", {})
    
    if is_affirmative:
        if cta_context and cta_context.get("type") == "article_writer":
            tasks: List[Dict[str, Any]] = cta_context.get("tasks", [])
            current_task_index: int = cta_context.get("current_task_index", 0)

            if tasks and isinstance(tasks, list) and 0 <= current_task_index < len(tasks):
                current_task = tasks[current_task_index]
                task_title = current_task.get("suggested_title", "the selected article suggestion")

                article_generated = False
                generated_article_content = None 
                generation_error_message = None

                if generate_article is None:
                    generation_error_message = language_manager.get_text(
                        "seo_helper_article_gen_func_missing", lang,
                        fallback="Article generation function is not available. Cannot generate article."
                    )
                    logging.error("generate_article function is None, cannot proceed with article generation.")
                elif not st.session_state.get("text_report") or not st.session_state.get("url"):
                    generation_error_message = language_manager.get_text(
                        "seo_helper_article_gen_missing_report_url", lang,
                        fallback="Cannot generate article: Missing base report or URL. Please ensure an analysis is complete."
                    )
                    logging.error(f"Article generation for '{task_title}' skipped: missing text_report or url.")
                elif not current_task.get("focus_keyword"):
                    generation_error_message = language_manager.get_text(
                        "seo_helper_article_gen_missing_focus_keyword", lang, task_title=task_title,
                        fallback=f"Cannot generate article '{task_title}': Focus keyword is missing from the task details."
                    )
                    logging.error(f"Article generation for '{task_title}' skipped: missing focus_keyword.")
                else:
                    logging.info(f"SEO Helper CTA: Attempting to generate article for task: {task_title}")
                    try:
                        article_options_for_generation = {
                            "focus_keyword": current_task.get("focus_keyword"),
                            "content_length": current_task.get("content_length", "Medium"),
                            "tone": current_task.get("article_tone", "Professional"),
                            "keywords": ", ".join(current_task.get("additional_keywords", [])) if isinstance(current_task.get("additional_keywords"), list) else current_task.get("additional_keywords", ""),
                            "custom_title": current_task.get("suggested_title", "")
                        }
                        spinner_text_key = "seo_helper_generating_article_spin"
                        spinner_text = language_manager.get_text(spinner_text_key, lang, task_title=task_title, fallback=f"Generating article '{task_title}'... Please wait.")
                        
                        with st.spinner(spinner_text):
                            generated_article_content = generate_article(
                                text_report=st.session_state.text_report,
                                url=st.session_state.url,
                                article_options=article_options_for_generation
                            )
                        
                        if generated_article_content and isinstance(generated_article_content, str) and generated_article_content.strip():
                            article_generated = True
                            logging.info(f"SEO Helper CTA: Successfully generated article for task: {task_title}")
                            
                            if "completed_tasks_article" not in st.session_state:
                                st.session_state.completed_tasks_article = []
                            st.session_state.completed_tasks_article.append({ 
                                "title": task_title,
                                "options_used": article_options_for_generation,
                                "content": generated_article_content, 
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            # NEW: Signal to Article Writer page to display this
                            st.session_state.display_newly_generated_article_on_aw = {
                                "title": task_title,
                                "content": generated_article_content
                            }
                            logging.info(f"SEO Helper CTA: Signalling Article Writer to display newly generated article: {task_title}")

                        else:
                            generation_error_message = language_manager.get_text(
                                "seo_helper_article_gen_failed_empty", lang, task_title=task_title,
                                fallback=f"Article generation for '{task_title}' completed, but the result was empty or invalid."
                            )
                            logging.warning(f"SEO Helper CTA: Article generation for '{task_title}' resulted in empty/invalid content.")

                    except Exception as e:
                        generation_error_message = language_manager.get_text(
                            "seo_helper_article_gen_exception", lang, task_title=task_title, error_message=str(e),
                            fallback=f"An error occurred while generating the article '{task_title}': {str(e)}"
                        )
                        logging.error(f"SEO Helper CTA: Exception during article generation for '{task_title}': {e}", exc_info=True)
                
                if article_generated:
                    st.session_state.trigger_article_suggestion_from_seo_helper = False
                    st.session_state.article_suggestion_to_trigger_details = None
                    logging.info(f"SEO Helper CTA: Article for '{task_title}' generated and stored. Flags for AW trigger cleared.")
                elif generation_error_message: 
                    st.session_state.article_suggestion_to_trigger_details = current_task
                    st.session_state.trigger_article_suggestion_from_seo_helper = True
                    logging.info(f"SEO Helper CTA: Article generation for '{task_title}' failed or skipped. Flags for AW trigger set.")
                else: 
                    st.session_state.article_suggestion_to_trigger_details = current_task
                    st.session_state.trigger_article_suggestion_from_seo_helper = True
                    logging.info(f"SEO Helper CTA: Task '{task_title}' prepared (no generation attempt or unclear status). Flags for AW trigger set.")

                confirmation_message_parts = []
                if article_generated:
                    confirmation_message_parts.append(
                        language_manager.get_text( 
                            "seo_helper_cta_yes_article_generated_success_stored", lang, task_title=task_title,
                            fallback=f"Great! I've generated the article for '{task_title}'. It has been stored for your reference."
                        )
                    )
                elif generation_error_message:
                    confirmation_message_parts.append(generation_error_message)
                else:
                    confirmation_message_parts.append(
                         language_manager.get_text(
                            "seo_helper_cta_yes_task_prepared_single", lang, task_title=task_title,
                            fallback=f"Okay, I've noted down the task '{task_title}'. (Generation status unclear)."
                        )
                    )
                
                cta_context["current_task_index"] = current_task_index + 1
                st.session_state.seo_helper_cta_context = cta_context

                if cta_context["current_task_index"] < len(tasks):
                    next_task = tasks[cta_context["current_task_index"]]
                    next_task_title = next_task.get("suggested_title", "the next article suggestion")
                    follow_up_question = language_manager.get_text(
                        "seo_helper_cta_yes_prepare_next_q", lang, next_task_title=next_task_title,
                        fallback=f" There are more article suggestions. Would you like me to prepare and generate the next one: '{next_task_title}'? (yes/no)"
                    )
                    confirmation_message_parts.append(follow_up_question)
                    logging.info(f"SEO Helper CTA 'yes': Processed task '{task_title}'. Next task '{next_task_title}' offered.")
                else:
                    concluding_message = language_manager.get_text(
                        "seo_helper_cta_yes_all_tasks_processed_generation", lang,
                        fallback=" That was the last suggestion. Any generated articles have been noted and stored." 
                    )
                    confirmation_message_parts.append(concluding_message)
                    st.session_state.awaiting_seo_helper_cta_response = False
                    st.session_state.seo_helper_cta_context = None
                    logging.info(f"SEO Helper CTA 'yes': Processed task '{task_title}'. All tasks processed.")
                
                final_confirmation_message = "\n\n".join(filter(None, confirmation_message_parts))
                st.session_state[message_list].append({"role": "assistant", "content": final_confirmation_message})
                
                st.rerun()
                return True
            
            else: 
                error_message = language_manager.get_text(
                    "seo_helper_cta_yes_no_tasks_in_queue", lang,
                    fallback="Okay. It seems there were no specific tasks queued up, or I lost track. You can still visit the Article Writer page."
                )
                st.session_state[message_list].append({"role": "assistant", "content": error_message})
                logging.warning(f"CTA affirmative (article_writer) but tasks list empty or index out of bounds. Tasks: {tasks}, Index: {current_task_index}")
                st.session_state.awaiting_seo_helper_cta_response = False
                st.session_state.seo_helper_cta_context = None
                st.rerun()
                return True
        else: 
             logging.warning(f"CTA affirmative but cta_context is invalid or not for article_writer: {cta_context}")
             generic_yes_message = language_manager.get_text("seo_helper_cta_yes_generic", lang, fallback="Okay!")
             st.session_state[message_list].append({"role": "assistant", "content": generic_yes_message})
             st.session_state.awaiting_seo_helper_cta_response = False
             st.session_state.seo_helper_cta_context = None
             st.rerun() 
             return True

    elif is_negative:
        response_message_text = language_manager.get_text(
            "seo_helper_cta_no_task_not_prepared", lang,
            fallback="Alright. I won't prepare that task. Let me know if you change your mind or want to proceed with other suggestions later!"
        )
        st.session_state[message_list].append({"role": "assistant", "content": response_message_text})
        st.session_state.awaiting_seo_helper_cta_response = False
        st.session_state.seo_helper_cta_context = None
        logging.info("CTA negative. Current article preparation sequence ended. Flags cleared.")
        st.rerun()
        return True

    else: 
        current_task_title_for_prompt = "the suggestion"
        if cta_context and cta_context.get("type") == "article_writer":
            tasks = cta_context.get("tasks", [])
            current_task_index = cta_context.get("current_task_index", 0)
            if tasks and 0 <= current_task_index < len(tasks):
                current_task_title_for_prompt = tasks[current_task_index].get("suggested_title", "the current suggestion")
        
        response_message = language_manager.get_text(
            "seo_helper_cta_invalid_response_specific", lang,
            current_task_title=current_task_title_for_prompt,
            fallback=f"Please respond with 'yes' or 'no' to whether you'd like me to prepare the article suggestion: '{current_task_title_for_prompt}'."
        )
        st.session_state[message_list].append({"role": "assistant", "content": response_message})
        logging.info(f"CTA unclear for task '{current_task_title_for_prompt}'. Re-prompting.")
        st.rerun()
        return True
    
    return False

# ... (rest of seo_main_helper8.py, including create_tools, process_chat_input, etc.)


def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools."""
    
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except Exception as e:
        logging.error(f"Failed to initialize Gemini model with 'gemini-1.5-flash-latest': {e}. Falling back to 'gemini-pro'.")
        try:
            model = genai.GenerativeModel('gemini-pro') # Fallback
        except Exception as e_pro:
            logging.error(f"Failed to initialize Gemini model with 'gemini-pro': {e_pro}. Tool creation might fail.")
            model = None


    async def process_question(prompt: str, context: str) -> str:
        """Process a question using Gemini."""
        if not model:
            return "Error: Gemini model not initialized. Cannot process question."
        try:
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
            language_instruction = f"Please respond in {language_names.get(st.session_state.language, 'English')}." if st.session_state.language != "en" else ""
            
            full_prompt = f"""{language_instruction}
You are SEO Helper, an expert SEO strategist and content architect.

Your primary goal is to answer the user's questions by providing SEO-optimized and creative content strategies, drawing from the website analysis report and other information provided in the 'User Information and Context' section below. This context is comprehensive and may already include AI-generated strategic insights, recommendations, keyword analysis, and subpage details from an SEO report.

When responding to the user's question:
1.  **Prioritize the Provided Context**: Thoroughly analyze the 'User Information and Context' (which includes any available SEO Report/Detailed Analysis, conversation history, and user information) to understand the user's query and the website's current SEO status.
2.  **Strategic Planning, Not Just Answers**: Your aim is to help the user decide on the best strategies considering the report and their question, and then to help them form a plan for implementation.
    * **Do NOT create full content directly.** Instead, guide the user by suggesting focus keywords, relevant long-tail and potentially low-competition keywords, ideas for content structure, content length considerations, overall tone, and other necessary details for content creation.
    * Explicitly mention that after your strategic advice, they can use tools like "Article Writer / Makale Yazarı" or "Product Writer / Ürün Yazarı " to generate the actual content based on your plan. If you have just helped them generate an article for a specific task, acknowledge that this specific part is done but they can use those tools for *other* tasks or ideas.
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
            response = await model.generate_content_async(full_prompt) # Use async version
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"

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
            parameters=[], 
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
    lang = st.session_state.get("language", "en")

    # --- START: CTA Response Handling ---
    prompt_handled_by_cta = await handle_seo_helper_cta_response(prompt, message_list, lang)
    if prompt_handled_by_cta:
        return # CTA response handled, no further processing needed for this input.
    # --- END: CTA Response Handling ---

    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"):
            st.markdown("You need to log in first to use this service.")
        st.session_state[message_list].append({"role": "assistant", "content": "You need to log in first to use this service."})
        return
    
    if re.match(r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$', prompt):
        with st.chat_message("assistant"):
            st.markdown(f"Processing URL: {prompt}...")
        await process_url_from_main(prompt, lang)
    else:
        if st.session_state.get("text_report") or (st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all")):
            if MISTRAL_API_KEY and (not GEMINI_API_KEY or st.session_state.get("use_mistral", False)):
                await process_with_mistral(prompt, MISTRAL_API_KEY, message_list)
            elif GEMINI_API_KEY:
                await process_with_gemini(prompt, GEMINI_API_KEY, message_list)
            else:
                error_msg_no_keys = "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY."
                with st.chat_message("assistant"):
                    st.markdown(error_msg_no_keys)
                st.session_state[message_list].append({"role": "assistant", "content": error_msg_no_keys})
        else:
            msg_provide_url = "Please provide a website URL first so I can analyze it and generate a comprehensive report."
            with st.chat_message("assistant"):
                st.markdown(msg_provide_url)
            st.session_state[message_list].append({"role": "assistant", "content": msg_provide_url})
        st.rerun() 

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str, message_list: str = "messages"):
    lang = st.session_state.get("language", "en")
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."

    with st.spinner(spinner_text):
        try:
            history_context = ""
            num_history_turns = 5 
            messages_to_process = st.session_state.get(message_list, [])
            actual_history = [m for m in messages_to_process if m.get('role') != 'system']
            history_candidates = actual_history[:-1] if actual_history and actual_history[-1]["content"] == prompt and actual_history[-1]["role"] == "user" else actual_history

            start_index = max(0, len(history_candidates) - num_history_turns)
            for message in history_candidates[start_index:]:
                history_context += f"{message['role'].capitalize()}: {message['content']}\n"
            
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
            
            context_data = ""
            if st.session_state.get("text_report"):
                context_data = f"SEO Report (Summary): {st.session_state.text_report}"
            elif st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                llm_analysis_content = st.session_state.full_report['llm_analysis_all']
                try:
                    context_data = f"Detailed Analysis Data (llm_analysis_all):\n{json.dumps(llm_analysis_content, indent=2, ensure_ascii=False)}"
                except Exception: 
                    context_data = f"Detailed Analysis Data (llm_analysis_all):\n{str(llm_analysis_content)}"
            else:
                context_data = "No SEO report or detailed analysis data is currently available."
            
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MISTRAL_API_KEY}"
            }
            
            language_info = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "
            system_prompt_content = f"""You are an SEO expert assistant and content strategist. {language_info}
Your primary role is to help users develop effective SEO and content strategies based on the website analysis data provided and their specific questions. You should guide them in planning content that they can later create using tools like "Article Writer" or "Product Writer". If you have just helped them generate an article for a specific task, acknowledge that this specific part is done but they can use those tools for *other* tasks or ideas.
Key Principles for Your Responses:
1.  **Prioritize Provided Context**: Analyze 'User Information and Context' (SEO Report, conversation history, user info) for the user's query and website's SEO status.
2.  **Strategic Planning, Not Just Answers**: Aim to help users decide on strategies and plan implementation.
    *   **Do NOT create full content.** Guide by suggesting keywords, content structure, length, tone for content creation.
    *   Mention users can use "Article Writer / Makale Yazarı" or "Product Writer / Ürün Yazarı" for actual content generation.
3.  **Leverage and Enhance Existing Insights**:
    *   If 'User Information and Context' has suggestions (e.g., 'suggested_keywords_for_seo', 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS'), *integrate, build upon, refine, or offer alternatives*. Explain how suggestions apply to the current query.
4.  **Incorporate Strategic SEO Elements**:
    *   **Keyword Strategy**: Suggest primary, secondary, low-competition keywords with rationale.
    *   **Content Opportunities**: Identify new topics, alternative page ideas (articles, FAQs, cornerstone content).
    *   **Tone and Audience Alignment**: Advise on aligning content tone with the target audience.
    *   **Actionable Steps**: Provide clear, actionable steps.
5.  **Be Specific and Practical**: Offer high-priority, easy-to-implement strategies. Consider internal linking, backlinks, social media, video content.
"""
            
            user_content_for_mistral = f"""User Information:
{username_context}

Conversation History (most recent turns for context):
{history_context}

Context from SEO Report (prioritize this for site-specific information):
{context_data}

Based on all the above information and my system persona (SEO expert assistant and content strategist), please answer the following user question. Focus on providing strategic advice and a plan, not generating full content (unless specifically asked to refine a previous generation or for very short snippets). Guide me on how I can use tools like "Article Writer" or "Product Writer" with your strategy.

User Question: {prompt}
"""
            data = {
                "model": "mistral-large-latest", # or "mistral-medium" / "mistral-small" based on needs
                "messages": [
                    {"role": "system", "content": system_prompt_content},
                    {"role": "user", "content": user_content_for_mistral}
                ],
                "temperature": 0.7, "max_tokens": 2000 # Adjust as needed
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('choices') and len(response_json['choices']) > 0 and response_json['choices'][0].get('message'):
                    response_text = response_json['choices'][0]['message']['content']
                    st.session_state[message_list].append({"role": "assistant", "content": response_text})
                else:
                    logging.error(f"Mistral API response format error: {response.text}")
                    st.session_state[message_list].append({"role": "assistant", "content": "Mistral API response error. Please try again."})
            else:
                logging.error(f"Mistral API error: {response.status_code} - {response.text}")
                st.session_state[message_list].append({"role": "assistant", "content": f"Mistral API error: {response.status_code}. Please try again."})
        except Exception as e:
            logging.error(f"Error connecting to Mistral API: {str(e)}")
            st.session_state[message_list].append({"role": "assistant", "content": "Error processing request. Please try again."})


async def process_with_gemini(prompt: str, GEMINI_API_KEY: str, message_list: str = "messages"):
    lang = st.session_state.get("language", "en")
    tools = create_tools(GEMINI_API_KEY) 
    
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."

    with st.spinner(spinner_text):
        try:
            if "used_tools" not in st.session_state: st.session_state.used_tools = set()
            tool_used = False

            # Keywords that might trigger the "generate_seo_suggestions" tool
            suggestion_keywords = ["suggest", "recommendation", "improve", "optimize", "enhance", "strategy", "plan"]
            # Check if the prompt seems to ask for general SEO suggestions AND detailed analysis is available
            if any(keyword in prompt.lower() for keyword in suggestion_keywords) and \
               "generate_seo_suggestions" not in st.session_state.used_tools and \
               st.session_state.get("full_report") and \
               st.session_state.full_report.get("llm_analysis_all"):
                
                # This tool 'generate_seo_suggestions' is specific and might be better called from 1_SEO_Helper.py logic directly
                # For general chat, 'process_question' should be the main handler which can synthesize info.
                # Keeping it here for now as per original structure, but it can lead to less conversational flow if triggered broadly.
                # Consider if this specific tool call should be removed from generic chat processing.
                # response = tools["generate_seo_suggestions"].function() 
                # st.session_state[message_list].append({"role": "assistant", "content": response})
                # st.session_state.used_tools.add("generate_seo_suggestions")
                # tool_used = True
                pass # Decided to let process_question handle this to be more conversational

            elif any(keyword in prompt.lower() for keyword in suggestion_keywords) and \
                 (not st.session_state.get("full_report") or not st.session_state.full_report.get("llm_analysis_all")):
                # If asking for suggestions but no detailed data, inform the user.
                msg = "To generate comprehensive SEO suggestions based on detailed page analysis, the full site analysis data is needed. Please analyze a URL first and ensure the detailed analysis (LLM analysis) is complete. I can still discuss any general SEO topics or suggestions present in the current summary if available."
                st.session_state[message_list].append({"role": "assistant", "content": msg})
                tool_used = True # Handled by informing the user

            if not tool_used:
                history_context = ""
                num_history_turns = 5 # Number of recent conversation turns to include
                messages_to_process = st.session_state.get(message_list, [])
                # Exclude system messages and the current user prompt if it's already appended
                actual_history = [m for m in messages_to_process if m.get('role') != 'system']
                history_candidates = actual_history[:-1] if actual_history and actual_history[-1]["content"] == prompt and actual_history[-1]["role"] == "user" else actual_history
                
                start_index = max(0, len(history_candidates) - num_history_turns)
                for message in history_candidates[start_index:]:
                    history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                context_data = ""
                if st.session_state.get("text_report"): # Basic text report
                    context_data = f"SEO Report (Summary): {st.session_state.text_report}"
                if st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"): # More detailed LLM analysis
                    llm_analysis_content = st.session_state.full_report['llm_analysis_all']
                    try: # Try to pretty print JSON if it's structured
                        context_data += f"\n\nDetailed Analysis Data (llm_analysis_all): {json.dumps(llm_analysis_content, indent=2, ensure_ascii=False)}"
                    except Exception: # Fallback to string representation
                        context_data += f"\n\nDetailed Analysis Data (llm_analysis_all): {str(llm_analysis_content)}"
                
                if not context_data: # If neither report is available
                    context_data = "No SEO report or detailed analysis data is currently available."

                context_for_gemini = f"""Username: {st.session_state.username if "username" in st.session_state and st.session_state.username else "Anonymous"}
{context_data}

Conversation History (for reference, prioritize the SEO Report/Detailed Analysis for site-specific questions):
{history_context}"""
                
                response = await tools["process_question"].function(prompt, context_for_gemini)
                st.session_state[message_list].append({"role": "assistant", "content": response})

        except Exception as e:
            logging.error(f"Error processing request with Gemini: {str(e)}", exc_info=True)
            st.session_state[message_list].append({"role": "assistant", "content": "Error processing request with Gemini. Please try again."})