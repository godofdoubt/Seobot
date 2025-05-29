# utils/seo_data_parser.py
import logging
import json
from datetime import datetime
import re
# Note: No Streamlit (st) imports here to keep these functions as pure utilities.
# Supabase client and other necessary dependencies are passed as arguments.

def parse_auto_suggestions(suggestions_text: str) -> dict:
    """
    Parse the AI-generated suggestions text, focusing on extracting the JSON block
    for content tasks and capturing surrounding text.
    
    Args:
        suggestions_text: Raw text from AI suggestion generation
        
    Returns:
        dict: Structured JSON with content tasks and surrounding prose.
    """
    try:
        structured_suggestions = {
            "pre_json_prose": None, # Text before the JSON block
            "content_creation_ideas": {}, # Parsed JSON tasks
            "post_json_prose": None, # Text after the JSON block
            "generated_timestamp": datetime.now().isoformat(),
            # "raw_suggestions" is intentionally removed as per requirement
        }
        
        # Pattern to find the JSON block and capture text before and after.
        # This pattern assumes the JSON block is enclosed in ```json ... ```
        json_block_pattern = re.compile(
            r"^(.*?)(```json\s*([\s\S]*?)\s*```)(.*)$",
            re.DOTALL | re.MULTILINE
        )
        
        match = json_block_pattern.search(suggestions_text)
        
        if match:
            logging.info("JSON block found in suggestions.")
            pre_json_text = match.group(1).strip()
            json_content_str = match.group(3).strip() # This is the content within ```json ... ```
            post_json_text = match.group(4).strip()

            if pre_json_text:
                structured_suggestions["pre_json_prose"] = pre_json_text
            
            if post_json_text:
                structured_suggestions["post_json_prose"] = post_json_text

            try:
                parsed_json_data = json.loads(json_content_str)
                logging.info("Successfully parsed JSON block.")
                # Merging parsed_json_data into content_creation_ideas
                for key, value in parsed_json_data.items():
                    structured_suggestions["content_creation_ideas"][key] = value
                
                structured_suggestions["content_creation_ideas"]["_source"] = "json_block"
                
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse JSON block from suggestions: {e}")
                structured_suggestions["content_creation_ideas"]["parsing_error_detail"] = f"JSON block parsing failed: {e}"
                structured_suggestions["content_creation_ideas"]["raw_unparsed_json_block"] = json_content_str
        else:
            logging.warning("No JSON block (```json ... ```) found in suggestions_text. Treating all text as pre-prose.")
            # If no JSON block, all text goes to pre_json_prose.
            # content_creation_ideas will be empty or indicate no block was found.
            if suggestions_text and suggestions_text.strip():
                 structured_suggestions["pre_json_prose"] = suggestions_text.strip()
            structured_suggestions["content_creation_ideas"]["_source"] = "no_json_block_found"

        # Clean up: remove prose fields if they are None or empty strings after strip
        if not structured_suggestions.get("pre_json_prose"): # Use .get for safety
            if "pre_json_prose" in structured_suggestions: del structured_suggestions["pre_json_prose"]
        if not structured_suggestions.get("post_json_prose"): # Use .get for safety
            if "post_json_prose" in structured_suggestions: del structured_suggestions["post_json_prose"]
        
        # Ensure content_creation_ideas is not removed even if empty, for consistency.
        if not structured_suggestions["content_creation_ideas"]: # e.g. if no json block and it was empty
             structured_suggestions["content_creation_ideas"] = {"_source": "no_json_block_found_or_empty"}


        return structured_suggestions
        
    except Exception as e:
        logging.error(f"Critical error in parse_auto_suggestions: {str(e)}", exc_info=True)
        # Fallback structure in case of major error
        return {
            "content_creation_ideas": {"parsing_error": f"Outer parser error: {str(e)}"},
            "generated_timestamp": datetime.now().isoformat(),
            "parsing_error_outer": f"Outer parser error: {str(e)}",
            "failed_input_text_on_error": suggestions_text # Store the problematic input
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
            # Ensure it's a dict, parse if it's a string (e.g. old format or error)
            if isinstance(auto_suggestions_data, str):
                try:
                    # First, try to load as JSON directly (if it was stored as a JSON string)
                    loaded_data = json.loads(auto_suggestions_data)
                    if isinstance(loaded_data, dict): # Check if it's a dictionary as expected
                        auto_suggestions_data = loaded_data
                    else: # If not a dict, it's likely raw text needing full parsing by parse_fn
                        logging.info(f"Loaded auto_suggestions for {url} as string, but not a dict. Re-parsing with parse_fn.")
                        auto_suggestions_data = parse_fn(auto_suggestions_data)
                except json.JSONDecodeError as je:
                    logging.warning(f"Error decoding JSON from Supabase auto_suggestions for {url}: {je}. Attempting to parse with parse_fn.")
                    # Fallback: try to parse it as if it's raw text using the provided parse_fn
                    auto_suggestions_data = parse_fn(auto_suggestions_data) 
            
            # At this point, auto_suggestions_data should be a dictionary
            # (either loaded directly, or parsed from string by json.loads or parse_fn)
            # We ensure it has the expected top-level keys for the new structure if it was an old format.
            # However, if it's already structured (new or old), we use it.
            # The main check is that it's a dict.
            if not isinstance(auto_suggestions_data, dict):
                 logging.error(f"Auto suggestions for {url} could not be resolved to a dictionary. Data: {auto_suggestions_data}")
                 return None # Or attempt one last parse_fn if it somehow became a string again.

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
            'auto_suggestions': structured_suggestions, # This will be a dict
            'auto_suggestions_timestamp': datetime.now().isoformat()
        }
        
        response = supabase_client.table('seo_reports').update(update_data).eq('url', url).execute()
        
        if response.data and len(response.data) > 0:
            logging.info(f"Successfully saved/updated auto suggestions in Supabase for URL: {url}")
            return True
        else:
            logging.warning(f"Failed to save auto suggestions to Supabase for URL: {url}. Response: {response.error if response.error else 'No data returned'}")
            # Attempt to insert if update failed (basic upsert logic)
            if user_id: 
                insert_data = {
                    'url': url,
                    # 'user_id': user_id, # Uncomment if 'user_id' is a required column
                    'auto_suggestions': structured_suggestions,
                    'auto_suggestions_timestamp': datetime.now().isoformat(),
                    'timestamp': datetime.now().isoformat() 
                }
                logging.info(f"Update failed for {url}. An insert attempt could be made here if schema supports it and base record is missing (user_id provided: {bool(user_id)}). This part is illustrative.")
            return False
            
    except Exception as e:
        logging.error(f"Error saving auto suggestions to Supabase for {url}: {str(e)}")
        return False