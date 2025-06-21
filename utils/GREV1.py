
import asyncio
from playwright.async_api import async_playwright
import json
import random
import time

class GoogleSearchScraper:
    """
    A class to scrape Google search results, including organic results, ads,
    and "People also searched for" sections, with support for multiple regions.
    """
    def __init__(self, region='en'):
        """
        Initializes the scraper.
        :param region: 'en' for International (English), 'tr' for Turkey (Turkish).
        """
        self.results = []
        self.ads = []
        self.people_also_searched = []
        self.region = region

    async def search_google(self, keyword):
        """
        Launches a Playwright browser, navigates to the correct Google domain,
        and performs the search.
        """
        # Region-specific configurations for URLs, language, and timezone
        search_configs = {
            'en': {
                'google_urls': ["https://www.google.com/ncr", "https://www.google.com"],
                'locale': "en-US",
                'timezone_id': "America/New_York"
            },
            'tr': {
                'google_urls': ["https://www.google.com.tr/ncr", "https://www.google.com.tr"],
                'locale': "tr-TR",
                'timezone_id': "Europe/Istanbul"
            }
        }
        config = search_configs.get(self.region, search_configs['en'])

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', '--disable-blink-features=AutomationControlled',
                    '--disable-web-security', '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage', '--no-first-run', '--disable-extensions',
                    '--disable-default-apps'
                ]
            )
            
            # Create a new browser context with region-specific settings
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale=config['locale'],
                timezone_id=config['timezone_id']
            )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """)
            
            page = await context.new_page()
            
            await page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate',
                'DNT': '1', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1',
            })
            
            try:
                # Use the region-specific Google URLs
                success = False
                for url in config['google_urls']:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        await page.wait_for_timeout(random.randint(2000, 4000))
                        success = True
                        break
                    except Exception:
                        continue
                
                if not success:
                    raise Exception("Could not load any Google URL")
                
                current_url = page.url
                if "sorry" in current_url.lower() or "blocked" in current_url.lower():
                    raise Exception("Google has blocked this request")
                
                await self.handle_cookie_consent(page)
                await self.perform_search(page, keyword)
                await page.wait_for_timeout(random.randint(3000, 5000))
                await self.check_for_blocks(page)
                await self.extract_advertisements(page)
                await self.extract_search_results(page)
                await self.extract_people_also_searched(page)
                
            except Exception as e:
                raise e
            finally:
                await browser.close()
    
    async def handle_cookie_consent(self, page):
        """Handles various cookie consent dialogs."""
        consent_selectors = [
            "button:has-text('Accept all')", "button:has-text('Tümünü kabul et')",
            "button:has-text('I agree')", "button:has-text('Accept')", "#L2AGLb",
            "[aria-label*='Accept']", "button[jsname='b3VHJd']",
        ]
        for selector in consent_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    await element.click()
                    await page.wait_for_timeout(1000)
                    return
            except Exception:
                continue
    
    async def perform_search(self, page, keyword):
        """Performs the actual search by typing and pressing Enter."""
        search_selectors = [
            "textarea[name='q']", "input[name='q']", "[aria-label='Search']",
            "#APjFqb", ".gLFyf"
        ]
        search_box = None
        for selector in search_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    search_box = element
                    break
            except Exception:
                continue
        
        if not search_box:
            raise Exception("Could not find search box")
        
        await search_box.click()
        await page.wait_for_timeout(random.randint(500, 1000))
        await search_box.fill(keyword)
        await page.wait_for_timeout(random.randint(500, 1000))
        await search_box.press("Enter")
    
    async def check_for_blocks(self, page):
        """Checks if Google is blocking the request."""
        blocking_indicators = [
            "Our systems have detected unusual traffic", "olağandışı trafik algıladık",
            "We're sorry", "Üzgünüz", "blocked", "captcha", "verify you're not a robot"
        ]
        page_content = await page.content()
        for indicator in blocking_indicators:
            if indicator.lower() in page_content.lower():
                raise Exception(f"Google is blocking requests: {indicator}")

    async def extract_advertisements(self, page):
        """Extracts advertisements from the search results page."""
        self.ads = []
        # A comprehensive list of selectors for different ad formats
        ad_selectors = [
            "#tads .uEierd", "#tads .ads-ad", "#tads [data-text-ad]",
            ".sh-pr__product-results .sh-dlr__list-result", ".commercial-unit-desktop-top .pla-unit",
            ".ads-ad", ".uEierd", "[data-text-ad='1']", "#rhs_block .ads-ad",
            "#tadsb .uEierd", "[data-ved*='2ahUK'] .uEierd"
        ]
        processed_ads = set()
        for selector in ad_selectors:
            try:
                ad_elements = await page.locator(selector).all()
                for ad_element in ad_elements:
                    if len(self.ads) >= 10: break
                    try:
                        title_elem = ad_element.locator("[role='heading']").first
                        title = await title_elem.inner_text()
                        ad_identifier = title.strip()[:50]
                        if not title.strip() or ad_identifier in processed_ads:
                            continue

                        link = ""
                        try:
                            link = await ad_element.locator("a").first.get_attribute("href")
                        except Exception: pass

                        self.ads.append({"position": len(self.ads) + 1, "title": title.strip(), "url": link})
                        processed_ads.add(ad_identifier)
                    except Exception:
                        continue
            except Exception:
                continue

    async def extract_search_results(self, page):
        """
        Extracts the top 7 organic search results using a robust, multi-selector approach.
        """
        self.results = []
        
        # A list of potential selectors for individual search result containers
        result_container_selectors = [
            "div.g",
            "div.MjjY7e",
            "div.kvH3mc",
            "div.srg div.g",
        ]
    
        all_results = []
        for selector in result_container_selectors:
            elements = await page.locator(selector).all()
            if elements:
                all_results = elements
                break
                
        # If no specific containers found, try a more generic one
        if not all_results:
            all_results = await page.locator("#rso > div").all()
    
        count = 0
        for result_element in all_results:
            if count >= 7:
                break
            
            try:
                # Skip if the element is an ad, "People also ask", or other non-organic result
                if await result_element.locator("span:has-text('Ad'), span:has-text('Sponsored'), span:has-text('Reklam'), h2:has-text('People also ask')").count() > 0:
                    continue
    
                title, url, description = "", "", ""
    
                # Try to extract title and URL from common container '.yuRUbf'
                if await result_element.locator(".yuRUbf").count() > 0:
                    title_container = result_element.locator(".yuRUbf").first
                    title = await title_container.locator("h3").first.inner_text()
                    url = await title_container.locator("a").first.get_attribute("href")
                else: # Fallback for other structures
                    title_elem = result_element.locator("h3").first
                    if await title_elem.count() > 0:
                        title = await title_elem.inner_text()
                    
                    link_elem = result_element.locator("a").first
                    if await link_elem.count() > 0:
                        url = await link_elem.get_attribute("href")
    
                # Try a list of potential selectors for the description
                desc_selectors = [".VwiC3b", "div[data-sncf]", "div[data-snhf='0']", ".s3v9rd"]
                for desc_sel in desc_selectors:
                    if await result_element.locator(desc_sel).count() > 0:
                        description = await result_element.locator(desc_sel).first.inner_text()
                        if description:
                            break
    
                # Validate and clean the result
                if title and url and not url.startswith('/search'):
                    self.results.append({
                        "position": count + 1,
                        "title": title.strip(),
                        "url": url,
                        "description": description.strip()
                    })
                    count += 1
                    
            except Exception:
                # Silently continue to the next potential result block
                continue
    
    async def extract_people_also_searched(self, page):
        """Extracts 'People also search for' or 'Related searches'."""
        self.people_also_searched = []
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

        # **FIX:** Added new robust selector first, based on user debug info.
        related_search_selectors = [
            "div[jsname='d3PE6e'] > div[data-hveid]",
            ".s75CSd a span", "div[data-ved] a[data-ved*='1t:'] span",
        ]

        for selector in related_search_selectors:
            try:
                elements = await page.locator(selector).all()
                for element in elements:
                    try:
                        text = await element.inner_text()
                        clean_text = ' '.join(text.strip().split())
                        if 2 < len(clean_text) < 100 and clean_text not in self.people_also_searched:
                            self.people_also_searched.append(clean_text)
                    except Exception:
                        continue
                if self.people_also_searched:
                    break
            except Exception:
                continue
        
        self.people_also_searched = list(dict.fromkeys(self.people_also_searched))[:10]

    def display_results(self, keyword):
        """Displays all extracted data in a formatted way."""
        print(f"\n{'='*60}\nSEARCH RESULTS FOR: '{keyword}' (Region: {self.region.upper()})\n{'='*60}")
        if self.ads:
            print(f"\n🎯 FOUND {len(self.ads)} ADVERTISEMENTS:\n" + "-"*40)
            for ad in self.ads:
                print(f"\n[AD {ad['position']}] {ad['title']}\n   URL: {ad.get('url', 'N/A')}")
        else:
            print("\n✔️ No advertisements found.")

        if self.results:
            print(f"\n🔍 FOUND {len(self.results)} ORGANIC RESULTS:\n" + "-"*40)
            for result in self.results:
                print(f"\n{result['position']}. {result['title']}\n   URL: {result['url']}")
                if result['description']:
                    print(f"   Description: {result['description'][:200]}...")
        else:
            print("\n❌ No organic results found.")

        if self.people_also_searched:
            print(f"\nRELATED SEARCHES\n" + "-"*40)
            for i, term in enumerate(self.people_also_searched, 1):
                print(f"{i}. {term}")
        else:
            print("\n❌ No related searches were found.")
    
    def save_to_json(self, keyword, filename=None):
        """Saves the extracted data to a JSON file."""
        if not filename:
            filename = f"Google Search_{keyword.replace(' ', '_')}_{self.region}.json"
        
        data = {
            "keyword": keyword, "region": self.region,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "ads_count": len(self.ads), "ads": self.ads,
            "results_count": len(self.results), "results": self.results,
            "related_searches_count": len(self.people_also_searched),
            "related_searches": self.people_also_searched,
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Results saved to: {filename}")

async def main():
    """Main function to run the scraper."""
    print("Google Search Scraper with Ad Detection\n=======================================")
    
    region_choice = ''
    while region_choice not in ['1', '2']:
        region_choice = input("Select search region:\n1. International (English)\n2. Turkey (Turkish)\nEnter choice (1 or 2): ").strip()
    
    region = 'en' if region_choice == '1' else 'tr'
    scraper = GoogleSearchScraper(region=region)
    
    keyword = input("\nEnter keyword to search: ").strip()
    if not keyword:
        print("Please enter a valid keyword.")
        return
    
    print(f"\nSearching Google for: '{keyword}'...\nThis may take a few moments...")
    
    try:
        await scraper.search_google(keyword)
        scraper.display_results(keyword)
        
        save_choice = input("\nSave results to JSON file? (y/n): ").strip().lower()
        if save_choice == 'y':
            scraper.save_to_json(keyword)
            
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
