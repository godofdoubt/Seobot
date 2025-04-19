#SeoTree/utils/language_support.py
class LanguageSupport:
    """Class to manage multi-language support in the application"""
    
    def __init__(self):
        self.translations = {
            "en": {
                # Buttons
                "login_button": "Login",
                "logout_button": "Logout",
                "analyze_button": "Analyze Website",
                "seo_helper_button": "SEO Helper",
                "article_writer_button": "Article Writer",
                "product_writer_button": "Product Writer",
                "generate_seo_suggestions": "Generate SEO Suggestions",
                "generate_article": "Generate Article",
                
                # Messages
                "welcome_message": "Welcome to Se10 AI",
                "enter_url": "Enter website URL to analyze",
                "enter_url_welcome": "Enter website URL to analyze: Or ask a question",
                "analysis_complete": "Analysis complete! You now have access to our suite of SEO tools.",
                "analyzing_website": "Analyzing website...",
                "found_existing_report": "Found existing report for this website.",
                "analysis_failed": "Failed to analyze the website. Please try again.",
                "analysis_results": "Analysis Results for {}",
                "authentication_required": "You need to log in first to use this service.",
                "login_failed": "Invalid API key. Please try again.",
                "enter_api_key": "Please enter your API key to access the service.",
                "logged_in_as": "Logged in as: **{}**",
                "next_steps": "Next Steps",
                "continue_optimizing": "Continue optimizing your website with our advanced SEO analysis tools:",
                "welcome_seo": "Welcome to Se10 Web Services",
                "welcome_authenticated": "Welcome to Se10 Chat, {}. \n \n Let's Analyze Your Web Site. Enter your URL below.",
                "welcome_seo_helper_analyzed": "Welcome to the Seo Helper Page.\nUsing analysis for: {}", # <-- ADDED KEY
                "welcome_article_writer_not_analyzed": "Welcome to the Article Writer page. Please analyze a website in the SEO Helper page first to proceed.",
                "welcome_article_writer_analyzed": "Welcome to the Article Writer page. Ready to help you write an article based on the analysis of {}.",
                "generating_new_report": "Generating new SEO report...",

                "content_generation_tools": "Content Generation Tools",
                "create_optimized_content": "Create optimized content based on your website analysis:",
                "analyze_with_ai": "You can also analyze your website with AI helper.",
                "seo_analysis_completed": "SEO Analysis for {} completed. How can I help you with your SEO strategy?",
                "provide_url_first": "Please provide a website URL first so I can analyze it.",
                "no_ai_model": "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY.",
                
                "generating_article": "Generating article...",
                "analyze_website_first": "Please analyze a website first in the SEO Helper page.",
                "analyze_website_first_chat": "Please analyze a website first in the SEO Helper page before I can help with article writing.",
                "article_prompt": "What kind of article would you like to write?",
                "getting_started": "Getting Started",
                "begin_by_analyzing": "Begin by analyzing your website to unlock our suite of SEO and content tools:",
                "platform_description": "Our platform helps you analyze your website and generate SEO-optimized content.",
                "need_to_login": "You need to log in first to use this service.",
                "login_required": "You need to log in first to use this service.", # Added for consistency


                #"product_writer_button": "Product Writer",
                "generate_product_description": "Generate Product Description",
                "generating_product_description": "Generating product description...",
                "welcome_product_writer_not_analyzed": "Welcome to the Product Writer page. Please analyze a website in the SEO Helper page first to proceed.",
                "welcome_product_writer_analyzed": "Welcome to the Product Writer page.\nUsing analysis for: **{}**",
                "product_description_prompt": "What kind of product description would you like to write?",
                "analyze_website_first_chat_product": "Please analyze a website first in the SEO Helper page before I can help with product writing.",
                "processing_question": "Processing your question", # Added
                "generating_response": "Generating response", # Added
                "could_not_generate_description": "Could not generate product description", # Added
                "error_processing_request": "Error processing request", # Added
                "analyzing": "Analyzing", # Added
                "no_ai_model_configured": "No AI model configured. Please provide either GEMINI_API_KEY or MISTRAL_API_KEY.", # Added for consistency
                "analyze_website_first_product": "Please analyze a website first in the SEO Helper page before I can help with product descriptions.",
                 
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

                # --- NEW Product Options Translations ---
                "product_options_title": "Product Description Options",
                "product_name": "Product Name",
                "product_name_placeholder": "Enter the name of the product",
                "product_details": "Product Details",
                "product_details_placeholder": "Enter product features, benefits, specifications, target audience, etc.",
                "product_tone": "Tone", # More generic 'Tone' for product
                "product_length": "Description Length",
                "product_length_short": "Short (~100-150 words)",
                "product_length_medium": "Medium (~150-250 words)",
                "product_length_long": "Long (~250-350 words)",
                # --- END NEW Product Translations ---

            },
            "tr": {
                # Buttons
                "login_button": "Giriş",
                "logout_button": "Çıkış",
                "analyze_button": "Web Siteni Analiz Et",
                "seo_helper_button": "S10 Analiz Yardımcısı",
                "article_writer_button": "Makale Yazarı",
                "product_writer_button": "Ürün açıklaması Yazarı",
                "generate_seo_suggestions": "Seo Analizimi Oluştur",
                "generate_article": "Makale Oluştur",
                
                # Messages
                "welcome_message": "S10 Yapay Zeka Web Servisine Hoş Geldiniz",
                "enter_url": "URL girin:",
                "enter_url_welcome": "Website URLnizi girin , Yada Soru Sorun.",
                "analysis_complete": "Analiz tamamlandı! Artık Servislere araçlarımıza erişebilirsiniz.",
                "analyzing_website": "....Web sitesi analiz ediliyor...",
                "found_existing_report": "Bu web sitesi için mevcut rapor bulundu.",
                "analysis_failed": "Web sitesi analizi başarısız oldu. Lütfen tekrar deneyin.",
                "analysis_results": "{} için Analiz Sonuçları",
                "authentication_required": "Bu hizmeti kullanmak için önce giriş yapmanız gerekiyor.",
                "login_failed": "Geçersiz API anahtarı. Lütfen tekrar deneyin.",
                "enter_api_key": "Hizmete erişmek için lütfen API anahtarınızı girin.",
                "logged_in_as": "Giriş yapıldı: **{}**",
                "next_steps": "Sonraki Adımlar",
                "continue_optimizing": "Gelişmiş SEO analiz araçlarımızla web sitenizi optimize etmeye devam edin:",
                "welcome_seo": "Se10 Web Hizmetlerine Hoş Geldiniz",
                "welcome_authenticated": "Se10 Sohbete Hoş Geldiniz, {}. \n \n Web Sitenizi Analiz Edelim. URL'nizi aşağıya girin.",
                "welcome_seo_helper_analyzed": "Seo Yardımcısı Sayfasına Hoş Geldiniz.\nAnaliz şunun için kullanılıyor: {}", # <-- ADDED KEY & TRANSLATION
                "welcome_article_writer_not_analyzed": "Makale Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_article_writer_analyzed": "Makale Yazarı sayfasına hoş geldiniz. {} analizine dayalı bir makale yazmanıza yardımcı olmaya hazırım.",
                "generating_new_report": "Yeni SEO raporu oluşturuluyor...",
                
                "content_generation_tools": "İçerik Oluşturma Araçları",
                "create_optimized_content": "Web sitesi analizinize dayalı optimize edilmiş içerik oluşturun:",
                "analyze_with_ai": "Web sitenizi AI yardımcısı ile de analiz edebilirsiniz.",
                "seo_analysis_completed": "{} için SEO Analizi tamamlandı. SEO stratejiniz için size nasıl yardımcı olabilirim?",
                "provide_url_first": "Lütfen önce analiz etmek için bir web sitesi URL'si girin.",
                "no_ai_model": "Yapılandırılmış AI modeli yok. Lütfen GEMINI_API_KEY veya MISTRAL_API_KEY sağlayın.",
                
                "generating_article": "Makale oluşturuluyor...",
                "analyze_website_first": "Lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "analyze_website_first_chat": "Makale yazımıyla yardımcı olmadan önce lütfen SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "article_prompt": "Ne tür bir makale yazmak istersiniz?",
                "getting_started": "Başlarken",
                "begin_by_analyzing": "SEO ve içerik araçlarımızın paketini açmak için web sitenizi analiz ederek başlayın:",
                "platform_description": "Platformumuz web sitenizi analiz etmenize ve SEO optimize edilmiş içerik oluşturmanıza yardımcı olur.",
                "need_to_login": "Bu hizmeti kullanmak için önce giriş yapmalısınız.",
                "login_required": "Bu hizmeti kullanmak için önce giriş yapmalısınız.", # Added for consistency

                #"product_writer_button": "Ürün açıklaması Yazarı",
                "generate_product_description": "Ürün Açıklaması Oluştur",
                "generating_product_description": "Ürün açıklaması oluşturuluyor...",
                "welcome_product_writer_not_analyzed": "Ürün Yazarı sayfasına hoş geldiniz. Devam etmek için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "welcome_product_writer_analyzed": "Ürün Yazarı sayfasına hoş geldiniz.\nAnaliz şunun için kullanılıyor: **{}**",
                "product_description_prompt": "Ne tür bir ürün açıklaması yazmak istersiniz?",
                "analyze_website_first_chat_product": "Ürün yazımıyla yardımcı olmadan önce lütfen SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                "processing_question": "Sorunuz işleniyor", # Added
                "generating_response": "Yanıt oluşturuluyor", # Added
                "could_not_generate_description": "Ürün açıklaması oluşturulamadı", # Added
                "error_processing_request": "İstek işlenirken hata oluştu", # Added
                "analyzing": "Analiz ediliyor", # Added
                "analysis_completed_no_report": "Analiz tamamlandı ancak rapor oluşturulamadı.", # Already exists
                "no_ai_model_configured": "Yapılandırılmış bir AI modeli yok. Lütfen GEMINI_API_KEY veya MISTRAL_API_KEY sağlayın.", # Added for consistency
                "analyze_website_first_product": "Ürün açıklamalarıyla yardımcı olabilmem için lütfen önce SEO Yardımcısı sayfasında bir web sitesi analiz edin.",
                

                # --- NEW Article Options Translations ---
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


                # --- NEW Product Options Translations ---
                "product_options_title": "Ürün Açıklaması Seçenekleri",
                "product_name": "Ürün Adı",
                "product_name_placeholder": "Ürünün adını girin",
                "product_details": "Ürün Detayları",
                "product_details_placeholder": "Ürün özelliklerini, faydalarını, spesifikasyonlarını, hedef kitlesini vb. girin",
                "product_tone": "Ton", # More generic 'Ton' for product
                "product_length": "Açıklama Uzunluğu",
                "product_length_short": "Kısa (~100-150 kelime)",
                "product_length_medium": "Orta (~150-250 kelime)",
                "product_length_long": "Uzun (~250-350 kelime)",
                # --- END NEW Product Translations ---


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
