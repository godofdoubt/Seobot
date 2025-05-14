import logging
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from urllib.parse import urlparse, urlunparse
from analyzer.methods import get_formatted_datetime, get_current_user
import analyzer.config as config
from analyzer.llm_analysis_start import llm_analysis_start
#import subprocess
# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client globally
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
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

    
        # DETAILS FOR START PAGE
        output.append(f"DETAILS FOR START PAGE: {analysis.get('url', 'Unknown URL')}")
        start_stats = analysis.get('page_statistics', {}).get(analysis.get('url'), {})
        
        # Cleaned Text
        cleaned = start_stats.get('cleaned_text', '')
        output.append("\nCLEANED TEXT (First 750 chars):")
        if cleaned:
            output.append(f"- {cleaned[:500]}{'...' if len(cleaned) > 750 else ''}")

        # LLM Analysis (if available)
        if analysis.get('llm_analysis'):
            llm_data = analysis.get('llm_analysis', {})
            output.append("\nLLM ANALYSIS:")
            output.append(f"- Content Summary: {llm_data.get('content_summary', 'Not available')}")
            
            keywords = llm_data.get('keywords', [])
            if keywords:
                output.append(f"- Keywords: {', '.join(keywords)}")
            
            seo_keywords = llm_data.get('suggested_keywords_for_seo', [])
            if seo_keywords:
                output.append(f"- Suggested SEO Keywords: {', '.join(seo_keywords)}")
            
            contacts = llm_data.get('other_information_and_contacts', [])
            if contacts:
                output.append(f"- Contact Information: {', '.join(contacts)}")
            

        # --- INDIVIDUAL PAGE STATISTICS (excluding start page) ---
     #   if 'page_statistics' in analysis and len(analysis['page_statistics']) > 1:
     #       output.append("\n\n" + "="*80)
            output.append("\nINDIVIDUAL INTERNAL PAGE DETAILS Will be Aviable after Full Analysis")
      #      output.append("="*80)

         #   page_stats = analysis['page_statistics']
          #  main_url = analysis.get('url')
           # sorted_internal_pages = sorted(
            #    [(k, v) for k, v in page_stats.items() if k != main_url],
             #   key=lambda item: item[0]
            #)

            #sample_size = min(10, len(sorted_internal_pages))
            #for i, (page_url, stats) in enumerate(sorted_internal_pages[:sample_size]):
            #    output.append(f"\n--- Page {i+1}: {page_url} ---")
             #   output.append(f"  Content: {stats.get('content_length', 0):,} chars, {stats.get('word_count', 0):,} words")

                # Cleaned Text
           #     cleaned_text = stats.get('cleaned_text', '')
            output.append("This is the Main page report.Please Wait Until Full Analyze Finish")
             #   if cleaned_text:
              #      output.append(f"  - {cleaned_text[:750]}{'...' if len(cleaned_text) > 750 else ''}")
                    
                # Headings
               # page_headings = stats.get('headings', {})
                #if page_headings and 'stats' in page_headings:
                 #   h_stats = page_headings['stats']
                  #  output.append("\n  Headings:")
                   # h_summary = []
                    #for h_level in range(1, 7):
                     #   h_tag = f'h{h_level}_count'
                      #  if h_stats.get(h_tag, 0) > 0:
                       #     h_summary.append(f"H{h_level}:{h_stats.get(h_tag, 0)}")
                    #if h_summary:
                     #   output.append(f"  - Counts: {', '.join(h_summary)}")
                    #else:
                     #   output.append("  - None found.")
                #else:
                 #   output.append("\n  Headings: Not analyzed")

        # List of crawled URLs
        if analysis.get('crawled_urls'):
            output.append("\n\n" + "="*50)
            output.append("\nLIST OF CRAWLED URLS:")
            output.append("="*50)
            for i, crawled_url in enumerate(analysis['crawled_urls'][:20]):
                output.append(f"{i+1}. {crawled_url}")
            if len(analysis['crawled_urls']) > 20:
                output.append(f"... and {len(analysis['crawled_urls']) - 20} more URLs")

        return "\n".join(output)

    async def save_reports(self, analysis):
        """
        Save analysis reports to Supabase, avoiding duplicates and ensuring text_report is set.
        
        Returns:
            dict: A dictionary containing success status and report_id if successful
        """
        try:
            if not analysis:
                logging.error("Cannot save reports: Analysis data is empty or None")
                return {"success": False, "report_id": None, "error": "Analysis data is empty"}

            original_url = analysis['url']
            standardized_url = self.standardize_url(original_url)
            logging.info(f"Standardized URL for {original_url}: {standardized_url}")

            # Check for existing report using standardized URL
            existing = await asyncio.to_thread(
                self.supabase.table('seo_reports').select('id').eq('url', standardized_url).execute
            )
            if existing.data:
                report_id = existing.data[0]['id']
                logging.info(f"Report for {standardized_url} already exists with ID {report_id}.")
                return {"success": True, "report_id": report_id, "existing": True}

            # Get LLM analysis for the main page
            llm_analysis_result = {}
            try:
                logging.info(f"Requesting LLM analysis for main page: {standardized_url}")
                llm_analysis_result = await llm_analysis_start(analysis)
                if not llm_analysis_result:
                    logging.warning(f"LLM analysis returned empty result for {standardized_url}")
                elif 'error' in llm_analysis_result:
                    logging.error(f"LLM analysis encountered an error: {llm_analysis_result.get('error')}")
                else:
                    logging.info(f"Successfully obtained LLM analysis for {standardized_url}")
                    # Add LLM analysis to the main analysis object for future reference
                    analysis['llm_analysis'] = llm_analysis_result
            except Exception as e:
                logging.error(f"Exception during LLM analysis for {standardized_url}: {e}")
                llm_analysis_result = {"error": f"Exception during LLM analysis: {str(e)}"}

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
                'llm_analysis': llm_analysis_result,
            }

            # Insert into Supabase
            response = await asyncio.to_thread(
                self.supabase.table('seo_reports').insert(data).execute
            )

            if hasattr(response, 'error') and response.error:
                logging.error(f"Failed to save report to Supabase: {response.error}")
                return {"success": False, "report_id": None, "error": str(response.error)}
            elif hasattr(response, 'data') and response.data:
                report_id = response.data[0]['id']
                logging.info(f"Reports saved to Supabase for {standardized_url} with ID {report_id}")
                # Trigger llm_analysis_end.py as a subprocess---------------------------------------------
               # try:
               #     subprocess.run(['python', 'analyzer/llm_analysis_end.py', str(report_id)], check=True)
                #    logging.info(f"Successfully triggered llm_analysis_end.py for report ID {report_id}")
                #except subprocess.CalledProcessError as e:
                #    logging.error(f"Failed to run llm_analysis_end.py: {e}")

               # return {"success": True, "report_id": report_id, "existing": False}
            else:
                logging.warning(f"Report saving status uncertain for {standardized_url}. Response: {response}")
                return {"success": False, "report_id": None, "error": "Uncertain response from database"}

        except Exception as e:
            logging.error(f"Error saving reports to Supabase for {original_url}: {e}")
            return {"success": False, "report_id": None, "error": str(e)}