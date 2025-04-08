import logging
from urllib.parse import urlparse
import time
import random
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright
from analyzer.methods import validate_url, extract_keywords, load_history, save_history, get_formatted_datetime, get_current_user

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client globally
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SEOReportSaver:
    def __init__(self):
        """Initialize with the global Supabase client."""
        self.supabase = supabase

    def format_analysis_results(self, analysis):
        """Format analysis results for text output."""
        if not analysis:
            return "Analysis failed or no results available."

        output = []
        # Header with datetime and user info
        output.append(f"Current Date and Time (UTC -MM-DD HH:MM:SS formatted): {get_formatted_datetime()}")
        output.append(f"Current User's Login: {get_current_user()}")
        output.append("\n" + "="*80)

        output.append(f"\nSEO Analysis Report for: {analysis.get('url', 'Unknown URL')}")
        output.append(f"Analysis Time: {analysis.get('timestamp', 'Unknown')}")
        output.append("\n" + "="*50 + "\n")

        # Keywords Section - Moved to top for prominence
        output.append("KEYWORD ANALYSIS:")
        keywords = analysis.get('keywords', {})
        if keywords:
            output.append("\nTop Keywords by Frequency:")
            sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
            for keyword, frequency in sorted_keywords:
                output.append(f"- {keyword}: {frequency} occurrences")
        else:
            output.append("No keywords found")

        output.append("\n" + "="*50 + "\n")

        # Product Analysis
        output.append("PRODUCT ANALYSIS:")
        products = analysis.get('content_types', {}).get('products', {})

        # URL-based product count with specific formatting
        url_based_count = products.get('url_based_count', 0)
        output.append(f'\n"url_based_count": {url_based_count}')

        # Categories with specific formatting and counts
        categories = products.get('categories', {})
        if categories:
            output.append('\n"categories":')
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            for category, count in sorted_categories:
                output.append(f'  "{category}": {count}')

            output.append(f"\nTotal Categories Found: {len(categories)}")
            total_products = sum(categories.values())
            output.append(f"Total Products in Categories: {total_products}")
        else:
            output.append('\n"categories":')
            output.append('  "no categories found"') # fixed: replaced hardcoded value with dynamic message

        # Product Distribution
        if categories:
            output.append("\nProduct Distribution by Category:")
            for category, count in sorted_categories:
                percentage = (count / url_based_count * 100) if url_based_count > 0 else 0
                bar_length = int(percentage / 2)
                bar = "█" * bar_length
                output.append(f"{category.ljust(20)}: {bar} {count} ({percentage:.1f}%)")

        # Visual Products Section
        output.append(f"\nVisually Detected Products: {products.get('count', 0)}")
        if products.get('elements'):
            output.append("\nSample Products:")
            for product in products['elements'][:5]:
                output.append(f"- {product}")

        # Product URLs Section
        if products.get('product_urls'):
            output.append("\nSample Product URLs:")
            for url in products['product_urls'][:5]:
                output.append(f"- {url}")
            if len(products['product_urls']) > 5:
                output.append(f"... and {len(products['product_urls']) - 5} more")

        # Articles Section
        output.append("\n" + "="*50)
        output.append("\nARTICLE ANALYSIS:")
        articles = analysis.get('content_types', {}).get('articles', {})
        output.append(f"Articles Found: {articles.get('count', 0)}")
        if articles.get('elements'):
            output.append("\nSample Articles:")
            for article in articles['elements'][:5]:
                output.append(f"- {article}")

        # Meta Info Section
        output.append("\n" + "="*50)
        output.append("\nMETA INFORMATION:")
        meta_tags = analysis.get('meta_tags', {})
        output.append(f"Title: {meta_tags.get('title', 'Not found')}")
        output.append(f"Description: {meta_tags.get('description', 'Not found')}")
        output.append(f"Keywords: {meta_tags.get('keywords', 'Not found')}")

        # Content Stats
        output.append("\nCONTENT STATISTICS:")
        output.append(f"Content Length: {analysis.get('content_length', 0)} characters")
        output.append(f"Word Count: {analysis.get('word_count', 0)} words")

        # Headings Structure
        output.append("\nHEADING STRUCTURE:")
        for heading_type, headings in analysis.get('headings', {}).items():
            if headings:
                output.append(f"\n{heading_type.upper()} Tags ({len(headings)}):")
                for heading in headings[:3]:
                    output.append(f"- {heading}")

        # Links Analysis
        links = analysis.get('links', {})
        output.append("\nLINK ANALYSIS:")
        output.append(f"Internal Links: {links.get('internal_count', 0)}")
        output.append(f"External Links: {links.get('external_count', 0)}")

        # Images Analysis
        images = analysis.get('images', [])
        total_images = len(images)
        images_with_alt = sum(1 for img in images if img.get('has_alt', False))
        output.append("\nIMAGE ANALYSIS:")
        output.append(f"Total Images: {total_images}")
        output.append(f"Images with Alt Text: {images_with_alt}")
        output.append(f"Images missing Alt Text: {total_images - images_with_alt}")

        return "\n".join(output)

    async def save_reports(self, analysis):
        """Save analysis reports to Supabase."""
        try:
            if not analysis:
                return

            # Generate text report
            text_report = self.format_analysis_results(analysis)

            # Prepare data for Supabase
            data = {
                'url': analysis['url'],
                'timestamp': analysis['timestamp'],
                'report': analysis,  # JSONB
                'text_report': text_report  # TEXT
            }

            # Use asyncio.to_thread for async compatibility
            response = await asyncio.to_thread(
                self.supabase.table('seo_reports').insert(data).execute
            )

            if response.data:
                logging.info(f"Reports saved to Supabase for {analysis['url']}")
            else:
                logging.error(f"Failed to save report to Supabase: {response.error}")

        except Exception as e:
            logging.error(f"Error saving reports to Supabase: {e}")

