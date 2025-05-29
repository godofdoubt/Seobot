'''
SEO Analyzer Configuration File - Updated
Contains all configurable parameters used by the SEO analyzer
analyzer/config.py
'''

# Crawling and Analysis Limits
MAX_PAGES_TO_ANALYZE = 25
MAX_LINKS_TO_DISCOVER = 182928
PAGE_TIMEOUT = 60000  # milliseconds

#MAX_CATEGORY_PAGES_TO_SCAN = 25
CRAWL_DELAY_MIN = 2
CRAWL_DELAY_MAX = 12
# Browser Configuration

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768

# URL Patterns to Exclude from Crawling
EXCLUDE_PATTERNS = [
    '?replytocom=',  # More specific match for replytocom URLs
    'replytocom=',   # Catch variations without the leading ?
    '&replytocom=',  # Catch when it's part of a query string
    # Rest of the existing exclude patterns remain the same...
    '/category/uncategorized/',
    '/tag/',
    '/tag',
    '/login',
    '/register',
    '/cart',
    '/checkout',
    '/account',
    '/user',
    '/search',
    '?sort=',
    '?filter=',
    '?page=',
    '/wp-admin',
    '/wp-login',
    '/author/',
    '/feed/',
    '/trackback/',
    '/comment-page-',
    '/cdn-cgi/',
    '.jpg',
    '.jpeg',
    '.png',
    '.gif',
    '.pdf',
    '.zip',
    '.rar',
    '.mp3',
    '.mp4',
    '.webm',
    '.css',
    '.js',
    '/sepet',
    '/odeme',
    '/order',
    '/hesap',
    '/my-account',
    '/profile',
    '/?replytocom',
    '/giris',
    '/signup',
    '/product-tag',
    '/product-category',
    'add-to-cart',
    'add_to_cart',
    'remove_item',
    '/lost-password/',
    '/hesabim/',
    '/hesabim',
    '?action=',
    '&action=',
    'javascript:',
    'mailto:',
    'tel:',
    '.exe',
    '?taxonomy=',
    '/wp-json/',
    '/wp-login.php',
    '/xmlrpc.php',
    '/mesafeli-satis-sozlesmesi',
    '/uyelik-sozlesmesi',
    '/UyelikSozlesme.aspx',
    '/sikca-sorulan-sorular',
    '/kisisel-verilerin-kullanilmasi',
    '/uyeliksiz-kisisel-verilerin-islenme-ve-aydinlatma-metni',
    '/site-kullanim-kosullari',
    '/UyeOl',
    '/e-bulten-kisisel-verilerin-islenmesi-ve-aydinlatma-metni',
    '/Hesabim.aspx',
    '/SifremiUnuttum',
    '/UyeGiris',
    '/siparistakip.aspx',
    '/acik-riza-metni',
    '/iade-ve-degisim-kosullari',
    '/iletisim',
    '/Sepetim',
    '//iso-',
    '/Iletisim',
    '/privacy-policy',
    '/gizlilik-politikasi',
    '/gizlilik',
    '/terms-conditions',
    '/terms-of-service',
    '/kullanim-kosullari',
    '/cookie-policy',
    '/cerez-politikasi',
    '/kvkk',
    '/gdpr',
    '/impressum',
    '/wishlist',
    '/istek-listesi',
    '/favori',
    '/compare',
    '/karsilastir',
    '/password-reset',
    '/sifre-sifirlama',
    '/activation',
    '/aktivasyon',
    '/unsubscribe',
    '/abonelikten-cik',
    '/newsletter',
    '/bulten',
    '/return-policy',
    '/iade-politikasi',
    '/shipping-policy',
    '/kargo-politikasi',
    '/teslimat',
    '/contact-form',
    '/iletisim-formu',
    '/payments',
    '/odeme-yontemleri',
    '/membership',
    '/uyelik',
    '/support',
    '/destek',
    '/faq',
    '/sss',
    '/sik-sorulan-sorular',
    '/help',
    '/yardim',
    '/about-us',
    '/about',
    '/hakkinda',
    '/delivery-information',
    '/teslimat-bilgileri',
    '/track-order',
    '/siparis-takip',
    '/my-orders',
    '/siparislerim',
    '/addresses',
    '/adreslerim',
    '/campaigns',
    '/kampanyalar',
    '/aydinlatma-metni',
    '/bilgilendirme',
    '/cookie-consent',
    '/cerez-izni',
    '/kosullar',
    '/terms',
    '/sartlar',
    '/bilgilendirme-formu',
    '/information-form',
    '/sertifikalar',
    '/certificates',
    '/partners',
    '/partnerlerimiz',
    '/testimonials',
    '/referanslar',
    '/references',
    '/musterilerimiz',
    '/reviews',
    '/yorumlar',
    '/degerlendirmeler',
    '/filter',
    '/filtre',
    '/sort',
    '/siralama',
    '/arama',
    '/404',
    '/error',
    '/hata',
    '/print',
    '/yazdir',
    '/share',
    '/paylas',
    '/download',
    '/indir',
    '/upload',
    '/iso-',
    '/yukle',
    '/admin',
    '/panel',
    '/dashboard',
    '/yonetim',
    '/yazar',
    '/yorum',
    '?utm_',
    '&utm_',
    '?ref=',
    '&ref=',
    '?affiliate=',
    '&affiliate=',
    '?source=',
    '&source=',
    '?fbclid=',
    '&fbclid=',
    '?gclid=',
    '&gclid=',
    
    # New exclude pattern for specific categories we want to skip
    '/category/tdt',  # Specifically exclude the tdt category
]


