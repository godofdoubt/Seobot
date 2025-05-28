# utils/seo_data_parser.py
import logging
import json
from datetime import datetime
import re
# Note: No Streamlit (st) imports here to keep these functions as pure utilities.
# Supabase client and other necessary dependencies are passed as arguments.

def parse_auto_suggestions(suggestions_text: str) -> dict:
    """
    Parse the auto-generated suggestions text into structured JSON format,
    with improved handling for embedded JSON blocks, various heading types,
    and prose content.
    
    Args:
        suggestions_text: Raw text from AI suggestion generation
        
    Returns:
        dict: Structured JSON with categorized suggestions.
    """
    try:
        structured_suggestions = {
            "introduction_prose": [],
            "seo_analysis": {},
            "content_creation_ideas": {},
            # "unclassified_body_prose": [], # Will be added if needed
            "generated_timestamp": datetime.now().isoformat(),
            "raw_suggestions": suggestions_text # Keep raw text for reference
        }
        
        temp_suggestions_text = suggestions_text

        # 1. Handle embedded JSON block for content creation ideas
        json_block_outer_pattern = re.compile(
            r"(^\s*\*\*(?:[^\*\n]*?(?:İÇERİK OLUŞTURMA|CONTENT CREATION|İÇERİK GÖREVLERİ|CONTENT TASKS)[^\*\n]*?)\*\*\s*\n)?(```json\s*([\s\S]*?)\s*```)",
            re.IGNORECASE | re.MULTILINE
        )
        
        json_block_match = json_block_outer_pattern.search(temp_suggestions_text)
        
        if json_block_match:
            logging.info("JSON block found in suggestions.")
            full_match_text = json_block_match.group(0)
            json_content_str = json_block_match.group(3)

            try:
                parsed_json_data = json.loads(json_content_str)
                logging.info("Successfully parsed JSON block.")
                # Merging parsed_json_data into content_creation_ideas
                # This handles various keys like "article_content_tasks", "product_content_tasks" etc.
                for key, value in parsed_json_data.items():
                    structured_suggestions["content_creation_ideas"][key] = value
                
                structured_suggestions["content_creation_ideas"]["_source"] = "json_block"
                temp_suggestions_text = temp_suggestions_text.replace(full_match_text, "", 1)
                
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse JSON block from suggestions: {e}")
                structured_suggestions["content_creation_ideas"]["parsing_error_detail"] = f"JSON block parsing failed: {e}"
                # If JSON parsing fails, it might be processed by the text parser if it resembles text structure.

        # 2. Process the remaining text part
        lines = temp_suggestions_text.split('\n')
        current_section_key = None       # e.g., "seo_analysis"
        current_subsection_key = None    # e.g., "technical_issues"
        
        accumulated_item_lines = []
        body_processing_started = False # True once the first known text heading is processed

        # Expanded pattern for various section headings
        block_heading_pattern = re.compile(
            r"^\s*\*\*(?:\d+\.\s*)?"
            r"(ÖZET ANALİZ|SUMMARY ANALYSIS|"
            r"GELİŞMİŞ SEO VE İÇERİK STRATEJİSİ ÖNERİLERİ|ADVANCED SEO AND CONTENT STRATEGY RECOMMENDATIONS|"
            r"SAYFA İÇİ SEO|ON-PAGE SEO|"
            r"SAYFA DIŞI SEO|OFF-PAGE SEO|"
            r"TEKNİK SEO|TECHNICAL SEO|"
            r"İÇERİK STRATEJİSİ|CONTENT STRATEGY|"
            r"İÇERİK ÖNERİLERİ|CONTENT RECOMMENDATIONS|" # More general content recommendations
            r"PERFORMANS|PERFORMANCE INSIGHTS|" # Performance can be too broad, use PERFORMANCE INSIGHTS for clarity
            r"ANAHTAR KELİME|KEYWORD OPPORTUNITIES|" # Keyword can be too broad
            r"EK ÖNERİLER|ADDITIONAL RECOMMENDATIONS|"
            r"SEO ANALİZİ)" # General SEO Analysis heading
            r"(?:.*?)\*\*\s*$",
            re.IGNORECASE
        )

        def flush_accumulated_item_to_structure():
            nonlocal accumulated_item_lines
            if accumulated_item_lines and current_section_key and current_subsection_key:
                target_section = structured_suggestions.get(current_section_key)
                if isinstance(target_section, dict):
                    target_list = target_section.get(current_subsection_key)
                    if isinstance(target_list, list):
                        full_item_text = "\n".join(line.strip() for line in accumulated_item_lines if line.strip()).strip()
                        if full_item_text:
                            target_list.append(full_item_text)
                    else:
                        logging.warning(f"Attempted to add item to non-list subsection: {current_section_key}.{current_subsection_key}")
                else:
                     logging.warning(f"Attempted to add item to non-dict section: {current_section_key}")
            accumulated_item_lines = []

        for line in lines:
            line_stripped = line.strip()

            if not line_stripped: # Blank line
                flush_accumulated_item_to_structure()
                continue

            heading_match = block_heading_pattern.match(line_stripped)
            if heading_match:
                flush_accumulated_item_to_structure()
                body_processing_started = True
                
                heading_text_upper = heading_match.group(1).upper()
                current_section_key = "seo_analysis" # Most text headings will fall under SEO analysis

                new_subsection_key = None
                if any(kw in heading_text_upper for kw in ["ÖZET ANALİZ", "SUMMARY ANALYSIS"]):
                    new_subsection_key = "summary_analysis_details"
                elif any(kw in heading_text_upper for kw in ["GELİŞMİŞ SEO VE İÇERİK STRATEJİSİ ÖNERİLERİ", "ADVANCED SEO AND CONTENT STRATEGY RECOMMENDATIONS"]):
                    new_subsection_key = "strategy_overview"
                elif any(kw in heading_text_upper for kw in ["SAYFA İÇİ SEO", "ON-PAGE SEO"]):
                    new_subsection_key = "on_page_seo"
                elif any(kw in heading_text_upper for kw in ["SAYFA DIŞI SEO", "OFF-PAGE SEO"]):
                    new_subsection_key = "off_page_seo"
                elif any(kw in heading_text_upper for kw in ["TEKNİK SEO", "TECHNICAL SEO"]):
                    new_subsection_key = "technical_issues"
                elif any(kw in heading_text_upper for kw in ["İÇERİK STRATEJİSİ", "CONTENT STRATEGY"]):
                    new_subsection_key = "content_strategy"
                elif any(kw in heading_text_upper for kw in ["İÇERİK ÖNERİLERİ", "CONTENT RECOMMENDATIONS"]): # General term
                    new_subsection_key = "general_content_recommendations"
                elif any(kw in heading_text_upper for kw in ["PERFORMANS", "PERFORMANCE INSIGHTS"]):
                    new_subsection_key = "performance_insights"
                elif any(kw in heading_text_upper for kw in ["ANAHTAR KELİME", "KEYWORD OPPORTUNITIES"]):
                    new_subsection_key = "keyword_opportunities"
                elif any(kw in heading_text_upper for kw in ["EK ÖNERİLER", "ADDITIONAL RECOMMENDATIONS"]):
                    new_subsection_key = "additional_recommendations"
                elif "SEO ANALİZİ" in heading_text_upper: # Broad "SEO Analysis" heading
                     new_subsection_key = "general_seo_analysis_notes"
                else: # Fallback for a matched heading pattern without specific keyword mapping
                    # This case should be rare if pattern is comprehensive
                    normalized_fallback_key = re.sub(r'\W+', '_', heading_text_upper.lower()) + "_details"
                    new_subsection_key = normalized_fallback_key
                    logging.info(f"Heading '{line_stripped}' mapped to new subsection: '{new_subsection_key}'.")

                current_subsection_key = new_subsection_key
                structured_suggestions[current_section_key].setdefault(current_subsection_key, [])
                continue

            # If not a heading:
            if not body_processing_started:
                if line_stripped:
                    structured_suggestions["introduction_prose"].append(line_stripped)
                continue

            # If body_processing_started and not a heading:
            is_list_item_start = line_stripped.startswith(('-', '•', '*'))
            
            if is_list_item_start:
                flush_accumulated_item_to_structure() 
                accumulated_item_lines.append(line_stripped.lstrip('-•* '))
            elif accumulated_item_lines: # Continuing a multi-line list item
                accumulated_item_lines.append(line_stripped)
            elif current_section_key and current_subsection_key: # Prose line within an active section/subsection
                if line_stripped:
                    # Ensure subsection list exists (should have been by heading processing)
                    if isinstance(structured_suggestions.get(current_section_key), dict) and \
                       isinstance(structured_suggestions[current_section_key].get(current_subsection_key), list):
                        structured_suggestions[current_section_key][current_subsection_key].append(line_stripped)
                    else: # Should not happen if logic is correct
                        logging.warning(f"Prose line '{line_stripped}' could not be added. Target {current_section_key}.{current_subsection_key} invalid.")
                        structured_suggestions.setdefault("unclassified_body_prose", []).append(f"[Context Lost: {current_section_key}.{current_subsection_key}] {line_stripped}")
            elif line_stripped: # Fallback for unclassified prose after body_processing_started
                structured_suggestions.setdefault("unclassified_body_prose", []).append(line_stripped)
                logging.debug(f"Line '{line_stripped}' added to 'unclassified_body_prose'.")
        
        flush_accumulated_item_to_structure() # Ensure the last item is processed

        # Clean up empty lists from initial structure or dynamically added, but preserve special keys
        special_keys = ["raw_suggestions", "parsing_error_detail", "generated_timestamp", "_source"]
        
        if not structured_suggestions["introduction_prose"]:
            del structured_suggestions["introduction_prose"]
        if "unclassified_body_prose" in structured_suggestions and not structured_suggestions["unclassified_body_prose"]:
            del structured_suggestions["unclassified_body_prose"]

        for section_name, section_data in list(structured_suggestions.items()): # Iterate copy for safe deletion
            if section_name in special_keys: continue

            if isinstance(section_data, dict):
                for sub_key in list(section_data.keys()):
                    if sub_key not in special_keys and isinstance(section_data[sub_key], list) and not section_data[sub_key]:
                        del section_data[sub_key]
                if not section_data and section_name not in ["content_creation_ideas"]: # Keep content_creation_ideas even if empty, for consistency
                    del structured_suggestions[section_name]
            elif isinstance(section_data, list) and not section_data:
                 del structured_suggestions[section_name] # e.g. empty introduction_prose

        return structured_suggestions
        
    except Exception as e:
        logging.error(f"Critical error in parse_auto_suggestions: {str(e)}", exc_info=True)
        # Fallback structure in case of major error
        return {
            "seo_analysis": {"raw_content_on_error": suggestions_text, "parsing_error": f"Outer parser error: {str(e)}"},
            "content_creation_ideas": {"raw_content_on_error": suggestions_text, "parsing_error": f"Outer parser error: {str(e)}"},
            "generated_timestamp": datetime.now().isoformat(),
            "parsing_error": f"Outer parser error: {str(e)}",
            "raw_suggestions": suggestions_text
        }

