# analyzer/llm_analysis_process_prompts.py
import json

class LLMAnalysisPrompts:
    """
    Centralized prompt management for LLM analysis processes.
    Contains all prompts used in the LLM analysis workflow.
    """
    
    @staticmethod
    def get_detailed_instructions():
        """Get the detailed instructions for each field in the analysis."""
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
        """Get the JSON structure template for LLM responses."""
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
        core_instruction_texts = [instructions[key] for key in core_instruction_keys]
        
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
    {json.dumps(json_structure, indent=2)}
    **Detailed Instructions for populating each field in the JSON object:**
    {"\n".join(core_instruction_texts)}
    """ # Corrected: Used "\n".join for proper spacing between instructions
        
        # Add main page specific instructions
        if is_main_page:
            prompt += f"""
    {instructions["header"]}
    {instructions["footer"]}"""
        
        prompt += """
    Ensure your entire response is ONLY a valid JSON object.
    """
        
        return prompt
    
    @staticmethod
    def build_ai_recommendations_prompt(website_data_summary: dict) -> str:
        """
        Build the comprehensive AI recommendations prompt.
    
        Args:
            website_data_summary: Dictionary containing complete website analysis data
    
        Returns:
            Complete prompt string for AI recommendations
        """
        return f"""
    Based on the comprehensive SEO and content analysis of this website, first, define 3-5 distinct target audience personas. Then, provide strategic recommendations and a few illustrative examples of actionable SEO optimization tasks. The focus is on showcasing a deep understanding of the data and its implications, rather than exhaustive lists of tasks.
    
    WEBSITE ANALYSIS DATA:
    {json.dumps(website_data_summary, indent=2, ensure_ascii=False)}
    
    Generate recommendations in the following JSON structure. For task-oriented sections (seo_content_optimization, content_strategy_insights, article_content_tasks, product_content_tasks), provide only 1-2 high-impact, illustrative examples for each:
    
    {{
        "target_audience_personas": [
            {{
                "persona_name": "string (e.g., 'Tech-Savvy Tom', 'Budget-Conscious Brenda', 'Araştırmacı Ayşe')",
                "demographics": "string (e.g., '25-35, Urban, Early Adopter', '40-55, Suburban, Value Seeker')",
                "occupation_role": "string (e.g., 'Software Developer', 'Small Business Owner', 'Pazarlama Müdürü')",
                "goals_related_to_site": ["string (what they want to achieve that this website can help with)"],
                "pain_points_challenges": ["string (challenges they face that this website's content/products can solve)"],
                "motivations_for_using_site": ["string (why they would choose this site/product over others)"],
                "information_sources": ["string (where they typically look for information - e.g., Google, Social Media, Forums)"],
                "key_message_for_persona": "string (a concise message that would resonate with this persona based on the site's offerings)"
            }}
        ],
        "strategic_recommendations": [
            {{
                "category": "string (e.g., 'SEO Optimization', 'Content Strategy', 'User Experience', 'Site Structure')",
                "title": "string (brief title for the recommendation)",
                "description": "string (detailed explanation and actionable steps)",
                "priority": "string (High/Medium/Low)",
                "implementation_difficulty": "string (Easy/Medium/Hard)",
                "based_on_data": "string (specific data point or metric that led to this recommendation)"
            }}
        ],
        "seo_content_optimization": [ // Provide 1-2 illustrative examples
            {{
                "focus_area": "string (e.g., 'Keyword Strategy', 'Content Gaps', 'Internal Linking', 'Meta Optimization')",
                "current_issue": "string (specific issue found in the data)",
                "recommendation": "string (specific actionable recommendation)",
                "expected_impact": "string (what improvement to expect)",
                "pages_affected": ["string (specific page URLs if applicable)"]
            }}
        ],
        "content_strategy_insights": [ // Provide 1-2 illustrative examples
            {{
                "insight": "string (key insight about content strategy based on analysis)",
                "supporting_data": "string (specific data that supports this insight)",
                "action_items": [ // For the example insight, provide 1 example action item
                    {{
                        "action_type": "string (Article/Product/Page Update/Technical Fix)",
                        "page_url": "string (target page URL or 'new page')",
                        "title": "string (suggested title)",
                        "description": "string (detailed action description)",
                        "target_persona": "string (which defined persona this action targets)",
                        "social_media_opportunity": "string (optional - social media angle)",
                        "media_suggestions": "string (image/video recommendations)",
                        "headings_structure": ["string (suggested H1, H2, H3 structure)"],
                        "priority": "string (High/Medium/Low)"
                    }}
                ]
            }}
        ],
        "article_content_tasks": [ // Provide 1-2 illustrative examples
            {{
                "focus_keyword": "string (primary keyword for the article)",
                "content_length": "string (Small: 300-500 words, Medium: 500-1000 words, Long: 1000-2000 words, Very Long: 2000+ words)",
                "article_tone": "string (Professional/Casual/Enthusiastic/Technical/Friendly)",
                "additional_keywords": ["string (optional supporting keywords)"],
                "suggested_title": "string (SEO-optimized title)",
                "target_page_url": "string (where this content should be published)",
                "content_gap_addressed": "string (what gap this content fills)",
                "target_audience_persona": "string (name of the persona this article targets)"
            }}
        ],
        "product_content_tasks": [ // Provide 1-2 illustrative examples
            {{
                "product_name": "string (product/service name)",
                "product_details": {{
                    "features": ["string (list of key features)"],
                    "benefits": ["string (list of key benefits)"],
                    "target_audience_persona": "string (name of the persona this product targets)"
                }},
                "tone": "string (Professional/Casual/Enthusiastic/Technical/Friendly)",
                "description_length": "string (Short: 50-150 words, Medium: 150-300 words, Long: 300+ words)",
                "target_page_url": "string (where this product content should appear)",
                "seo_keywords": ["string (relevant keywords for this product)"],
                "competitive_advantage": "string (what makes this product unique based on analysis)"
            }}
        ]
    }}
    
    CRITICAL REQUIREMENTS:
    
    1.  **Language Detection**: If website content (keywords, summaries, topic categories from `website_data_summary`) is primarily in Turkish, respond entirely in Turkish, including persona names and details. Otherwise, use English.
    
    2.  **Persona Definition First**: Generate 3-5 detailed `target_audience_personas` based on the `website_data_summary` (keywords, content themes, inferred user intent). These personas should inform subsequent recommendations.
    
    3.  **Data-Driven Recommendations**: ALL recommendations and personas MUST be based on the actual `technical_statistics` and `website_analysis_data` provided. Reference specific metrics, issues, or opportunities found in the data.
    
    4.  **Illustrative Examples**: For `seo_content_optimization`, `content_strategy_insights`, `article_content_tasks`, and `product_content_tasks`, provide only 1-2 carefully selected, high-impact examples for each category. These examples should demonstrate a strong analytical link to the input data and the defined personas.
    
    5.  **Strategic Focus Areas** (provide 3-5 strategic recommendations covering):
        - SEO technical issues (alt text coverage, mobile optimization, site speed)
        - Content gaps identified from keyword analysis (and relevant to personas)
        - User experience improvements based on site structure
        - Conversion optimization opportunities (considering persona motivations)
    
    6.  **Specific Technical Issues to Address** (ensure strategic recommendations consider these if present in data):
        - Alt text coverage percentage
        - Mobile responsiveness issues
        - Site structure and navigation problems
        - Page loading performance
        - Internal linking opportunities
    
    7.  **Content Strategy Requirements for Examples**:
        - Illustrate addressing content gaps from keyword analysis relevant to defined personas.
        - Consider target personas and topic categories found.
        - If suggesting page improvements, use specific URLs.
    
    8.  **Actionable Item Examples Must Include**:
        - Specific page URLs where applicable.
        - Exact keywords to target.
        - Expected outcomes.
        - Implementation difficulty.
        - Which persona they are targeting, if applicable.
    
    9.  **No Generic Advice**: Every recommendation and example must reference specific data points from the analysis. Avoid generic SEO advice not tied to the actual website data.
    
    10. **Prioritization**: Rank `strategic_recommendations` by potential impact and implementation difficulty. Example tasks should ideally be high-impact.
    
    Output ONLY the JSON object with no additional text, markdown, or formatting.
    """