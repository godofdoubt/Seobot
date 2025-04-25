import logging
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from analyzer.methods import get_formatted_datetime, get_current_user

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

        # Crawling statistics - NEW SECTION
        crawled_count = analysis.get('crawled_internal_pages_count', 0)
        output.append(f"CRAWLING STATS: {crawled_count + 1} pages analyzed (main page + {crawled_count} internal pages)")
    
        # Content Length Statistics - NEW SECTION
        if 'content_length_stats' in analysis:
            cl_stats = analysis['content_length_stats']
            output.append("\nCONTENT LENGTH STATISTICS:")
            output.append(f"Total Content: {cl_stats.get('total', 0):,} characters across all pages")
            output.append(f"Average: {cl_stats.get('average', 0):.0f} characters per page")
            output.append(f"Min: {cl_stats.get('min', 0):,} characters")
            output.append(f"Max: {cl_stats.get('max', 0):,} characters")
            output.append(f"Median: {cl_stats.get('median', 0):,} characters")

        # Word Count Statistics - NEW SECTION
        if 'word_count_stats' in analysis:
            wc_stats = analysis['word_count_stats']
            output.append("\nWORD COUNT STATISTICS:")
            output.append(f"Total Words: {wc_stats.get('total', 0):,} words across all pages")
            output.append(f"Average: {wc_stats.get('average', 0):.0f} words per page")
            output.append(f"Min: {wc_stats.get('min', 0):,} words")
            output.append(f"Max: {wc_stats.get('max', 0):,} words")
            output.append(f"Median: {wc_stats.get('median', 0):,} words")

        output.append("\n" + "="*50 + "\n")

        # Keywords Section - Now includes aggregated keywords
        output.append("KEYWORD ANALYSIS:")
        output.append(f"Keywords aggregated from {crawled_count + 1} pages")
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
            output.append('  "no categories found"')

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

        # Content Stats of main page
        output.append("\nMAIN PAGE CONTENT STATISTICS:")
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

        # Individual Page Statistics - NEW SECTION
        if 'page_statistics' in analysis and len(analysis['page_statistics']) > 1:  # More than just the main URL
            output.append("\n" + "="*50)
            output.append("\nINDIVIDUAL PAGE STATISTICS:")
            output.append("\nContent length by page (Top 10):")
        
            # Sort pages by content length (descending)
            page_stats = analysis['page_statistics']
            sorted_pages = sorted(
                page_stats.items(), 
                key=lambda x: x[1].get('content_length', 0), 
                reverse=True
            )
        
            # Display top 10 pages by content length
            for i, (page_url, stats) in enumerate(sorted_pages[:10]):
                output.append(f"{i+1}. {page_url}")
                output.append(f"   - Content Length: {stats.get('content_length', 0):,} characters")
                output.append(f"   - Word Count: {stats.get('word_count', 0):,} words")
        
            # Mention if there are more pages
            if len(sorted_pages) > 10:
                output.append(f"... and {len(sorted_pages) - 10} more pages")

        # List of crawled URLs - NEW SECTION
        if analysis.get('crawled_urls'):
            output.append("\n" + "="*50)
            output.append("\nCRAWLED URLS:")
            for i, crawled_url in enumerate(analysis['crawled_urls'][:10]):
                output.append(f"{i+1}. {crawled_url}")
            if len(analysis['crawled_urls']) > 10:
                output.append(f"... and {len(analysis['crawled_urls']) - 10} more URLs")

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