# SeoTree/utils/language_support.py

class LanguageSupport:
    """Class to manage multi-language support in the application"""

    def __init__(self):
        self.translations = {
            "en": {
                # Buttons
                "login_button": "Login",
                "logout_button": "Logout",
                "analyze_button": "Analyze Website",
                "seo_helper_button": "🚀 SEO Helper",
                "article_writer_button": "✍️ Article Writer",
                "product_writer_button": "🛍️ Product Writer",
                "generate_seo_suggestions": "Generate SEO Suggestions",
                "generate_seo_suggestions_button_text": "Generate Suggestions🔍", 
                 "generate_article": "Generate Article",

                "generate_product_description": "Generate Product Description",
                "check_report_update_button": "🔄 Check for Full Report / Refresh",
                "refresh_analysis_status": "🔄 Just a sec.../ Refresh",
                "refresh_comprehensive_report": "🔄 Rehresh Comprehensive Report",
                "go_to_login":"ℹ️Please Login First",
                # newly added
                "detailed_analysis_init_error": "Error initializing detailed analysis processor. Please check logs or contact support.",
                "detailed_analysis_runtime_error": "Runtime error during detailed analysis processor setup. Please check logs or contact support.",
                "detailed_analysis_trigger_error": "Failed to start the detailed site-wide analysis. Please try again or contact support.",
                "detailed_analysis_error_status": "Detailed analysis for this report encountered an error: {0}. Please check logs or contact support.", # {0} is for the error message
                "full_site_analysis_complete": "Full site-wide LLM analysis is complete!",
                "detailed_analysis_inprogress": "Detailed site-wide LLM analysis is in progress. You can check the status later.",
                "detailed_analysis_still_inprogress": "Detailed site-wide LLM analysis is still in progress. Please check back again.",
                "check_report_update_button": "🔄 Check for Full Site Analysis Update",
                "error_checking_report_status": "Error checking report status. Please try again.",
                
                "main_settings_title": " Panel: Open/Close '<' ^^ ",
                "home_page_label": " 👋 Home",
                "language_select_label": "Language / Dil",
                 "select_ai_model_label": "Select AI Model:",
                 "model_o10": "o10 (Gemini)",
                 "model_Se10": "Se10 (Mistral)",
                 "view_seo_report_expander_label": "View SEO Report",
                 "your_website_report_label": "Report for: {0}",
                 "no_text_report_available": "No text report available.",
                 "analysis_running_sidebar_info": "Analysis is in progress. Some controls and navigation links are temporarily disabled.",
                 "logout_button": "Logout" ,

                # Messages
                "welcome_message": "Welcome nevaR Web Services!",
                "welcome_seo": "Welcome nevaR Web Services Beta!",
                "welcome_authenticated": "Welcome, {0}!",
                "logged_in_as": "Logged in as: **{0}**",
                "analysis_complete_message": "✅ Analysis for your URL is complete.",
                "analyzing_website": "Analyzing your website, please wait...",
                "found_existing_report": "Found an existing report for this URL.",
                "analysis_failed": "Failed to analyze the website. Please try again.",
                "analysis_results_for_url": "Analysis Results for: {0}",
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
                "detailed_analysis_still_inprogress": " Detailed analysis still in progress please wait. 🔄.",
                "analysis_in_progress_for": " Analysis still in progress please wait. 🔄.",
                 
                "llm_analysis_status_unknown": "Status of detailed sub-page analysis is currently unknown. Analyze or refresh if expecting results.",
                "no_ai_model": "No AI model API key (Gemini or Mistral) is configured. Please set at least one in your environment.",
                "no_ai_model_configured": "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY.",
                "seo_report_summary_label": "SEO Report Summary",
                "seo_report_label": "Your Analysis Report is Here",
                "text_report_not_available": "Text report summary is not available.",
                "analysis_completed_no_report": "Analysis completed, but no report was generated.",
                "seo_analysis_completed": "SEO Analysis for {0} completed. How can I help you with your SEO strategy?",
                "provide_url_first": "Please provide a website URL first so I can analyze it.",
                "generating_article": "Generating article...",
                "analyze_website_first": "Please analyze a website first in the SEO Helper page.",
                "analyze_website_first_chat": "Please analyze a website first in the SEO Helper page before I can help with article writing.",
                "article_prompt": "What kind of article would you like to write?",
                "getting_started": "Getting Started",
                "begin_by_analyzing": "Begin by entering your website URL below to get an SEO analysis report.",
                "platform_description": "This platform provides tools to analyze your website's SEO, generate SEO suggestions, and create optimized content. Side bar panel open/close from the top left corner. '<'",
                "need_to_login": "You need to log in first to use this service.",
                "login_required": "You need to log in first to use this service.",
                "generating_product_description": "Generating product description...",
                "welcome_product_writer_not_analyzed": "Welcome to the Product Writer page. Please analyze a website in the SEO Helper page first to proceed.",
                "welcome_product_writer_analyzed": "Welcome to the Product Writer page.\nUsing analysis for: **{0}**",
                "product_description_prompt": "What kind of product description would you like to write?",
                "analyze_website_first_chat_product": "Please analyze a website first in the SEO Helper page before I can help with product writing.",
                "processing_question": "Processing your question 🔄",
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

                # Product Options
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

    

                "seo_suggestions_for_pages_label": "SEO Suggestions for Pages:",
                "select_pages_for_seo_suggestions": "Select pages(s)/delete 🔸 ",
                
            },

            "tr": {

                "select_pages_for_seo_suggestions": " Sayfa(lar) Seç/Sil: 🔸 ",
                # newly added 1.1
                "detailed_analysis_init_error": "Detaylı analiz işlemcisi başlatılırken hata oluştu. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_runtime_error": "Detaylı analiz işlemcisi kurulumu sırasında çalışma zamanı hatası. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "detailed_analysis_trigger_error": "Detaylı site genelinde analiz başlatılamadı. Lütfen tekrar deneyin veya destek ile iletişime geçin.",
                "detailed_analysis_error_status": "Bu rapor için detaylı analizde bir hata oluştu: {0}. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
                "full_site_analysis_complete": "Tam site genelinde LLM analizi tamamlandı!",
                "detailed_analysis_inprogress": "Detaylı site genelinde LLM analizi devam ediyor. Durumu daha sonra kontrol edebilirsiniz.",
                "detailed_analysis_still_inprogress": "Detaylı site genelinde LLM analizi hala devam ediyor. Lütfen tekrar kontrol edin.",
                "check_report_update_button": "🔄 Tam Site Analizi Güncellemesini Kontrol Et",
                "refresh_comprehensive_report": "🔄  Analizi Yenile",
                "refresh_analysis_status": "🔄 Lütfen biraz bekleyin.../ Refresh",
                "error_checking_report_status": "Rapor durumu kontrol edilirken hata oluştu. Lütfen tekrar deneyin.",

                # newly added 1.2
                "main_settings_title": " Panel: Aç/Kapa'<' ^^ ",
                "home_page_label": "👋 Ana Sayfa",
                "language_select_label": "Dil / Language",
                "select_ai_model_label": "AI Modelini Seçin:",
                "model_o10": "o10 (Gemini)",
                "model_Se10": "Se10 (Mistral)",
                "view_seo_report_expander_label": "SEO Raporunu Görüntüle",
                "your_website_report_label": "Rapor: {0}",
                "no_text_report_available": "Metin raporu mevcut değil.",
                "analysis_running_sidebar_info": "Analiz devam ediyor. Bazı kontroller ve gezinme bağlantıları geçici olarak devre dışı bırakıldı.",
                "logout_button": "Çıkış Yap",
  
                
                # Buttons
                "login_button": "Giriş",
                "logout_button": "Çıkış",
                "analyze_button": "Web Sitesini Analiz Et",
                "seo_helper_button": "🚀 SEO Yardımcısı",
                "article_writer_button": "✍️ Makale Yazarı",
                "product_writer_button": "🛍️ Ürün Yazarı",
                "generate_seo_suggestions": "SEO Analizimi Oluştur",
                "generate_article": "Makale Oluştur",
                "generate_product_description": "Ürün Açıklaması Oluştur",
                "check_report_update_button": "🔄 Tam Raporu Kontrol Et / Yenile",
                "go_to_login":"Lütfen Giriş Yapın.",
                "generate_seo_suggestions_button_text": "Öneri Yarat🔍", 
                "seo_suggestions_for_pages_label": "Seo Önerileri Sayfaları:", 
                

                # Messages
                "welcome_message": "nevaR Web Servislerine Hoş Geldiniz!",
                "welcome_seo": "nevaR Beta'ya Hoş Geldiniz!",
                "welcome_authenticated": "Hoş geldiniz, {0}!",
                "logged_in_as": "Giriş yapıldı: **{0}**",
                "analysis_complete_message": "✅URL'niz için analiz tamamlandı.",
                "analyzing_website": "Web siteniz analiz ediliyor, lütfen bekleyin...",
                "found_existing_report": "Bu URL için mevcut bir rapor bulundu.",
                "analysis_failed": "Web sitesi analizi başarısız oldu. Lütfen tekrar deneyin.",
                "analysis_results_for_url": "Şunun için analiz sonuçları: {0}",
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
                "detailed_analysis_still_inprogress": " Detaylı Analiz hala devam ediyor. 🔄.",
                "analysis_in_progress_for": " Analiz hala devam ediyor. 🔄.",
                "llm_analysis_status_unknown": "Detaylı alt sayfa analizinin durumu şu anda bilinmiyor. Sonuç bekliyorsanız analiz edin veya yenileyin.",
                "no_ai_model": "Hiçbir AI modeli API anahtarı (Gemini veya Mistral) yapılandırılmamış. Lütfen ortamınızda en az birini ayarlayın.",
                "no_ai_model_configured": "Yapılandırılmış bir AI modeli yok. Lütfen GEMINI_API_KEY veya MISTRAL_API_KEY sağlayın.",
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
                "need_to_login": "Bu hizmeti kullanmak için önce giriş yapmalısınız.",
                "login_required": "Bu hizmeti kullanmak için önce giriş yapmalısınız.",
                "generating_product_description": "Ürün açıklaması oluşturuluyor...",
                "welcome_product_writer_not_analyzed": "Ürün Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_product_writer_analyzed": "Ürün Yazarı sayfasına hoş geldiniz.\nAnaliz şunun için kullanılıyor: **{0}**",
                "product_description_prompt": "Ne tür bir ürün açıklaması yazmak istersiniz?",
                "analyze_website_first_chat_product": "Ürün yazımıyla yardımcı olmadan önce lütfen SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "processing_question": "Sorunuz işleniyor🔄",
                "processing_request": "Sorunuz işleniyor🔄",
                "generating_response": "Yanıt oluşturuluyor 🔄",
                "could_not_generate_description": "Ürün açıklaması oluşturulamadı",
                "error_processing_request": "İstek işlenirken hata oluştu",
                "processing_request": "İstek işleniyor..🔄",
                "analyzing": "Analiz ediliyor",
                "analyze_website_first_product": "Ürün açıklamalarıyla yardımcı olabilmem için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_seo_helper_analyzed": "Seo Yardımcısı Sayfasına Hoş Geldiniz.\nAnaliz şunun için kullanılıyor: {0}",
                "welcome_article_writer_not_analyzed": "Makale Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_article_writer_analyzed": "Makale Yazarı sayfasına hoş geldiniz. {0} analizine dayalı bir makale yazmanıza yardımcı olmaya hazırım.",
                "enter_url_or_question_seo_helper":" Url Gir ve Analiz Değiştir...Sayfa Seç Öneri yarat.....Sana Yardım etmek için buradayım......",
                "enter_url_placeholder":"Web sitenizin adresini girin.",
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

                # Product Options
                "product_options_title": "Ürün Açıklaması Seçenekleri",
                "product_name": "Ürün Adı",
                "product_name_placeholder": "Ürünün adını girin",
                "product_details": "Ürün Detayları",
                "product_details_placeholder": "Ürün özelliklerini, faydalarını, spesifikasyonlarını, hedef kitlesini vb. girin",
                "product_tone": "Ton",
                "product_length": "Açıklama Uzunluğu",
                "product_length_short": "Kısa (~100-150 kelime)",
                "product_length_medium": "Orta (~150-250 kelime)",
                "product_length_long": "Uzun (~250-350 kelime)"
            }
        }

    def get_text(self, key, lang="en", *args, fallback=None):
        """
        Get translated text for the given key in the specified language

        Parameters:
            key (str): The translation key to look up
            lang (str): The language code (e.g., "en", "tr")
            *args: Arguments to format into the translated string
            fallback (str, optional): Fallback text if the key is not found

        Returns:
            str: Translated text
        """
        if lang not in self.translations:
            lang = "en"  # Default to English if language not supported

        if key not in self.translations[lang]:
            # Return fallback or key itself if translation not found
            return fallback or key

        # Format the string with any provided arguments
        if args:
            return self.translations[lang][key].format(*args)
        return self.translations[lang][key]

    def get_available_languages(self):
        """Return a list of available languages"""
        return list(self.translations.keys())


# Create a singleton instance
language_manager = LanguageSupport()