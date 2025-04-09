#/buttons/generate_article.py
import google.generativeai as genai
import re
import random
import time
import logging
import os
import streamlit as st # Import streamlit to access session state
from utils.language_support import language_manager

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash-latest') # Keep your chosen model

def select_focus_keyword(text_report: str) -> str:
    """Selects a focus keyword from the text report."""
    try:
        # Attempt to parse "Top Keywords" section
        match = re.search(r"Top Keywords by Frequency:(.*?)(\n|\Z)", text_report, re.DOTALL)
        if match:
            keywords_section = match.group(1)
            keywords = re.findall(r"- (.*?):", keywords_section)
            if keywords:
                return random.choice(keywords)

        # Attempt to extract product categories
        match = re.search(r'"categories":\s*\{(.*?)\}', text_report, re.DOTALL)
        if match:
            categories_section = match.group(1)
            categories = re.findall(r'"(.*?)"', categories_section)
            if categories:
                return random.choice(categories)

        # Fallback to general keyword extraction
        keywords = re.findall(r'\b[a-zA-Z]{3,}\b', text_report)
        if keywords:
            filtered_keywords = [
                word for word in keywords
                if word.lower() not in ["the", "and", "for", "with", "this", "that"]
            ]
            if filtered_keywords:
                return random.choice(filtered_keywords)

        return "general information about the website"
    except Exception as e:
        logging.error(f"Error in select_focus_keyword: {e}")
        return "general information about the website"

# Fix for the f-string backslash issue in generate_article.py
# Replace the problematic part in your code with this approach:

def generate_article(text_report: str, url: str, article_options: dict = None) -> str:
    """Generates an article using Gemini based on the text report and URL, supporting multiple languages."""
    try:
        # --- Get Language ---
        lang = st.session_state.get("language", "en")

        # --- Prepare Variables ---
        website_name = url.replace("https://", "").replace("http://", "").split("/")[0]
        focus_keyword = article_options.get("focus_keyword", "") if article_options and article_options.get("focus_keyword") else select_focus_keyword(text_report)
        variation_seed = time.time()
        
        # Default options if not provided
        if article_options is None:
            article_options = {
                "content_length": "Medium",
                "tone": "Professional",
                "keywords": "",
                "custom_title": "",
                "focus_keyword": ""
            }
        
        # --- Set token limit based on content length ---
        token_limits = {
            "Short": 1024,
            "Medium": 2048,
            "Long": 3072,
            "Very Long": 4096
        }
        max_tokens = token_limits.get(article_options["content_length"], 2048)
        
        # --- Process custom keywords if provided ---
        custom_keywords = ""
        if article_options["keywords"]:
            custom_keywords = f"\n\n**Additional Required Keywords:** {article_options['keywords']}"
        
        # --- Process custom title if provided ---
        title_instruction = ""
        if article_options["custom_title"]:
            title_instruction = f"\n\n**Required Title:** Use this exact title for the article: \"{article_options['custom_title']}\""
        
        # --- Set tone instruction ---
        tone_instruction = f"\n\n**Tone:** Write the article in a {article_options['tone'].lower()} tone."
        
        prompt_variants = [
            f"Write an engaging article about {website_name} focusing on {focus_keyword}...",
            f"Craft an informative piece on {website_name} centered around {focus_keyword}...",
            f"Develop a reader-friendly article about {website_name} with the topic being {focus_keyword}..."
        ]
        prompt_prefix = random.choice(prompt_variants)

        # --- Gemini Language Instruction ---
        language_instruction = f"Respond in Turkish. " if lang == "tr" else "" # Add more languages as needed

        # --- Fix: prepare the title instruction outside the f-string ---
        # This avoids using backslashes in f-string expressions
        if article_options['custom_title']:
            title_part = "Use the provided title exactly as specified."
        else:
            # Create the part with quotes separately, avoiding backslashes in f-string expressions
            title_part = f'Create a creative and compelling title that accurately reflects the article\'s content, emphasizing **"{focus_keyword}"**.'

        # --- Construct the Full Prompt ---
        prompt = f"""{language_instruction}{prompt_prefix} based on the SEO analysis below.

**Instructions for Article Generation:**

1. **Focus Keyword:** The article must be focused on the keyword or topic: **"{focus_keyword}"**. Use this as the central theme and build the article's content around it. Prioritize incorporating information and insights from the SEO report that are relevant to **"{focus_keyword}"**.{custom_keywords}

2. **Engaging and Natural Content:** Write a natural, engaging article about **"{focus_keyword}"** for {website_name}, seamlessly incorporating insights from the SEO analysis. The article should be informative and valuable to the target audience interested in **"{focus_keyword}"**.{title_instruction}

3. **Tone and Style:** Maintain a {article_options['tone'].lower()}, yet engaging and reader-friendly tone.{tone_instruction}

4. **Avoid SEO Jargon:** Do not mention SEO reports, SEO suggestions, keyword analysis, or generic SEO advice directly in the article's body.

5. **Content Length:** Generate an article with {article_options['content_length'].lower()} length. {"Keep it concise with 2-3 paragraphs." if article_options['content_length'] == "Short" else ""}{"Provide a comprehensive article with multiple sections." if article_options['content_length'] in ["Long", "Very Long"] else ""}

6. **Product/Topic Focus:** Avoid discussing the company's overall growth or generic advice. Stay laser-focused on **"{focus_keyword}"** and its relevance to {website_name}, as derived from the SEO report.

7. **Keyword Selection and Listing:**
    * **Identify Key Keywords:** From the SEO report, identify the most relevant keywords and concepts related to **"{focus_keyword}"**.
    * **Incorporate Keywords:** Naturally incorporate these identified keywords throughout the article where contextually appropriate, especially related to **"{focus_keyword}"**.
    * **List Used Keywords:** At the end of the article, under the heading "Keywords:", provide a bulleted list of the *primary keywords you intentionally used* in the article, including **"{focus_keyword}"**.
    * **Suggest New Keywords (Optional):** If possible, also suggest 2-3 *additional, potentially new* keywords that could be relevant to **"{focus_keyword}"** for future content or SEO efforts. List these under "Suggested Keywords:" if applicable. If not applicable or you cannot think of new keywords, skip this "Suggested Keywords:" section.

8. **Compelling Title:** {title_part}

**SEO Report for {website_name}:**

{text_report}

**--- Timestamp for Variation: {variation_seed} ---**

"""
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.9,
                "top_p": 0.8,
                "max_output_tokens": max_tokens,
            }
        )
        return response.text
    except Exception as e:
        logging.error(f"Error generating article: {e}")
        lang = st.session_state.get("language", "en")
        error_message = "Could not generate article due to an error."
        if lang == "tr":
            error_message = "Bir hata nedeniyle makale oluşturulamadı."
        return f"{error_message} ({str(e)})"