class SEOAnalyzer:
    def __init__(self):
        self.history = {}  # Initialize empty history
        self.saver = SEOReportSaver()

    async def analyze_meta_tags(self, page):
        """Analyze meta tags of the page"""
        return await page.evaluate("""
            () => {
                const meta = {
                    title: document.title,
                    description: '',
                    keywords: ''
                };

                const descTag = document.querySelector('meta[name="description"]');
                const keywordsTag = document.querySelector('meta[name="keywords"]');

                if (descTag) meta.description = descTag.content;
                if (keywordsTag) meta.keywords = keywordsTag.content;

                return meta;
            }
        """)

    async def analyze_headings(self, page):
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

    async def analyze_links(self, page, base_url):
        """Analyze links on the page"""
        try:
            base_domain = urlparse(base_url).netloc.replace('www.', '')

            links = await page.evaluate("""
                (baseUrl) => {
                    try {
                        const baseUrlObj = new URL(baseUrl);
                        const baseDomain = baseUrlObj.hostname.replace('www.', '');

                        const allLinks = Array.from(document.links)
                            .map(link => link.href)
                            .filter(href => href && href.startsWith('http'));

                        const internal = [];
                        const external = [];

                        allLinks.forEach(link => {
                            try {
                                const linkUrl = new URL(link);
                                const linkDomain = linkUrl.hostname.replace('www.', '');

                                if (linkDomain === baseDomain) {
                                    internal.push(link);
                                } else {
                                    external.push(link);
                                }
                            } catch (e) {
                                console.error('Invalid URL:', link);
                            }
                        });

                        return {
                            internal_links: internal,
                            external_links: external,
                            internal_count: internal.length,
                            external_count: external.length
                        };
                    } catch (e) {
                        console.error('Error in link analysis:', e);
                        return {
                            internal_links: [],
                            external_links: [],
                            internal_count: 0,
                            external_count: 0
                        };
                    }
                }
            """, base_url)

            verified_internal = []
            verified_external = []

            all_links = (links.get('internal_links', []) + links.get('external_links', []))

            for link in all_links:
                try:
                    link_domain = urlparse(link).netloc.replace('www.', '')
                    if link_domain == base_domain:
                        if link not in verified_internal:
                            verified_internal.append(link)
                    else:
                        if link not in verified_external:
                            verified_external.append(link)
                except Exception as e:
                    logging.error(f"Error processing link {link}: {e}")
                    continue

            return {
                'internal_links': verified_internal,
                'external_links': verified_external,
                'internal_count': len(verified_internal),
                'external_count': len(verified_external)
            }

        except Exception as e:
            logging.error(f"Error in analyze_links: {e}")
            return {
                'internal_links': [],
                'external_links': [],
                'internal_count': 0,
                'external_count': 0
            }

    async def analyze_images(self, page):
        """Analyze images on the page"""
        return await page.evaluate("""
            () => {
                return Array.from(document.images).map(img => ({
                    src: img.src,
                    alt: img.alt,
                    has_alt: !!img.alt
                }));
            }
        """)

    async def analyze_content_types(self, page):
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

            return content_analysis['content_types']
        except Exception as e:
            logging.error(f"Error analyzing content types: {e}")
            return {'articles': {'count': 0, 'elements': []},
                    'products': {
                        'count': 0,
                        'elements': [],
                        'categories': {},
                        'url_based_count': 0,
                        'product_urls': []
                    }}

    async def analyze_url(self, url):
        """Perform SEO analysis on the given URL using Playwright"""
        browser = None
        try:
            url = validate_url(url)
            self.history = load_history()

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                await asyncio.sleep(random.uniform(1, 2))
                await page.goto(url, wait_until='networkidle', timeout=30000)
                text_content = await page.evaluate('() => document.body.innerText')

                analysis = {
                    'url': url,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'meta_tags': await self.analyze_meta_tags(page),
                    'headings': await self.analyze_headings(page),
                    'keywords': extract_keywords(text_content),
                    'links': await self.analyze_links(page, url),
                    'images': await self.analyze_images(page),
                    'content_length': len(text_content) if text_content else 0,
                    'word_count': len(text_content.split()) if text_content else 0,
                    'content_types': await self.analyze_content_types(page)
                }

                if url not in self.history:
                    self.history[url] = []
                self.history[url].append(analysis)
                save_history(self.history)

                # Save reports to Supabase (async call)
                await self.saver.save_reports(analysis)

                return analysis

        except Exception as e:
            logging.error(f"Error analyzing URL {url}: {e}")
            return None
        finally:
            if browser:
                await browser.close()
