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
    # Assuming 'gemini-2.0-flash' is a valid model identifier you intend to use.
    
    model = genai.GenerativeModel('gemini-2.0-flash') # Using a common valid model

    async def process_question(prompt: str, context: str) -> str:
        """
        Process a question using Gemini with language support, leveraging the detailed SEO report in context.
        The 'context' parameter is expected to contain username, the full SEO report, conversation history, and focus.
        """
        try:
            language_instruction = f"Please respond in {language_names.get(st.session_state.language, 'English')}." if st.session_state.language != "en" else ""

            seo_report_guidance = """
You have access to a comprehensive SEO Analysis Report within the 'Context'. This report is structured as follows:
- 'Main Page Analysis': Contains Content Summary, Primary Keywords, Suggested SEO Keywords, Contact Information & Key Mentions, and Footer Elements for the main analyzed site.
- 'Subpage Analysis': Provides detailed analysis for multiple subpages, including their purpose, content overview, extracted keywords, and specific SEO keyword suggestions.
- 'Site-Wide Subpage Keyword Analysis': Lists the most common keywords found across all analyzed subpages.
- 'Site-Wide Subpage SEO Suggestions': Lists the most frequently suggested SEO keywords for subpages.
- 'General Recommendations': Offers overall SEO advice for the site.
- '## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS': This section provides deeper, actionable advice and includes sub-sections (often marked with '###') such as:
    - 'Strategic Recommendations': High-level strategies for keyword targeting, content gaps, technical SEO, and user experience.
    - 'SEO & Content Optimization': Specific recommendations for keyword strategy, content gaps, meta descriptions, internal linking, schema markup, and image optimization.
    - 'Content Strategy Insights': Insights into storytelling, visual content, audience targeting, and thematic focus for content.
- '## Performance Monitoring & Next Steps': Guidance on implementing recommendations and tracking success.

When answering, leverage ALL relevant sections of the SEO report to provide specific and actionable advice related to product descriptions, product writing, and product page SEO.
For example:
- If the question relates to a specific product or subpage, consult the 'Subpage Analysis' section.
- For broader strategy, keyword ideas, or general product content advice, refer to 'Main Page Analysis', 'Site-Wide' sections, 'General Recommendations', and especially the detailed advice within '## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS' (like 'Content Strategy Insights' for content ideas, 'SEO & Content Optimization' for specific techniques, and 'Strategic Recommendations' for overall direction) and '## Performance Monitoring & Next Steps' for implementation context.
"""

            full_prompt = f"""{language_instruction}
{seo_report_guidance}

Context:
{context}

Question: {prompt}

Please provide a helpful and detailed response focused on product descriptions and product writing.
Think about how to use the detailed website analysis from the SEO Report (especially content summaries, keywords, SEO suggestions, and the AI-Powered Strategic Insights) to create effective product copy or provide strategic advice.
"""
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"

    # Import only the necessary tool for product writing
    from buttons.generate_product_description import generate_product_description

    tools = {
        "process_question": Tool(
            description="Process a question using the chat context and comprehensive SEO report with focus on product writing",
            function=process_question,
            parameters=["prompt", "context"], # 'context' here is the string built in process_with_gemini
            validation=True,
            prompt="Processing your product-related question..."
        ),
        "generate_product_description": Tool(
            description="Generate a product description based on the SEO report for a given URL (typically the main site URL or a specific product page URL found in the report).",
            function=lambda text_report, url: generate_product_description(text_report, url, st.session_state.get("product_options", None)),
            parameters=["text_report", "url"], # Parameters for Gemini function calling (if used)
            validation=True,
            prompt="Generating product description..."
        )
    }

    return tools