# Product Related URL Patterns
PRODUCT_PATTERNS = ['/product/', '/urun/', '/ürün/', '/item/','/shop']

# Resource Types to Block When Crawling (for performance)
BLOCKED_RESOURCES = ['image', 'stylesheet', 'font', 'media','other_resource_type_if_not_needed']

# Domains to Block When Crawling (analytics, ads, etc.)
BLOCKED_DOMAINS = [
    'google-analytics.com', 
    'googletagmanager.com', 
    'facebook.net', 
    'doubleclick.net',
    '.aspx',
    'facebook.com/tr',
    'connect.facebook.net',
    'doubleclick.net',
    'analytics',
    'tracker',
    'pixel',
    'adservice',
    'yandex.ru/metrika', # Yandex Metrica
    'youtube.com/embed', # Gömülü videolar için
    'vimeo.com/player',  # Gömülü videolar için
    'fonts.googleapis.com', # Fontlar engellenirse sayfa görünümü bozulabilir, BLOCKED_RESOURCES içinde 'font' varsa bu gereksiz olabilir.
    'fonts.gstatic.com',    # Fontlar için
]

# Category Detection Patterns
CATEGORY_PATTERNS = [
    '/category/', 
    '/category',
    '/kategori/', 
    '/shop/category/', 
    '/store/', 
    '/dukkan/', 
    '/dükkân/',
     '/collection/',
    '/collections/',
    '/categories/',
    '/kategoriler/',           
]




COMMON_STOP_WORDS = {
    'a', 'an', 'the', 'in', 'on', 'at', 'and', 'or', 'of', 'to', 'for', 'ile', 've', 'veya', 'ama', 'fakat',
    'ancak', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'this', 'bir', 'bu', 'şu', 'o', 'olarak',
    'olan', 'that', 'it', 'its', 'they', 'we', 'you', 'he', 'she', 'has', 'have', 'için', 'gibi', 'çok',
    'daha', 'had', 'do', 'does', 'did', 'but', 'from', 'what', 'when', 'where', 'en', 'her', 'şey', 'değil',
    'mi', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'some', 'such', 'var', 'yok', 'ben', 'sen',
    'biz', 'siz', 'onlar', 'no', 'nor', 'too', 'very', 'can', 'will', 'just', 'com', 'www', 'birşey', 'diye',
    'sadece', 'sonra', 'önce', 'http', 'https', 'html', 'page', 'click', 'site', 'website', 'web', 'net',
    'org', 'gov', 'edu', 'info', 'biz', 'menu', 'search', 'contact', 'about', 'home', 'not', 'your', 'our',
    'ne', 'nasıl', 'neden', 'kim', 'nereye', 'their', 'his', 'may', 'if', 'as', 'so', 'who', 'which', 'than',
}