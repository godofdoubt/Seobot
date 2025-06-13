
import json

def get_analysis_prompt(page_url: str, cleaned_text: str, headings_data: dict, language_code: str = "en") -> str:
    """
    Generate the analysis prompt for LLM processing.
    
    Args:
        page_url: The URL of the page being analyzed.
        cleaned_text: The cleaned text content from the page.
        headings_data: Dictionary containing page headings.
        language_code: The target language for the analysis output (e.g., 'tr', 'en').
    
    Returns:
        str: The formatted prompt for LLM analysis.
    """
    
    # FIX: Simplified language instruction logic. The prompt now generates its own
    # strong instruction based only on the language_code, removing the buggy override parameter.
    if language_code == 'tr':
        language_instruction = "Analizini ve tüm JSON alanlarındaki (özellikle 'content_summary' ve 'suggested_keywords_for_seo') metinleri kesinlikle Türkçe yap. Sayfa dili ne olursa olsun, analiz çıktısı Türkçe olmalıdır."
    else: # Default to English
        language_instruction = "Perform your analysis and generate all text fields (especially 'content_summary' and 'suggested_keywords_for_seo') strictly in English, regardless of the source page language."

    # Truncate text if too long
    max_text_len = 30000
    truncated_cleaned_text = cleaned_text[:max_text_len] + ('...' if len(cleaned_text) > max_text_len else '')
    
    prompt = f"""{language_instruction}
    Analyze the following web page content for the URL: {page_url}
    
    **Page Content (Cleaned Text Snippet):**
    ---
    {truncated_cleaned_text}
    ---
    
    **Page Headings (JSON format):**
    ---
    {json.dumps(headings_data, indent=2, ensure_ascii=False)}
    ---
    
    Based on the provided text and headings, generate a JSON object strictly adhering to the following structure.
    Output ONLY the JSON object. Do NOT include any explanatory text, markdown formatting (like ```json), or anything else outside the JSON object itself.
    
    {{
        "keywords": ["string"],
        "content_summary": "string",
        "other_information_and_contacts": ["string"],
        "suggested_keywords_for_seo": ["string"],
        "header": ["string"],
        "footer": ["string"],
        "needless_info": ["string"],
        "main_content": ["string"],
        "navigation_items": ["string"],
        "language_consistency": "string"
    }}
    
    **Enhanced Instructions for Better Content Detection and Separation:**
    
    1. **"keywords"**:
       * Extract 5-7 most relevant keywords/phrases from MAIN CONTENT only (exclude navigation, footer, accessibility text)
       * Focus on business/service-related terms that represent the page's primary purpose
       * Prioritize multi-word phrases over single words
       * Exclude generic terms like "home", "contact", "menu"
       * Return as list of strings, empty list [] if none found
    
    2. **"content_summary"**:
       * Summarize ONLY the main informational content (5-7 sentences, 100-200 words). **The summary language MUST match the primary instruction language (e.g., Turkish for Turkish analysis).**
       * Ignore navigation menus, headers, footers, and accessibility text.
       * Focus on what the business/service actually offers or what the page is about.
       * If main content is minimal, state the equivalent of "Insufficient main content for summary" in the target language.
    
    3. **"other_information_and_contacts"**:
       * Extract specific, actionable contact information:
         - Email addresses (format: "Email: address@domain.com")
         - Phone numbers (format: "Phone: +XX XXX XXX XXXX")
         - Physical addresses (format: "Address: full address")
         - Company/brand names (format: "Company: Name")
         - Social media URLs (format: "Platform: URL")
         - Key personnel (format: "Person: Name - Role")
       * Only include if explicitly mentioned in content
       * Exclude generic phrases like "Contact us" or "Follow us"
       * Return empty list [] if no specific information found
    
    4. **"suggested_keywords_for_seo"**:
       * Suggest 3-5 SEO-relevant keywords based on the main content theme. **Keywords MUST be in the same language as the requested analysis language.**
       * Consider long-tail variations and related services/products
       * Focus on search intent (what users might search for to find this page)
       * Exclude already identified primary keywords
       * Return empty list [] if no distinct suggestions possible
    
    5. **"header"** (Improved Detection):
       * Extract elements from the TOP portion of cleaned text that represent:
         - Site branding/logo text
         - Main navigation menu items
         - Primary taglines or slogans
         - Site-wide trust signals like quality certifications (e.g., "ISO 22000-2018 Gıda Güvenliği Yönetim Sistemi", "Helal Sertifikası") if they appear in a consistent, repeating top banner.
       * Stop extraction when main content clearly begins (look for paragraph text, detailed descriptions)
       * Example pattern recognition:
         - Navigation: "Home | About | Services | Contact"
         - Categories: "Products" followed by "Product A, Product B, Product C"
       * Return empty list [] if no clear header structure
    
    6. **"footer"** (Better Identification):
       * Extract elements from the BOTTOM portion of cleaned text:
         - Copyright notices (e.g., "© 2023 Gıdaormanı")
         - Legal links ("Privacy Policy", "Terms", "KVKK")
         - Repeated contact info in footer context
         - Footer-specific social media links
         - **Also include footer section headings (e.g., "KURUMSAL", "MÜŞTERİ HİZMETLERİ", "ALIŞVERİŞ BİLGİLERİ").**
       * Look for typical footer patterns: copyright symbols, years, legal terminology.
       * Do NOT include the full paragraph of cookie consent text here; classify that as needless_info.
       * Return empty list [] if no clear footer identified
    
    7. **"needless_info"** (Enhanced Filtering):
       * Identify and extract truly non-content elements:
         - Accessibility text: "Skip to Content", "Skip to main content"
         - Full cookie consent banner text (e.g., "Çerez Kullanımı Sizlere iyi alışveriş deneyimi sunabilmek adına sitemizde yasal düzenlemelere uygun çerezler(cookies) kullanmaktayız...")
         - Repeated navigation blocks (if same menu appears multiple times)
         - Generic image alt text: "Slide Background", "Image placeholder", "decorative image"
         - Shopping cart indicators: "My Cart 0.00", cart counters
         - Generic action text: "Open Menu", "Close Menu", "Read More", "Devamını oku"
         - Pagination controls: "Next", "Previous", page numbers (e.g., "1 2 >")
         - Placeholder content: "Lorem ipsum" text
         - Technical artifacts: view counters, share buttons without context
       * Be conservative - only include if clearly non-informational
       * Return empty list [] if all content appears purposeful
    
    8. **"main_content"** (Better Content Separation):
       * Extract the core informational content of the page
       * Exclude header, footer, navigation, and needless info
       * Focus on paragraphs, descriptions, main text blocks
       * Include service descriptions, product details, about information
       * This helps separate actual content from structural elements
       * Return empty list [] if no substantial main content identified
    
    9. **"navigation_items"** (Cleaner Navigation Detection):
       * Specifically extract navigation menu items and their sub-items
       * Include both main menu categories and dropdown/submenu items
       * Format as hierarchical when possible: "Services > Web Design"
       * Helps distinguish between navigation and main content mentions
       * Return empty list [] if no clear navigation structure
    
    10. **"language_consistency"** (Language Detection):
        * Analyze the dominant language of the content
        * Identify mixed language issues: "Turkish content with scattered English terms"
        * Note if language mixing seems intentional (brand names, technical terms) vs accidental
        * Example values: "Consistent Turkish", "Mixed Turkish-English", "Predominantly English"
        * Helps identify content quality issues
    
    **Additional Processing Rules:**
    - **CRITICAL - Verbatim Extraction:** For "header", "footer", "needless_info", and "navigation_items", you MUST extract the text fragments *EXACTLY* as they appear in the provided page content.
      - **DO NOT** add, remove, summarize, or change any words.
      - **DO NOT** infer or add context. For example, if the text is `Detaylı bilgi sözleşmesini`, you MUST return `Detaylı bilgi sözleşmesini` and NOT `Detaylı bilgi KVKK sözleşmesini`.
      - Your task is to copy the fragment precisely as-is. This is essential for later processing.
    - Prioritize context over keywords when categorizing text elements
    - Use position indicators (beginning/end of content) to help identify headers/footers
    - Consider semantic meaning - don't just pattern match
    - When in doubt, err on the side of including text in main_content rather than needless_info
    - Pay attention to repetition patterns to identify structural vs content elements
    
    Ensure your entire response is ONLY a valid JSON object with all fields included.
    """
    
    return prompt


def get_gemini_analysis_prompt(page_url: str, cleaned_text: str, headings_data: dict, language_code: str = "en") -> str:
    """
    Get the analysis prompt specifically optimized for Gemini models.
    
    Args:
        page_url: The URL of the page being analyzed
        cleaned_text: The cleaned text content from the page
        headings_data: Dictionary containing page headings
        language_code: The target language for the analysis output.
    
    Returns:
        str: The formatted prompt for Gemini LLM analysis
    """
    return get_analysis_prompt(page_url, cleaned_text, headings_data, language_code)


def get_mistral_analysis_prompt(page_url: str, cleaned_text: str, headings_data: dict, language_code: str = "en") -> str:
    """
    Get the analysis prompt specifically optimized for Mistral models.
    
    Args:
        page_url: The URL of the page being analyzed
        cleaned_text: The cleaned text content from the page
        headings_data: Dictionary containing page headings
        language_code: The target language for the analysis output.
    
    Returns:
        str: The formatted prompt for Mistral LLM analysis
    """
    return get_analysis_prompt(page_url, cleaned_text, headings_data, language_code)
