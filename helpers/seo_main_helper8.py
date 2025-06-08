
#Seobot/helpers/seo_main_helper8.py
import streamlit as st
import re
import json
import google.generativeai as genai
import requests
import os # Ensure os is imported
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

try:
    from buttons.generate_product_description import generate_product_description_with_api_choice
except ImportError:
    logging.error("Failed to import generate_product_description_with_api_choice from buttons.generate_product_description.py in seo_main_helper8.py")
    generate_product_description_with_api_choice = None


language_names = {"en": "English", "tr": "Turkish"}

# --- HELPER FUNCTION ---
def get_task_title(task_item, task_type_str):
    if not task_item: return "the current suggestion"
    if task_type_str == "article_writer":
        return task_item.get("suggested_title", "the current article suggestion")
    elif task_type_str == "product_writer":
        return task_item.get("product_name", "the current product suggestion")
    return "the current suggestion"

def get_next_task_prompt(current_tasks_list, current_idx, current_task_type, current_lang):
    next_task_detail = current_tasks_list[current_idx]
    next_task_name = get_task_title(next_task_detail, current_task_type)
    
    prompt_key = "seo_helper_cta_next_task_q_extended_options_article" \
        if current_task_type == "article_writer" else "seo_helper_cta_next_task_q_extended_options_product"
    
    return language_manager.get_text(
        prompt_key, current_lang, task_title=next_task_name,
        current_num=current_idx + 1, total_num=len(current_tasks_list),
        fallback=(f"The next {current_task_type.replace('_', ' ')} task ({current_idx + 1}/{len(current_tasks_list)}) is '{next_task_name}'. "
                  f"Shall I prepare it, skip to the next, or stop? (yes/skip/stop)")
    )

# --- NEW HELPER FUNCTION ---
def _handle_task_batch_completion_or_transition(
    initial_response_parts: List[str], 
    cta_context: Dict[str, Any], 
    completed_task_type: str, 
    lang: str, 
    message_list: str
):
    """
    Handles the completion of a task batch (e.g., articles).
    Transitions to secondary tasks if available, otherwise ends the CTA.
    Appends a consolidated message to the chat.
    """
    final_response_parts = list(initial_response_parts) # Make a copy

    secondary_info = cta_context.get("secondary_tasks_info")
    
    if secondary_info and secondary_info.get("type") and secondary_info.get("tasks"):
        primary_type_readable = completed_task_type.replace('_', ' ')
        secondary_type_readable = secondary_info["type"].replace('_', ' ')
        
        final_response_parts.append(language_manager.get_text(
            "seo_helper_cta_primary_done_now_secondary", lang, 
            primary_type=primary_type_readable, 
            secondary_type=secondary_type_readable, 
            fallback=f"Great! We've addressed the {primary_type_readable} tasks. Now, I also found some {secondary_type_readable} tasks."
        ))
        
        # Update CTA context for the secondary tasks
        cta_context["type"] = secondary_info["type"]
        cta_context["tasks"] = secondary_info["tasks"]
        cta_context["current_task_index"] = 0
        cta_context["secondary_tasks_info"] = None # Mark as consumed
        
        st.session_state.seo_helper_cta_context = cta_context
        st.session_state.awaiting_seo_helper_cta_response = True # Continue CTA for the new batch
        
        # Add prompt for the first task of the new (secondary) batch
        final_response_parts.append(get_next_task_prompt(cta_context["tasks"], 0, cta_context["type"], lang))
        logging.info(f"CTA: Primary batch '{completed_task_type}' done. Transitioning to secondary batch '{cta_context['type']}'.")
    else:
        final_response_parts.append(language_manager.get_text(
            "seo_helper_cta_all_tasks_processed_or_skipped", lang, 
            fallback="All tasks in this sequence have been addressed or skipped."
        ))
        st.session_state.awaiting_seo_helper_cta_response = False
        st.session_state.seo_helper_cta_context = None
        st.session_state.paused_cta_context = None # Clear pause if we naturally finish all batches
        logging.info(f"CTA: All tasks for batch '{completed_task_type}' completed. No further (e.g. secondary) tasks found or they were already processed.")
        
    st.session_state[message_list].append({"role": "assistant", "content": "\n\n".join(filter(None, final_response_parts))})

