import logging
from urllib.parse import urlparse, urljoin
import time
import random
import asyncio
import os
from collections import deque, Counter
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from analyzer.methods import validate_url, extract_keywords, load_history, save_history
from analyzer.seoreportsaver import SEOReportSaver
from analyzer.seocons import analyze_meta_tags, analyze_headings, analyze_content_types , analyze_images

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SEOAnalyzer:
    def __init__(self):
        self.history = {}
        self.saver = SEOReportSaver()
    
    async def _get_text_from_url(self, context, url):
        """Helper method to extract text content from a URL"""
        try:
            page = await context.new_page()
            await page.goto(url, wait_until='networkidle', timeout=20000)  # Using PAGE_TIMEOUT
            text_content = await page.evaluate('() => document.body ? document.body.innerText : ""')
            await page.close()
            return text_content
        except Exception as e:
            logging.error(f"Error retrieving text from {url}: {e}")
            if page and not page.is_closed():
                await page.close()
            return None

    

    async def analyze_links(self, page: Page, base_url: str):
        """Analyze links ON A SINGLE page."""
        try:
            base_domain = urlparse(base_url).netloc.replace('www.', '')
            links_data = await page.evaluate("""
                ([baseDomain, pageUrl]) => {
                    const internal = new Set();
                    const external = new Set();
                    const allowedSchemes = ['http:', 'https:'];
                    try {
                        Array.from(document.links).forEach(link => {
                            try {
                                const absoluteUrl = new URL(link.href, pageUrl).href;
                                const linkUrl = new URL(absoluteUrl);
                                if (!allowedSchemes.includes(linkUrl.protocol)) return;
                                const linkDomain = linkUrl.hostname.replace('www.', '');
                                const normalizedUrl = absoluteUrl.split('#')[0];
                                if (linkDomain === baseDomain) {
                                    internal.add(normalizedUrl);
                                } else {
                                    external.add(normalizedUrl);
                                }
                            } catch (e) { /* ignore */ }
                        });
                    } catch (e) { console.error('Error extracting links:', e); }
                    return { internal_links: Array.from(internal), external_links: Array.from(external) };
                }
            """, [base_domain, page.url])
            return {
                'internal_links': links_data.get('internal_links', []),
                'external_links': links_data.get('external_links', []),
                'internal_count': len(links_data.get('internal_links', [])),
                'external_count': len(links_data.get('external_links', []))
            }
        except Exception as e:
            logging.error(f"Error in analyze_links for {base_url}: {e}")
            return {'internal_links': [], 'external_links': [], 'internal_count': 0, 'external_count': 0}

    
    async def scan_for_product_links(self, page, base_url):
        """Perform a deeper scan specifically targeting product links"""
        try:
            base_domain = urlparse(base_url).netloc.replace('www.', '')
            product_patterns = ['/product/', '/products/', '/urun/', '/ürün/', '/item/', '/items/']
            category_patterns = ['/category/', '/kategori/', '/shop/', '/store/', '/dukkan/', '/dükkân/']

            js_helpers = """
                const isSameDomain = (url, baseDomain) => {
                    try { return new URL(url).hostname.replace('www.', '') === baseDomain; }
                    catch (e) { return false; }
                };
                const checkPatterns = (url, patterns) => {
                    const lcUrl = url.toLowerCase();
                    return patterns.some(p => lcUrl.includes(p.toLowerCase()));
                };
            """

            initial_links = await page.evaluate(f"""
                ({js_helpers}) (baseDomain, productPatterns, categoryPatterns) => {{
                    const allLinks = Array.from(document.querySelectorAll('a[href]'))
                        .map(a => {{ try {{ return new URL(a.href, document.baseURI).href; }} catch(e){{ return null; }} }})
                        .filter(href => href && href.startsWith('http') && isSameDomain(href, baseDomain));
                    const productLinks = allLinks.filter(url => checkPatterns(url, productPatterns));
                    const categoryPages = allLinks.filter(url => checkPatterns(url, categoryPatterns));
                    return {{ productLinks: [...new Set(productLinks)], categoryPages: [...new Set(categoryPages)] }};
                }}
            """, base_domain, product_patterns, category_patterns)

            result_links = set(initial_links['productLinks'])
            category_pages_to_scan = initial_links['categoryPages']

            if category_pages_to_scan:
                logging.info(f"[Product Scan] Found {len(category_pages_to_scan)} category pages to scan")
                MAX_CATEGORY_PAGES_TO_SCAN = 5
                scanned_categories = 0
                for category_url in category_pages_to_scan:
                    if scanned_categories >= MAX_CATEGORY_PAGES_TO_SCAN: break
                    scanned_categories += 1
                    category_page = None
                    try:
                        logging.info(f"[Product Scan] Scanning category page: {category_url}")
                        category_page = await page.context.new_page()
                        await category_page.goto(category_url, wait_until='domcontentloaded', timeout=15000)
                        category_product_links = await category_page.evaluate(f"""
                           ({js_helpers}) (baseDomain, productPatterns) => {{
                                return Array.from(document.querySelectorAll('a[href]'))
                                    .map(a => {{ try {{ return new URL(a.href, document.baseURI).href; }} catch(e){{ return null; }} }})
                                    .filter(href => href && href.startsWith('http') && isSameDomain(href, baseDomain))
                                    .filter(url => checkPatterns(url, productPatterns));
                            }}
                        """, base_domain, product_patterns)
                        if category_product_links:
                            logging.info(f"[Product Scan] Found {len(category_product_links)} product links on category page {category_url}")
                            result_links.update(category_product_links)
                        await category_page.close()
                        await asyncio.sleep(random.uniform(0.5, 1))
                    except Exception as e:
                        logging.error(f"[Product Scan] Error scanning category page {category_url}: {e}")
                        if category_page and not category_page.is_closed():
                            await category_page.close()

            return list(result_links)
        except Exception as e:
            logging.error(f"Error in scan_for_product_links: {e}")
            return []

    def _normalize_url(self, url: str, base_url: str) -> str | None:
        """Improved URL normalization, handling relative URLs and protocol differences"""
        try:
            absolute_url = urljoin(base_url, url)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                return None
            scheme = "https"
            netloc = parsed.netloc.lower().replace('www.', '')
            path = parsed.path if parsed.path else '/'
            query = parsed.query
            normalized = f"{scheme}://{netloc}{path}"
            if query:
                normalized += f"?{query}"
            return normalized
        except Exception as e:
            return None

    async def _extract_internal_links_from_page(self, page: Page, base_domain: str, exclude_patterns: list[str]) -> set[str]:
        """Helper to extract, normalize, and filter internal links from a given page"""
        found_links = set()
        try:
            links_on_page = await page.evaluate(f"""
                (baseDomain) => {{
                    const links = new Set();
                    const allowedSchemes = ['http:', 'https:'];
                    try {{
                        Array.from(document.links).forEach(link => {{
                            try {{
                                const absoluteUrl = new URL(link.href, document.baseURI).href;
                                const linkUrl = new URL(absoluteUrl);
                                if (!allowedSchemes.includes(linkUrl.protocol)) return;
                                const linkDomain = linkUrl.hostname.replace('www.', '');
                                if (linkDomain === baseDomain) {{
                                    links.add(absoluteUrl.split('#')[0]);
                                }}
                            }} catch (e) {{ /* Malformed href or URL */ }}
                        }});
                    }} catch (e) {{ console.error('Error extracting links:', e); }}
                    return Array.from(links);
                }}
            """, base_domain)

            page_url = page.url
            for link in links_on_page:
                normalized = self._normalize_url(link, page_url)
                if normalized and not any(exclude in normalized for exclude in exclude_patterns):
                    found_links.add(normalized)
        except Exception as e:
            logging.warning(f"Could not extract links from {page.url}: {e}")
        return found_links

    async def analyze_url(self, url):
        """Perform SEO analysis on the given URL using Playwright, with integrated internal link crawling"""
        browser = None
        context = None
        start_time = time.time()
        try:
            # Configuration
            MAX_PAGES_TO_ANALYZE = 100
            MAX_LINKS_TO_DISCOVER = 500
            PAGE_TIMEOUT = 20000
            AGGREGATED_KEYWORD_COUNT = 50
            EXCLUDE_PATTERNS = [
                '/sepet', '/cart', '/checkout', '/odeme', '/order',
                '/hesap', '/account', '/my-account', '/profile', '/?replytocom',
                '/giris', '/login', '/register', '/signup', '/product-tag',
                'add-to-cart', 'add_to_cart', 'remove_item', '/category',
                '?action=', '&action=', 'javascript:', 'mailto:', 'tel:',
                '.pdf', '.jpg', '.png', '.zip', '.rar', '.exe', '.css', '.js',
                '/wp-json/', '/feed/', '/wp-login.php', '/xmlrpc.php', '/tag',
            ]
            PRODUCT_PATTERNS = ['/product/', '/urun/', '/ürün/', '/item/']

            valid_start_url = validate_url(url)
            if not valid_start_url:
                logging.error(f"Invalid start URL provided: {url}")
                return None
            url = valid_start_url
            self.history = load_history()
            start_domain = urlparse(url).netloc.replace('www.', '').lower()

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 SEOAnalyzerBot/1.0',
                    viewport={'width': 1920, 'height': 1080},
                )
                await context.route("**/*", lambda route: route.abort()
                    if route.request.resource_type in {"image", "stylesheet", "font", "media"} or \
                       any(domain in route.request.url for domain in ["google-analytics.com", "googletagmanager.com", "facebook.net", "doubleclick.net"])
                    else route.continue_()
                )

                page = await context.new_page()
                await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT * 1.5)
                text_content = await page.evaluate('() => document.body ? document.body.innerText : ""')

                # Initial Analysis of Start Page
                analysis = {
                    'url': url,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'meta_tags': await analyze_meta_tags(page),
                    'headings': await analyze_headings(page),
                    'links': await self.analyze_links(page, url),
                    'images': await analyze_images(page),
                    'content_length': len(text_content) if text_content else 0,
                    'word_count': len(text_content.split()) if text_content else 0,
                    'content_types': await analyze_content_types(page),
                    'crawled_internal_pages_count': 0,
                    'crawled_urls': [],
                    'page_statistics': {
                        'main_url': {
                            'url': url,
                            'content_length': len(text_content) if text_content else 0,
                            'word_count': len(text_content.split()) if text_content else 0
                        }
                    },
                    'content_length_stats': {},
                    'word_count_stats': {},
                    'keywords': {},
                    'analysis_duration_seconds': 0  # Will be updated at the end
                }
                logging.info(f"Initial analysis of {url} complete.")

                # Setup for Crawling
                aggregated_keywords = Counter()
                if text_content:
                    initial_keywords = extract_keywords(text_content)
                    aggregated_keywords.update(initial_keywords)

                content_lengths = [analysis['content_length']] if text_content else []
                word_counts = [analysis['word_count']] if text_content else []

                urls_to_visit = deque()
                visited_urls = set()
                all_discovered_links = set()
                analyzed_urls = []  # To track URLs analyzed for stats

                initial_links_on_page = await self._extract_internal_links_from_page(page, start_domain, EXCLUDE_PATTERNS)
                logging.info(f"Found {len(initial_links_on_page)} initial internal links on start page.")

                normalized_start_url = self._normalize_url(url, url)
                if normalized_start_url:
                    visited_urls.add(normalized_start_url)
                    all_discovered_links.add(normalized_start_url)

                for link in initial_links_on_page:
                    if link not in visited_urls:
                        urls_to_visit.append(link)
                        visited_urls.add(link)
                        all_discovered_links.add(link)

                await page.close()

                logging.info(f"Starting crawl. Queue size: {len(urls_to_visit)}. Max links to discover: {MAX_LINKS_TO_DISCOVER}. Max pages to analyze: {MAX_PAGES_TO_ANALYZE}")

                analyzed_count = 0

                # Integrated Crawling Loop
                while urls_to_visit and len(all_discovered_links) < MAX_LINKS_TO_DISCOVER:
                    current_url = urls_to_visit.popleft()

                    analyze_this_page = analyzed_count < MAX_PAGES_TO_ANALYZE
                    if analyze_this_page:
                        logging.info(f"Analyzing page #{analyzed_count + 1}: {current_url}")
                    else:
                        logging.info(f"Fetching links from: {current_url} (Discovery limit: {len(all_discovered_links)}/{MAX_LINKS_TO_DISCOVER})")

                    internal_page = None
                    try:
                        internal_page = await context.new_page()
                        await internal_page.goto(current_url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)

                        newly_found_links = await self._extract_internal_links_from_page(internal_page, start_domain, EXCLUDE_PATTERNS)
                        for link in newly_found_links:
                            if link not in visited_urls and len(all_discovered_links) < MAX_LINKS_TO_DISCOVER:
                                urls_to_visit.append(link)
                                visited_urls.add(link)
                                all_discovered_links.add(link)

                        if analyze_this_page:
                            internal_text = await internal_page.evaluate('() => document.body ? document.body.innerText : ""')
                            if internal_text:
                                text_length = len(internal_text)
                                words = len(internal_text.split())
                                content_lengths.append(text_length)
                                word_counts.append(words)

                                analysis['page_statistics'][current_url] = {
                                    'url': current_url,
                                    'content_length': text_length,
                                    'word_count': words
                                }

                                internal_keywords = extract_keywords(internal_text)
                                aggregated_keywords.update(internal_keywords)
                                analyzed_urls.append(current_url)
                                logging.debug(f" -> Analyzed: {len(internal_keywords)} keywords. Length: {text_length}")
                            else:
                                logging.debug(f" -> Page empty or text extraction failed.")
                            analyzed_count += 1

                        await internal_page.close()
                        internal_page = None
                        await asyncio.sleep(random.uniform(0.3, 0.8))

                    except PlaywrightTimeoutError:
                        logging.warning(f"Timeout loading: {current_url}")
                    except Exception as e:
                        logging.error(f"Error processing {current_url}: {type(e).__name__} - {e}")
                    finally:
                        if internal_page and not internal_page.is_closed():
                            await internal_page.close()

                logging.info(f"Crawl finished. Discovered {len(all_discovered_links)} unique internal links. Analyzed {analyzed_count} pages for stats.")

                # Final Calculations and Report Update
                if content_lengths:
                    analysis['content_length_stats'] = {
                        'total': sum(content_lengths),
                        'average': round(sum(content_lengths) / len(content_lengths), 2),
                        'min': min(content_lengths),
                        'max': max(content_lengths),
                        'median': sorted(content_lengths)[len(content_lengths) // 2],
                        'pages_analyzed': len(content_lengths)
                    }
                if word_counts:
                    analysis['word_count_stats'] = {
                        'total': sum(word_counts),
                        'average': round(sum(word_counts) / len(word_counts), 2),
                        'min': min(word_counts),
                        'max': max(word_counts),
                        'median': sorted(word_counts)[len(word_counts) // 2],
                        'pages_analyzed': len(word_counts)
                    }

                analysis['keywords'] = dict(aggregated_keywords.most_common(AGGREGATED_KEYWORD_COUNT))
                analysis['crawled_urls'] = analyzed_urls
                analysis['crawled_internal_pages_count'] = analyzed_count
                analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)

                # History and Saving
                if url not in self.history:
                    self.history[url] = []
                self.history[url].append(analysis)
                save_history(self.history)

                await self.saver.save_reports(analysis)
                logging.info(f"Analysis saved. Duration: {analysis['analysis_duration_seconds']}s")

                return analysis

        except Exception as e:
            logging.error(f"Error analyzing URL {url}: {e}")
            return None
        finally:
            if browser:
                await browser.close()