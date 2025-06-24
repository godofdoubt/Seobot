# Seobot/utils/GREV2.py

import asyncio
from playwright.async_api import async_playwright
import random
from urllib.parse import urlparse
import logging

class CompetitorContentScraper:
    """
    Scrapes Google for content from a specific competitor's website using the 'site:' operator.
    This version incorporates advanced anti-bot detection measures based on GREV1.
    """
    def __init__(self, region='en'):
        """
        Initializes the scraper.
        :param region: 'en' for International (English), 'tr' for Turkey (Turkish).
        """
        self.results = []
        self.region = region
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _get_normalized_domain(self, url: str) -> str:
        """Helper to get domain from a URL, used for the site: search operator."""
        if not url:
            return ""
        try:
            if '://' not in url:
                url = 'http://' + url
            parsed_uri = urlparse(url)
            domain = parsed_uri.netloc
            return domain
        except Exception as e:
            logging.error(f"Could not parse domain from URL '{url}': {e}")
            return url

    async def _check_for_blocks(self, page):
        """Checks if Google is blocking the request before trying to scrape."""
        blocking_indicators = [
            "Our systems have detected unusual traffic", "olağandışı trafik algıladık",
            "We're sorry", "Üzgünüz", "blocked", "captcha", "verify you're not a robot"
        ]
        page_content = await page.content()
        for indicator in blocking_indicators:
            if indicator.lower() in page_content.lower():
                logging.error(f"GREV2: Google blocking detected with indicator: '{indicator}'")
                raise Exception(f"Google is blocking requests: {indicator}")

    async def analyze_competitor_content(self, keyword: str, competitor_url: str):
        """
        Launches Playwright, performs a 'site:' search, and extracts results.
        Returns a formatted markdown string of the findings.
        """
        competitor_domain = self._get_normalized_domain(competitor_url)
        if not competitor_domain:
            return f"❌ **Error:** Could not extract a valid domain from the competitor URL `{competitor_url}`."

        search_query = f'"{keyword}" site:{competitor_domain}'
        logging.info(f"GREV2: Starting competitor analysis with query: {search_query}")
        
        search_configs = {
            'en': {'google_urls': ["https://www.google.com/ncr"], 'locale': "en-US", 'timezone_id': "America/New_York"},
            'tr': {'google_urls': ["https://www.google.com.tr/ncr"], 'locale': "tr-TR", 'timezone_id': "Europe/Istanbul"}
        }
        config = search_configs.get(self.region, search_configs['en'])

        try:
            async with async_playwright() as p:
                # --- USING THE ADVANCED BROWSER CONFIGURATION FROM GREV1 ---
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox', '--disable-blink-features=AutomationControlled',
                        '--disable-web-security', '--disable-features=VizDisplayCompositor',
                        '--disable-dev-shm-usage', '--no-first-run', '--disable-extensions',
                        '--disable-default-apps'
                    ]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1366, "height": 768},
                    locale=config['locale'],
                    timezone_id=config['timezone_id']
                )

                # --- ADDING CRITICAL STEALTH SCRIPTS FROM GREV1 ---
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                """)
                
                page = await context.new_page()

                # --- ADDING REALISTIC HTTP HEADERS FROM GREV1 ---
                await page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1',
                })
                
                await page.goto(config['google_urls'][0], wait_until="domcontentloaded", timeout=15000)
                
                consent_selectors = ["#L2AGLb", "button:has-text('Accept all')", "button:has-text('Tümünü kabul et')"]
                for selector in consent_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible(timeout=3000):
                            await element.click()
                            logging.info(f"GREV2: Handled consent with selector: {selector}")
                            await page.wait_for_timeout(random.randint(500, 1000))
                            break
                    except Exception:
                        continue
                
                # --- ADDED PROACTIVE BLOCK CHECK FROM GREV1 ---
                await self._check_for_blocks(page)

                search_box = page.locator("textarea[name='q'], input[name='q']").first
                await search_box.fill(search_query)
                await page.wait_for_timeout(random.randint(500, 900))
                await search_box.press("Enter")
                await page.wait_for_load_state('domcontentloaded', timeout=12000)

                # --- RE-CHECK FOR BLOCKS AFTER SEARCH ACTION ---
                await self._check_for_blocks(page)

                no_results_locator = page.locator("#rso")
                if await no_results_locator.count() == 0:
                    raise Exception("The main results container (#rso) was not found on the page.")

                no_results_text = await no_results_locator.inner_text()
                if "did not match any documents" in no_results_text or "ile eşleşen hiçbir belge bulunamadı" in no_results_text:
                    logging.info(f"GREV2: No results found for query: {search_query}")
                    await browser.close()
                    return self._format_results(keyword, competitor_domain)

                result_container = page.locator("#rso")
                result_blocks = await result_container.locator("> div").all()
                logging.info(f"GREV2: Found {len(result_blocks)} potential result blocks.")

                count = 0
                for block in result_blocks:
                    if count >= 10: break
                    try:
                        title_link = block.locator("a:has(h3)").first
                        if await title_link.count() == 0: continue
                        
                        title = await title_link.locator("h3").first.inner_text()
                        url = await title_link.get_attribute("href")
                        if not url: continue

                        description_element = block.locator("div[style*='-webkit-line-clamp:2']").first
                        description = await description_element.inner_text() if await description_element.count() > 0 else "No description found."
                        
                        self.results.append({"title": title.strip(), "url": url, "description": description.strip()})
                        count += 1
                        logging.info(f"GREV2: Successfully parsed result: {title.strip()}")

                    except Exception as e:
                        logging.warning(f"GREV2: Could not parse a result block. It might be an ad or other element. Error: {e}")
                        continue
                
                await browser.close()
        
        except Exception as e:
            error_message = f"An error occurred while analyzing competitor content: {e}"
            logging.error(f"GREV2: {error_message}", exc_info=True)
            return f"❌ **Error:**\n`{error_message}`\n\nThis can happen if Google blocks the request or the page structure has significantly changed. Please try again later."

        return self._format_results(keyword, competitor_domain)

    def _format_results(self, keyword: str, competitor_domain: str):
        # This function remains unchanged.
        output = [
            f"## 🕵️‍♂️ Competitor Content Analysis for '{competitor_domain}'",
            f"### Keyword: `{keyword}`\n"
        ]

        if not self.results:
            output.append("---")
            output.append(f"**❌ No specific content matching the keyword '{keyword}' was found on `{competitor_domain}` via Google search.**")
            output.append("\n**Possible Reasons:**")
            output.append("- The competitor does not have content ranking for this exact keyword phrase.")
            output.append("- The content exists but is not well-indexed or optimized for this query.")
            output.append("- Your keyword might be too specific. Try a broader term.")
            return "\n".join(output)

        output.append("---")
        output.append(f"**✅ Found {len(self.results)} relevant pages:**\n")

        for i, res in enumerate(self.results, 1):
            output.append(f"**{i}. {res['title']}**")
            output.append(f"   - **URL:** `{res['url']}`")
            output.append(f"   - **Description:** *{res['description']}*")
            output.append("") # For spacing

        return "\n".join(output)