# --- MODIFIED FUNCTION ---
async def handle_seo_helper_cta_response(prompt: str, message_list: str, lang: str) -> bool:
    """Handles the user's response to a CTA from SEO Helper, with direct article/product generation and storage."""
    if not st.session_state.get("awaiting_seo_helper_cta_response", False):
        return False

    prompt_lower = prompt.lower().strip()
    
    yes_keywords_list = language_manager.get_text("yes_keywords_list", lang, fallback="yes,evet,ok,okay,proceed,yep,yeah,do it,start,affirmative,please do,select,tamam").split(',')
    no_keywords_list = language_manager.get_text("no_keywords_list", lang, fallback="no,hayır,nope,stop,cancel,don't,negative,not now,later,dur,iptal,bitir").split(',')
    skip_keywords_list = language_manager.get_text("skip_keywords_list", lang, fallback="skip,atla,next,sonraki,pass,geç").split(',')


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
    
    is_skip = False
    if not is_affirmative and not is_negative:
        for kw in skip_keywords_list:
            kw_stripped = kw.strip()
            if kw_stripped == prompt_lower or (f" {kw_stripped} " in f" {prompt_lower} ") or \
               prompt_lower.startswith(kw_stripped + " ") or prompt_lower.endswith(" " + kw_stripped):
                is_skip = True
                break

    logging.info(f"CTA Response Handling: Prompt='{prompt}', Affirmative={is_affirmative}, Negative={is_negative}, Skip={is_skip}")

    cta_context = st.session_state.get("seo_helper_cta_context", {})
    task_type = cta_context.get("type") # article_writer or product_writer

    if is_affirmative:
        if cta_context and task_type == "article_writer":
            tasks: List[Dict[str, Any]] = cta_context.get("tasks", [])
            current_task_index: int = cta_context.get("current_task_index", 0)

            if tasks and isinstance(tasks, list) and 0 <= current_task_index < len(tasks):
                current_task = tasks[current_task_index]
                task_title = get_task_title(current_task, task_type)

                article_generated = False
                generated_article_content = None 
                generation_error_message = None
                article_options = {} 

                if generate_article is None:
                    generation_error_message = language_manager.get_text("seo_helper_article_gen_func_missing", lang, fallback="Article generation function is not available.")
                elif not st.session_state.get("text_report") or not st.session_state.get("url"):
                    generation_error_message = language_manager.get_text("seo_helper_article_gen_missing_report_url", lang, fallback="Missing base report or URL for article generation.")
                elif not current_task.get("focus_keyword"):
                    generation_error_message = language_manager.get_text("seo_helper_article_gen_missing_focus_keyword", lang, task_title=task_title, fallback=f"Focus keyword missing for '{task_title}'.")
                else:
                    logging.info(f"SEO Helper CTA: Attempting to generate article for task: {task_title}")
                    try:
                        article_options = { 
                            "focus_keyword": current_task.get("focus_keyword"),
                            "content_length": current_task.get("content_length", "Medium"),
                            "tone": current_task.get("article_tone", "Professional"),
                            "keywords": ", ".join(current_task.get("additional_keywords", [])) if isinstance(current_task.get("additional_keywords"), list) else current_task.get("additional_keywords", ""),
                            "custom_title": current_task.get("suggested_title", "")
                        }
                        spinner_text = language_manager.get_text("seo_helper_generating_article_spin", lang, task_title=task_title, fallback=f"Generating article '{task_title}'...")
                        with st.spinner(spinner_text):
                            generated_article_content = generate_article(st.session_state.text_report, st.session_state.url, article_options)
                        
                        if generated_article_content and isinstance(generated_article_content, str) and generated_article_content.strip() and not generated_article_content.lower().startswith("error:"):
                            article_generated = True
                        else:
                            generation_error_message = language_manager.get_text("seo_helper_article_gen_failed_empty", lang, task_title=task_title, fallback=f"Article generation for '{task_title}' was empty or indicated an error: {generated_article_content}")
                    except Exception as e:
                        generation_error_message = language_manager.get_text("seo_helper_article_gen_exception", lang, task_title=task_title, error_message=str(e), fallback=f"Error generating '{task_title}': {e}")
                
                confirmation_parts = []
                if article_generated:
                    if "articles_pending_display_on_aw" not in st.session_state:
                        st.session_state.articles_pending_display_on_aw = []
                    
                    st.session_state.articles_pending_display_on_aw.append({
                        "title": task_title, 
                        "content": generated_article_content,
                        "options_used": article_options
                    })
                    logging.info(f"SEO Helper: Added '{task_title}' to articles_pending_display_on_aw. List size: {len(st.session_state.articles_pending_display_on_aw)}")

                    if "completed_tasks_article" not in st.session_state: 
                        st.session_state.completed_tasks_article = []
                    st.session_state.completed_tasks_article.append({
                        "title": task_title, 
                        "options_used": article_options, 
                        "content_generated_directly": True,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    st.session_state.trigger_article_suggestion_from_seo_helper = False 
                    st.session_state.article_suggestion_to_trigger_details = None # Clear as it's handled

                    confirmation_parts.append(language_manager.get_text(
                        "seo_helper_cta_yes_article_generated_success_multi", lang, task_title=task_title,
                        fallback=f"Generated article for '{task_title}'. It will be available on the Article Writer page."
                    ))

                elif generation_error_message: 
                    st.session_state.trigger_article_suggestion_from_seo_helper = True 
                    st.session_state.article_suggestion_to_trigger_details = current_task
                    confirmation_parts.append(generation_error_message)
                    confirmation_parts.append(language_manager.get_text(
                        "seo_helper_cta_article_gen_error_goto_aw", lang, task_title=task_title,
                        fallback=f"Due to an error, the article for '{task_title}' could not be generated directly. Options have been sent to Article Writer."
                    ))
                else: # Fallback if no generation attempted or specific error. Should ideally not be hit if logic is correct.
                    st.session_state.trigger_article_suggestion_from_seo_helper = True 
                    st.session_state.article_suggestion_to_trigger_details = current_task
                    confirmation_parts.append(language_manager.get_text("seo_helper_cta_yes_task_prepared_single", lang, task_title=task_title, fallback=f"Prepared task '{task_title}'. Use Article Writer."))
                
                cta_context["current_task_index"] = current_task_index + 1
                st.session_state.seo_helper_cta_context = cta_context

                if cta_context["current_task_index"] < len(tasks):
                    confirmation_parts.append(get_next_task_prompt(tasks, cta_context["current_task_index"], task_type, lang))
                    st.session_state[message_list].append({"role": "assistant", "content": "\n\n".join(filter(None, confirmation_parts))})
                else: 
                    _handle_task_batch_completion_or_transition(confirmation_parts, cta_context, task_type, lang, message_list)
                
                st.rerun()
                return True
            else: 
                error_msg = language_manager.get_text("seo_helper_cta_yes_no_tasks_in_queue", lang, fallback="Okay. No tasks queued or lost track.")
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})
                st.session_state.awaiting_seo_helper_cta_response = False; st.session_state.seo_helper_cta_context = None; st.session_state.paused_cta_context = None
                st.rerun(); return True

        elif cta_context and task_type == "product_writer":
            tasks: List[Dict[str, Any]] = cta_context.get("tasks", [])
            current_task_index: int = cta_context.get("current_task_index", 0)

            if tasks and isinstance(tasks, list) and 0 <= current_task_index < len(tasks):
                current_task = tasks[current_task_index]
                task_title = get_task_title(current_task, task_type) # This uses product_name

                product_generated = False
                generated_product_description = None
                generation_error_message = None
                product_options_for_gen = {}

                if generate_product_description_with_api_choice is None:
                    generation_error_message = language_manager.get_text("seo_helper_product_gen_func_missing", lang, fallback="Product description generation function is not available.")
                elif not st.session_state.get("text_report"):
                    generation_error_message = language_manager.get_text("seo_helper_product_gen_missing_report", lang, fallback="Missing base report for product description generation.")
                elif not current_task.get("product_name"): # task_title is product_name
                    generation_error_message = language_manager.get_text("seo_helper_product_gen_missing_name", lang, fallback="Product name is missing for the current suggestion.")
                else:
                    logging.info(f"SEO Helper CTA: Attempting to generate product description for task: {task_title}")
                    try:
                        # Construct product_details string
                        details_parts = []
                        if current_task.get("target_audience"): details_parts.append(f"Target Audience: {current_task['target_audience']}")
                        if current_task.get("value_proposition"): details_parts.append(f"Value Proposition: {current_task['value_proposition']}")
                        if current_task.get("key_features"):
                            features = current_task['key_features']
                            details_parts.append(f"Key Features: {', '.join(features) if isinstance(features, list) else features}")
                        elif current_task.get("product_features"): # Alternative key
                            features = current_task['product_features']
                            details_parts.append(f"Key Features: {', '.join(features) if isinstance(features, list) else features}")

                        if current_task.get("seo_keywords"): details_parts.append(f"Relevant Keywords: {', '.join(current_task['seo_keywords'])}")
                        
                        product_details_str = "\n".join(details_parts)
                        if not product_details_str: # Minimal fallback if other fields are empty
                            product_details_str = f"Details about {task_title}."


                        product_options_for_gen = {
                            "product_name": task_title,
                            "product_details": product_details_str,
                            "tone": current_task.get("tone_of_voice", current_task.get("tone", "Professional")),
                            "length": current_task.get("suggested_length", current_task.get("length", "Medium")),
                        }
                        
                        spinner_text = language_manager.get_text("seo_helper_generating_product_spin", lang, task_title=task_title, fallback=f"Generating product description for '{task_title}'...")
                        with st.spinner(spinner_text):
                            generated_product_description = generate_product_description_with_api_choice(st.session_state.text_report, product_options_for_gen)
                        
                        if generated_product_description and isinstance(generated_product_description, str) and generated_product_description.strip() and not generated_product_description.lower().startswith("error:"):
                            product_generated = True
                        else:
                            generation_error_message = language_manager.get_text("seo_helper_product_gen_failed_empty", lang, task_title=task_title, fallback=f"Product description generation for '{task_title}' was empty or indicated an error: {generated_product_description}")
                    except Exception as e:
                        generation_error_message = language_manager.get_text("seo_helper_product_gen_exception", lang, task_title=task_title, error_message=str(e), fallback=f"Error generating product description for '{task_title}': {e}")

                confirmation_parts = []
                if product_generated:
                    if "products_pending_display_on_pw" not in st.session_state:
                        st.session_state.products_pending_display_on_pw = []
                    
                    st.session_state.products_pending_display_on_pw.append({
                        "name": task_title, 
                        "description": generated_product_description,
                        "options_used": product_options_for_gen
                    })
                    logging.info(f"SEO Helper: Added '{task_title}' description to products_pending_display_on_pw. List size: {len(st.session_state.products_pending_display_on_pw)}")

                    if "completed_tasks_product" not in st.session_state: 
                        st.session_state.completed_tasks_product = []
                    st.session_state.completed_tasks_product.append({
                        "name": task_title, 
                        "details": current_task, # Original task details
                        "options_used_for_generation": product_options_for_gen,
                        "content_generated_directly": True,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    st.session_state.trigger_product_suggestion_from_seo_helper = False
                    st.session_state.product_suggestion_to_trigger_details = None # Clear as it's handled

                    confirmation_parts.append(language_manager.get_text(
                        "seo_helper_cta_yes_product_generated_success", lang, task_title=task_title,
                        fallback=f"Generated product description for '{task_title}'. It will be available on the Product Writer page."
                    ))
                elif generation_error_message:
                    st.session_state.trigger_product_suggestion_from_seo_helper = True
                    st.session_state.product_suggestion_to_trigger_details = current_task
                    confirmation_parts.append(generation_error_message)
                    confirmation_parts.append(language_manager.get_text(
                        "seo_helper_cta_product_gen_error_goto_pw", lang, task_title=task_title,
                        fallback=f"Due to an error, the product description for '{task_title}' could not be generated directly. Options have been sent to Product Writer."
                    ))
                else: # Fallback (e.g. if generation was skipped due to missing pre-requisites not caught above)
                    st.session_state.trigger_product_suggestion_from_seo_helper = True
                    st.session_state.product_suggestion_to_trigger_details = current_task
                    if "completed_tasks_product" not in st.session_state: st.session_state.completed_tasks_product = []
                    st.session_state.completed_tasks_product.append({"name": task_title, "details": current_task, "timestamp": datetime.now().isoformat(), "content_generated_directly": False})
                    confirmation_parts.append(language_manager.get_text("seo_helper_cta_yes_product_prepared", lang, task_title=task_title, fallback=f"Prepared product task '{task_title}'. Use Product Writer."))

                cta_context["current_task_index"] = current_task_index + 1
                st.session_state.seo_helper_cta_context = cta_context

                if cta_context["current_task_index"] < len(tasks):
                    confirmation_parts.append(get_next_task_prompt(tasks, cta_context["current_task_index"], task_type, lang))
                    st.session_state[message_list].append({"role": "assistant", "content": "\n\n".join(filter(None, confirmation_parts))})
                else: 
                    _handle_task_batch_completion_or_transition(confirmation_parts, cta_context, task_type, lang, message_list)

                st.rerun()
                return True
            else: 
                error_msg = language_manager.get_text("seo_helper_cta_yes_no_tasks_in_queue", lang, fallback="Okay. No tasks queued or lost track.")
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})
                st.session_state.awaiting_seo_helper_cta_response = False; st.session_state.seo_helper_cta_context = None; st.session_state.paused_cta_context = None
                st.rerun(); return True
        else: 
             logging.warning(f"CTA affirmative but cta_context invalid or type not handled: {cta_context}")
             st.session_state[message_list].append({"role": "assistant", "content": language_manager.get_text("seo_helper_cta_yes_generic", lang, fallback="Okay!")})
             st.session_state.awaiting_seo_helper_cta_response = False; st.session_state.seo_helper_cta_context = None; st.session_state.paused_cta_context = None
             st.rerun(); return True

    elif is_skip:
        if cta_context and task_type in ["article_writer", "product_writer"]:
            tasks: List[Dict[str, Any]] = cta_context.get("tasks", [])
            current_task_index: int = cta_context.get("current_task_index", 0)

            if tasks and isinstance(tasks, list) and 0 <= current_task_index < len(tasks):
                skipped_task = tasks[current_task_index]
                skipped_task_title = get_task_title(skipped_task, task_type)
                logging.info(f"SEO Helper CTA 'skip': Skipping task: {skipped_task_title} (Type: {task_type})")
                
                skip_message_parts = [language_manager.get_text("seo_helper_cta_skip_task_confirmation", lang, task_title=skipped_task_title, fallback=f"Okay, skipping '{skipped_task_title}'.")]

                cta_context["current_task_index"] = current_task_index + 1
                st.session_state.seo_helper_cta_context = cta_context # Update session state

                if cta_context["current_task_index"] < len(tasks):
                    skip_message_parts.append(get_next_task_prompt(tasks, cta_context["current_task_index"], task_type, lang))
                    st.session_state[message_list].append({"role": "assistant", "content": "\n\n".join(filter(None, skip_message_parts))})
                else: # Current batch of tasks exhausted by skipping
                    _handle_task_batch_completion_or_transition(skip_message_parts, cta_context, task_type, lang, message_list)
                
                st.rerun()
                return True
            else: 
                error_msg = language_manager.get_text("seo_helper_cta_skip_no_tasks_in_queue", lang, fallback="Okay. No tasks to skip or lost track.")
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})
                logging.warning(f"CTA skip but tasks list empty or index out of bounds. Task type: {task_type}, Tasks: {tasks}, Index: {current_task_index}")
                st.session_state.awaiting_seo_helper_cta_response = False; st.session_state.seo_helper_cta_context = None; st.session_state.paused_cta_context = None
                st.rerun(); return True
        else: 
            logging.warning(f"CTA skip but cta_context is invalid or type not handled for skip: {cta_context}")
            st.session_state[message_list].append({"role": "assistant", "content": language_manager.get_text("seo_helper_cta_skip_generic", lang, fallback="Okay, noted.")})
            st.session_state.awaiting_seo_helper_cta_response = False; st.session_state.seo_helper_cta_context = None; st.session_state.paused_cta_context = None
            st.rerun(); return True

    elif is_negative: # "stop"
        response_message_text = ""
        if cta_context and task_type in ["article_writer", "product_writer"] and \
           cta_context.get("tasks") and isinstance(cta_context.get("tasks"), list) and \
           0 <= cta_context.get("current_task_index", 0) < len(cta_context["tasks"]): 
            
            st.session_state.paused_cta_context = dict(st.session_state.seo_helper_cta_context) 
            current_task_item_for_pause = st.session_state.paused_cta_context["tasks"][st.session_state.paused_cta_context["current_task_index"]]
            task_title_paused_at = get_task_title(current_task_item_for_pause, task_type)
            
            logging.info(f"CTA negative: Paused context for {task_type} with {len(st.session_state.paused_cta_context['tasks'])} tasks at index {st.session_state.paused_cta_context['current_task_index']} (task: '{task_title_paused_at}'). Secondary info (if any) is preserved in paused_cta_context.")
            response_message_text = language_manager.get_text("seo_helper_cta_no_task_paused_generic", lang, task_title=task_title_paused_at, task_type_readable=task_type.replace('_', ' '), fallback=f"Alright. Task '{task_title_paused_at}' for {task_type.replace('_', ' ')} preparation is paused. You can resume this sequence from the SEO Helper panel later.")
        else: 
            response_message_text = language_manager.get_text("seo_helper_cta_no_task_not_prepared", lang, fallback="Alright. Won't prepare the task. Let me know if you change your mind or want to try other suggestions.")
            st.session_state.paused_cta_context = None 

        st.session_state[message_list].append({"role": "assistant", "content": response_message_text})
        st.session_state.awaiting_seo_helper_cta_response = False 
        st.session_state.seo_helper_cta_context = None 
        st.rerun()
        return True

    else: # Unclear response
        current_task_title_for_prompt = "the suggestion"
        if cta_context and task_type in ["article_writer", "product_writer"]:
            tasks = cta_context.get("tasks", [])
            current_task_index = cta_context.get("current_task_index", 0)
            if tasks and 0 <= current_task_index < len(tasks):
                current_task_title_for_prompt = get_task_title(tasks[current_task_index], task_type)
        
        response_message = language_manager.get_text("seo_helper_cta_invalid_response_extended_options", lang, current_task_title=current_task_title_for_prompt, fallback=f"For '{current_task_title_for_prompt}', please say 'yes', 'skip', or 'stop'.")
        st.session_state[message_list].append({"role": "assistant", "content": response_message})
        logging.info(f"CTA unclear for task '{current_task_title_for_prompt}'. Re-prompting.")
        st.rerun()
        return True
    
    return False # Should not be reached


