import re
#from collections import Counter
import logging
from datetime import datetime
import getpass
import os
from urllib.parse import urlparse
#import analyzer.config as config 
from typing import List, Optional  # For type hinting

# Module-level logger for better log organization
logger = logging.getLogger(__name__)
logger.debug(f"DEBUG LOGGING TEST FROM TOP OF methods.py. Effective level: {logger.getEffectiveLevel()}") # NEW TEST LINE




def get_current_user():
    """Get current user's login name"""
    try:
        return getpass.getuser()
    except Exception:
        return os.getenv('USER') or os.getenv('USERNAME') or 'unknown_user'


def get_formatted_datetime():
    """Get current datetime in UTC"""
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def validate_url(url):
    """Validate and normalize URL"""
    if not url:
        return None
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            logging.warning(f"Invalid URL structure after attempting to normalize: {url}")
            return None
        return url.strip()
    except Exception as e:
        logging.error(f"Error validating or parsing URL '{url}': {e}")
        return None   




def normalize_turkish_text(text: str) -> str:
    """
    Normalize Turkish text by handling specific issues:
    1. Fix 'i letişim' -> 'iletişim' type of errors
    2. Properly process Turkish characters
    """
    # Fix spaces before punctuation
    text = re.sub(r'\s+([,.!?:;])', r'\1', text)
    
    # Fix mis-spaced Turkish words
    text = re.sub(r'([a-zçğıöşü])\s+([a-zçğıöşü])', lambda m: 
            f"{m.group(1)} {m.group(2)}" if len(m.group(1)) == 1 or len(m.group(2)) == 1
            else f"{m.group(1)}{m.group(2)}", text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

# In analyzer/methods.py

# ... (other imports, logger definition) ...

def _remove_snippets_from_text_internal(text: str, snippets_to_remove: Optional[List[str]]) -> str:
    """
    Internal helper to remove a list of text snippets from a larger text string.
    Uses case-insensitive matching, ensuring snippets are not part of larger words.
    """
    modified_text = text
    if not snippets_to_remove or not text:
        #logger.debug("In _remove_snippets_from_text_internal: No snippets or no text, returning early.")
        return text
    
    # Check if any snippet in the list is actually non-empty after stripping
    actual_snippets_to_process = [s for s in snippets_to_remove if s and s.strip()]
    if not actual_snippets_to_process:
        #logger.debug(f"In _remove_snippets_from_text_internal: Snippets list provided, but all are empty/whitespace. Original snippets: {snippets_to_remove}")
        return text
        
    for snippet_content in actual_snippets_to_process:
        # snippet_content is already stripped and verified non-empty here
        try:
            # Using lookarounds to ensure the snippet is not part of a larger "word"
            # (?<!\w) - not preceded by a word character (allows start of string or punctuation/space before)
            # (?!\w) - not followed by a word character (allows end of string or punctuation/space after)
            escaped_snippet = re.escape(snippet_content) # No .strip() needed here, done above
            pattern = r'(?<!\w)' + escaped_snippet + r'(?!\w)'
            
            # Log the pattern being used for this specific snippet
            #logger.debug(f"Attempting to remove snippet with pattern: {pattern} (from original: '{snippet_content[:50]}...')")

            # Store length BEFORE modification for optional logging
            original_len_before_sub = len(modified_text)

            # Perform the actual modification 
            modified_text = re.sub(pattern, '', modified_text, flags=re.IGNORECASE | re.UNICODE)

            #if len(modified_text) != original_len_before_sub:
              #  logger.debug(f"Snippet '{snippet_content[:50]}...' REMOVED. Text length change: {original_len_before_sub} -> {len(modified_text)}")
            #else:
             #   logger.debug(f"Snippet '{snippet_content[:50]}...' NOT found/removed with pattern '{pattern}'.")

        except re.error as e:
            logger.warning(f"Regex error while trying to remove snippet '{snippet_content[:50]}...': {e}")
            pass 
    
    # Clean up multiple spaces that might result from removals and trim
    modified_text = re.sub(r'\s{2,}', ' ', modified_text).strip()
    return modified_text

def extract_text(text: str, 
                 header_snippets: Optional[List[str]] = None, 
                 footer_snippets: Optional[List[str]] = None) -> str:
    """
    Extracts and cleans text. Optionally removes provided header and footer snippets
    after initial normalization but before aggressive character stripping.
    """
    logger.debug(f"extract_text CALLED. Has headers: {bool(header_snippets)}, Has footers: {bool(footer_snippets)}")
    if header_snippets: logger.debug(f"Header snippets received: {header_snippets}")
    if footer_snippets: logger.debug(f"Footer snippets received: {footer_snippets}")

    if not text or len(text.strip()) < 10: 
        return "" 
    
    processed_text = normalize_turkish_text(text)
    processed_text = re.sub(r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})(?=\d{1,2}[/.-])', r'\1 ', processed_text)
    
    text_for_hf_removal = processed_text
    original_length_for_debug = len(text_for_hf_removal)

    if header_snippets:
        logger.debug(f"Attempting to remove headers. Text length before: {len(text_for_hf_removal)}")
        text_for_hf_removal = _remove_snippets_from_text_internal(text_for_hf_removal, header_snippets)
        logger.debug(f"Text length after header removal: {len(text_for_hf_removal)}")
        
    if footer_snippets:
        logger.debug(f"Attempting to remove footers. Text length before: {len(text_for_hf_removal)}")
        text_for_hf_removal = _remove_snippets_from_text_internal(text_for_hf_removal, footer_snippets)
        logger.debug(f"Text length after footer removal: {len(text_for_hf_removal)}")
        
    if (header_snippets or footer_snippets) and logger.isEnabledFor(logging.DEBUG):
        if original_length_for_debug != len(text_for_hf_removal):
            logger.debug(f"Overall text length changed by H/F removal: {original_length_for_debug} -> {len(text_for_hf_removal)}")
        elif any(s and s.strip() for s in (header_snippets or [])) or \
             any(s and s.strip() for s in (footer_snippets or [])):
            logger.debug(f"Text length ({original_length_for_debug}) not changed by H/F removal, though non-empty snippets were provided (may indicate no matches, or snippets were all empty).")

    cleaned_text = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', text_for_hf_removal) 
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip() 
    
    return cleaned_text

