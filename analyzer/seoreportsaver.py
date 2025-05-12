import logging
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from urllib.parse import urlparse, urlunparse
from analyzer.methods import get_formatted_datetime, get_current_user, semantic_analyze
import analyzer.config as config
import nltk
# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client globally
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



class SEOReportSaver:
    def __init__(self):
        """Initialize with the global Supabase client."""
        self.supabase = supabase

    def standardize_url(self, url: str) -> str:
        """Standardize the URL by ensuring it has a protocol and removing trailing slashes."""
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'https://' + url
            parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        standardized = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
        return standardized

    def format_analysis_results(self, analysis):
        """Format analysis results for text output, including semantic analysis for cleaned text."""
        if not analysis:
            return "Analysis failed or no results available."

        output = []
        # Header with datetime and user info
        output.append(f"Current Date and Time (UTC): {get_formatted_datetime()}")
        output.append(f"Current User's Login: {get_current_user()}")
        output.append("\n" + "="*80)
        
        # Basic Site Info
        output.append(f"\nSEO Analysis Report for: {analysis.get('url', 'Unknown URL')}")
        output.append(f"Analysis Time: {analysis.get('timestamp', 'Unknown')}")
        output.append(f"Analysis Duration: {analysis.get('analysis_duration_seconds', 'N/A')} seconds")
        output.append("\n" + "="*50 + "\n")

        # Sitemap Information
        if analysis.get('sitemap_found'):
            output.append("SITEMAP INFORMATION:")
            output.append(f"- Sitemap Found: Yes")
            output.append(f"- Number of Sitemap URLs: {analysis.get('sitemap_urls_count', 0)}")
            output.append(f"- Number of Pages in Sitemap: {analysis.get('sitemap_pages_count', 0)}")
        else:
            output.append("SITEMAP INFORMATION:")
            output.append(f"- Sitemap Found: No")
        output.append("\n" + "-"*50 + "\n")

        # Crawling statistics
        crawled_count = analysis.get('crawled_internal_pages_count', 0)
        discovered_links = len(analysis.get('links', {}).get('internal_links', [])) if 'links' in analysis else 0
        output.append(f"CRAWLING STATS:")
        output.append(f"- Pages Analyzed: {crawled_count}")
        output.append(f"- Internal Links Discovered: {discovered_links}")

        # Content Length Statistics
        if 'content_length_stats' in analysis and analysis['content_length_stats']:
            cl_stats = analysis['content_length_stats']
            output.append("\nOVERALL CONTENT LENGTH STATISTICS:")
            output.append(f"- Total Content: {cl_stats.get('total', 0):,} characters across {cl_stats.get('pages_analyzed', 0)} pages")
            output.append(f"- Average: {cl_stats.get('average', 0):.0f} characters per page")
            output.append(f"- Min: {cl_stats.get('min', 0):,} characters")
            output.append(f"- Max: {cl_stats.get('max', 0):,} characters")
            output.append(f"- Median: {cl_stats.get('median', 0):,} characters")

        # Word Count Statistics
        if 'word_count_stats' in analysis and analysis['word_count_stats']:
            wc_stats = analysis['word_count_stats']
            output.append("\nOVERALL WORD COUNT STATISTICS:")
            output.append(f"- Total Words: {wc_stats.get('total', 0):,} words across {wc_stats.get('pages_analyzed', 0)} pages")
            output.append(f"- Average: {wc_stats.get('average', 0):.0f} words per page")
            output.append(f"- Min: {wc_stats.get('min', 0):,} words")
            output.append(f"- Max: {wc_stats.get('max', 0):,} words")
            output.append(f"- Median: {wc_stats.get('median', 0):,} words")

        output.append("\n" + "="*50 + "\n")

        # Aggregated Keywords Section
        keyword_count = len(analysis.get('aggregated_keywords', {}))
        output.append("AGGREGATED KEYWORD ANALYSIS (Site-Wide):")
        output.append(f"Top {keyword_count} keywords aggregated from {crawled_count} analyzed pages")
        agg_keywords = analysis.get('aggregated_keywords', {})
        if agg_keywords:
            sorted_agg_keywords = sorted(agg_keywords.items(), key=lambda x: x[1], reverse=True)
            output.append("Top Keywords by Page Frequency:")
            keyword_list = [f"{kw} ({freq})" for kw, freq in sorted_agg_keywords]
            cols = 3
            lines = [" | ".join(keyword_list[i:i+cols]) for i in range(0, len(keyword_list), cols)]
            output.extend(lines)
        else:
            output.append("No aggregated keywords found.")

        output.append("\n" + "="*50 + "\n")

        # DETAILS FOR START PAGE
        output.append(f"DETAILS FOR START PAGE: {analysis.get('url', 'Unknown URL')}")
        start_stats = analysis.get('page_statistics', {}).get(analysis.get('url'), {})
        
        # Cleaned Text
        cleaned = start_stats.get('cleaned_text', '')
        output.append("\nCLEANED TEXT (First 500 chars):")
        if cleaned:
            output.append(f"- {cleaned[:500]}{'...' if len(cleaned) > 500 else ''}")

            # Semantic Analysis Section
            sem = semantic_analyze(cleaned)
            output.append("\nSEMANTIC ANALYSIS:")
            # Show POS tag sample
            pos_sample = sem.get('pos_tags', [])[:10]
            output.append(f"- POS Tags (first 10): {pos_sample}")
            # Show lemmas sample
            lemma_sample = sem.get('lemmas', [])[:10]
            output.append(f"- Lemmas (first 10): {lemma_sample}")
            # Optionally show synonyms for first few lemmas
            syn_sample = {lem: sem['synonyms'].get(lem, []) for lem in lemma_sample[:5]}
            output.append(f"- Synonyms (sample): {syn_sample}")
        else:
            output.append("- No cleaned text available.")

        # NEW SECTION: Extracted Information
        output.append("\nEXTRACTED INFORMATION:")
        extracted_info = start_stats.get('extracted_info', {})
        if extracted_info:
            # Phone Numbers
            if extracted_info.get('phone_numbers'):
                output.append(f"- Phone Numbers: {', '.join(extracted_info['phone_numbers'][:10])}")
                if len(extracted_info['phone_numbers']) > 10:
                    output.append(f"  ...and {len(extracted_info['phone_numbers']) - 10} more")
            
            # Emails
            if extracted_info.get('emails'):
                output.append(f"- Email Addresses: {', '.join(extracted_info['emails'][:10])}")
                if len(extracted_info['emails']) > 10:
                    output.append(f"  ...and {len(extracted_info['emails']) - 10} more")
            
            # URLs
            if extracted_info.get('urls'):
                output.append(f"- URLs: {', '.join(extracted_info['urls'][:10])}")
                if len(extracted_info['urls']) > 10:
                    output.append(f"  ...and {len(extracted_info['urls']) - 10} more")
            
            # Prices
            if extracted_info.get('prices'):
                output.append(f"- Prices: {', '.join(extracted_info['prices'][:10])}")
                if len(extracted_info['prices']) > 10:
                    output.append(f"  ...and {len(extracted_info['prices']) - 10} more")
            
            # Dates
            if extracted_info.get('dates'):
                output.append(f"- Dates: {', '.join(extracted_info['dates'][:10])}")
                if len(extracted_info['dates']) > 10:
                    output.append(f"  ...and {len(extracted_info['dates']) - 10} more")
            
            # Numbers
            if extracted_info.get('numbers'):
                output.append(f"- Numbers: {', '.join(extracted_info['numbers'][:10])}")
                if len(extracted_info['numbers']) > 10:
                    output.append(f"  ...and {len(extracted_info['numbers']) - 10} more")
        else:
            output.append("- No extracted information available.")

        # Keywords
        start_keywords = start_stats.get('keywords', [])
        output.append("\nKEYWORDS (Top 5):")
        if start_keywords:
            kw_list = start_keywords[:5]
            output.append(f"- {', '.join(kw_list)}")
        else:
            output.append("- No keywords extracted for this page.")

        # --- INDIVIDUAL PAGE STATISTICS (excluding start page) ---
        if 'page_statistics' in analysis and len(analysis['page_statistics']) > 1:
            output.append("\n\n" + "="*80)
            output.append("\nINDIVIDUAL INTERNAL PAGE DETAILS (Sample)")
            output.append("="*80)

            page_stats = analysis['page_statistics']
            main_url = analysis.get('url')
            sorted_internal_pages = sorted(
                [(k, v) for k, v in page_stats.items() if k != main_url],
                key=lambda item: item[0]
            )

            sample_size = min(10, len(sorted_internal_pages))
            for i, (page_url, stats) in enumerate(sorted_internal_pages[:sample_size]):
                output.append(f"\n--- Page {i+1}: {page_url} ---")
                output.append(f"  Content: {stats.get('content_length', 0):,} chars, {stats.get('word_count', 0):,} words")

                # Cleaned Text
                cleaned_text = stats.get('cleaned_text', '')
                output.append("  Cleaned Text (First 500 chars):")
                if cleaned_text:
                    output.append(f"  - {cleaned_text[:500]}{'...' if len(cleaned_text) > 500 else ''}")
                    
                    # Semantic Analysis Section
                    sem = semantic_analyze(cleaned_text)
                    output.append("\n  SEMANTIC ANALYSIS:")
                    # Show POS tag sample
                    pos_sample = sem.get('pos_tags', [])[:10]
                    output.append(f"  - POS Tags (first 10): {pos_sample}")
                    # Show lemmas sample
                    lemma_sample = sem.get('lemmas', [])[:10]
                    output.append(f"  - Lemmas (first 10): {lemma_sample}")
                    # Optionally show synonyms for first few lemmas
                    syn_sample = {lem: sem['synonyms'].get(lem, []) for lem in lemma_sample[:5]}
                    output.append(f"  - Synonyms (sample): {syn_sample}")
                else:
                    output.append("  - No cleaned text available.")
                
                # NEW SECTION: Extracted Information for each page
                output.append("\n  EXTRACTED INFORMATION:")
                page_extracted_info = stats.get('extracted_info', {})
                if page_extracted_info:
                    # Phone Numbers
                    if page_extracted_info.get('phone_numbers'):
                        output.append(f"  - Phone Numbers: {', '.join(page_extracted_info['phone_numbers'][:5])}")
                        if len(page_extracted_info['phone_numbers']) > 5:
                            output.append(f"    ...and {len(page_extracted_info['phone_numbers']) - 5} more")
                    
                    # Emails
                    if page_extracted_info.get('emails'):
                        output.append(f"  - Email Addresses: {', '.join(page_extracted_info['emails'][:5])}")
                        if len(page_extracted_info['emails']) > 5:
                            output.append(f"    ...and {len(page_extracted_info['emails']) - 5} more")
                    
                    # Other important extracted info (shortened for internal pages)
                    info_counts = {
                        'URLs': len(page_extracted_info.get('urls', [])),
                        'Prices': len(page_extracted_info.get('prices', [])),
                        'Dates': len(page_extracted_info.get('dates', [])),
                        'Numbers': len(page_extracted_info.get('numbers', []))
                    }
                    output.append(f"  - Other: {', '.join([f'{k}: {v}' for k, v in info_counts.items() if v > 0])}")
                else:
                    output.append("  - No extracted information available.")
                
                # Filtered_words
                filtered_words = stats.get('filtered_words', '')
                output.append("\n  Filtered (First 500 chars):")
                if filtered_words:
                    output.append(f"  - {filtered_words[:500]}{'...' if len(filtered_words) > 500 else ''}")
                else:
                    output.append("  - No filtered_words available.")     

                # Keywords
                page_keywords = stats.get('keywords', [])
                output.append("\n  Keywords (Top 5):")
                if page_keywords:
                    kw_list = page_keywords[:5]
                    output.append(f"  - {', '.join(kw_list)}")
                else:
                    output.append("  - None extracted.")

                # Headings
                page_headings = stats.get('headings', {})
                if page_headings and 'stats' in page_headings:
                    h_stats = page_headings['stats']
                    output.append("\n  Headings:")
                    h_summary = []
                    for h_level in range(1, 7):
                        h_tag = f'h{h_level}_count'
                        if h_stats.get(h_tag, 0) > 0:
                            h_summary.append(f"H{h_level}:{h_stats.get(h_tag, 0)}")
                    if h_summary:
                        output.append(f"  - Counts: {', '.join(h_summary)}")
                    else:
                        output.append("  - None found.")
                else:
                    output.append("\n  Headings: Not analyzed")

        # List of crawled URLs
        if analysis.get('crawled_urls'):
            output.append("\n\n" + "="*50)
            output.append("\nLIST OF ANALYZED URLS:")
            output.append("="*50)
            for i, crawled_url in enumerate(analysis['crawled_urls'][:20]):
                output.append(f"{i+1}. {crawled_url}")
            if len(analysis['crawled_urls']) > 20:
                output.append(f"... and {len(analysis['crawled_urls']) - 20} more URLs")

        return "\n".join(output)

    async def save_reports(self, analysis):
        """Save analysis reports to Supabase, avoiding duplicates and ensuring text_report is set."""
        try:
            if not analysis:
                logging.error("Cannot save reports: Analysis data is empty or None")
                return False

            original_url = analysis['url']
            standardized_url = self.standardize_url(original_url)
            logging.info(f"Standardized URL for {original_url}: {standardized_url}")

            # Check for existing report using standardized URL
            existing = await asyncio.to_thread(
                self.supabase.table('seo_reports').select('id').eq('url', standardized_url).execute
            )
            if existing.data:
                logging.info(f"Report for {standardized_url} already exists. Skipping insertion.")
                return False

            # Generate text report with error handling
            try:
                text_report = self.format_analysis_results(analysis)
            except Exception as e:
                logging.error(f"Error generating text report for {standardized_url}: {e}")
                text_report = f"Error generating text report: {str(e)}"

            # Prepare data for Supabase using standardized URL
            data = {
                'url': standardized_url,
                'timestamp': analysis['timestamp'],
                'report': analysis,
                'text_report': text_report,
            }

            # Insert into Supabase
            response = await asyncio.to_thread(
                self.supabase.table('seo_reports').insert(data).execute
            )

            if hasattr(response, 'error') and response.error:
                logging.error(f"Failed to save report to Supabase: {response.error}")
                return False
            elif hasattr(response, 'data') and response.data:
                logging.info(f"Reports saved to Supabase for {standardized_url}")
                return True
            else:
                logging.warning(f"Report saving status uncertain for {standardized_url}. Response: {response}")
                return False

        except Exception as e:
            logging.error(f"Error saving reports to Supabase for {original_url}: {e}")
            return False