def create_tools(GEMINI_API_KEY: str) -> Dict[str, Tool]:
    """Create and return a dictionary of available tools."""
    
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        logging.error(f"Failed to initialize Gemini model with 'gemini-2.0-flash: {e}. Falling back to 'gemini-pro'.")
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
    * **Do NOT create full content directly (e.g. full articles, full product descriptions).** Instead, guide the user by suggesting focus keywords, relevant long-tail and potentially low-competition keywords, ideas for content structure, content length considerations, overall tone, and other necessary details for content creation.
    * Explicitly mention that after your strategic advice, they can use tools like "Article Writer / Makale Yazarı" or "Product Writer / Ürün Yazarı " to generate the actual content based on your plan. If you have just helped them generate an article or product description for a specific task (e.g. via a 'yes' to a CTA), acknowledge that this specific part is done but they can use those tools for *other* tasks or ideas.
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
    message_list: str = "messages"
):
    lang = st.session_state.get("language", "en")

    if st.session_state.get("awaiting_seo_helper_cta_response"): 
        prompt_handled_by_cta = await handle_seo_helper_cta_response(prompt, message_list, lang)
        if prompt_handled_by_cta:
            return 

    actual_mistral_api_key = os.getenv("MISTRAL_API_KEY")
    actual_gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"): st.markdown("You need to log in first to use this service.")
        st.session_state[message_list].append({"role": "assistant", "content": "You need to log in first to use this service."})
        return
    
    if re.match(r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$', prompt):
        st.session_state.awaiting_seo_helper_cta_response = False 
        st.session_state.seo_helper_cta_context = None
        st.session_state.paused_cta_context = None
        with st.chat_message("assistant"): st.markdown(f"Processing URL: {prompt}...")
        await process_url_from_main(prompt, lang) 
    else:
        if st.session_state.get("text_report") or (st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all")):
            if actual_mistral_api_key and (not actual_gemini_api_key or st.session_state.get("use_mistral", False)):
                await process_with_mistral(prompt, actual_mistral_api_key, message_list)
            elif actual_gemini_api_key:
                await process_with_gemini(prompt, actual_gemini_api_key, message_list)
            else:
                error_msg = language_manager.get_text("no_ai_api_keys_configured", lang, fallback="No AI model configured.")
                with st.chat_message("assistant"): st.markdown(error_msg)
                st.session_state[message_list].append({"role": "assistant", "content": error_msg})
        else: 
            msg_provide_url = language_manager.get_text("provide_url_or_ask_general_seo", lang, fallback="Provide a URL or ask a general SEO question if a report is loaded.")
            with st.chat_message("assistant"): st.markdown(msg_provide_url)
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
            history_candidates = actual_history
            if actual_history and actual_history[-1]["content"] == prompt and actual_history[-1]["role"] == "user":
                 history_candidates = actual_history[:-1]

            start_index = max(0, len(history_candidates) - num_history_turns)
            for message in history_candidates[start_index:]:
                history_context += f"{message['role'].capitalize()}: {message['content']}\n"
            
            username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
            
            context_data = ""
            if st.session_state.get("text_report"):
                context_data = f"SEO Report (Summary): {st.session_state.text_report}"
            elif st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"):
                llm_analysis_content = st.session_state.full_report['llm_analysis_all']
                try: context_data = f"Detailed Analysis Data (llm_analysis_all):\n{json.dumps(llm_analysis_content, indent=2, ensure_ascii=False)}"
                except Exception: context_data = f"Detailed Analysis Data (llm_analysis_all):\n{str(llm_analysis_content)}"
            else: context_data = "No SEO report or detailed analysis data is currently available."
            
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {MISTRAL_API_KEY}"}
            
            language_info = f"Please ensure your entire response is in {language_names.get(lang, 'English')}. "
            system_prompt_content = f"""You are an SEO expert assistant and content strategist. {language_info}
Your primary role is to help users develop effective SEO and content strategies based on the website analysis data provided and their specific questions. You should guide them in planning content that they can later create using tools like "Article Writer" or "Product Writer". If you have just helped them generate an article or product description for a specific task (e.g. via a 'yes' to a CTA), acknowledge that this specific part is done but they can use those tools for *other* tasks or ideas.
Key Principles for Your Responses:
1.  **Prioritize Provided Context**: Analyze 'User Information and Context' (SEO Report, conversation history, user info) for the user's query and website's SEO status.
2.  **Strategic Planning, Not Just Answers**: Aim to help users decide on strategies and plan implementation.
    * **Do NOT create full content (e.g. full articles, full product descriptions).** Guide by suggesting keywords, content structure, length, tone for content creation.
    * Mention users can use "Article Writer / Makale Yazarı" or "Product Writer / Ürün Yazarı" for actual content generation.
3.  **Leverage and Enhance Existing Insights**:
    * If 'User Information and Context' has suggestions (e.g., 'suggested_keywords_for_seo', 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS'), *integrate, build upon, refine, or offer alternatives*. Explain how suggestions apply to the current query.
4.  **Incorporate Strategic SEO Elements**:
    * **Keyword Strategy**: Suggest primary, secondary, low-competition keywords with rationale.
    * **Content Opportunities**: Identify new topics, alternative page ideas (articles, FAQs, cornerstone content).
    * **Tone and Audience Alignment**: Advise on aligning content tone with the target audience.
    * **Actionable Steps**: Provide clear, actionable steps.
5.  **Be Specific and Practical**: Offer high-priority, easy-to-implement strategies. Consider internal linking, backlinks, social media, video content.
"""
            
            user_content_for_mistral = f"""User Information:\n{username_context}
Conversation History (most recent turns for context):\n{history_context}
Context from SEO Report (prioritize this for site-specific information):\n{context_data}
Based on all the above information and my system persona (SEO expert assistant and content strategist), please answer the following user question. Focus on providing strategic advice and a plan, not generating full content (unless specifically asked to refine a previous generation or for very short snippets). Guide me on how I can use tools like "Article Writer" or "Product Writer" with your strategy.
User Question: {prompt}"""
            data = {
                "model": "mistral-large-latest", 
                "messages": [{"role": "system", "content": system_prompt_content}, {"role": "user", "content": user_content_for_mistral}],
                "temperature": 0.7, "max_tokens": 2000
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('choices') and response_json['choices'][0].get('message'):
                    st.session_state[message_list].append({"role": "assistant", "content": response_json['choices'][0]['message']['content']})
                else: st.session_state[message_list].append({"role": "assistant", "content": "Mistral API response error."})
            else: st.session_state[message_list].append({"role": "assistant", "content": f"Mistral API error: {response.status_code}."})
        except Exception as e:
            st.session_state[message_list].append({"role": "assistant", "content": "Error processing request."})

async def process_with_gemini(prompt: str, GEMINI_API_KEY: str, message_list: str = "messages"):
    lang = st.session_state.get("language", "en")
    tools = create_tools(GEMINI_API_KEY) 
    spinner_text = language_manager.get_text("processing_request", lang) if hasattr(language_manager, "get_text") else "Processing your request..."

    with st.spinner(spinner_text):
        try:
            history_context = ""
            num_history_turns = 5 
            messages_to_process = st.session_state.get(message_list, [])
            actual_history = [m for m in messages_to_process if m.get('role') != 'system']
            history_candidates = actual_history
            if actual_history and actual_history[-1]["content"] == prompt and actual_history[-1]["role"] == "user":
                 history_candidates = actual_history[:-1]
            
            start_index = max(0, len(history_candidates) - num_history_turns)
            for message in history_candidates[start_index:]:
                history_context += f"{message['role'].capitalize()}: {message['content']}\n"

            context_data = ""
            if st.session_state.get("text_report"): context_data = f"SEO Report (Summary): {st.session_state.text_report}"
            if st.session_state.get("full_report") and st.session_state.full_report.get("llm_analysis_all"): 
                llm_analysis_content = st.session_state.full_report['llm_analysis_all']
                try: context_data += f"\n\nDetailed Analysis Data (llm_analysis_all): {json.dumps(llm_analysis_content, indent=2, ensure_ascii=False)}"
                except Exception: context_data += f"\n\nDetailed Analysis Data (llm_analysis_all): {str(llm_analysis_content)}"
            if not context_data: context_data = "No SEO report or detailed analysis data is currently available."

            context_for_gemini = f"""Username: {st.session_state.username if "username" in st.session_state and st.session_state.username else "Anonymous"}
{context_data}
Conversation History (for reference, prioritize the SEO Report/Detailed Analysis for site-specific questions):
{history_context}"""
            
            response = await tools["process_question"].function(prompt, context_for_gemini)
            st.session_state[message_list].append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state[message_list].append({"role": "assistant", "content": "Error processing request with Gemini."})