async def process_with_mistral(prompt: str, MISTRAL_API_KEY: str):
    """Process the chat input using Mistral API with focus on product writing, language support, and the new SEO report structure."""
    lang = st.session_state.get("language", "en")
    with st.spinner(language_manager.get_text("generating_response", lang) + " (Product Writer)..."):
        with st.chat_message("assistant"):
            try:
                history_context = ""
                num_history_turns = 5
                messages = st.session_state.messages
                start_index = max(0, len(messages) - num_history_turns)
                for message in messages[start_index:]:
                    history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                username_context = f"Username: {st.session_state.username}\n" if "username" in st.session_state and st.session_state.username else ""
                language_info = f"Please respond in {language_names.get(lang, 'English')}. " if lang != "en" else ""
                
                current_analyzed_site_url_hint = f"(e.g., for the site {st.session_state.get('current_url', 'the analyzed website')})"


                if any(keyword in prompt.lower() for keyword in ["product", "description", "feature", "generate", "create", "write"]):
                    system_content = f"""You are an expert product copywriter and SEO specialist. {language_info}
Your task is to generate a well-structured, SEO-optimized product description.
You will be provided with a comprehensive SEO Analysis Report. This report contains:
- 'Main Page Analysis': Includes Content Summary, Primary Keywords, Suggested SEO Keywords, Contact Information & Key Mentions, and Footer Elements for the main site {current_analyzed_site_url_hint}.
- 'Subpage Analysis': Provides details for multiple subpages, including their purpose, content overview, extracted keywords, and specific SEO keyword suggestions. If the user's prompt or conversation history implies a specific product/subpage, focus on its analysis.
- 'Site-Wide Subpage Keyword Analysis': Lists common keywords across subpages.
- 'Site-Wide Subpage SEO Suggestions': Lists frequently suggested SEO keywords.
- 'General Recommendations': Overall SEO advice for the site.
- '## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS': This section offers deeper insights including sub-sections (often marked with '###') such as:
    - 'Strategic Recommendations': High-level advice on keyword targeting, content gaps, technical SEO, and UX.
    - 'SEO & Content Optimization': Specific tactics for keyword strategy, filling content gaps, meta descriptions, internal linking, schema, and image optimization.
    - 'Content Strategy Insights': Ideas for storytelling, visual content, audience targeting, and thematic content focus.
- '## Performance Monitoring & Next Steps': Guidance on how to implement recommendations and track success.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.text_report}

Instructions for product description generation:
1. Identify the most relevant product or page to focus on. Use the user's prompt, conversation history, or assume the main page {current_analyzed_site_url_hint} if no specific product is indicated.
2. Consult the 'Main Page Analysis' or the specific 'Subpage Analysis' in the SEO Report for content ideas, keywords (Primary, Suggested, extracted), and SEO suggestions relevant to that product/page.
3. Utilize insights from '## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS', especially 'Content Strategy Insights' (for storytelling, visuals, audience targeting) and 'SEO & Content Optimization' (for keyword usage, meta description ideas, etc.) to enhance the product description. The '## Performance Monitoring & Next Steps' section might also provide context on strategic priorities.
4. Create a compelling product headline that includes relevant keywords from the report.
5. Structure the description with clear features and benefits, drawing inspiration from the content summaries, keyword analysis, and strategic insights in the report.
6. Aim for approximately 300-500 words of high-quality content.
7. Include specifications and technical details where appropriate (if inferable from the report or general product type).
8. Optimize for SEO using primary and suggested keywords from the report (see 'Main Page Analysis', 'Subpage Analysis', 'Site-Wide' sections, and the 'SEO & Content Optimization' section of 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS'), while maintaining persuasive sales copy.
9. Use a professional but engaging tone, informed by 'Content Strategy Insights' if applicable.
10. Include a strong call-to-action.
"""
                else:
                    system_content = f"""You are an expert in product copywriting and SEO strategy. {language_info}
Your goal is to provide helpful responses about product descriptions, feature highlights, and SEO optimization for product pages.
You have access to a comprehensive SEO Analysis Report. This report contains:
- 'Main Page Analysis': Includes Content Summary, Primary Keywords, Suggested SEO Keywords, Contact Information & Key Mentions, and Footer Elements for the main site {current_analyzed_site_url_hint}.
- 'Subpage Analysis': Provides details for multiple subpages, including their purpose, content overview, extracted keywords, and specific SEO keyword suggestions.
- 'Site-Wide Subpage Keyword Analysis': Lists the most common keywords found across all analyzed subpages.
- 'Site-Wide Subpage SEO Suggestions': Lists the most frequently suggested SEO keywords for subpages.
- 'General Recommendations': Provides overall SEO advice for the site.
- '## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS': This section offers deeper, actionable advice and includes sub-sections (often marked with '###') such as:
    - 'Strategic Recommendations': High-level strategies for keyword targeting, content gaps, technical SEO, and user experience.
    - 'SEO & Content Optimization': Specific recommendations for keyword strategy, content gaps, meta descriptions, internal linking, schema markup, and image optimization.
    - 'Content Strategy Insights': Insights into storytelling, visual content, audience targeting, and thematic focus for content.
- '## Performance Monitoring & Next Steps': Guidance on implementing recommendations and tracking success.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{st.session_state.text_report}

Please provide specific, actionable advice related to product content creation and copywriting.
Base your advice on the insights from the SEO Report. For example:
- When discussing keywords, refer to 'Primary Keywords', 'Suggested SEO Keywords' (from Main Page or relevant Subpage Analysis), 'Site-Wide Subpage Keyword Analysis', 'Site-Wide Subpage SEO Suggestions', and the 'Keyword Strategy' section within 'SEO & Content Optimization' (under 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS').
- If discussing content strategy for a specific product or page, refer to its corresponding 'Subpage Analysis' section and relevant parts of 'Content Strategy Insights' or 'Content Gaps' under 'SEO & Content Optimization' (within 'AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS').
- For general site-wide product content strategy or overarching SEO improvements, consider the 'Main Page Analysis', 'Site-Wide' sections, 'General Recommendations', and extensively draw from '## AI-POWERED STRATEGIC INSIGHTS & RECOMMENDATIONS' (particularly 'Strategic Recommendations', 'SEO & Content Optimization', and 'Content Strategy Insights') and '## Performance Monitoring & Next Steps' for implementation and prioritization context.
"""

                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {MISTRAL_API_KEY}"
                }
                data = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": prompt}
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
    """Process the chat input using Gemini with tools, focus on product descriptions, and language support."""
    lang = st.session_state.get("language", "en")
    tools = create_tools(GEMINI_API_KEY)

    with st.spinner(language_manager.get_text("processing_question", lang) + "..."):
        try:
            if "used_tools" not in st.session_state:
                st.session_state.used_tools = set()

            tool_used = False

            if prompt.lower() == "write random product description" or prompt.lower() == "rastgele ürün açıklaması oluştur":
                with st.chat_message("assistant"):
                    try:
                        current_analyzed_url = st.session_state.get("current_url")
                        if not current_analyzed_url and st.session_state.get("text_report"):
                            # Fallback: try to extract from the report if current_url is missing
                            report_url_match = re.search(r"## Main Page Analysis:\s*(https?://[^\s]+)", st.session_state.text_report)
                            if report_url_match:
                                current_analyzed_url = report_url_match.group(1).strip()
                        
                        if not current_analyzed_url:
                            # Ensure this language key exists in your language_manager
                            error_message = language_manager.get_text("error_main_url_not_found_for_description", lang) + \
                                            " " + language_manager.get_text("ensure_website_analyzed", lang) # ensure_website_analyzed might be a new key
                            st.error(error_message)
                            st.session_state.messages.append({"role": "assistant", "content": error_message})
                        else:
                            response = tools["generate_product_description"].function(
                                st.session_state.text_report,
                                current_analyzed_url # Pass the URL
                            )
                            st.markdown(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            tool_used = True
                    except Exception as product_desc_error:
                        error_message = language_manager.get_text("could_not_generate_description", lang) + f": {product_desc_error}"
                        st.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
            
            if not tool_used:
                with st.chat_message("assistant"):
                    history_context = ""
                    num_history_turns = 5 # Keep this consistent with Mistral if desired
                    messages = st.session_state.get("messages", []) # Ensure messages exists
                    start_index = max(0, len(messages) - num_history_turns)
                    for message in messages[start_index:]:
                        history_context += f"{message['role'].capitalize()}: {message['content']}\n"

                    # Construct the comprehensive context for the process_question tool
                    context_for_tool = f"""
Username: {st.session_state.username if "username" in st.session_state and st.session_state.username else "Anonymous"}
SEO Report:
{st.session_state.text_report}

Conversation History:
{history_context}
Focus: Product descriptions and product content strategy using the provided SEO report.
"""
                    response = await tools["process_question"].function(prompt, context_for_tool)
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
    message_list: str = "messages", # This parameter seems unused, st.session_state.messages is used directly
):
    """Processes chat input for the Product Writer page with language support."""
    lang = st.session_state.get("language", "en")

    if not st.session_state.get("authenticated", False):
        with st.chat_message("assistant"):
            st.markdown(language_manager.get_text("login_required", lang))
            return

    if re.match(r'^(https?://)?[\w.-]+\.[a-z]{2,}$', prompt) and analyze_website and load_saved_report and display_report_and_services:
        normalized_url = normalize_url(prompt)
        st.session_state.current_url = normalized_url # Store the current URL for other functions
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
        if not st.session_state.get("text_report"): # Check if text_report exists in session_state
            with st.chat_message("assistant"):
                st.markdown(language_manager.get_text("analyze_website_first_product", lang))
                st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text("analyze_website_first_product", lang)})
            return

        # Add prompt to messages BEFORE processing, so history is up-to-date for the LLM call
        # st.session_state.messages.append({"role": "user", "content": prompt}) # This is typically handled by the calling page

        if MISTRAL_API_KEY and (not GEMINI_API_KEY or st.session_state.get("use_mistral", False)):
            await process_with_mistral(prompt, MISTRAL_API_KEY)
        elif GEMINI_API_KEY:
            await process_with_gemini(prompt, GEMINI_API_KEY)
        else:
            with st.chat_message("assistant"):
                st.markdown(language_manager.get_text("no_ai_model_configured", lang))
                st.session_state.messages.append({"role": "assistant", "content": language_manager.get_text("no_ai_model_configured", lang)})