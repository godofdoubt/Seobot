# utils/seo_analyzer.py

import asyncio
from urllib.parse import urlparse
from utils.GREV1 import GoogleSearchScraper

def get_normalized_domain(url: str) -> str:
    """
    Extracts and normalizes the domain from a URL.
    Example: 'https://www.example.co.uk/path' -> 'example.co.uk'
    """
    if not url:
        return ""
    try:
        if '://' not in url:
            url = 'http://' + url
        
        domain = urlparse(url).netloc
        if domain.startswith('www.'):
            return domain[4:]
        return domain
    except Exception:
        return ""

async def analyze_keyword_difficulty(user_url: str, keyword: str, region: str = 'en'):
    """
    Performs a Google search and analyzes the results to find competitors,
    advertisers, and estimate keyword difficulty.
    Returns a formatted string with the analysis report.
    """
    analysis_lines = [
        f"## 🚀 SERP Analysis for Keyword: '{keyword}'",
        f"### Comparing against URL: `{user_url}` (Region: {region.upper()})\n"
    ]
    
    user_domain = get_normalized_domain(user_url)
    if not user_domain:
        return "❌ **Error:** Could not parse a valid domain from the provided URL."

    # 1. Scrape Google
    scraper = GoogleSearchScraper(region=region)
    try:
        await scraper.search_google(keyword)
    except Exception as e:
        return f"❌ **An error occurred during the scrape:**\n\n`{str(e)}`"

    # --- Analysis Step ---
    organic_results = scraper.results
    ad_results = scraper.ads
    related_searches = scraper.people_also_searched

    # 2. Get competitor list
    competitors = []
    user_url_found_in_top_7 = False
    for result in organic_results:
        result_domain = get_normalized_domain(result.get('url', ''))
        if result_domain and result_domain == user_domain:
            user_url_found_in_top_7 = True
            break
    
    if user_url_found_in_top_7:
        analysis_lines.append("\n✅ **Your domain was found in the top 7 organic results!**")
        for result in organic_results:
            result_domain = get_normalized_domain(result.get('url', ''))
            if result_domain and result_domain != user_domain:
                competitors.append(result)
    else:
        analysis_lines.append("\n⚠️ **Your domain was NOT found in the top 7 organic results.**")
        competitors = organic_results[:5]

    # 3. Get advertisers URL list
    advertisers = [ad for ad in ad_results if get_normalized_domain(ad.get('url', '')) != user_domain][:3]

    # 4. Get estimated level of difficulty for the keyword
    difficulty_score = 0
    score_breakdown = []

    # Rule: Ads on page
    if ad_results:
        points = 15 * min(len(ad_results), 4)
        difficulty_score += points
        score_breakdown.append(f"+{points} ({len(ad_results)} ads found - high commercial intent)")
    else:
        score_breakdown.append("+0 (No ads found - lower commercial intent)")

    # Rule: User URL not found
    if not user_url_found_in_top_7:
        difficulty_score += 50
        score_breakdown.append("+50 (Your domain is not in the top 7)")
    else:
        difficulty_score -= 25
        score_breakdown.append("-25 (Bonus: Your domain is in the top 7!)")

    # Rule: Keyword length
    word_count = len(keyword.split())
    if word_count == 1:
        difficulty_score += 40
        score_breakdown.append("+40 (Single-word keyword - highly competitive)")
    elif word_count in [2, 3]:
        difficulty_score += 20
        score_breakdown.append("+20 (Short-tail keyword)")
    else:
        score_breakdown.append("+0 (Long-tail keyword - less competitive)")

    # Rule: Related searches count
    if not related_searches:
        difficulty_score += 15
        score_breakdown.append("+15 (No related searches found - very niche term)")
    else:
        penalty = -min(len(related_searches), 10)
        difficulty_score += penalty
        score_breakdown.append(f"{penalty} ({len(related_searches)} related searches found - indicates user interest)")

    # Normalize score and determine level
    difficulty_score = max(0, difficulty_score)
    if difficulty_score < 30: difficulty_level = "Low"
    elif difficulty_score < 60: difficulty_level = "Medium"
    elif difficulty_score < 90: difficulty_level = "High"
    else: difficulty_level = "Very High"

    # --- Build Display String ---
    analysis_lines.extend([
        "\n" + "="*30,
        "### 📊 SEO Analysis Results",
        "="*30,
        f"\n**📉 Estimated Keyword Difficulty: {difficulty_score} / ~150 ({difficulty_level})**",
        "*(Note: Lower score is better. This is a simplified estimation.)*",
        "\n**Score Breakdown:**"
    ])
    for item in score_breakdown:
        analysis_lines.append(f"  - {item}")

    analysis_lines.append(f"\n**🏆 Top Organic Competitors (max 5)**")
    if competitors:
        for i, competitor in enumerate(competitors, 1):
            analysis_lines.append(f"{i}. **{competitor['title']}**\n   - URL: `{competitor['url']}`")
    else:
        analysis_lines.append("   - No other organic competitors found.")

    analysis_lines.append(f"\n**💰 Top Advertisers (max 3)**")
    if advertisers:
        for i, advertiser in enumerate(advertisers, 1):
            analysis_lines.append(f"{i}. **{advertiser['title']}**\n   - URL: `{advertiser.get('url', 'N/A')}`")
    else:
        analysis_lines.append("   - No competing advertisers found.")
    
    analysis_lines.append("\n" + "="*30)

    return "\n".join(analysis_lines)