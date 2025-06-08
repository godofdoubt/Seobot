# Seobot/utils/keys_tr.py

translations = {
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
    "refresh_analysis_status": "🔄 Lütfen biraz bekleyin.../ Refresh", # Note: English "Refresh" kept as per original
    "refresh_comprehensive_report": "🔄 Analizi Yenile",
    "recheck_comprehensive_report": "🔄 Analizi Yeniden Kontrol Et",
    "go_to_login":"Lütfen Giriş Yapın.",
    "resume_article_tasks_button": "'{task_title}' ile Devam Et ▶️", # UPDATED
    "resume_product_tasks_button": "'{task_title}' ile Devam Et ▶️", # UPDATED

    # Detailed Analysis Messages
    "detailed_analysis_init_error": "Detaylı analiz işlemcisi başlatılırken hata oluştu. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
    "detailed_analysis_runtime_error": "Detaylı analiz işlemcisi kurulumu sırasında çalışma zamanı hatası. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
    "detailed_analysis_trigger_error": "Detaylı site genelinde analiz başlatılamadı. Lütfen tekrar deneyin veya destek ile iletişime geçin.",
    "detailed_analysis_error_status": "Bu rapor için detaylı analizde bir hata oluştu: {llm_analysis_error}. Lütfen günlükleri kontrol edin veya destek ile iletişime geçin.",
    "detailed_analysis_still_inprogress": "Detaylı site genelinde LLM analizi hala devam ediyor. Lütfen tekrar kontrol edin.",
    "detailed_analysis_initiated": "Detaylı site genelinde analiz başlatıldı. Bu biraz zaman alabilir. İlerlemeyi buradan takip edebilirsiniz.",
    "error_checking_report_status": "Rapor durumu kontrol edilirken hata oluştu. Lütfen tekrar deneyin.",
    "status_check_failed_error": "Bir hata nedeniyle rapor durumu kontrol edilemedi.",

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
    "show_less_report_sidebar": "Daha az göster",
    "read_more_report_sidebar": "Devamını oku",
    "auto_refresh_checkbox": "🔄 Oto-kontrol",
    "auto_refresh_help": "Tamamlanmayı otomatik olarak kontrol eder",

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
    "not_available_short": "Yok", # UPDATED from "Mevcut Değil" to match "N/A" intent
    "no_details_provided_short": "Belirli bir detay sağlanmadı.",
    "generic_page_welcome": "{page_name} sayfasına hoş geldiniz.",
    "report_up_to_date_toast": "Rapor güncel.",
    "found_suffix": "Bulundu",

    # SEO Helper - Task Panel (Content Generation CTA Progress)
    "content_tasks_expander_title": "📝 İçerik Üretim Görevleri İlerlemesi ↕️",
    "cta_status_paused_at": "Makale görevi hazırlığı '{title}' için duraklatıldı.",
    "cta_status_awaiting_response_for": "Makale görevi '{title}' için yanıt bekleniyor.",
    "cta_status_paused_at_product": "Ürün görevi hazırlığı '{title}' için duraklatıldı.",
    "cta_status_awaiting_response_for_product": "Ürün görevi '{title}' için yanıt bekleniyor.",
    "cta_status_awaiting_response_generic": "Önerilen görev için yanıt bekleniyor.",
    "cta_all_tasks_addressed_panel": "Bu gruptaki tüm içerik görevleri ele alındı.",
      
    # Article Options
    "target_page_url_label": "Hedef Sayfa URL'si",
    "content_gap_label": "İçerik Boşluğu",
    # "target_audience_label": "Hedef Kitle", # Zaten Ürün Seçeneklerinde var, ortak
    "outline_preview_label": "Taslak Önizlemesi",

    "article_options_title": "Makale Seçenekleri",
    "focus_keyword": "Odak Anahtar Kelime", # Note: also appears later, ensure consistency. Turkish "Odak Kelime" is also used.
    "focus_keyword_help": "Makalenizin odaklanacağı anahtar kelime",
    "content_length": "İçerik Uzunluğu", # Note: also appears later
    "content_length_short": "Kısa",
    "content_length_medium": "Orta",
    "content_length_long": "Uzun",
    "content_length_very_long": "Çok Uzun",
    "tone": "Makale Tonu", # Note: also appears later
    "tone_professional": "Profesyonel",
    "tone_casual": "Günlük",
    "tone_enthusiastic": "Hevesli",
    "tone_technical": "Teknik",
    "tone_friendly": "Dostça",
    "custom_keywords": "Ek Anahtar Kelimeler (isteğe bağlı)",
    "custom_keywords_help": "Anahtar kelimeleri virgülle ayırarak girin",
    "custom_title": "Özel Başlık (isteğe bağlı)",
    "product_content_tasks_label":"Ürün Yazarı Görevleri",
    "competitive_advantage_label": "Rekaber Avantajı", # Typo: Rekabet
    "rec_strategic_priority_label": "Önem", # Note: Also "Öncelik" used later. "Öncelik" is better for "Priority"

    # Article Writer UI & Suggestions
    "suggested_article_tasks_title": "Önerilen Makale Görevleri",
    "suggested_article_tasks_intro": "SEO analizine dayanarak bazı makale önerileri bulduk. Makale seçeneklerini önceden doldurmak için birini seçin:",
    "suggestion_task_label": "Öneri",
    "focus_keyword_label": "Odak Anahtar Kelime", # Matches "focus_keyword" better
    "content_length_label": "İçerik Uzunluğu",
    "article_tone_label": "Makale Tonu",
    "additional_keywords_label": "Ek Anahtar Kelimeler",
    "suggested_title_label": "Önerilen Başlık",
    "use_this_suggestion_button": "Bu Öneriyi Kullan",
    "suggestion_applied_message": "Öneri uygulandı! Kenar çubuğundaki Makale Seçeneklerini kontrol edin.",
    "no_article_suggestions_found": "Mevcut raporun otomatik öneri verilerinde belirli bir makale önerisi bulunamadı veya veri formatı tanınmıyor.",
    "focus_keyword_required_warning": "Makale oluşturmak için Odak Anahtar Kelime gereklidir. Lütfen kenar çubuğunda doldurun.",
    "analyze_site_for_article_options": "Makale seçeneklerini görmek için SEO Yardımcısı'nda bir siteyi analiz edin.",
    "article_writer_activated_by_seo_helper": "Makale Yazarı, SEO Yardımcısı tarafından şunun için etkinleştirildi: **{task_title}**. Makale oluşturuluyor...",
    "article_writer_options_prefilled_by_seo_helper": "Makale Yazarı seçenekleri SEO Yardımcısı tarafından şunun için önceden dolduruldu: **{task_title}**. Gözden geçirin ve 'Makale Oluştur'a tıklayın.",
    "generated_article_from_seo_helper_title": "Oluşturulan Makale (SEO Yardımcısından): {title}",
    "focus_keyword_required_for_auto_gen": "Bu öneride odak anahtar kelime eksik. Oluşturmak için lütfen kenar çubuğunda bir tane sağlayın.",
    "article_generation_prerequisites_warning": "Makale oluşturulamıyor. Bir sitenin analiz edildiğinden ve konunun kenar çubuğunda sağlandığından emin olun.",
    "could_not_generate_article": "Üzgünüm, şu anda makaleyi oluşturamadım.",

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
    "target_audience_label": "Hedef Kitle", # Consistent use
    # "competitive_advantage_label": "Rekabet Avantajı", # Already here, typo "Rekaber" above fixed.
    "suggested_seo_keywords_label": "Önerilen SEO Anahtar Kelimeleri",

    # Product Writer UI & Suggestions
    "suggested_product_tasks_title": "Önerilen Ürün Görevleri",
    "suggested_product_tasks_intro": "SEO analizine dayanarak bazı ürün açıklaması önerileri bulduk. Ürün seçeneklerini önceden doldurmak için birini seçin:",
    "untitled_suggestion": "Başlıksız Öneri",
    "product_name_label": "Ürün Adı",
    "product_description_length_label": "Açıklama Uzunluğu", # "productone_labelt_description_length_label" was a typo in original
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
    
    # Section Titles for AI Recommendations
    "rec_title_strategic": "### Stratejik Öneriler",
    "rec_title_seo": "### SEO Optimizasyon İçgörüleri", # "SEO Optimiziazsyonu" typo fixed
    "rec_title_personas": "### Hedef Kitle Personaları",
    "rec_title_content_insights": "### İçerik Stratejisi İçgörüleri", # "İçerik İçgörüleri" is also used. This is more specific.

    # Strategic Recommendations labels (rec_strategic_priority_label uses "Öncelik" here, "Önem" earlier. "Öncelik" for Priority)
    # "rec_strategic_priority_label": "Öncelik", # This is correct for Priority.
    "rec_strategic_implementation_label": "Uygulama",
    "rec_strategic_data_source_label": "Veri Kaynağı",
    # "rec_title_seo": "### SEO Optimiziazsyonu", # Duplicate, typo fixed above
    "rec_seo_observed_issue_label": "Gözlemlenen Sorun/Fırsat", # "Fırsatlar/Hedefler" also used. This is more direct.
    # "persona_demographics_label": "Demografi", # Duplicates below.
    # "persona_occupation_role_label": "Meslek/Ünvan", # Duplicates below
    # "persona_goals_label": "Hedefler (site için)", # Duplicates below
    # "persona_pain_points_label": "Engeller/Zorluklar", # Duplicates below
    # "persona_motivations_label": "Marka Motivasyonu", # "Siteyi Kullanma Motivasyonları" is more accurate for Persona
    # "persona_key_message_label": "Anahtar Aksiyon", # "Anahtar Mesaj" is more accurate for Persona

    # SEO Optimization Insights labels
    "rec_seo_default_focus_area": "SEO Önerisi",
    # "rec_seo_observed_issue_label": "Gözlemlenen Sorun/Fırsat", # Already above
    "rec_seo_insight_action_label": "İçgörü ve Aksiyon",
    "rec_seo_potential_impact_label": "Potansiyel Etki",
    "rec_seo_strategic_action_label": "Stratejik Aksiyon Örneği",

    # Target Audience Personas labels
    # "target_page_url_label": "Hedef URL", # Already present
    # "target_audience_label": "Hedef Kitle", # Already present
    "persona_item_prefix_label": "Persona", 
    "persona_demographics_label": "Demografi",
    "persona_occupation_role_label": "Meslek/Rol", # "Meslek/Ünvan" is also fine
    "persona_goals_label": "Hedefler (siteyle ilgili)",
    "persona_pain_points_label": "Zorluklar/Engeller", 
    "persona_motivations_label": "Siteyi Kullanma Motivasyonları",
    "persona_info_sources_label": "Bilgi Kaynakları",
    "persona_key_message_label": "Anahtar Mesaj",
    # "common_supporting_data_label": "Destekleyici Veri", # Duplicates below

    # Content Strategy Insights labels
    "rec_content_insight_item_prefix_label": "İçgörü",
    "rec_cs_implications_label": "İçeriğe Etkileri", # "İçerik için Etkileri" is also fine
    "rec_cs_illustrative_opp_label": "Örnek İçerik Fırsatı:", # "İçerik Fırsatı Görünümü" is less direct
    "rec_cs_opp_type_label": "Tür",
    "rec_cs_opp_description_label": "Açıklama",
    "rec_cs_opp_target_persona_label": "Hedef Persona Uyumu",
    "rec_cs_opp_potential_topics_label": "Potansiyel Konular/Bakış Açıları", # "Potansiyel Topik/Açı" is less natural
    "rec_cs_opp_justification_label": "Gerekçelendirme", # "Gerekçe" is also fine
    "seo_suggestions_and_content_ideas_title": " SEO Önerileri / Fikirleri",
    'article_content_tasks_label':"İçerik Görevleri Makaleler", # "Makale İçerik Görevleri" or "Makaleler için İçerik Görevleri"
    # "tone": "Makale Tonu", # Duplicated
    # "article_tone_label": "Makale Tonu", # Duplicated
    # "focus_keyword": "Odak Kelime", # Duplicated, better "Odak Anahtar Kelime"
    # "focus_keyword_label": "Odak Kelime", # Duplicated
    # "content_length": "İçerik Uzunluğu", # Duplicated
    
    # "rec_cs_implications_label": "İçerik için Etkileri", # Duplicate
    # "rec_cs_illustrative_opp_label": "Örnek İçerik Fırsatı:", # Duplicate
    # "rec_cs_opp_type_label": "Tür", # Duplicate
    # "rec_cs_opp_description_label": "Açıklama", # Duplicate
    # "rec_cs_opp_target_persona_label": "Hedef Persona Uyumu", # Duplicate
    # "rec_cs_opp_potential_topics_label": "Potansiyel Konular/Bakış Açıları", # Duplicate
    # "rec_cs_opp_justification_label": "Gerekçe", # Duplicate
    # "rec_title_content_insights": "### İçerik İçgörüleri", # Duplicate

    # Common labels
    "common_supporting_data_label": "Destekleyici Veri",
    
    # Chart/Dashboard related keys used in main.py
    "seo_score_gauge_title": "SEO Skoru",
    "metric_thin_content_pages": "Zayıf İçerikli Sayfalar",
    "tooltip_thin_content_pages": "{thin_pages_count} sayfada ~220 kelimeden az içerik bulundu. Bunlar arama motorları tarafından düşük değerli olarak görülebilir.",
    "metric_bad_format_titles": "Başlık Formatı Sorunlu Sayfalar",
    "tooltip_bad_format_titles": "{bad_titles_count} sayfada başlık formatlama sorunları bulundu (örn. <br> etiketleri). Başlıkların temiz ve açıklayıcı olduğundan emin olun.",
    "content_quality_overview_title": "İçerik Kalitesine Genel Bakış",
    "xaxis_label_num_pages": "Sayfa Sayısı",
    "metric_word_count": "Kelime Sayısı",
    "metric_images": "Görsel Sayısı",
    "metric_internal_links": "İç Bağlantılar",
    "metric_external_links": "Dış Bağlantılar",
    "metric_headings": "Başlık Sayısı",
    "page_content_metrics_bar_title_hp": "Sayfa İçerik Metrikleri (Ana Sayfa)",
    "metrics_axis_label": "Metrikler",
    "count_axis_label": "Sayı",
    "tech_mobile_friendly": "Mobil Uyumlu",
    "tech_ssl_secure": "SSL Güvenli",
    "tech_page_speed": "Sayfa Hızı (Tahmini)",
    "tech_title_tag_hp": "Başlık Etiketi (Ana Sayfa)",
    "tech_robots_txt": "Robots.txt Durumu",
    "tech_sitemap_status": "Site Haritası Durumu",
    "tech_internal_404s": "İç 404 Hataları",
    "status_good": "İyi",
    "status_warning": "Uyarı",
    "status_error": "Hata",
    "technical_seo_status_title": "Teknik SEO Durumu",
    "seo_dashboard_main_title": "📊 SEO Analiz Paneli",
    "seo_score_not_available_caption": "Sınırlı veri nedeniyle SEO Skoru 0 olabilir.",
    "page_metrics_not_available_hp": "Sayfa İçerik Metrikleri (Ana Sayfa) mevcut değil.",
    "content_quality_overview_not_available": "İçerik Kalitesine Genel Bakış verileri mevcut değil.",
    "content_issue_thin_pages_found": "{count} sayfa potansiyel olarak zayıf içerikli",
    "content_issue_bad_titles_found": "{count} sayfa başlık formatı sorunlu",
    "low_score_content_advice": "SEO skorunuz içerik kalitesinden etkilenebilir. Şunları ele almayı düşünün: {issues}. Bu alanları iyileştirmek sitenizin performansını artırabilir.",
    "low_score_other_factors": "SEO skorunuz optimal aralığın altında. Bu taramada site genelinde büyük zayıf içerik veya başlık formatı sorunları tespit edilmese de, iyileştirme alanlarını belirlemek için diğer teknik yönleri, içerik alaka düzeyini ve kullanıcı deneyimini gözden geçirin.",
    "technical_seo_status_not_available": "Teknik SEO Durumu mevcut değil.",
    
    "raw_report_data_label": "Ham Rapor Verisi (JSON)", # UPDATED - Value changed, comment indicates usage by LLMAnalysisProcess & main.py
    "raw_report_help": "Bu, geliştiriciler için veya diğer araçlara aktarmak için faydalı olan tam analizin ham JSON verileridir.", # NEW - For JSON data, used by LLMAnalysisProcess
    "raw_report_help_main": "Bu, ham metin raporu özetidir.", # NEW (formerly raw_report_help) - For main.py text_report expander help

    "show_full_json_report": "Tam JSON Rapor Verilerini Göster (hata ayıklama için)",
    "full_json_report_label": "Tam JSON Raporu",
    "invalid_url_format_warning": "Geçersiz URL formatı. Lütfen geçerli bir web sitesi adresi girin (örneğin, https://example.com).",
    "detailed_analysis_trigger_failed_status": "Detaylı analiz süreci başlatılamadı.",
    "please_enter_url": "Lütfen bir URL girin.",
    "analyzing_website_main_page_info": "{url} için analiz devam ediyor...",

    # START OF NEW KEYS FOR LLMAnalysisProcess REPORT
    "report_main_title": "KAPSAMLI SEO & İÇERİK ANALİZ RAPORU",
    "report_generated_at": "Oluşturulma Zamanı",
    "report_technical_overview": "Teknik Genel Bakış",
    "report_website_analysis_summary": "Web Sitesi Analiz Özeti",
    "report_total_pages_crawled": "Taranan Toplam Sayfa Sayısı",
    "report_analysis_duration": "Analiz Süresi",
    "report_minutes_label": "dakika",
    "report_seconds_label": "saniye",
    "report_content_metrics": "İçerik Metrikleri",
    "report_total_content_analyzed": "Analiz Edilen Toplam İçerik",
    "report_characters_label": "karakter",
    "report_average_content_per_page": "Sayfa Başına Ortalama İçerik Uzunluğu",
    "report_total_headings_found": "Bulunan Toplam Başlık Sayısı",
    "report_image_optimization": "Görsel Optimizasyonu",
    "report_total_images_found": "Bulunan Toplam Görsel Sayısı",
    "report_images_missing_alt_text": "Alt Metni Eksik Görseller",
    "report_alt_text_coverage": "Alt Metin Kapsamı",
    "report_status": "Durum",
    "report_excellent": "Mükemmel",
    "report_good": "İyi",
    "report_needs_improvement": "İyileştirilmesi Gerekir",
    "report_critical": "Kritik",
    "report_no_images_found": "Taranan sayfalarda hiç görsel bulunamadı.",
    "report_mobile_friendliness": "Mobil Uyumluluk",
    "report_pages_with_mobile_viewport": "Mobil Görüntü Alanına Sahip Sayfalar",
    "report_mobile_optimization_coverage": "Mobil Optimizasyon Kapsamı",
    "report_basic_technical_setup": "Temel Teknik Kurulum",
    "report_robots_txt_file": "robots.txt Dosyası",
    "report_found": "Bulundu", # Rapora özel, found_suffix'ten farklı
    "report_not_found": "Bulunamadı",
    "report_recommendation": "Öneri",
    "report_robots_txt_recommendation": "Arama motoru tarayıcılarını yönlendirmek için bir robots.txt dosyası oluşturmayı düşünün.",
    "report_main_page_analysis": "Ana Sayfa Analizi",
    "report_url_not_found_in_data": "URL verilerde bulunamadı",
    "report_via_llm_provider": "LLM Sağlayıcısı aracılığıyla",
    "report_note": "Not",
    "report_main_page_analysis_error": "Ana sayfa analizi sırasında bir hata oluştu",
    "report_overall_content_tone": "Genel İçerik Tonu",
    "report_identified_target_audience": "Belirlenen Hedef Kitle",
    "report_main_topic_categories": "Ana Konu Kategorileri",
    "report_content_summary": "İçerik Özeti",
    "report_primary_keywords_identified": "Belirlenen Birincil Anahtar Kelimeler",
    # "report_suggested_seo_keywords": "Önerilen SEO Anahtar Kelimeleri", # Already exists
    "report_contact_info_key_mentions": "İletişim Bilgileri & Önemli Bahsetmeler",
    "report_no_contacts_identified": "LLM tarafından belirli bir iletişim bilgisi veya önemli bahsetme bulunamadı.",
    "report_key_header_elements": "Önemli Üst Bilgi Öğeleri",
    "report_no_header_elements_identified": "LLM tarafından belirgin üst bilgi öğesi tanımlanmadı.",
    "report_key_footer_elements": "Önemli Alt Bilgi Öğeleri",
    "report_no_footer_elements_identified": "LLM tarafından belirgin alt bilgi öğesi tanımlanmadı.",
    "report_main_page_data_missing": "Ana sayfa analiz verileri mevcut değil.",
    "report_subpage_analysis_overview": "Alt Sayfa Analizine Genel Bakış",
    "report_num_additional_pages_analyzed": "Analiz Edilen Ek Sayfa Sayısı",
    "report_highlights_individual_subpages": "Bireysel Alt Sayfalardan Öne Çıkanlar",
    "report_page": "Sayfa",
    "report_subpage_analysis_error": "Bu alt sayfanın analizi sırasında bir hata oluştu",
    "report_summary_prefix": "Özet",
    "report_tone_prefix": "Ton",
    "report_audience_prefix": "Kitle",
    "report_topics_prefix": "Konular",
    "report_common_keywords_subpages_title_format": "Alt Sayfalardaki En Yaygın {count} Anahtar Kelime",
    "report_mentioned_in_subpages_format": "{count} alt sayfada bahsedildi",
    "report_frequently_suggested_seo_keywords_subpages_title_format": "Alt Sayfalar İçin En Sık Önerilen {count} SEO Anahtar Kelimesi",
    "report_common_topic_categories_subpages_title_format": "Alt Sayfalardaki En Yaygın {count} Konu Kategorisi",
    "report_common_target_audiences_subpages_title_format": "Alt Sayfalar İçin En Yaygın {count} Hedef Kitle",
    "report_common_content_tones_subpages_title_format": "Alt Sayfalardaki En Yaygın {count} İçerik Tonu",
    "report_ai_powered_strategic_insights": "Yapay Zeka Destekli Stratejik İçgörüler ve Öneriler",
    "report_no_ai_recommendations": "Yapay zeka önerileri oluşturulmadı.",
    "report_error_generating_ai_recommendations": "Yapay zeka destekli öneriler oluşturulurken bir hata oluştu.",
    "report_no_ai_recommendations_configured": "Bu görev için hiçbir LLM yapılandırılmadığından yapay zeka önerileri oluşturulamıyor.",
    "report_performance_monitoring_next_steps": "Performans İzleme ve Sonraki Adımlar",
    "report_next_steps_1": "- **SEO Performansını Düzenli Olarak İzleyin:** Anahtar kelime sıralamalarını, organik trafiği, hemen çıkma oranlarını ve dönüşüm oranlarını izlemek için Google Analytics, Google Search Console ve diğer SEO platformları gibi araçları kullanın. Bu rapora dayanarak uygulanan değişikliklerin metriklerinizi nasıl etkilediğine dikkat edin.",
    "report_next_steps_2": "- **İçerik Güncellemeleri ve Boşluk Doldurma:** Mevcut içeriği taze, alakalı ve doğru tutmak için periyodik olarak gözden geçirin ve güncelleyin. Kullanıcı ihtiyaçlarını ve arama amacını karşılayan yeni içerik oluşturmak için belirlenen anahtar kelime boşluklarını ve konu önerilerini kullanın.",
    "report_next_steps_3": "- **Teknik SEO Denetimleri:** Kırık bağlantılar, yavaş sayfa hızı, tarama hataları ve mobil kullanılabilirlik sorunları gibi sorunları belirlemek ve düzeltmek için periyodik teknik SEO denetimleri yapın. Sitemap.xml ve robots.txt dosyalarınızın güncel olduğundan emin olun.",
    "report_next_steps_4": "- **Backlink Profil Yönetimi:** Backlink profilinizi düzenli olarak analiz edin. Zararlı bağlantıları reddedin ve sitenizin otoritesini artırmak için aktif olarak yüksek kaliteli, alakalı backlink'ler arayın.",
    "report_next_steps_5": "- **SEO Trendleriyle Güncel Kalın:** SEO ortamı sürekli gelişmektedir. Stratejinizi buna göre uyarlamak için algoritma güncellemeleri, yeni en iyi uygulamalar ve gelişmekte olan teknolojiler (arama motorlarında yapay zeka gibi) hakkında bilgi sahibi olun.",
    "report_end_of_report": "Rapor Sonu."
    # END OF NEW KEYS FOR LLMAnalysisProcess REPORT
}