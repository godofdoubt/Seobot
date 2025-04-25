import logging
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

async def analyze_meta_tags(page: Page):
    """Analyze meta tags of the page"""
    return await page.evaluate("""
        () => {
            const meta = { title: document.title, description: '', keywords: '' };
            const descTag = document.querySelector('meta[name="description"]');
            const keywordsTag = document.querySelector('meta[name="keywords"]');
            if (descTag) meta.description = descTag.content;
            if (keywordsTag) meta.keywords = keywordsTag.content;
            return meta;
        }
    """)

async def analyze_headings(page: Page):
    """Analyze heading structure of the page"""
    return await page.evaluate("""
        () => {
            const headings = {};
            for (let i = 1; i <= 6; i++) {
                const elements = document.getElementsByTagName('h' + i);
                headings['h' + i] = Array.from(elements).map(el => el.innerText.trim());
            }
            return headings;
        }
    """)

async def analyze_images(page):
    """Analyze images on the page"""
    return await page.evaluate("""
        () => {
            return Array.from(document.images).map(img => ({
                src: img.src, alt: img.alt, has_alt: !!img.alt
            }));
        }
    """)


async def analyze_content_types(page: Page):
    """Analyze article and product counts on the website including URL-based product counts"""
    try:
        content_analysis = await page.evaluate("""
            () => {
                const analysis = {
                    content_types: {
                        articles: {
                            count: 0,
                            elements: []
                        },
                        products: {
                            count: 0,
                            elements: [],
                            categories: {},
                            url_based_count: 0,
                            product_urls: []
                        }
                    }
                };

                const getProductPathInfo = (url) => {
                    const paths = [
                        '/urunler/', '/ürünler/',
                        '/products/', '/product/',
                        '/urun/', '/ürün/',
                        '/items/', '/item/',
                        '/katalog/', '/catalog/'
                    ];

                    try {
                        const urlObj = new URL(url);
                        const path = urlObj.pathname;

                        for (const productPath of paths) {
                            if (path.includes(productPath)) {
                                const parts = path.split(productPath)[1].split('/').filter(p => p);
                                if (parts.length > 0) {
                                    return {
                                        isProduct: true,
                                        category: parts.length > 1 ? parts[0] : 'uncategorized',
                                        path: parts.join('/')
                                    };
                                }
                            }
                        }
                    } catch (e) {
                        console.error('Error parsing URL:', e);
                    }
                    return { isProduct: false };
                };

                const links = Array.from(document.getElementsByTagName('a'));
                const processedUrls = new Set();

                links.forEach(link => {
                    const href = link.href;
                    if (!processedUrls.has(href) && href) {
                        const productInfo = getProductPathInfo(href);
                        if (productInfo.isProduct) {
                            processedUrls.add(href);
                            analysis.content_types.products.url_based_count++;
                            analysis.content_types.products.product_urls.push(href);

                            const category = productInfo.category;
                            analysis.content_types.products.categories[category] =
                                (analysis.content_types.products.categories[category] || 0) + 1;
                        }
                    }
                });

                const productSelectors = [
                    '[itemtype*="Product"]',
                    '.product',
                    '.product-item',
                    '[class*="product-"]',
                    '[id*="product-"]',
                    '.woocommerce-product',
                    '.shopify-product',
                    '[data-product]',
                    '[class*="ProductCard"]',
                    '[class*="product-card"]',
                    '[class*="productCard"]',
                    '[class*="item-card"]',
                    '[class*="shop-item"]',
                    '.item-product',
                    '.catalog-item',
                    '.product-grid-item',
                    '.product-list-item',
                    '#urunler', '.urunler',
                    '.ürünler', '#ürünler',
                    '[class*="urun"]',
                    '[class*="ürün"]',
                    '[id*="urun"]',
                    '[id*="ürün"]',
                    '.urun-detay', '.ürün-detay',
                    '.urun-karti', '.ürün-kartı',
                    '[class*="urun-fiyat"]',
                    '[class*="ürün-fiyat"]',
                    '.stok-urun', '.stok-ürün'
                ];

                const getUniqueTextContent = (element) => {
                    const titleSelectors = [
                        'h1', 'h2', 'h3',
                        '[class*="title"]', '[class*="name"]',
                        '[class*="heading"]', '.product-name',
                        '[itemprop="name"]',
                        '[class*="baslik"]', '[class*="başlık"]',
                        '.urun-adi', '.ürün-adı',
                        '[class*="urun-isim"]', '[class*="ürün-isim"]'
                    ];

                    for (const selector of titleSelectors) {
                        const titleElement = element.querySelector(selector);
                        if (titleElement) {
                            const text = titleElement.innerText.trim();
                            if (text) return text;
                        }
                    }

                    const text = element.innerText.trim().split('\\n')[0];
                    return text.length > 100 ? text.substring(0, 100) + '...' : text;
                };

                const isVisible = (element) => {
                    const style = window.getComputedStyle(element);
                    return style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            style.opacity !== '0' &&
                            element.offsetWidth > 0 &&
                            element.offsetHeight > 0;
                };

                productSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(element => {
                        if (isVisible(element)) {
                            const text = getUniqueTextContent(element);
                            if (text && !analysis.content_types.products.elements.includes(text)) {
                                analysis.content_types.products.elements.push(text);
                                analysis.content_types.products.count++;
                            }
                        }
                    });
                });

                const isLikelyArticle = (text) => {
                    const wordCount = text.trim().split(/\\s+/).length;
                    const sentenceCount = text.split(/[.!?]+/).length;
                    return wordCount > 100 && sentenceCount > 3 && text.length > 500;
                };

                document.querySelectorAll('article, .article, .post, .blog-post, [class*="article"], [class*="blog"]').forEach(element => {
                    if (isVisible(element) && isLikelyArticle(element.innerText)) {
                        const text = getUniqueTextContent(element);
                        if (text && !analysis.content_types.articles.elements.includes(text)) {
                            analysis.content_types.articles.elements.push(text);
                            analysis.content_types.articles.count++;
                        }
                    }
                });

                return analysis;
            }
        """)
        return content_analysis.get('content_types', {
            'articles': {'count': 0, 'elements': []},
            'products': {'count': 0, 'elements': [], 'categories': {}, 'url_based_count': 0, 'product_urls': []}
        })
    except Exception as e:
        logging.error(f"Error analyzing content types on {page.url}: {e}")
        return {'articles': {'count': 0, 'elements': []},
                'products': {'count': 0, 'elements': [], 'categories': {}, 'url_based_count': 0, 'product_urls': []}}