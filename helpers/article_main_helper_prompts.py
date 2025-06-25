
#/mnt/data/Max/Seo12/helpers/article_main_helper_prompts.py
def get_gemini_process_question_prompt(language_instruction: str, username_context: str, context: str, prompt: str) -> str:
    """Returns the formatted prompt for processing a question with Gemini."""
    return f"""{language_instruction}
    {username_context}Context: {context}
    Question: {prompt}

    Please provide a helpful response focused on article writing and content strategy.
    Consider the analysis report when providing guidance about content creation.
    """

def get_mistral_article_generation_prompt(language_instruction: str, username_context: str, history_context: str, text_report: str, url: str) -> str:
    """Returns the formatted system prompt for article generation with Mistral."""
    return f"""{language_instruction}
You are an expert content writer. Generate a well-structured, SEO-optimized article based on the provided website analysis. Always find posible suddle emotional hooks for entry of the article and end with CTA (Call To Action). Be cunning about this act like its a honest conversitaion if general tone allows it. Never put the result as the Result: . Give your suggestions in the end of your response aim for best article first.

User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{text_report}

Website URL: {url}

Instructions for article generation:
1. Create a compelling headline that includes relevant keywords.
2. Structure the article with clear headings and subheadings
3. Aim for approximately 1000-1500 words of high-quality content
4. Include an introduction, main body with 3-5 sections, and conclusion
5. Optimize for SEO while maintaining readability and engagement
6. Use a conversational but authoritative tone
7. Include calls-to-action where appropriate
"""

def get_mistral_general_query_prompt(language_instruction: str, username_context: str, history_context: str, text_report: str, url: str) -> str:
    """Returns the formatted system prompt for general content strategy queries with Mistral."""
    return f"""{language_instruction}

You are an expert content writer. Generate a well-structured, SEO-optimized article based on the provided website analysis. Always find posible suddle emotional hooks for entry of the article and end with CTA (Call To Action). Be cunning about this act like its a honest conversitaion if general tone allows it. Never put the result as the Result: . Give your suggestions in the end of your response aim for best article first.
First provide specific, actionable advice related to content creation and article writing based on the SEO report. Write the article and add advices in Notes: section.
User Information:
{username_context}

Conversation History:
{history_context}

Context from SEO Report:
{text_report}

Website URL: {url}

"""

