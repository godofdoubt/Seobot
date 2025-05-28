# SeoTree/utils/language_support.py
import logging # Added import

class LanguageSupport:
    """Class to manage multi-language support in the application"""

    def __init__(self):
        self.translations = {
            "en": {
                 "seo_helper_prepare_for_article_writer_cta": "\n\nI've identified {0} potential article ideas from this analysis. I can prepare these for you to work on in the Article Writer. Would you like to do that? (Type 'yes' or 'no')",
                  "seo_helper_cta_yes_article_writer_stay": "Great! I've noted these article suggestions. You can head over to the 'Article Writer' page (from the sidebar) to start developing them when you're ready.",
                  "seo_helper_cta_no_article_writer": "Alright. Let me know if you change your mind or need help with anything else!",
                  "seo_helper_cta_invalid_response": "Please respond with 'yes' or 'no' to the previous question about preparing article suggestions.",
                  "seo_helper_cta_yes_no_tasks": "Okay. It seems there were no specific tasks to prepare. You can still visit the Article Writer page.",
                  "seo_helper_cta_yes_generic": "Okay!",
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
                "go_to_login":"ℹ️Please Login First",

                # Detailed Analysis Messages
                "detailed_analysis_init_error": "Error initializing detailed analysis processor. Please check logs or contact support.",
                "detailed_analysis_runtime_error": "Runtime error during detailed analysis processor setup. Please check logs or contact support.",
                "detailed_analysis_trigger_error": "Failed to start the detailed site-wide analysis. Please try again or contact support.",
                "detailed_analysis_error_status": "Detailed analysis for this report encountered an error: {0}. Please check logs or contact support.", # {0} is for the error message
                "detailed_analysis_still_inprogress": "Detailed site-wide LLM analysis is still in progress. Please check back again.",
                "error_checking_report_status": "Error checking report status. Please try again.",

                # Main UI Elements
                "main_settings_title": " Panel: '<' ^^ ",
                "home_page_label": " 👋 Home",
                "language_select_label": "Language / Dil",
                "select_ai_model_label": "Select AI Model:",
                "model_o10": "o10 (Gemini)",
                "model_Se10": "Se10 (Mistral)",
                "view_seo_report_expander_label": "View SEO Report",
                "your_website_report_label": "Report for: {0}",
                "no_text_report_available": "No text report available.",
                "analysis_running_sidebar_info": "Analysis is in progress. Some controls and navigation links are temporarily disabled.",

                # General Messages
                "welcome_message": "Welcome nevaR Web Services!",
                "welcome_seo": "Welcome nevaR Web Services Beta!",
                "welcome_authenticated": "Welcome, {0}!", # {0} is username
                "logged_in_as": "Logged in as: **{0}**", # {0} is username
                "analysis_complete_message": "✅ Analysis for your URL is complete.",
                "analyzing_website": "Analyzing your website, please wait...",
                "found_existing_report": "Found an existing report for this URL.",
                "analysis_failed": "Failed to analyze the website. Please try again.",
                "analysis_results_for_url": "Analysis Results for: {0}", # {0} is URL
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
                "no_ai_api_keys_configured": "No AI API keys configured. Please check your configuration.", # NEW
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
                "error_processing_request": "Error processing request🔄", # As per current usage, no {0} for error detail
                "Processing_request": "Processing request", # Kept distinct due to capitalization, if used.
                "analyzing": "Analyzing",
                "analyze_website_first_product": "Please analyze a website first in the SEO Helper page before I can help with product descriptions.",
                "welcome_seo_helper_analyzed": "Welcome to the Seo Helper Page.\nUsing analysis for: {0}", # {0} is URL
                "welcome_article_writer_not_analyzed": "Welcome to the Article Writer page. Please analyze a website in the SEO Helper page first to proceed.",
                "welcome_article_writer_analyzed": "Welcome to the Article Writer page. Ready to help you write an article based on the analysis of {0}.", # {0} is URL
                "enter_url_or_question_seo_helper":"Enter Url.....Select Page and generate srategy....I am here to help...",
                "enter_url_placeholder":"Enter Url.",
                "report_data_unavailable": "Report data is not available.",
                "invalid_length_in_suggestion_warning": "Warning: The suggested length '{0}' is invalid. Defaulting to '{1}'.",
                "invalid_tone_in_suggestion_warning": "Warning: The suggested tone '{0}' is invalid. Defaulting to '{1}'.",
                "unexpected_error_refresh": "An unexpected error occurred. Please refresh the page and try again.", # NEW
                "fallback_ai_service": "Primary AI service unavailable. Using {0} as fallback...", # NEW
                "none_value": "None", # NEW - General utility

                # Article Options
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
                "suggestion_task_label": "Suggestion", # Used in expander label with index
                "focus_keyword_label": "Focus Keyword", # Label within suggestion expander
                "content_length_label": "Content Length", # Label within suggestion expander
                "article_tone_label": "Article Tone", # Label within suggestion expander
                "additional_keywords_label": "Additional Keywords", # Label within suggestion expander
                "suggested_title_label": "Suggested Title", # Label within suggestion expander
                "use_this_suggestion_button": "Use This Suggestion",
                "suggestion_applied_message": "Suggestion applied! Check the Article Options in the sidebar.",
                "no_article_suggestions_found": "No specific article suggestions found in the current report's auto_suggestions data, or the data format is unrecognized.",
                "focus_keyword_required_warning": "Focus Keyword is required to generate an article. Please fill it in the sidebar.",

                # Product Options & Details Formatting
                "product_options_title": "Product Description Options",
                "product_name": "Product Name", # For input field
                "product_name_placeholder": "Enter the name of the product",
                "product_details": "Product Details", # For text area
                "product_details_placeholder": "Enter product features, benefits, specifications, target audience, etc.",
                "product_tone": "Tone", # For selectbox label
                "product_length": "Description Length", # For selectbox label
                "product_length_short": "Short (~100-150 words)",
                "product_length_medium": "Medium (~150-250 words)",
                "product_length_long": "Long (~250-350 words)",
                "features_label": "Features", # NEW - for formatting product details
                "benefits_label": "Benefits", # NEW - for formatting product details
                "target_audience_label": "Target Audience", # NEW - for formatting product details
                "competitive_advantage_label": "Competitive Advantage", # NEW - for formatting product details
                "suggested_seo_keywords_label": "Suggested SEO Keywords", # NEW - for formatting product details (distinct from seo_keywords_label for suggestions)

                # Product Writer UI & Suggestions (NEW SECTION)
                "suggested_product_tasks_title": "Suggested Product Tasks", # NEW
                "suggested_product_tasks_intro": "We found some product description suggestions based on the SEO analysis. Select one to pre-fill the product options:", # NEW
                "untitled_suggestion": "Untitled Suggestion", # NEW
                "product_name_label": "Product Name", # NEW - Label for product name within a suggestion expander
                "product_description_length_label": "Description Length", # NEW - Label for length within a suggestion expander
                "tone_label": "Tone", # NEW - Label for tone within a suggestion expander
                "seo_keywords_label": "SEO Keywords", # NEW - Label for keywords within a suggestion expander
                "product_details_summary_label": "Product Details Summary", # NEW
                "no_product_suggestions_found": "No specific product suggestions found in the current report, or the data format is unrecognized.", # NEW
                "product_name_required_warning": "Product Name is required. Please fill it in the sidebar options.", # NEW
                "product_details_required_warning": "Product Details are required. Please fill them in the sidebar options.", # NEW


                # SEO Suggestions Specific
                "seo_suggestions_for_pages_label": "SEO Suggestions for Pages:",
                "select_pages_for_detailed_suggestions": "Select pages or leave empty for general report suggestions✖️ ",
                "multiselect_seo_help_text_v3": "Select specific pages for focused suggestions. If empty, general suggestions will be generated from the text report. 'main_page' contains the homepage analysis.",
                "text_report_suggestions_only": "Detailed page analysis not available. General suggestions will be generated from the text report.",
                "error_no_text_report_available": "Error: No text report available for suggestions.",
                "analyze_url_first_for_suggestions": "Analyze a URL to enable SEO suggestions.",
                "using_text_report_for_suggestions": "No specific pages selected. Generating general suggestions based on the text report.",
                "using_selected_pages_for_suggestions": "Generating suggestions for selected pages: {0}", # {0} is for page list
                "error_selected_pages_no_valid_data": "Error: None of the selected pages have data available for suggestions.",
                "loading_existing_suggestions": "Loading existing SEO suggestions from database...", # NEW
                "auto_generating_initial_suggestions": "Analysis complete. Automatically generating initial suggestions based on the text report...", # NEW
                "auto_processing_initial_suggestions": "Auto-generating initial suggestions...", # NEW
                "no_pages_in_analysis_data": "No pages available in the analysis data.", # NEW
                "error_all_ai_services_failed": "All AI services failed to generate suggestions. Please try again later.", # NEW
                "error_auto_suggestions_failed": "Unable to generate automatic suggestions. You can still request manual suggestions using the sidebar.", # NEW
                "error_generating_suggestions": "An error occurred while generating suggestions. Please try again.", # NEW
            },

            "tr": {
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
                "go_to_login":"Lütfen Giriş Yapın.",

                # Detailed Analysis Messages
                "detailed_analysis_init_error": "Detaylı analiz işlemcisi başlatılırken hata oluştu. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_runtime_error": "Detaylı analiz işlemcisi kurulumu sırasında çalışma zamanı hatası. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_trigger_error": "Detaylı site genelinde analiz başlatılamadı. Lütfen tekrar deneyin veya destek ile iletişime geçin.",
                "detailed_analysis_error_status": "Bu rapor için detaylı analizde bir hata oluştu: {0}. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_still_inprogress": "Detaylı site genelinde LLM analizi hala devam ediyor. Lütfen tekrar kontrol edin.",
                "error_checking_report_status": "Rapor durumu kontrol edilirken hata oluştu. Lütfen tekrar deneyin.",

                # Main UI Elements
                "main_settings_title": " Panel: '<' ^^ ",
                "home_page_label": "👋 Ana Sayfa",
                "language_select_label": "Dil / Language",
                "select_ai_model_label": "AI Modelini Seçin:",
                "model_o10": "o10 (Gemini)",
                "model_Se10": "Se10 (Mistral)",
                "view_seo_report_expander_label": "SEO Raporunu Görüntüle",
                "your_website_report_label": "Rapor: {0}",
                "no_text_report_available": "Metin raporu mevcut değil.",
                "analysis_running_sidebar_info": "Analiz devam ediyor. Bazı kontroller ve gezinme bağlantıları geçici olarak devre dışı bırakıldı.",

                # General Messages
                "welcome_message": "nevaR Web Servislerine Hoş Geldiniz!",
                "welcome_seo": "nevaR Beta'ya Hoş Geldiniz!",
                "welcome_authenticated": "Hoş geldiniz, {0}!", # {0} is username
                "logged_in_as": "Giriş yapıldı: **{0}**", # {0} is username
                "analysis_complete_message": "✅URL'niz için analiz tamamlandı.",
                "analyzing_website": "Web siteniz analiz ediliyor, lütfen bekleyin...",
                "found_existing_report": "Bu URL için mevcut bir rapor bulundu.",
                "analysis_failed": "Web sitesi analizi başarısız oldu. Lütfen tekrar deneyin.",
                "analysis_results_for_url": "Şunun için analiz sonuçları: {0}", # {0} is URL
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
                "analysis_in_progress_for": "**{0}** için analiz hala devam ediyor. Lütfen bekleyin. 🔄.", # MODIFIED, {0} is for URL
                "llm_analysis_status_unknown": "Detaylı alt sayfa analizinin durumu şu anda bilinmiyor. Sonuç bekliyorsanız analiz edin veya yenileyin.",
                "no_ai_model": "Hiçbir AI modeli API anahtarı (Gemini veya Mistral) yapılandırılmamış. Lütfen ortamınızda en az birini ayarlayın.",
                "no_ai_model_configured": "Yapılandırılmış bir AI modeli yok. Lütfen GEMINI_API_KEY veya MISTRAL_API_KEY sağlayın.",
                "no_ai_api_keys_configured": "AI API anahtarları yapılandırılmamış. Lütfen yapılandırmanızı kontrol edin.", # NEW
                "seo_report_summary_label": "SEO Rapor Özeti",
                "seo_report_label": "Analiz Raporunuz Burada",
                "text_report_not_available": "Metin rapor özeti mevcut değil.",
                "analysis_completed_no_report": "Analiz tamamlandı ancak rapor oluşturulamadı.",
                "seo_analysis_completed": "{0} için SEO Analizi tamamlandı. SEO stratejiniz için size nasıl yardımcı olabilirim?", # {0} is URL
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
                "welcome_product_writer_analyzed": "Ürün Yazarı sayfasına hoş geldiniz.\nAnaliz şunun için kullanılıyor: **{0}**", # {0} is URL
                "product_description_prompt": "Ne tür bir ürün açıklaması yazmak istersiniz?",
                "analyze_website_first_chat_product": "Ürün yazımıyla yardımcı olmadan önce lütfen SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "processing_request": "İsteğiniz işleniyor🔄",
                "generating_response": "Yanıt oluşturuluyor 🔄",
                "could_not_generate_description": "Ürün açıklaması oluşturulamadı",
                "error_processing_request": "İstek işlenirken hata oluştu", # As per current usage, no {0} for error detail
                "Processing_request": "İstek işleniyor..🔄", # Kept distinct due to capitalization, if used.
                "analyzing": "Analiz ediliyor",
                "analyze_website_first_product": "Ürün açıklamalarıyla yardımcı olabilmem için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_seo_helper_analyzed": "Seo Yardımcısı Sayfasına Hoş Geldiniz.\nAnaliz şunun için kullanılıyor: {0}", # {0} is URL
                "welcome_article_writer_not_analyzed": "Makale Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_article_writer_analyzed": "Makale Yazarı sayfasına hoş geldiniz. {0} analizine dayalı bir makale yazmanıza yardımcı olmaya hazırım.", # {0} is URL
                "enter_url_or_question_seo_helper":" Url Gir ve Analiz Değiştir...Sayfa Seç Öneri yarat.....Sana Yardım etmek için buradayım......",
                "enter_url_placeholder":"Web sitenizin adresini girin.",
                "report_data_unavailable": "Rapor verisi mevcut değil.",
                "invalid_length_in_suggestion_warning": "Uyarı: Önerilen '{0}' uzunluğu geçersiz. Varsayılan '{1}' olarak ayarlandı.",
                "invalid_tone_in_suggestion_warning": "Uyarı: Önerilen '{0}' tonu geçersiz. Varsayılan '{1}' olarak ayarlandı.",
                "unexpected_error_refresh": "Beklenmeyen bir hata oluştu. Lütfen sayfayı yenileyin ve tekrar deneyin.", # NEW
                "fallback_ai_service": "Birincil AI servisi kullanılamıyor. Yedek olarak {0} kullanılıyor...", # NEW
                "none_value": "Yok", # NEW - General utility

                # Article Options
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

                # Article Writer UI & Suggestions / Makale Yazarı Arayüzü ve Önerileri
                "suggested_article_tasks_title": "Önerilen Makale Görevleri",
                "suggested_article_tasks_intro": "SEO analizine dayanarak bazı makale önerileri bulduk. Makale seçeneklerini önceden doldurmak için birini seçin:",
                "suggestion_task_label": "Öneri", # İndeks ile genişletici etiketinde kullanılır
                "focus_keyword_label": "Odak Anahtar Kelime", # Öneri genişleticisi içindeki etiket
                "content_length_label": "İçerik Uzunluğu", # Öneri genişleticisi içindeki etiket
                "article_tone_label": "Makale Tonu", # Öneri genişleticisi içindeki etiket
                "additional_keywords_label": "Ek Anahtar Kelimeler", # Öneri genişleticisi içindeki etiket
                "suggested_title_label": "Önerilen Başlık", # Öneri genişleticisi içindeki etiket
                "use_this_suggestion_button": "Bu Öneriyi Kullan",
                "suggestion_applied_message": "Öneri uygulandı! Kenar çubuğundaki Makale Seçeneklerini kontrol edin.",
                "no_article_suggestions_found": "Mevcut raporun otomatik öneri verilerinde belirli bir makale önerisi bulunamadı veya veri formatı tanınmıyor.",
                "focus_keyword_required_warning": "Makale oluşturmak için Odak Anahtar Kelime gereklidir. Lütfen kenar çubuğunda doldurun.",

                # Product Options & Details Formatting
                "product_options_title": "Ürün Açıklaması Seçenekleri",
                "product_name": "Ürün Adı", # Giriş alanı için
                "product_name_placeholder": "Ürünün adını girin",
                "product_details": "Ürün Detayları", # Metin alanı için
                "product_details_placeholder": "Ürün özelliklerini, faydalarını, spesifikasyonlarını, hedef kitlesini vb. girin",
                "product_tone": "Ton", # Seçim kutusu etiketi için
                "product_length": "Açıklama Uzunluğu", # Seçim kutusu etiketi için
                "product_length_short": "Kısa (~100-150 kelime)",
                "product_length_medium": "Orta (~150-250 kelime)",
                "product_length_long": "Uzun (~250-350 kelime)",
                "features_label": "Özellikler", # YENİ - ürün detaylarını formatlamak için
                "benefits_label": "Faydalar", # YENİ - ürün detaylarını formatlamak için
                "target_audience_label": "Hedef Kitle", # YENİ - ürün detaylarını formatlamak için
                "competitive_advantage_label": "Rekabet Avantajı", # YENİ - ürün detaylarını formatlamak için
                "suggested_seo_keywords_label": "Önerilen SEO Anahtar Kelimeleri", # YENİ - ürün detaylarını formatlamak için

                # Product Writer UI & Suggestions (YENİ BÖLÜM)
                "suggested_product_tasks_title": "Önerilen Ürün Görevleri", # YENİ
                "suggested_product_tasks_intro": "SEO analizine dayanarak bazı ürün açıklaması önerileri bulduk. Ürün seçeneklerini önceden doldurmak için birini seçin:", # YENİ
                "untitled_suggestion": "Başlıksız Öneri", # YENİ
                "product_name_label": "Ürün Adı", # YENİ - Öneri genişleticisi içindeki ürün adı etiketi
                "product_description_length_label": "Açıklama Uzunluğu", # YENİ - Öneri genişleticisi içindeki uzunluk etiketi
                "tone_label": "Ton", # YENİ - Öneri genişleticisi içindeki ton etiketi
                "seo_keywords_label": "SEO Anahtar Kelimeleri", # YENİ - Öneri genişleticisi içindeki anahtar kelimeler etiketi
                "product_details_summary_label": "Ürün Detayları Özeti", # YENİ
                "no_product_suggestions_found": "Mevcut raporda belirli bir ürün önerisi bulunamadı veya veri formatı tanınmıyor.", # YENİ
                "product_name_required_warning": "Ürün Adı gereklidir. Lütfen kenar çubuğundaki seçeneklerden doldurun.", # YENİ
                "product_details_required_warning": "Ürün Detayları gereklidir. Lütfen kenar çubuğundaki seçeneklerden doldurun.", # YENİ

                # SEO Suggestions Specific
                "seo_suggestions_for_pages_label": "Seo Önerileri Sayfaları:",
                "select_pages_for_detailed_suggestions": "Sayfa Seç Yada genel öneri için boş bırak✖️ ",
                "multiselect_seo_help_text_v3": "Odaklanmış öneriler için belirli sayfaları seçin. Boş bırakılırsa, genel öneriler metin raporundan oluşturulur. 'main_page' ana sayfa analizini içerir.",
                "text_report_suggestions_only": "Detaylı sayfa analizi mevcut değil. Genel öneriler metin raporundan oluşturulacaktır.",
                "error_no_text_report_available": "Hata: Öneriler için metin raporu mevcut değil.",
                "analyze_url_first_for_suggestions": "SEO önerilerini etkinleştirmek için bir URL analiz edin.",
                "using_text_report_for_suggestions": "Belirli bir sayfa seçilmedi. Metin raporuna göre genel öneriler oluşturuluyor.",
                "using_selected_pages_for_suggestions": "Seçili sayfalar için öneriler oluşturuluyor: {0}", # {0} is for page list
                "error_selected_pages_no_valid_data": "Hata: Seçili sayfaların hiçbirinde öneri için kullanılabilir veri bulunmuyor.",
                "loading_existing_suggestions": "Mevcut SEO önerileri veritabanından yükleniyor...", # NEW
                "auto_generating_initial_suggestions": "Analiz tamamlandı. Metin raporuna göre ilk öneriler otomatik olarak oluşturuluyor...", # NEW
                "auto_processing_initial_suggestions": "İlk öneriler otomatik olarak işleniyor...", # NEW
                "no_pages_in_analysis_data": "Analiz verilerinde uygun sayfa bulunamadı.", # NEW
                "error_all_ai_services_failed": "Tüm AI servisleri öneri oluşturmada başarısız oldu. Lütfen daha sonra tekrar deneyin.", # NEW
                "error_auto_suggestions_failed": "Otomatik öneriler oluşturulamadı. Yan menüyü kullanarak manuel öneriler talep edebilirsiniz.", # NEW
                "error_generating_suggestions": "Öneriler oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.", # NEW
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