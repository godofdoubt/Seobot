
#/buttons/generate_article.py
import google.generativeai as genai
import re
import random
import time
import logging
import os
import streamlit as st # Import streamlit to access session state
import json # Import json
# from utils.language_support import language_manager # Assuming this is available if needed

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash') # Keep your chosen model

def select_focus_keyword_from_structured_data(page_data: dict, main_page_data: dict = None) -> str:
    """
    Selects a focus keyword from structured page data.
    Priority is given to keywords from the specific page_data if available.
    """
    keywords_to_consider = []

    # From specific page data (e.g., target_page_analysis)
    if page_data:
        keywords_to_consider.extend(page_data.get("keywords", []))
        keywords_to_consider.extend(page_data.get("suggested_keywords_for_seo", []))
        # Consider adding other relevant fields like 'h1_tags', 'meta_title_extracted' if they might contain good keywords
        # Ensure topic_categories are strings
        categories = page_data.get("topic_categories", [])
        if isinstance(categories, list):
            keywords_to_consider.extend([str(cat) for cat in categories if isinstance(cat, (str, int, float))])
        elif isinstance(categories, str):
            keywords_to_consider.append(categories)


    # From main page data (less priority if specific page data exists and yielded keywords)
    if not keywords_to_consider and main_page_data:
        keywords_to_consider.extend(main_page_data.get("keywords", []))
        keywords_to_consider.extend(main_page_data.get("suggested_keywords_for_seo", []))
        categories = main_page_data.get("topic_categories", [])
        if isinstance(categories, list):
            keywords_to_consider.extend([str(cat) for cat in categories if isinstance(cat, (str, int, float))])
        elif isinstance(categories, str):
            keywords_to_consider.append(categories)

    if keywords_to_consider:
        # Filter out None, empty strings, and very common words. Ensure keywords are strings.
        filtered_keywords = [
            str(kw).strip() for kw in keywords_to_consider
            if kw and isinstance(kw, (str, int, float)) # Ensure kw is not None and can be stringified
        ]
        filtered_keywords = [
            kw for kw in filtered_keywords
            if kw and kw.lower() not in ["the", "and", "for", "with", "this", "that", "is", "are", "of", "to", "in"] and len(kw.split()) < 5
        ]
        if filtered_keywords:
            return random.choice(filtered_keywords)

    return "information about the website" # Fallback

