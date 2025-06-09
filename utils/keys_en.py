# keys_en.py
# Seobot/utils/keys_en.py

translations = {
    # Existing keys ...
     "seo_helper_prepare_for_article_writer_cta": "\n\nI've identified {0} potential article ideas from this analysis. I can prepare these for you to work on in the Article Writer. Would you like to do that? (Type 'yes' or 'no')",
      "seo_helper_cta_yes_article_writer_stay": "Great! I've noted these article suggestions. You can head over to the 'Article Writer' page (from the sidebar) to start developing them when you're ready.",
      "seo_helper_cta_no_article_writer": "Alright. Let me know if you change your mind or need help with anything else!",
      "seo_helper_cta_invalid_response": "Please respond with 'yes' or 'no' to the previous question about preparing article suggestions.",
      "seo_helper_cta_yes_no_tasks": "Okay. It seems there were no specific tasks to prepare. You can still visit the Article Writer page.",
      "seo_helper_cta_yes_generic": "Okay!",
    # NEW SEO Helper CTA (extended)
    "seo_helper_initial_cta_article_extended": "\n\nI've identified {num_tasks} potential article ideas. The first is '{first_task_title}'. Shall I prepare it for the Article Writer? (Type 'yes' to prepare, 'skip' for the next, or 'stop' to cancel this process)",
    "the_first_article_generic": "the first article",
    "seo_helper_initial_cta_product_extended": "\n\nI've found {num_tasks} product description tasks. The first is for '{first_task_title}'. Shall I prepare it for the Product Writer? (Type 'yes' to prepare, 'skip' for the next, or 'stop' to cancel this process)",
    "the_first_product_generic": "the first product",
    "seo_helper_cta_input_placeholder_extended": "Your response for '{task_name}' (yes/skip/stop)...",
    "seo_helper_cta_resumed_chat_prompt_extended_options": "Resuming article task preparation. I am now focused on '{task_title}'. Shall I prepare it, skip to the next, or stop this process? (Type 'yes', 'skip', or 'stop')",
    "seo_helper_cta_resumed_chat_prompt_product_extended_options": "Resuming product task preparation. I am now focused on '{task_title}'. Shall I prepare it, skip to the next, or stop this process? (Type 'yes', 'skip', or 'stop')",

    # Buttons
    "login_button": "Login",
    "logout_button": "Logout",
    "analyze_button": "Analyze Website",
    "seo_helper_button": "🚀 SEO Helper",
    "article_writer_button": "✍️ Article Writer",
    "product_writer_button": "🛍️ Product Writer",
    "generate_seo_suggestions_button_text": "Generate Suggestions🔍",
    "generate_article": "Generate Article",
    "generate_product_description": "Generate Product Description",
    "check_report_update_button": "🔄 Check for Full Site Analysis Update",
    "refresh_analysis_status": "🔄 Just a sec.../ Refresh",
    "refresh_comprehensive_report": "🔄 Refresh Comprehensive Report",
    "recheck_comprehensive_report": "🔄 Re-check Analysis", # NEW (distinct from refresh_comprehensive_report)
    "go_to_login":"ℹ️Please Login First",
    "resume_article_tasks_button": "▶Resume with: '{task_title}'▶️", # NEW - SEO Helper Task Panel
    "resume_product_tasks_button": "▶️Resume with: '{task_title}'▶️", # NEW - SEO Helper Task Panel


    # Detailed Analysis Messages
    "detailed_analysis_init_error": "Error initializing detailed analysis processor. Please check logs or contact support.",
    "detailed_analysis_runtime_error": "Runtime error during detailed analysis processor setup. Please check logs or contact support.",
    "detailed_analysis_trigger_error": "Failed to start the detailed site-wide analysis. Please try again or contact support.",
    "detailed_analysis_error_status": "Detailed analysis for this report encountered an error: {llm_analysis_error}. Please check logs or contact support.",
    "detailed_analysis_still_inprogress": "Detailed site-wide LLM analysis is still in progress. Please check back again.",
    "detailed_analysis_initiated": "Detailed site-wide analysis initiated. This may take some time. You can monitor progress here.", # NEW
    "error_checking_report_status": "Error checking report status. Please try again.",
    "status_check_failed_error": "Failed to check report status due to an error.", # NEW

    # Main UI Elements
    "main_settings_title": " Panel: '<' ^^ ",
    "home_page_label": " 👋 Home",
    "language_select_label": "Language / Dil",
    "select_ai_model_label": "Select AI Model:",
    "model_o10": "o10 (Gemini)",
    "model_Se10": "Se10 (Mistral)",
    "view_seo_report_expander_label": "📝 View SEO Report",
    "your_website_report_label": "Report for: {0}",
    "no_text_report_available": "No text report available.",
    "analysis_running_sidebar_info": "Analysis is in progress. Some controls and navigation links are temporarily disabled.",
    "show_less_report_sidebar": "Show less", # NEW
    "read_more_report_sidebar": "Read more", # NEW
    "auto_refresh_checkbox": "🔄 Auto-check", # NEW
    "auto_refresh_help": "Automatically checks for completion", # NEW

    # General Messages
    "welcome_message": "Welcome nevaR Web Services!",
    "welcome_seo": "Welcome nevaR Web Services Beta!",
    "welcome_authenticated": "Welcome, {0}!", # {0} is username
    "logged_in_as": "Logged in as: **{username}**",
    "analysis_complete_message": "✅ Analysis for your URL is complete.",
    "analyzing_website": "Analyzing your website, please wait...",
    "found_existing_report": "Found an existing report for this URL.",
    "analysis_failed": "Failed to analyze the website. Please try again.",
    "analysis_results_for_url": "Analysis Results for: {url}",
    "authentication_required": "You need to log in first to use this service.",
    "login_failed": "Authentication failed. Please check your API key.",
    "enter_api_key_label": "Please enter your API key to continue:",
    "enter_api_key": "Please enter your API key to continue:",
    "next_steps": "Next Steps:",
    "continue_optimizing": "Continue optimizing your site or generate content:",
    "content_generation_tools": "Content Generation Tools",
    "create_optimized_content": "Use our AI tools to create optimized content based on the analysis:",
    "analyze_with_ai": "Or, jump directly to AI tools (requires prior analysis for best results):",
    "generating_new_report": "Generating new SEO report...",
    "generating_new_analysis": "No existing report found. Generating a new analysis, this may take a few moments...",
    "failed_to_analyze": "Sorry, we encountered an error while trying to analyze the website. Please try again or contact support.",
    "no_report_available_error": "An error occurred, and no report is available for this URL.",
    "full_site_analysis_complete": "✅ Full site analysis, including all sub-pages, is complete!",
    "detailed_analysis_inprogress": "ℹ️ Main page analysis is complete. In-depth analysis for all site pages is currently processing.",
    "analysis_in_progress_for": "Analysis for **{0}** is still in progress. Please wait. 🔄.", # MODIFIED, {0} is for URL
    "llm_analysis_status_unknown": "Status of detailed sub-page analysis is currently unknown. Analyze or refresh if expecting results.",
    "no_ai_model": "No AI model API key (Gemini or Mistral) is configured. Please set at least one in your environment.",
    "no_ai_model_configured": "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY.",
    "no_ai_api_keys_configured": "No AI API keys configured. Please check your configuration.",
    "seo_report_summary_label": "SEO Report Summary",
    "seo_report_label": "Your Analysis Report is Here",
    "text_report_not_available": "Text report summary is not available.",
    "analysis_completed_no_report": "Analysis completed, but no report was generated.",
    "seo_analysis_completed": "SEO Analysis for {0} completed. How can I help you with your SEO strategy?", # {0} is URL
    "provide_url_first": "Please provide a website URL first so I can analyze it.",
    "generating_article": "Generating article...",
    "analyze_website_first": "Please analyze a website first in the SEO Helper page.",
    "analyze_website_first_chat": "Please analyze a website first in the SEO Helper page before I can help with article writing.",
    "article_prompt": "What kind of article would you like to write?",
    "getting_started": "Getting Started",
    "begin_by_analyzing": "Begin by entering your website URL below to get an SEO analysis report.",
    "platform_description": "This platform provides tools to analyze your website's SEO, generate SEO suggestions, and create optimized content. Side bar panel open/close from the top left corner. '<'",
    "generating_product_description": "Generating product description...",
    "welcome_product_writer_not_analyzed": "Welcome to the Product Writer page. Please analyze a website in the SEO Helper page first to proceed.",
    "welcome_product_writer_analyzed": "Welcome to the Product Writer page.\nUsing analysis for: **{0}**", # {0} is URL
    "product_description_prompt": "What kind of product description would you like to write?",
    "analyze_website_first_chat_product": "Please analyze a website first in the SEO Helper page before I can help with product writing.",
    "processing_request": "Processing your request 🔄",
    "generating_response": "Generating response",
    "could_not_generate_description": "Could not generate product description",
    "error_processing_request": "Error processing request🔄",
    "Processing_request": "Processing request",
    "analyzing": "Analyzing",
    "analyze_website_first_product": "Please analyze a website first in the SEO Helper page before I can help with product descriptions.",
    "welcome_seo_helper_analyzed": "Welcome to the Seo Helper Page.\nUsing analysis for: {0}",
    "welcome_article_writer_not_analyzed": "Welcome to the Article Writer page. Please analyze a website in the SEO Helper page first to proceed.",
    "welcome_article_writer_analyzed": "Welcome to the Article Writer page. Ready to help you write an article based on the analysis of {0}.",
    "enter_url_or_question_seo_helper":"Enter Url.....Select Page and generate srategy....I am here to help...",
    "enter_url_placeholder":"Enter Url.",
    "report_data_unavailable": "Report data is not available.",
    "invalid_length_in_suggestion_warning": "Warning: The suggested length '{0}' is invalid. Defaulting to '{1}'.",
    "invalid_tone_in_suggestion_warning": "Warning: The suggested tone '{0}' is invalid. Defaulting to '{1}'.",
    "unexpected_error_refresh": "An unexpected error occurred. Please refresh the page and try again.",
    "fallback_ai_service": "Primary AI service unavailable. Using {0} as fallback...",
    "none_value": "None",
    "not_available_short": "N/A", # NEW - General short display
    "no_details_provided_short": "No specific details provided.", # NEW - General short display
    "generic_page_welcome": "Welcome to the {page_name} page.", # NEW
    "report_up_to_date_toast": "Report is up-to-date.", # NEW
    "found_suffix": "Found", # Added for localization in technical_status_chart

    # SEO Helper - Task Panel (Content Generation CTA Progress)
    "content_tasks_expander_title": "📝Content Generation Tasks Progress↕️", # NEW
    "cta_status_paused_at": "Paused article task preparation at: '{title}'.", # NEW
    "cta_status_awaiting_response_for": "Awaiting response for article task: '{title}'.", # NEW
    "cta_status_paused_at_product": "Paused product task preparation at: '{title}'.", # NEW
    "cta_status_awaiting_response_for_product": "Awaiting response for product task: '{title}'.", # NEW
    "cta_status_awaiting_response_generic": "Awaiting response for suggested task.", # NEW
    "cta_all_tasks_addressed_panel": "All content tasks in this batch have been addressed.", # NEW

    # Article Options
    "target_page_url_label": "Target Page URL",
    "content_gap_label": "Content Gap",
    # "target_audience_label": "Target Audience", # Already exists in Product Options, shared
    "outline_preview_label": "Outline Preview",
    
    "article_options_title": "Article Options",
    "focus_keyword": "Focus Keyword",
    "focus_keyword_label": "Focus Keyword",
    "focus_keyword_help": "The main keyword your article will focus on",
    "content_length": "Content Length",
    "content_length_short": "Short",
    "content_length_medium": "Medium",
    "content_length_long": "Long",
    "content_length_very_long": "Very Long",
    "tone": "Article Tone",
    "tone_professional": "Professional",
    "tone_casual": "Casual",
    "tone_enthusiastic": "Enthusiastic",
    "tone_technical": "Technical",
    "tone_friendly": "Friendly",
    "custom_keywords": "Additional Keywords (optional)",
    "additional_keywords_label": "Additional Keywords",
    "custom_keywords_help": "Enter keywords separated by commas",
    "custom_title": "Custom Title (optional)",
    'product_content_tasks_label':"Product Content Tasks",

    # Article Writer UI & Suggestions
    "suggested_article_tasks_title": "Suggested Article Tasks",
    "suggested_article_tasks_intro": "We found some article suggestions based on the SEO analysis. Select one to pre-fill the article options:",
    "suggestion_task_label": "Suggestion",
    
    "content_length_label": "Content Length",
    "article_tone_label": "Article Tone",
    
    "suggested_title_label": "Suggested Title",
    "use_this_suggestion_button": "Use This Suggestion",
    "suggestion_applied_message": "Suggestion applied! Check the Article Options in the sidebar.",
    "no_article_suggestions_found": "No specific article suggestions found in the current report's auto_suggestions data, or the data format is unrecognized.",
    "focus_keyword_required_warning": "Focus Keyword is required to generate an article. Please fill it in the sidebar.",
    "analyze_site_for_article_options": "Analyze a site in SEO Helper to see article options.", # NEW
    "article_writer_activated_by_seo_helper": "Article Writer activated by SEO Helper for: **{task_title}**. Generating article...", # NEW
    "article_writer_options_prefilled_by_seo_helper": "Article Writer options pre-filled by SEO Helper for: **{task_title}**. Review and click 'Generate Article'.", # NEW
    "generated_article_from_seo_helper_title": "Generated Article (from SEO Helper): {title}", # NEW
    "focus_keyword_required_for_auto_gen": "Focus keyword is missing in this suggestion. Please provide one in the sidebar to generate.", # NEW
    "article_generation_prerequisites_warning": "Cannot generate article. Ensure a site is analyzed and topic is provided in the sidebar.", # NEW
    "could_not_generate_article": "Sorry, I couldn't generate the article at this time.", # NEW

    # Product Options & Details Formatting
    "product_options_title": "Product Description Options",
    "product_name": "Product Name",
    "product_name_placeholder": "Enter the name of the product",
    "product_details": "Product Details",
    "product_details_placeholder": "Enter product features, benefits, specifications, target audience, etc.",
    "product_tone": "Tone",
    "product_length": "Description Length",
    "product_length_short": "Short (~100-150 words)",
    "product_length_medium": "Medium (~150-250 words)",
    "product_length_long": "Long (~250-350 words)",
    "features_label": "Features",
    "benefits_label": "Benefits",
    "target_audience_label": "Target Audience",
    "competitive_advantage_label": "Competitive Advantage",
    "suggested_seo_keywords_label": "Suggested SEO Keywords",

    # Product Writer UI & Suggestions
    "suggested_product_tasks_title": "Suggested Product Tasks",
    "suggested_product_tasks_intro": "We found some product description suggestions based on the SEO analysis. Select one to pre-fill the product options:",
    "untitled_suggestion": "Untitled Suggestion",
    "product_name_label": "Product Name",
    "product_description_length_label": "Description Length",
    "tone_label": "Tone",
    "seo_keywords_label": "SEO Keywords",
    "product_details_summary_label": "Product Details Summary",
    "no_product_suggestions_found": "No specific product suggestions found in the current report, or the data format is unrecognized.",
    "product_name_required_warning": "Product Name is required. Please fill it in the sidebar options.",
    "product_details_required_warning": "Product Details are required. Please fill them in the sidebar options.",


    # SEO Suggestions Specific
    "seo_suggestions_for_pages_label": "SEO Suggestions for Pages:",
    "select_pages_for_detailed_suggestions": "Select pages or leave empty for general report suggestions✖️ ",
    "multiselect_seo_help_text_v3": "Select specific pages for focused suggestions. If empty, general suggestions will be generated from the text report. 'main_page' contains the homepage analysis.",
    "text_report_suggestions_only": "Detailed page analysis not available. General suggestions will be generated from the text report.",
    "error_no_text_report_available": "Error: No text report available for suggestions.",
    "analyze_url_first_for_suggestions": "Analyze a URL to enable SEO suggestions.",
    "using_text_report_for_suggestions": "No specific pages selected. Generating general suggestions based on the text report.",
    "using_selected_pages_for_suggestions": "Generating suggestions for selected pages: {0}",
    "error_selected_pages_no_valid_data": "Error: None of the selected pages have data available for suggestions.",
    "loading_existing_suggestions": "Loading existing SEO suggestions from database...",
    "auto_generating_initial_suggestions": "Analysis complete. Automatically generating initial suggestions based on the text report...",
    "auto_processing_initial_suggestions": "Auto-generating initial suggestions...",
    "no_pages_in_analysis_data": "No pages available in the analysis data.",
    "error_all_ai_services_failed": "All AI services failed to generate suggestions. Please try again later.",
    "error_auto_suggestions_failed": "Unable to generate automatic suggestions. You can still request manual suggestions using the sidebar.",
    "error_generating_suggestions": "An error occurred while generating suggestions. Please try again.",

    # Keys that were mentioned in the log or context (raw_report_data_label, raw_report_help)
    "raw_report_data_label": "Raw Report Data (JSON)", # Used by LLMAnalysisProcess & main.py
    "raw_report_help": "This is the raw JSON data of the full analysis, useful for developers or for importing into other tools.", # Used by LLMAnalysisProcess

    # Section Titles for AI Recommendations
    "rec_title_strategic": "### Strategic Recommendations",
    "rec_title_seo": "### SEO Optimization Insights",
    "rec_title_personas": "### Target Audience Personas",
    "rec_title_content_insights": "### Content Strategy Insights",

    # Strategic Recommendations labels
    "rec_strategic_priority_label": "Priority",
    "rec_strategic_implementation_label": "Implementation",
    "rec_strategic_data_source_label": "Data Source",

    # SEO Optimization Insights labels
    "rec_seo_default_focus_area": "SEO Suggestion",
    "rec_seo_observed_issue_label": "Observed Issue/Opportunity",
    "rec_seo_insight_action_label": "Insight & Action",
    "rec_seo_potential_impact_label": "Potential Impact",
    "rec_seo_strategic_action_label": "Strategic Action Example",
    
    # Target Audience Personas labels
    "persona_item_prefix_label": "Persona",
    "persona_demographics_label": "Demographics",
    "persona_occupation_role_label": "Occupation/Role",
    "persona_goals_label": "Goals (related to site)",
    "persona_pain_points_label": "Pain Points/Challenges",
    "persona_motivations_label": "Motivations for Using Site",
    "persona_info_sources_label": "Information Sources",
    "persona_key_message_label": "Key Message",

    # Content Strategy Insights labels
    "rec_content_insight_item_prefix_label": "Insight",
    "rec_cs_implications_label": "Implications for Content",
    "rec_cs_illustrative_opp_label": "Illustrative Content Opportunity:",
    "rec_cs_opp_type_label": "Type",
    "rec_cs_opp_description_label": "Description",
    "rec_cs_opp_target_persona_label": "Target Persona Alignment",
    "rec_cs_opp_potential_topics_label": "Potential Topics/Angles",
    "rec_cs_opp_justification_label": "Justification",
    "seo_suggestions_and_content_ideas_title": " SEO Suggestions & Content Ideas",
    'article_content_tasks_label':"Article Content Tasks",

    # Common labels
    "common_supporting_data_label": "Supporting Data",

    # Chart/Dashboard related keys used in main.py
    "seo_score_gauge_title": "SEO Score",
    "metric_thin_content_pages": "Thin Content Pages",
    "tooltip_thin_content_pages": "{thin_pages_count} pages found with less than ~220 words. These may be seen as low-value by search engines.",
    "metric_bad_format_titles": "Pages with Title Format Issues",
    "tooltip_bad_format_titles": "{bad_titles_count} pages found with title formatting problems (e.g., <br> tags). Ensure titles are clean and descriptive.",
    "content_quality_overview_title": "Content Quality Overview",
    "xaxis_label_num_pages": "Number of Pages",
    "metric_word_count": "Word Count",
    "metric_images": "Images",
    "metric_internal_links": "Internal Links",
    "metric_external_links": "External Links",
    "metric_headings": "Headings",
    "page_content_metrics_bar_title_hp": "Page Content Metrics (Homepage)",
    "metrics_axis_label": "Metrics",
    "count_axis_label": "Count",
    "tech_mobile_friendly": "Mobile Friendly",
    "tech_ssl_secure": "SSL Secure",
    "tech_page_speed": "Page Speed (Est.)",
    "tech_title_tag_hp": "Title Tag (Homepage)",
    "tech_robots_txt": "Robots.txt Status",
    "tech_sitemap_status": "Sitemap Status",
    "tech_internal_404s": "Internal 404s",
    "status_good": "Good",
    "status_warning": "Warning",
    "status_error": "Error",
    "technical_seo_status_title": "Technical SEO Status",
    "seo_dashboard_main_title": "📊 SEO Analysis Dashboard",
    "seo_score_not_available_caption": "SEO Score might be 0 due to limited data for calculation.",
    "page_metrics_not_available_hp": "Page Content Metrics (Homepage) not available.",
    "content_quality_overview_not_available": "Content Quality Overview data not available.",
    "content_issue_thin_pages_found": "{count} page(s) with potentially thin content",
    "content_issue_bad_titles_found": "{count} page(s) with title format issues",
    "low_score_content_advice": "Your SEO score may be affected by content quality. Consider addressing: {issues}. Improving these areas can enhance your site's performance.",
    "low_score_other_factors": "Your SEO score is below the optimal range. While major thin content or title format issues weren't detected site-wide from this scan, review other technical aspects, content relevance, and user experience to identify areas for improvement.",
    "technical_seo_status_not_available": "Technical SEO Status not available.",
    # "raw_report_data_label": "Raw Report Data", # This one is for main.py expander. ALREADY EXISTS ABOVE.
    "raw_report_help_main": "This is the raw text report summary.", # This one is for main.py expander (distinct from the JSON help)
    "show_full_json_report": "Show Full JSON Report Data (for debugging)",
    "full_json_report_label": "Full JSON Report",
    "invalid_url_format_warning": "Invalid URL format. Please enter a valid website address (e.g., https://example.com).",
    "detailed_analysis_trigger_failed_status": "Failed to start detailed analysis process.",
    "please_enter_url": "Please enter a URL.",
    "analyzing_website_main_page_info": "Analysis for {url} is in progress...",

    # START OF NEW KEYS FOR LLMAnalysisProcess REPORT
    "report_main_title": "COMPREHENSIVE SEO & CONTENT ANALYSIS REPORT",
    "report_generated_at": "Generated at",
    "report_technical_overview": "Technical Overview",
    "report_website_analysis_summary": "Website Analysis Summary",
    "report_total_pages_crawled": "Total Pages Crawled",
    "report_analysis_duration": "Analysis Duration",
    "report_minutes_label": "minutes",
    "report_seconds_label": "seconds",
    "report_content_metrics": "Content Metrics",
    "report_total_content_analyzed": "Total Content Analyzed",
    "report_characters_label": "characters",
    "report_average_content_per_page": "Average Content Length per Page",
    "report_total_headings_found": "Total Headings Found",
    "report_image_optimization": "Image Optimization",
    "report_total_images_found": "Total Images Found",
    "report_images_missing_alt_text": "Images Missing Alt Text",
    "report_alt_text_coverage": "Alt Text Coverage",
    "report_status": "Status",
    "report_excellent": "Excellent",
    "report_good": "Good",
    "report_needs_improvement": "Needs Improvement",
    "report_critical": "Critical",
    "report_no_images_found": "No images found on the crawled pages.",
    "report_mobile_friendliness": "Mobile Friendliness",
    "report_pages_with_mobile_viewport": "Pages with Mobile Viewport",
    "report_mobile_optimization_coverage": "Mobile Optimization Coverage",
    "report_basic_technical_setup": "Basic Technical Setup",
    "report_robots_txt_file": "robots.txt File",
    "report_found": "Found", # Specific for report, distinct from found_suffix
    "report_not_found": "Not Found",
    "report_recommendation": "Recommendation",
    "report_robots_txt_recommendation": "Consider creating a robots.txt file to guide search engine crawlers.",
    "report_main_page_analysis": "Main Page Analysis",
    "report_url_not_found_in_data": "URL not found in data",
    "report_via_llm_provider": "via LLM Provider",
    "report_note": "Note",
    "report_main_page_analysis_error": "Analysis for the main page encountered an error",
    "report_overall_content_tone": "Overall Content Tone",
    "report_identified_target_audience": "Identified Target Audience",
    "report_main_topic_categories": "Main Topic Categories",
    "report_content_summary": "Content Summary",
    "report_primary_keywords_identified": "Primary Keywords Identified",
    "report_suggested_seo_keywords": "Suggested SEO Keywords",
    "report_contact_info_key_mentions": "Contact Info & Key Mentions",
    "report_no_contacts_identified": "No specific contact information or key mentions found by LLM.",
    "report_key_header_elements": "Key Header Elements",
    "report_no_header_elements_identified": "No distinct header elements identified by LLM.",
    "report_key_footer_elements": "Key Footer Elements",
    "report_no_footer_elements_identified": "No distinct footer elements identified by LLM.",
    "report_main_page_data_missing": "Main page analysis data is not available.",
    "report_subpage_analysis_overview": "Subpage Analysis Overview",
    "report_num_additional_pages_analyzed": "Number of Additional Pages Analyzed",
    "report_highlights_individual_subpages": "Highlights from Individual Subpages",
    "report_page": "Page",
    "report_subpage_analysis_error": "Analysis for this subpage encountered an error",
    "report_summary_prefix": "Summary",
    "report_tone_prefix": "Tone",
    "report_audience_prefix": "Audience",
    "report_topics_prefix": "Topics",
    "report_common_keywords_subpages_title_format": "Top {count} Common Keywords Across Subpages",
    "report_mentioned_in_subpages_format": "mentioned in {count} subpage(s)",
    "report_frequently_suggested_seo_keywords_subpages_title_format": "Top {count} Frequently Suggested SEO Keywords for Subpages",
    "report_common_topic_categories_subpages_title_format": "Top {count} Common Topic Categories in Subpages",
    "report_common_target_audiences_subpages_title_format": "Top {count} Common Target Audiences for Subpages",
    "report_common_content_tones_subpages_title_format": "Top {count} Common Content Tones in Subpages",
    "report_ai_powered_strategic_insights": "AI-Powered Strategic Insights & Recommendations",
    "ai_powered_strategic_insights": "AI-Powered Strategic Insights & Recommendations",
    #reportsuz seo helper page.
    "report_no_ai_recommendations": "AI recommendations were not generated.",
    "report_error_generating_ai_recommendations": "An error occurred while generating AI-powered recommendations.",
    "report_no_ai_recommendations_configured": "AI recommendations cannot be generated as no LLM is configured for this task.",
    "report_performance_monitoring_next_steps": "Performance Monitoring & Next Steps",
    "report_next_steps_1": "- **Regularly Monitor SEO Performance:** Use tools like Google Analytics, Google Search Console, and other SEO platforms to track keyword rankings, organic traffic, bounce rates, and conversion rates. Pay attention to how changes implemented based on this report affect your metrics.",
    "report_next_steps_2": "- **Content Updates & Gap Filling:** Periodically review and update existing content to keep it fresh, relevant, and accurate. Use the identified keyword gaps and topic suggestions to create new content that meets user needs and search intent.",
    "report_next_steps_3": "- **Technical SEO Audits:** Conduct periodic technical SEO audits to identify and fix issues like broken links, slow page speed, crawl errors, and mobile usability problems. Ensure your sitemap.xml and robots.txt files are up-to-date.",
    "report_next_steps_4": "- **Backlink Profile Management:** Analyze your backlink profile regularly. Disavow toxic links and actively seek high-quality, relevant backlinks to improve your site's authority.",
    "report_next_steps_5": "- **Stay Updated with SEO Trends:** The SEO landscape is constantly evolving. Stay informed about algorithm updates, new best practices, and emerging technologies (like AI in search) to adapt your strategy accordingly.",
    "report_end_of_report": "End of Report."
    # raw_report_data_label and raw_report_help are already defined above and will be reused.
    # END OF NEW KEYS FOR LLMAnalysisProcess REPORT
}