def load_auto_suggestions_from_supabase(url: str, supabase_client, parse_fn) -> dict | None:
    """
    Load existing auto-generated suggestions from Supabase for a given URL.
    
    Args:
        url: The URL to check for existing suggestions
        supabase_client: An initialized Supabase client instance
        parse_fn: The parsing function (e.g., parse_auto_suggestions)
        
    Returns:
        dict or None: Structured suggestions if found, None otherwise
    """
    try:
        if not supabase_client:
            logging.warning("Supabase client not available for loading suggestions.")
            return None
            
        response = supabase_client.table('seo_reports').select('auto_suggestions').eq('url', url).maybe_single().execute()
        
        if response.data and response.data.get('auto_suggestions'):
            auto_suggestions_data = response.data['auto_suggestions']
            # Ensure it's a dict, parse if it's a string
            if isinstance(auto_suggestions_data, str):
                try:
                    auto_suggestions_data = json.loads(auto_suggestions_data)
                except json.JSONDecodeError as je:
                    logging.error(f"Error decoding JSON from Supabase auto_suggestions for {url}: {je}")
                    # Fallback: try to parse it as if it's raw text
                    return parse_fn(auto_suggestions_data) 
            
            logging.info(f"Loaded existing auto suggestions for URL: {url}")
            return auto_suggestions_data
        
        logging.info(f"No existing auto suggestions found in Supabase for URL: {url}")
        return None
        
    except Exception as e:
        logging.error(f"Error loading auto suggestions from Supabase for {url}: {str(e)}")
        return None

