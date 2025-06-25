#/buttons/generate_article_prompts.py

def get_article_generation_prompts(
    language_instruction: str,
    prompt_prefix: str,
    website_name: str,
    focus_keyword: str,
    custom_keywords_prompt_part: str,
    tone_instruction_prompt_part: str,
    content_tone_title_instruction: str, # Corresponds to original title_instruction_prompt_part
    notes_prompt_section: str,
    content_length: str,
    final_title_directive: str, # Corresponds to original title_generation_instruction_part
    analysis_data_json: str,
    variation_seed: float
) -> str:
    """
    Generates the full prompt for article creation based on provided components.
    """
    content_length_description = ""
    if content_length == "Short":
        content_length_description = "Concise: 2-3 paragraphs."
    elif content_length in ["Long", "Very Long"]:
        content_length_description = "Comprehensive: multiple sections and paragraphs."
    else:
        content_length_description = "A moderately detailed article with several paragraphs."

    # Note: The prompt structure and wording are preserved from the original version.
    prompt = f"""You are an expert content writer. Generate a well-structured, SEO-optimized article based on the provided website analysis. Always find posible suddle emotional hooks for entry of the article and end with CTA (Call To Action). Be cunning about this act like its a honest conversitaion if general tone allows it Never put the result as the Result:.
    {language_instruction}{prompt_prefix} using the provided page analysis data.

**Website Name:** {website_name}

**Core Instructions for Article Generation:**

1.  **Primary Focus:** The article's central theme MUST be **"{focus_keyword}"**. All content should revolve around and support this topic.
    {custom_keywords_prompt_part}

2.  **Source Material:** Your primary source of information is the "Page Analysis Data" (in JSON format) provided below. Extract relevant details, summaries, keywords, target audience information, and other contextual data from this JSON to build your article.
    *   If "target_page_analysis" is present within the JSON, prioritize its content (like `content_summary`, `keywords`, `suggested_keywords_for_seo`, 'content_summary', `topic_categories`, `target_audience`) for the article's main subject.
    *   Use "main_page_analysis" for general site context (e.g., overall brand voice, primary services/products if relevant to the focus keyword, but avoid just listing header/footer elements unless they contribute to the article's theme).

3.  **Content and Tone:**
    *   Write naturally and engagingly for an audience interested in **"{focus_keyword}"** as it relates to {website_name}.
    {tone_instruction_prompt_part}
    {content_tone_title_instruction}
    {notes_prompt_section}

4.  **Avoid Meta-Commentary:** Do NOT mention "Page Analysis Data," "SEO report," "JSON data," or directly quote field names from the analysis (e.g., "the `content_summary` field says..."). Integrate the information seamlessly and naturally into the article.

5.  **Content Length:** Aim for a {content_length.lower()} article. {content_length_description}

6.  **Adherence to Directives:** Carefully follow all "Key Directives for Article Generation," especially any provided 'Content Outline', 'Target Audience for Article', and 'Internal Linking Opportunities'. These directives are crucial for tailoring the article.

7.  **Keyword Usage & Listing:**
    *   From the "Page Analysis Data" (primarily `keywords`, `suggested_keywords_for_seo` within `target_page_analysis` or `main_page_analysis`), identify the most relevant keywords related to **"{focus_keyword}"**.
    *   Naturally incorporate these identified keywords and any 'Additional Required Keywords' throughout the article where contextually appropriate.
    *   At the very end of the article, under a specific heading "Notes:" Summurise your notes. and  "Keywords Used:", provide a bulleted list of the *primary keywords you intentionally used* in the article's body, including **"{focus_keyword}"**.

8.  **Title:** {final_title_directive}

**Page Analysis Data (JSON format):**
```json
{analysis_data_json}
```

--- Timestamp for Variation: {variation_seed} ---
"""
    return prompt