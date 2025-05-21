import logging
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from urllib.parse import urlparse, urlunparse
from analyzer.methods import get_formatted_datetime, get_current_user
import analyzer.config as config

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class SEOReportSaver:
    def __init__(self):
        self.supabase = supabase

    def standardize_url(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'https://' + url
            parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        standardized = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
        return standardized

    def format_analysis_results(self, analysis):
        if not analysis:
            return "Analysis failed or no results available."

        output = []
        output.append(f"Current Date and Time (UTC): {get_formatted_datetime()}")
        output.append(f"Current User's Login: {get_current_user()}")
        output.append("\n" + "="*80)
        
        output.append(f"\nSEO Analysis Report for: {analysis.get('url', 'Unknown URL')}")
        output.append(f"Analysis Time: {analysis.get('timestamp', 'Unknown')}")
        output.append(f"Analysis Duration: {analysis.get('analysis_duration_seconds', 'N/A')} seconds")
        output.append("\n" + "="*50 + "\n")

        if analysis.get('sitemap_found'):
            output.append("SITEMAP INFORMATION:")
            output.append(f"- Sitemap Found: Yes")
            output.append(f"- Number of Sitemap URLs: {analysis.get('sitemap_urls_discovered_count', 0)}")
            output.append(f"- Number of Pages in Sitemap: {analysis.get('sitemap_pages_processed_count', 0)}")
        else:
            output.append("SITEMAP INFORMATION:")
            output.append(f"- Sitemap Found: No")
            output.append("\n" + "-"*50 + "\n")

        crawled_count = analysis.get('crawled_internal_pages_count', 0)
        output.append(f"CRAWLING STATS:")
        output.append(f"- Pages Analyzed: {crawled_count}")

        # Main URL Details section - now using llm_analysis directly to avoid duplication
        main_url = analysis.get('url', 'Unknown URL')
        output.append(f"DETAILS FOR START PAGE: {main_url}")
        
        # We use main page's cleaned text from llm_analysis rather than page_statistics
        if analysis.get('llm_analysis') and analysis['llm_analysis'].get('cleaned_text'): 
            cleaned = analysis['llm_analysis'].get('cleaned_text', '')
            output.append("\nCLEANED TEXT (First 500 chars):")
            if cleaned:
                output.append(f"- {cleaned[:500]}{'...' if len(cleaned) > 500 else ''}")

        if analysis.get('llm_analysis'): 
            llm_data = analysis.get('llm_analysis', {})
            output.append("\nLLM ANALYSIS (MAIN PAGE):")
            if llm_data.get("error"):
                 output.append(f"- Error: {llm_data.get('error')}")
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
            
            header_snippets = llm_data.get('header', [])
            if header_snippets:
                 output.append(f"- Identified Header Snippets: {', '.join(header_snippets[:5])}{'...' if len(header_snippets) > 5 else ''}")
            footer_snippets = llm_data.get('footer', [])
            if footer_snippets:
                 output.append(f"- Identified Footer Snippets: {', '.join(footer_snippets[:5])}{'...' if len(footer_snippets) > 5 else ''}")

        output.append("\n\nINDIVIDUAL INTERNAL PAGE DETAILS Will be Available after Full Analysis (if enabled).")
        output.append("This is the Main page report. Please Wait Until Full Analyze Finishes for sitewide details.")

        if analysis.get('crawled_urls'):
            output.append("\n\n" + "="*50)
            output.append("\nLIST OF CRAWLED URLS (Up to 20 shown):")
            output.append("="*50)
            for i, crawled_url in enumerate(analysis['crawled_urls'][:20]):
                output.append(f"{i+1}. {crawled_url}")
            if len(analysis['crawled_urls']) > 20:
                output.append(f"... and {len(analysis['crawled_urls']) - 20} more URLs")

        return "\n".join(output)


    async def save_reports(self, analysis: dict):
        try:
            if not analysis:
                logging.error("Cannot save reports: Analysis data is empty or None")
                return {"success": False, "report_id": None, "error": "Analysis data is empty"}

            original_url = analysis['url']
            standardized_url = self.standardize_url(original_url)
            logging.info(f"Standardized URL for {original_url}: {standardized_url}")

            # Ensure the main URL is not duplicated in both llm_analysis and page_statistics
            if 'page_statistics' in analysis and analysis['url'] in analysis['page_statistics']:
                logging.info(f"Removing main URL {analysis['url']} from page_statistics to avoid duplication")
                del analysis['page_statistics'][analysis['url']]

            existing = await asyncio.to_thread(
                self.supabase.table('seo_reports').select('id').eq('url', standardized_url).execute
            )
            if existing.data:
                report_id = existing.data[0]['id']
                logging.info(f"Report for {standardized_url} already exists with ID {report_id}.")
                return {"success": True, "report_id": report_id, "existing": True}

            # Ensure LLM analysis is properly included in the report JSONB
            llm_analysis_data = analysis.get('llm_analysis')
            if not llm_analysis_data:
                logging.warning(f"LLM analysis for main page {standardized_url} was not found in the provided analysis object. Adding default LLM data.")
                llm_analysis_data = {
                    "url": standardized_url,
                    "error": "LLM analysis not available or failed during initial processing in seo.py.",
                    "keywords": [], "content_summary": "", "other_information_and_contacts": [], 
                    "suggested_keywords_for_seo": [], "header": [], "footer": []
                }
                analysis['llm_analysis'] = llm_analysis_data
            elif llm_analysis_data.get("error"):
                logging.error(f"Pre-computed LLM analysis for {standardized_url} contains an error: {llm_analysis_data.get('error')}")
            else:
                logging.info(f"Using pre-computed LLM analysis for {standardized_url} from seo.py")
            
            try:
                text_report = self.format_analysis_results(analysis)
            except Exception as e:
                logging.error(f"Error generating text report for {standardized_url}: {e}")
                text_report = f"Error generating text report: {str(e)}\nLLM Analysis part might be missing or incomplete due to this."

            data = {
                'url': standardized_url,
                'timestamp': analysis['timestamp'],
                'report': analysis,  # This already contains 'llm_analysis'
                'text_report': text_report,
                # No separate llm_analysis field - we use the one embedded in 'report'
            }

            response = await asyncio.to_thread(
                self.supabase.table('seo_reports').insert(data).execute
            )

            if hasattr(response, 'error') and response.error:
                logging.error(f"Failed to save report to Supabase: {response.error}")
                return {"success": False, "report_id": None, "error": str(response.error)}
            elif hasattr(response, 'data') and response.data:
                report_id = response.data[0]['id']
                logging.info(f"Reports saved to Supabase for {standardized_url} with ID {report_id}")
                return {"success": True, "report_id": report_id, "existing": False}
            else:
                logging.warning(f"Report saving status uncertain for {standardized_url}. Response: {response}")
                return {"success": False, "report_id": None, "error": "Uncertain response from database"}

        except Exception as e:
            logging.error(f"Error saving reports to Supabase for {analysis.get('url', 'Unknown URL')}: {e}", exc_info=True)
            return {"success": False, "report_id": None, "error": str(e)}