def save_auto_suggestions_to_supabase(url: str, structured_suggestions: dict, supabase_client, user_id: str | None = None) -> bool:
    """
    Save auto-generated suggestions to Supabase.
    
    Args:
        url: The URL these suggestions are for
        structured_suggestions: The structured JSON suggestions to save
        supabase_client: An initialized Supabase client instance
        user_id: The ID of the user, if applicable for inserts/RLS (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not supabase_client:
            logging.warning("Supabase client not available for saving suggestions.")
            return False
        
        update_data = {
            'auto_suggestions': structured_suggestions,
            'auto_suggestions_timestamp': datetime.now().isoformat()
        }
        
        response = supabase_client.table('seo_reports').update(update_data).eq('url', url).execute()
        
        if response.data and len(response.data) > 0:
            logging.info(f"Successfully saved/updated auto suggestions in Supabase for URL: {url}")
            return True
        else:
            logging.warning(f"Failed to save auto suggestions to Supabase for URL: {url}. Response: {response.error if response.error else 'No data returned'}")
            # Attempt to insert if update failed (basic upsert logic)
            # This assumes user_id is available and needed for insert if RLS or table constraints demand it.
            if user_id: # Example: Only attempt insert if user_id is known AND relevant for your schema
                insert_data = {
                    'url': url,
                    # 'user_id': user_id, # Uncomment if 'user_id' is a required column
                    'auto_suggestions': structured_suggestions,
                    'auto_suggestions_timestamp': datetime.now().isoformat(),
                    'timestamp': datetime.now().isoformat() # Ensure timestamp for new records
                    # Add other necessary fields for a new record if any, e.g. 'report': {}
                }
                # This is a simplified insert. A robust upsert is more complex.
                # For this example, we focus on the update path.
                # insert_response = supabase_client.table('seo_reports').insert(insert_data).execute()
                # if insert_response.data and len(insert_response.data) > 0:
                #    logging.info(f"Successfully inserted auto suggestions for new URL: {url}")
                #    return True
                # else:
                #    logging.warning(f"Insert attempt also failed for {url}. Error: {insert_response.error}")
                logging.info(f"Update failed for {url}. An insert attempt could be made here if schema supports it and base record is missing (user_id provided: {bool(user_id)}).")
            return False
            
    except Exception as e:
        logging.error(f"Error saving auto suggestions to Supabase for {url}: {str(e)}")
        return False