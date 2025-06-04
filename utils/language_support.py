# SeoTree/utils/language_support.py
import logging # Added import

class LanguageSupport:
    """Class to manage multi-language support in the application"""

    def __init__(self):
        self.translations = {
            "en": {
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
                #"detailed_analysis_error_status": "Detailed analysis for this report encountered an error: {0}. Please check logs or contact support.", # {0} is for the error message
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
                #"logged_in_as": "Logged in as: **{0}**", # {0} is username
                "logged_in_as": "Logged in as: **{username}**",
                "analysis_complete_message": "✅ Analysis for your URL is complete.",
                "analyzing_website": "Analyzing your website, please wait...",
                "found_existing_report": "Found an existing report for this URL.",
                "analysis_failed": "Failed to analyze the website. Please try again.",
                #"analysis_results_for_url": "Analysis Results for: {0}", # {0} is URL
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
                "custom_keywords_help": "Enter keywords separated by commas",
                "custom_title": "Custom Title (optional)",

                # Article Writer UI & Suggestions
                "suggested_article_tasks_title": "Suggested Article Tasks",
                "suggested_article_tasks_intro": "We found some article suggestions based on the SEO analysis. Select one to pre-fill the article options:",
                "suggestion_task_label": "Suggestion",
                "focus_keyword_label": "Focus Keyword",
                "content_length_label": "Content Length",
                "article_tone_label": "Article Tone",
                "additional_keywords_label": "Additional Keywords",
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
            },

            "tr": {
                # Existing keys ...
                 "seo_helper_prepare_for_article_writer_cta": "\n\nBu analizden {0} potansiyel makale fikri belirledim. Bunları Makale Yazarı'nda üzerinde çalışmanız için hazırlayabilirim. Bunu yapmak ister misiniz? ('evet' veya 'hayır' yazın)",
                  "seo_helper_cta_yes_article_writer_stay": "Harika! Bu makale önerilerini not aldım. Hazır olduğunuzda geliştirmeye başlamak için (yan menüden) 'Makale Yazarı' sayfasına gidebilirsiniz.",
                  "seo_helper_cta_no_article_writer": "Pekala. Fikrinizi değiştirirseniz veya başka bir konuda yardıma ihtiyacınız olursa bana bildirin!",
                  "seo_helper_cta_invalid_response": "Lütfen makale önerileri hazırlama konusundaki önceki soruya 'evet' veya 'hayır' ile yanıt verin.",
                  "seo_helper_cta_yes_no_tasks": "Tamam. Görünüşe göre hazırlanacak belirli bir görev yoktu. Yine de Makale Yazarı sayfasını ziyaret edebilirsiniz.",
                  "seo_helper_cta_yes_generic": "Tamam!",
                # NEW SEO Helper CTA (extended)
                "seo_helper_initial_cta_article_extended": "\n\n{num_tasks} potansiyel makale fikri belirledim. İlki '{first_task_title}'. Bunu Makale Yazarı için hazırlayayım mı? (Hazırlamak için 'evet', bir sonrakine geçmek için 'atla' veya bu işlemi iptal etmek için 'dur' yazın)",
                "the_first_article_generic": "ilk makale",
                "seo_helper_initial_cta_product_extended": "\n\n{num_tasks} ürün açıklaması görevi buldum. İlki '{first_task_title}' için. Bunu Ürün Yazarı için hazırlayayım mı? (Hazırlamak için 'evet', bir sonrakine geçmek için 'atla' veya bu işlemi iptal etmek için 'dur' yazın)",
                "the_first_product_generic": "ilk ürün",
                "seo_helper_cta_input_placeholder_extended": "'{task_name}' için yanıtınız (evet/atla/dur)...",
                "seo_helper_cta_resumed_chat_prompt_extended_options": "Makale görevi hazırlığına devam ediyorum. Şimdi '{task_title}' konusuna odaklandım. Hazırlayayım mı, bir sonrakine mi geçeyim, yoksa bu işlemi durdurayım mı? ('evet', 'atla' veya 'dur' yazın)",
                "seo_helper_cta_resumed_chat_prompt_product_extended_options": "Ürün görevi hazırlığına devam ediyorum. Şimdi '{task_title}' konusuna odaklandım. Hazırlayayım mı, bir sonrakine mi geçeyim, yoksa bu işlemi durdurayım mı? ('evet', 'atla' veya 'dur' yazın)",

                # Buttons
                "login_button": "Giriş",
                "logout_button": "Çıkış Yap",
                "analyze_button": "Web Sitesini Analiz Et",
                "seo_helper_button": "🚀 SEO Yardımcısı",
                "article_writer_button": "✍️ Makale Yazarı",
                "product_writer_button": "🛍️ Ürün Yazarı",
                "generate_seo_suggestions_button_text": "Öneri Yarat🔍",
                "generate_article": "Makale Oluştur",
                "generate_product_description": "Ürün Açıklaması Oluştur",
                "check_report_update_button": "🔄 Tam Site Analizi Güncellemesini Kontrol Et",
                "refresh_analysis_status": "🔄 Lütfen biraz bekleyin.../ Refresh",
                "refresh_comprehensive_report": "🔄 Analizi Yenile",
                "recheck_comprehensive_report": "🔄 Analizi Yeniden Kontrol Et", # NEW
                "go_to_login":"Lütfen Giriş Yapın.",
                "resume_article_tasks_button": "İçerik Oluşturmaya devam et: '{task_title}'⏯️  ", # NEW - SEO Helper Task Panel
                "resume_product_tasks_button": "İçerik Oluşturmaya devam et: '{task_title}'⏯️", # NEW - SEO Helper Task Panel

                # Detailed Analysis Messages
                "detailed_analysis_init_error": "Detaylı analiz işlemcisi başlatılırken hata oluştu. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_runtime_error": "Detaylı analiz işlemcisi kurulumu sırasında çalışma zamanı hatası. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_trigger_error": "Detaylı site genelinde analiz başlatılamadı. Lütfen tekrar deneyin veya destek ile iletişime geçin.",
                "detailed_analysis_error_status": "Bu rapor için detaylı analizde bir hata oluştu: {llm_analysis_error}. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_still_inprogress": "Detaylı site genelinde LLM analizi hala devam ediyor. Lütfen tekrar kontrol edin.",
                "detailed_analysis_initiated": "Detaylı site genelinde analiz başlatıldı. Bu biraz zaman alabilir. İlerlemeyi buradan takip edebilirsiniz.", # NEW
                "error_checking_report_status": "Rapor durumu kontrol edilirken hata oluştu. Lütfen tekrar deneyin.",
                "status_check_failed_error": "Bir hata nedeniyle rapor durumu kontrol edilemedi.", # NEW

                # Main UI Elements
                "main_settings_title": " Panel: '<' ^^ ",
                "home_page_label": "👋 Ana Sayfa",
                "language_select_label": "Dil / Language",
                "select_ai_model_label": "AI Modelini Seçin:",
                "model_o10": "o10 (Gemini)",
                "model_Se10": "Se10 (Mistral)",
                "view_seo_report_expander_label": "📝 SEO Raporunu Görüntüle",
                "your_website_report_label": "Rapor: {0}",
                "no_text_report_available": "Metin raporu mevcut değil.",
                "analysis_running_sidebar_info": "Analiz devam ediyor. Bazı kontroller ve gezinme bağlantıları geçici olarak devre dışı bırakıldı.",
                "show_less_report_sidebar": "Daha az göster", # NEW
                "read_more_report_sidebar": "Devamını oku", # NEW
                "auto_refresh_checkbox": "🔄 Oto-kontrol", # NEW
                "auto_refresh_help": "Tamamlanmayı otomatik olarak kontrol eder", # NEW

                # General Messages
                "welcome_message": "nevaR Web Servislerine Hoş Geldiniz!",
                "welcome_seo": "nevaR Beta'ya Hoş Geldiniz!",
                "welcome_authenticated": "Hoş geldiniz, {0}!",
                "logged_in_as": "Giriş yapıldı: **{username}**",
                "analysis_complete_message": "✅URL'niz için analiz tamamlandı.",
                "analyzing_website": "Web siteniz analiz ediliyor, lütfen bekleyin...",
                "found_existing_report": "Bu URL için mevcut bir rapor bulundu.",
                "analysis_failed": "Web sitesi analizi başarısız oldu. Lütfen tekrar deneyin.",
                "analysis_results_for_url": "Şunun için analiz sonuçları: {url}",
                "authentication_required": "Bu hizmeti kullanmak için önce giriş yapmanız gerekiyor.",
                "login_failed": "Kimlik doğrulama başarısız oldu. Lütfen API anahtarınızı kontrol edin.",
                "enter_api_key_label": "Devam etmek için lütfen API anahtarınızı girin:",
                "enter_api_key": "Devam etmek için lütfen API anahtarınızı girin:",
                "next_steps": "Sonraki Adımlar:",
                "continue_optimizing": "Sitenizi optimize etmeye devam edin veya içerik oluşturun:",
                "content_generation_tools": "İçerik Oluşturma Araçları",
                "create_optimized_content": "Analize dayalı olarak optimize edilmiş içerik oluşturmak için AI araçlarımızı kullanın:",
                "analyze_with_ai": "Veya doğrudan AI araçlarına geçin (en iyi sonuç için ön analiz gereklidir):",
                "generating_new_report": "Yeni SEO raporu oluşturuluyor...",
                "generating_new_analysis": "Mevcut rapor bulunamadı. Yeni analiz oluşturuluyor, bu birkaç dakika sürebilir...",
                "failed_to_analyze": "Üzgünüz, web sitesini analiz etmeye çalışırken bir hata oluştu. Lütfen tekrar deneyin veya destekle iletişime geçin.",
                "no_report_available_error": "Bir hata oluştu ve bu URL için rapor mevcut değil.",
                "full_site_analysis_complete": "✅ Tüm alt sayfalar dahil olmak üzere tam site analizi tamamlandı!",
                "detailed_analysis_inprogress": "ℹ️ Ana sayfa analizi tamamlandı. Tüm site sayfaları için derinlemesine analiz işleniyor.",
                "analysis_in_progress_for": "**{0}** için analiz hala devam ediyor. Lütfen bekleyin. 🔄.",
                "llm_analysis_status_unknown": "Detaylı alt sayfa analizinin durumu şu anda bilinmiyor. Sonuç bekliyorsanız analiz edin veya yenileyin.",
                "no_ai_model": "Hiçbir AI modeli API anahtarı (Gemini veya Mistral) yapılandırılmamış. Lütfen ortamınızda en az birini ayarlayın.",
                "no_ai_model_configured": "Yapılandırılmış bir AI modeli yok. Lütfen GEMINI_API_KEY veya MISTRAL_API_KEY sağlayın.",
                "no_ai_api_keys_configured": "AI API anahtarları yapılandırılmamış. Lütfen yapılandırmanızı kontrol edin.",
                "seo_report_summary_label": "SEO Rapor Özeti",
                "seo_report_label": "Analiz Raporunuz Burada",
                "text_report_not_available": "Metin rapor özeti mevcut değil.",
                "analysis_completed_no_report": "Analiz tamamlandı ancak rapor oluşturulamadı.",
                "seo_analysis_completed": "{0} için SEO Analizi tamamlandı. SEO stratejiniz için size nasıl yardımcı olabilirim?",
                "provide_url_first": "Lütfen önce analiz etmek için bir web sitesi URL'si girin.",
                "generating_article": "Makale oluşturuluyor...",
                "analyze_website_first": "Lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "analyze_website_first_chat": "Makale yazımıyla yardımcı olmadan önce lütfen SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "article_prompt": "Ne tür bir makale yazmak istersiniz?",
                "getting_started": "Başlarken",
                "begin_by_analyzing": "Aşağıya web sitenizin URL'sini girerek bir SEO analiz raporu alın.",
                "platform_description": "Bu platform, web sitenizin SEO'sunu analiz etmek, SEO önerileri oluşturmak ve optimize edilmiş içerik üretmek için araçlar sunar. Panel ağma kapama tüşü sol üst köşededir. '<' ",
                "generating_product_description": "Ürün açıklaması oluşturuluyor...",
                "welcome_product_writer_not_analyzed": "Ürün Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_product_writer_analyzed": "Ürün Yazarı sayfasına hoş geldiniz.\nAnaliz şunun için kullanılıyor: **{0}**",
                "product_description_prompt": "Ne tür bir ürün açıklaması yazmak istersiniz?",
                "analyze_website_first_chat_product": "Ürün yazımıyla yardımcı olmadan önce lütfen SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "processing_request": "İsteğiniz işleniyor🔄",
                "generating_response": "Yanıt oluşturuluyor 🔄",
                "could_not_generate_description": "Ürün açıklaması oluşturulamadı",
                "error_processing_request": "İstek işlenirken hata oluştu",
                "Processing_request": "İstek işleniyor..🔄",
                "analyzing": "Analiz ediliyor",
                "analyze_website_first_product": "Ürün açıklamalarıyla yardımcı olabilmem için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_seo_helper_analyzed": "Seo Yardımcısı Sayfasına Hoş Geldiniz.\nAnaliz şunun için kullanılıyor: {0}",
                "welcome_article_writer_not_analyzed": "Makale Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_article_writer_analyzed": "Makale Yazarı sayfasına hoş geldiniz. {0} analizine dayalı bir makale yazmanıza yardımcı olmaya hazırım.",
                "enter_url_or_question_seo_helper":" Url Gir ve Analiz Değiştir...Sayfa Seç Öneri yarat.....Sana Yardım etmek için buradayım......",
                "enter_url_placeholder":"Web sitenizin adresini girin.",
                "report_data_unavailable": "Rapor verisi mevcut değil.",
                "invalid_length_in_suggestion_warning": "Uyarı: Önerilen '{0}' uzunluğu geçersiz. Varsayılan '{1}' olarak ayarlandı.",
                "invalid_tone_in_suggestion_warning": "Uyarı: Önerilen '{0}' tonu geçersiz. Varsayılan '{1}' olarak ayarlandı.",
                "unexpected_error_refresh": "Beklenmeyen bir hata oluştu. Lütfen sayfayı yenileyin ve tekrar deneyin.",
                "fallback_ai_service": "Birincil AI servisi kullanılamıyor. Yedek olarak {0} kullanılıyor...",
                "none_value": "Yok",
                "not_available_short": "Mevcut Değil", # NEW
                "no_details_provided_short": "Belirli bir detay sağlanmadı.", # NEW
                "generic_page_welcome": "{page_name} sayfasına hoş geldiniz.", # NEW
                "report_up_to_date_toast": "Rapor güncel.", # NEW

                # SEO Helper - Task Panel (Content Generation CTA Progress)
                "content_tasks_expander_title": "📝 İçerik Üretim Görevleri İlerlemesi ↕️", # NEW
                "cta_status_paused_at": "Makale görevi hazırlığı '{title}' için duraklatıldı.", # NEW
                "cta_status_awaiting_response_for": "Makale görevi '{title}' için yanıt bekleniyor.", # NEW
                "cta_status_paused_at_product": "Ürün görevi hazırlığı '{title}' için duraklatıldı.", # NEW
                "cta_status_awaiting_response_for_product": "Ürün görevi '{title}' için yanıt bekleniyor.", # NEW
                "cta_status_awaiting_response_generic": "Önerilen görev için yanıt bekleniyor.", # NEW
                "cta_all_tasks_addressed_panel": "Bu gruptaki tüm içerik görevleri ele alındı.", # NEW
                  
                # Article Options
                "target_page_url_label": "Hedef Sayfa URL'si",
                "content_gap_label": "İçerik Boşluğu",
                # "target_audience_label": "Hedef Kitle", # Zaten Ürün Seçeneklerinde var, ortak
                "outline_preview_label": "Taslak Önizlemesi",

                "article_options_title": "Makale Seçenekleri",
                "focus_keyword": "Odak Anahtar Kelime",
                "focus_keyword_help": "Makalenizin odaklanacağı anahtar kelime",
                "content_length": "İçerik Uzunluğu",
                "content_length_short": "Kısa",
                "content_length_medium": "Orta",
                "content_length_long": "Uzun",
                "content_length_very_long": "Çok Uzun",
                "tone": "Makale Tonu",
                "tone_professional": "Profesyonel",
                "tone_casual": "Günlük",
                "tone_enthusiastic": "Hevesli",
                "tone_technical": "Teknik",
                "tone_friendly": "Dostça",
                "custom_keywords": "Ek Anahtar Kelimeler (isteğe bağlı)",
                "custom_keywords_help": "Anahtar kelimeleri virgülle ayırarak girin",
                "custom_title": "Özel Başlık (isteğe bağlı)",

                # Article Writer UI & Suggestions
                "suggested_article_tasks_title": "Önerilen Makale Görevleri",
                "suggested_article_tasks_intro": "SEO analizine dayanarak bazı makale önerileri bulduk. Makale seçeneklerini önceden doldurmak için birini seçin:",
                "suggestion_task_label": "Öneri",
                "focus_keyword_label": "Odak Anahtar Kelime",
                "content_length_label": "İçerik Uzunluğu",
                "article_tone_label": "Makale Tonu",
                "additional_keywords_label": "Ek Anahtar Kelimeler",
                "suggested_title_label": "Önerilen Başlık",
                "use_this_suggestion_button": "Bu Öneriyi Kullan",
                "suggestion_applied_message": "Öneri uygulandı! Kenar çubuğundaki Makale Seçeneklerini kontrol edin.",
                "no_article_suggestions_found": "Mevcut raporun otomatik öneri verilerinde belirli bir makale önerisi bulunamadı veya veri formatı tanınmıyor.",
                "focus_keyword_required_warning": "Makale oluşturmak için Odak Anahtar Kelime gereklidir. Lütfen kenar çubuğunda doldurun.",
                "analyze_site_for_article_options": "Makale seçeneklerini görmek için SEO Yardımcısı'nda bir siteyi analiz edin.", # NEW
                "article_writer_activated_by_seo_helper": "Makale Yazarı, SEO Yardımcısı tarafından şunun için etkinleştirildi: **{task_title}**. Makale oluşturuluyor...", # NEW
                "article_writer_options_prefilled_by_seo_helper": "Makale Yazarı seçenekleri SEO Yardımcısı tarafından şunun için önceden dolduruldu: **{task_title}**. Gözden geçirin ve 'Makale Oluştur'a tıklayın.", # NEW
                "generated_article_from_seo_helper_title": "Oluşturulan Makale (SEO Yardımcısından): {title}", # NEW
                "focus_keyword_required_for_auto_gen": "Bu öneride odak anahtar kelime eksik. Oluşturmak için lütfen kenar çubuğunda bir tane sağlayın.", # NEW
                "article_generation_prerequisites_warning": "Makale oluşturulamıyor. Bir sitenin analiz edildiğinden ve konunun kenar çubuğunda sağlandığından emin olun.", # NEW
                "could_not_generate_article": "Üzgünüm, şu anda makaleyi oluşturamadım.", # NEW

                # Product Options & Details Formatting
                "product_options_title": "Ürün Açıklaması Seçenekleri",
                "product_name": "Ürün Adı",
                "product_name_placeholder": "Ürünün adını girin",
                "product_details": "Ürün Detayları",
                "product_details_placeholder": "Ürün özelliklerini, faydalarını, spesifikasyonlarını, hedef kitlesini vb. girin",
                "product_tone": "Ton",
                "product_length": "Açıklama Uzunluğu",
                "product_length_short": "Kısa (~100-150 kelime)",
                "product_length_medium": "Orta (~150-250 kelime)",
                "product_length_long": "Uzun (~250-350 kelime)",
                "features_label": "Özellikler",
                "benefits_label": "Faydalar",
                "target_audience_label": "Hedef Kitle",
                "competitive_advantage_label": "Rekabet Avantajı",
                "suggested_seo_keywords_label": "Önerilen SEO Anahtar Kelimeleri",

                # Product Writer UI & Suggestions
                "suggested_product_tasks_title": "Önerilen Ürün Görevleri",
                "suggested_product_tasks_intro": "SEO analizine dayanarak bazı ürün açıklaması önerileri bulduk. Ürün seçeneklerini önceden doldurmak için birini seçin:",
                "untitled_suggestion": "Başlıksız Öneri",
                "product_name_label": "Ürün Adı",
                "product_description_length_label": "Açıklama Uzunluğu",
                "tone_label": "Ton",
                "seo_keywords_label": "SEO Anahtar Kelimeleri",
                "product_details_summary_label": "Ürün Detayları Özeti",
                "no_product_suggestions_found": "Mevcut raporda belirli bir ürün önerisi bulunamadı veya veri formatı tanınmıyor.",
                "product_name_required_warning": "Ürün Adı gereklidir. Lütfen kenar çubuğundaki seçeneklerden doldurun.",
                "product_details_required_warning": "Ürün Detayları gereklidir. Lütfen kenar çubuğundaki seçeneklerden doldurun.",

                # SEO Suggestions Specific
                "seo_suggestions_for_pages_label": "Seo Önerileri Sayfaları:",
                "select_pages_for_detailed_suggestions": "Sayfa Seç Yada genel öneri için boş bırak✖️ ",
                "multiselect_seo_help_text_v3": "Odaklanmış öneriler için belirli sayfaları seçin. Boş bırakılırsa, genel öneriler metin raporundan oluşturulur. 'main_page' ana sayfa analizini içerir.",
                "text_report_suggestions_only": "Detaylı sayfa analizi mevcut değil. Genel öneriler metin raporundan oluşturulacaktır.",
                "error_no_text_report_available": "Hata: Öneriler için metin raporu mevcut değil.",
                "analyze_url_first_for_suggestions": "SEO önerilerini etkinleştirmek için bir URL analiz edin.",
                "using_text_report_for_suggestions": "Belirli bir sayfa seçilmedi. Metin raporuna göre genel öneriler oluşturuluyor.",
                "using_selected_pages_for_suggestions": "Seçili sayfalar için öneriler oluşturuluyor: {0}",
                "error_selected_pages_no_valid_data": "Hata: Seçili sayfaların hiçbirinde öneri için kullanılabilir veri bulunmuyor.",
                "loading_existing_suggestions": "Mevcut SEO önerileri veritabanından yükleniyor...",
                "auto_generating_initial_suggestions": "Analiz tamamlandı. Metin raporuna göre ilk öneriler otomatik olarak oluşturuluyor...",
                "auto_processing_initial_suggestions": "İlk öneriler otomatik olarak işleniyor...",
                "no_pages_in_analysis_data": "Analiz verilerinde uygun sayfa bulunamadı.",
                "error_all_ai_services_failed": "Tüm AI servisleri öneri oluşturmada başarısız oldu. Lütfen daha sonra tekrar deneyin.",
                "error_auto_suggestions_failed": "Otomatik öneriler oluşturulamadı. Yan menüyü kullanarak manuel öneriler talep edebilirsiniz.",
                "error_generating_suggestions": "Öneriler oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
            }
        }


    def get_text(self, key, lang="en", *args, fallback=None, **kwargs): # Added **kwargs
        """
        Get translated text for the given key in the specified language

        Parameters:
            key (str): The translation key to look up
            lang (str): The language code (e.g., "en", "tr")
            *args: Positional arguments to format into the translated string
            fallback (str, optional): Fallback text if the key is not found
            **kwargs: Keyword arguments to format into the translated string

        Returns:
            str: Translated text
        """
        if lang not in self.translations:
            lang = "en"  # Default to English if language not supported

        translation_template = self.translations[lang].get(key)

        if translation_template is None and lang != "en":
            translation_template = self.translations["en"].get(key)
        
        if translation_template is None:
            # Determine the string to format (fallback or key itself)
            text_to_format = fallback if fallback is not None else key
            
            if isinstance(text_to_format, str):
                try:
                    if args and kwargs:
                        return text_to_format.format(*args, **kwargs)
                    elif args:
                        return text_to_format.format(*args)
                    elif kwargs:
                        return text_to_format.format(**kwargs)
                    else:
                        return text_to_format # No arguments to format with
                except (KeyError, IndexError, TypeError) as e:
                    logging.warning(
                        f"Failed to format fallback/key string for key '{key}'. "
                        f"String: '{text_to_format}', Args: {args}, Kwargs: {kwargs}. Error: {e}"
                    )
                    return text_to_format # Return unformatted string on error
            return text_to_format # If not a string, return as is

        # Format the found translation template
        if isinstance(translation_template, str):
            try:
                if args and kwargs:
                    return translation_template.format(*args, **kwargs)
                elif args:
                    return translation_template.format(*args)
                elif kwargs:
                    return translation_template.format(**kwargs)
                return translation_template # No arguments to format with
            except (KeyError, IndexError, TypeError) as e:
                logging.warning(
                    f"Failed to format translation for key '{key}'. "
                    f"Template: '{translation_template}', Args: {args}, Kwargs: {kwargs}. Error: {e}"
                )
                return translation_template # Return unformatted template on error
        return translation_template # If not a string, return as is

    def get_available_languages(self):
        """Return a list of available languages"""
        return list(self.translations.keys())


# Create a singleton instance
language_manager = LanguageSupport()