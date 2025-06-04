# analyzer/llm_analysis_process_prompts.py
import json

class LLMAnalysisPrompts:
    """
    Centralized prompt management for LLM analysis processes.
    Contains prompts used for single-page LLM analysis.
    The AI recommendations prompt has been moved to generate_ai_recommendations_prompt.py.
    """
    
    @staticmethod
    def get_detailed_instructions():
        """Get the detailed instructions for each field in the single-page analysis."""
        return {
            "keywords": """1. **"keywords"**:
        * Identify and list the top 7-10 most relevant and frequently occurring keywords or key phrases from the page content and headings.
        * These should accurately represent the main topics and themes of the page.
        * Prioritize multi-word phrases if they are more descriptive. Example: ["data analysis solutions", "cloud computing services", "enterprise software"]
        * Return as a list of strings. If no distinct keywords are found, return an empty list [].""",
            
            "content_summary": """2. **"content_summary"**:
        * Provide a concise summary of the page content in 5-7 sentences (target 300-550 words).
        * The summary must capture the main purpose, key offerings, or core information presented on the page.
        * It should be informative and engaging.
        * If the content is too sparse for a meaningful summary, provide a brief note like "Low page content. Skiping Detailed Analysis." """,
            
            "other_information_and_contacts": """3. **"other_information_and_contacts"**:
        * Extract any explicit contact information: email addresses, phone numbers, physical addresses.
        * Identify specific company names, key product names and prices, or important service names mentioned.
        * List social media profile URLs if clearly present.
        * If the page mentions specific individuals (e.g., team members, authors), list their names and roles if available. Turkish names and surnames can be longer.
        * Format each piece of information as a descriptive string in a list. Put the relevant information next to each other.
        * Example: ["Email: contact@example.com", "Phone: (555) 123-4567", "Main Office: 123 Innovation Drive, Tech City", "Product: Alpha Suite", "Twitter: https://twitter.com/example"]
        * If no such information is found, return an empty list [].""",
            
            "suggested_keywords_for_seo": """4. **"suggested_keywords_for_seo"**:
        * Based on the page content and its main topics, suggest 3-5 additional keywords or key phrases that could be targeted for low competitive SEO.
        * Plus to those suggest 3-5 more should be relevant variations, related topics or potential long-tail and alternatives but relevant keywords. Dont use alternative region , city names if its not in the content.
        * Consider user intent (informational, transactional, navigational). Example: ["benefits of data analysis", "best cloud providers for small business", "custom enterprise software development"]
        * If no strong distinct suggestions can be made, return an empty list [].""",
            
            "overall_tone": """5. **"overall_tone"**:
        * Describe the general tone or style of the content on the page (e.g., formal, informal, professional, casual, authoritative, promotional, educational, humorous, technical).
        * Provide a single, concise descriptive word or short phrase. Example: "professional and informative", "casual and engaging".""",
            
            "target_audience": """6. **"target_audience"**:
        * Identify the primary target audience(s) for the content on this page. Consider who the content is intended for (e.g., businesses, consumers, technical professionals, students, specific demographics).
        * List 1-3 distinct groups as strings. Example: ["small business owners", "software developers", "parents"]
        * If not clearly discernible, return an empty list [].""",
            
            "topic_categories": """7. **"topic_categories"**:
        * Categorize the main topics or themes covered on the page into 2-4 broad categories. Think of general industry or subject areas.
        * Example: ["Software Development", "Digital Marketing", "Financial Services", "Health & Wellness"]
        * If no clear categories, return an empty list [].""",
            
            "header": """8. **"header"**:
        * From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main header.
        * This typically includes site navigation links (e.g., "Home", "About Us", "Services", "Contact"), site branding text (e.g., company name if prominently in header), or a primary tagline.
        * Provide these as a list of strings. Each string can be a distinct link text or a phrase from the header.
        * If no clear header text is discernible, return an empty list [].
        * Example: ["Home", "Products", "Blog", "Login", "Site Title Example Inc."]""",
            
            "footer": """9. **"footer"**:
        * From the "Page Content (Cleaned Text Snippet)", identify and extract text elements that likely constitute the website's main footer.
        * This typically includes copyright notices, links to privacy policy, terms of service, sitemap, contact information repeated in the footer, or social media links.
        * Provide these as a list of strings. Each string can be a distinct link text or a phrase from the footer.
        * If no clear footer text is discernible, return an empty list [].
        * Example: ["© 2024 Company Name", "Privacy Policy", "Terms of Use", "Contact Us", "Follow us on Twitter" , "Bizi Arayın : (555) 123-4567"]"""
        }
    
    @staticmethod
    def get_json_structure(is_main_page: bool = False):
        """Get the JSON structure template for LLM responses for single-page analysis."""
        base_structure = {
            "keywords": ["string"],
            "content_summary": "string",
            "other_information_and_contacts": ["string"],
            "suggested_keywords_for_seo": ["string"],
            "overall_tone": "string",
            "target_audience": ["string"],
            "topic_categories": ["string"]
        }
        
        if is_main_page:
            base_structure.update({
                "header": ["string"],
                "footer": ["string"]
            })
        
        return base_structure
    
    @staticmethod
    def build_single_page_analysis_prompt(page_url: str, truncated_cleaned_text: str, 
                                        headings_data: dict, is_main_page: bool = False) -> str:
        """
        Build the complete prompt for single page analysis.
        
        Args:
            page_url: The URL of the page being analyzed
            truncated_cleaned_text: The cleaned text content of the page
            headings_data: Dictionary containing heading structure
            is_main_page: Whether this is the main page (includes header/footer analysis)
            
        Returns:
            Complete prompt string for LLM analysis
        """
        instructions = LLMAnalysisPrompts.get_detailed_instructions()
        json_structure = LLMAnalysisPrompts.get_json_structure(is_main_page)
        
        # Build the core instructions in the correct order
        core_instruction_keys = [
            "keywords", "content_summary", "other_information_and_contacts", 
            "suggested_keywords_for_seo", "overall_tone", "target_audience", "topic_categories"
        ]
        # Ensure only relevant instructions are included
        instruction_texts_to_include = [instructions[key] for key in core_instruction_keys]
        
        prompt = f"""If content is Turkish make your analysis in Turkish, Otherwise make it in English.
    --
    Analyze the following web page content for the URL: {page_url}
    ---
    **Page Content (Cleaned Text Snippet):**
    ---
    {truncated_cleaned_text}
    ---
    **Page Headings (JSON format):**
    ---
    {json.dumps(headings_data, indent=2, ensure_ascii=False)}
    ---
    Based on the provided text and headings, generate a JSON object strictly adhering to the following structure.
    Output ONLY the JSON object. Do NOT include any explanatory text, markdown formatting, or anything else outside the JSON object itself.
    {json.dumps(json_structure, indent=2, ensure_ascii=False)}
    **Detailed Instructions for populating each field in the JSON object:**
    {"\n".join(instruction_texts_to_include)}
    """
        
        # Add main page specific instructions if applicable
        if is_main_page:
            prompt += f"""
    {instructions["header"]}
    {instructions["footer"]}"""
        
        prompt += """
    Ensure your entire response is ONLY a valid JSON object.
    """
        
        return prompt
    
    # The build_ai_recommendations_prompt method has been moved to 
    # generate_ai_recommendations_prompt.py
    # No other changes to this class are needed for this specific request.