def generate_article(
    analysis_data_json: str, # Expects a JSON string of the relevant llm_analysis_all parts
    site_url: str, # The main URL of the site for website_name
    article_options: dict = None
) -> str:
    """
    Generates an article using Gemini based on structured analysis data (from llm_analysis_all)
    and article options.
    """
    try:
        lang = st.session_state.get("language", "en")
        website_name = site_url.replace("https://", "").replace("http://", "").split("/")[0]

        opts = {}
        if article_options:
            opts.update(article_options)

        # --- Parse the incoming analysis_data_json ---
        try:
            # The analysis_data_json is already a string, it will be passed directly to the LLM.
            # We parse it here primarily for selecting the focus_keyword if not provided.
            parsed_analysis_data = json.loads(analysis_data_json)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding analysis_data_json for keyword selection: {e}")
            # If parsing fails, we can't use it for keyword selection, but the raw string can still be sent to LLM.
            parsed_analysis_data = {}


        target_page_analysis = parsed_analysis_data.get("target_page_analysis")
        main_page_analysis = parsed_analysis_data.get("main_page_analysis")

        # --- Determine Focus Keyword ---
        focus_keyword = opts.get("focus_keyword")
        if not focus_keyword:
            if target_page_analysis:
                focus_keyword = select_focus_keyword_from_structured_data(target_page_analysis, main_page_analysis)
            elif main_page_analysis:
                focus_keyword = select_focus_keyword_from_structured_data(main_page_analysis)
            else:
                # Fallback if no analysis data could be parsed for keyword selection
                # or if analysis data is empty.
                # The LLM will still receive the raw analysis_data_json string.
                generic_keywords_match = re.search(r'"keywords":\s*\["(.*?)"', analysis_data_json)
                if generic_keywords_match and generic_keywords_match.group(1):
                    focus_keyword = generic_keywords_match.group(1)
                else:
                    focus_keyword = "key aspects of " + website_name
        
        content_length = opts.get("content_length", "Medium")
        tone = opts.get("article_tone") or opts.get("tone", "Professional")
        keywords_data = opts.get("additional_keywords") or opts.get("keywords", [])
        custom_title = opts.get("suggested_title") or opts.get("custom_title", "")
        variation_seed = time.time()

        token_limits = {"Short": 1024, "Medium": 2048, "Long": 3072, "Very Long": 4096}
        max_tokens = token_limits.get(content_length, 2048)

        custom_keywords_prompt_part = ""
        if keywords_data:
            processed_keywords = []
            if isinstance(keywords_data, list):
                processed_keywords = [str(kw).strip() for kw in keywords_data if kw and str(kw).strip()]
            elif isinstance(keywords_data, str) and keywords_data.strip():
                processed_keywords = [kw.strip() for kw in keywords_data.split(',') if kw.strip()]
            
            if processed_keywords:
                keywords_str = ", ".join(processed_keywords)
                custom_keywords_prompt_part = f"\n\n**Additional Required Keywords:** {keywords_str}"


        title_instruction_prompt_part = ""
        if custom_title:
            title_instruction_prompt_part = f"\n\n**Required Title:** Use this exact title for the article: \"{custom_title}\""

        tone_instruction_prompt_part = f"\n\n**Tone:** Write the article in a {tone.lower()} tone."

        notes_section_parts = []
        if opts.get("target_page_url"):
            notes_section_parts.append(f"- **Article Target URL:** {opts['target_page_url']}")
        if opts.get("content_gap_addressed"):
            notes_section_parts.append(f"- **Content Gap Addressed:** {opts['content_gap_addressed']}")
        if opts.get("target_audience"):
            notes_section_parts.append(f"- **Target Audience for Article:** {opts['target_audience']}")
        if opts.get("content_outline"):
            outline_items = opts['content_outline']
            outline_str = ""
            if isinstance(outline_items, list):
                processed_outline_items = [str(item).strip() for item in outline_items if item and str(item).strip()]
                if processed_outline_items: outline_str = "\n  - " + "\n  - ".join(processed_outline_items)
            elif isinstance(outline_items, str) and outline_items.strip(): outline_str = "\n  - " + outline_items.strip() # Ensure it's also bulleted if a string
            if outline_str.strip(): notes_section_parts.append(f"- **Content Outline:** {outline_str}")
        if opts.get("internal_linking_opportunities"):
            linking_items = opts['internal_linking_opportunities']
            linking_str = ""
            if isinstance(linking_items, list):
                processed_linking_items = [str(item).strip() for item in linking_items if item and str(item).strip()]
                if processed_linking_items: linking_str = "\n  - " + "\n  - ".join(processed_linking_items)
            elif isinstance(linking_items, str) and linking_items.strip(): linking_str = "\n  - " + linking_items.strip() # Ensure it's also bulleted
            if linking_str.strip(): notes_section_parts.append(f"- **Internal Linking Opportunities:** {linking_str}")

        notes_prompt_section = ""
        if notes_section_parts:
            notes_prompt_section = "\n\n**Key Directives for Article Generation (from SEO Task):**\n" + "\n".join(notes_section_parts)

        prompt_variants = [
            f"Write an engaging article about {website_name} focusing on \"{focus_keyword}\"...",
            f"Craft an informative piece on {website_name} centered around \"{focus_keyword}\"...",
        ]
        prompt_prefix = random.choice(prompt_variants)
        language_instruction = f"Respond in Turkish. " if lang == "tr" else ""

        title_generation_instruction_part = f'Create a creative and compelling title that accurately reflects the article\'s content, emphasizing **"{focus_keyword}"**.'
        if custom_title:
            title_generation_instruction_part = "Use the provided title exactly as specified."

        prompt = f"""{language_instruction}{prompt_prefix} using the provided page analysis data.

**Website Name:** {website_name}

**Core Instructions for Article Generation:**

1.  **Primary Focus:** The article's central theme MUST be **"{focus_keyword}"**. All content should revolve around and support this topic.
    {custom_keywords_prompt_part}

2.  **Source Material:** Your primary source of information is the "Page Analysis Data" (in JSON format) provided below. Extract relevant details, summaries, keywords, target audience information, and other contextual data from this JSON to build your article.
    *   If "target_page_analysis" is present within the JSON, prioritize its content (like `content_summary`, `keywords`, `h1_tags`, `meta_description_extracted`, `topic_categories`, `target_audience_identified`) for the article's main subject.
    *   Use "main_page_analysis" for general site context (e.g., overall brand voice, primary services/products if relevant to the focus keyword, but avoid just listing header/footer elements unless they contribute to the article's theme).

3.  **Content and Tone:**
    *   Write naturally and engagingly for an audience interested in **"{focus_keyword}"** as it relates to {website_name}.
    *   Maintain a {tone.lower()} tone. {title_instruction_prompt_part}
    * {notes_prompt_section} # These are specific instructions from the SEO task

4.  **Avoid Meta-Commentary:** Do NOT mention "Page Analysis Data," "SEO report," "JSON data," or directly quote field names from the analysis (e.g., "the `content_summary` field says..."). Integrate the information seamlessly and naturally into the article.

5.  **Content Length:** Aim for a {content_length.lower()} article. {"Concise: 2-3 paragraphs." if content_length == "Short" else ""}{"Comprehensive: multiple sections and paragraphs." if content_length in ["Long", "Very Long"] else "A moderately detailed article with several paragraphs."}

6.  **Adherence to Directives:** Carefully follow all "Key Directives for Article Generation," especially any provided 'Content Outline', 'Target Audience for Article', and 'Internal Linking Opportunities'. These directives are crucial for tailoring the article.

7.  **Keyword Usage & Listing:**
    *   From the "Page Analysis Data" (primarily `keywords`, `suggested_keywords_for_seo` within `target_page_analysis` or `main_page_analysis`), identify the most relevant keywords related to **"{focus_keyword}"**.
    *   Naturally incorporate these identified keywords and any 'Additional Required Keywords' throughout the article where contextually appropriate.
    *   At the very end of the article, under a specific heading "Notes:" Summurise your notes. and  "Keywords Used:", provide a bulleted list of the *primary keywords you intentionally used* in the article's body, including **"{focus_keyword}"**.

8.  **Title:** {title_generation_instruction_part}

**Page Analysis Data (JSON format):**
```json
{analysis_data_json}
```

--- Timestamp for Variation: {variation_seed} ---
"""
        # For debugging the prompt:
        # st.text_area("Generated Prompt:", prompt, height=500)

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.9, "top_p": 0.8, "max_output_tokens": max_tokens}
        )
        return response.text

    except Exception as e:
        logging.error(f"Error generating article: {e}", exc_info=True)
        lang = st.session_state.get("language", "en")
        error_message = "Could not generate article due to an error."
        if lang == "tr": error_message = "Bir hata nedeniyle makale oluşturulamadı."
        return f"{error_message} (Error: {str(e)})"

