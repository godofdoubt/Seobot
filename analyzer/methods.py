import re
from collections import Counter
import logging
from datetime import datetime
import getpass
import os
from urllib.parse import urlparse
import analyzer.config as config 
from typing import List, Optional  # For type hinting
#text i intial page content olarak değiştirebiliriz
# analyzer/methods.py




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




def _remove_snippets_from_text_internal(text: str, snippets_to_remove: Optional[List[str]]) -> str:
    """
    Internal helper to remove a list of text snippets from a larger text string.
    Uses case-insensitive, whole-word matching.
    """
    modified_text = text
    if not snippets_to_remove or not text or not any(s and s.strip() for s in snippets_to_remove):
        return text
        
    for snippet in snippets_to_remove:
        if snippet and snippet.strip(): # Ensure snippet is not None and not just whitespace
            try:
                # Using regex for case-insensitive, whole-word replacement
                # re.escape handles any special regex characters in the snippet
                pattern = r'\b' + re.escape(snippet.strip()) + r'\b'
                modified_text = re.sub(pattern, '', modified_text, flags=re.IGNORECASE | re.UNICODE)
            except re.error as e:
                # Log this error if you have logging configured for methods.py
                logging.warning(f"Regex error while trying to remove snippet '{snippet[:50]}...': {e}")
                pass # Continue with other snippets
    
    # Clean up multiple spaces that might result from removals and trim
    modified_text = re.sub(r'\s{2,}', ' ', modified_text).strip()
    return modified_text

def extract_text(text: str, 
                 header_snippets: Optional[List[str]] = None, 
                 footer_snippets: Optional[List[str]] = None) -> str:
    """
    Extracts and cleans text. Optionally removes provided header and footer snippets
    after initial cleaning.
    The original function snippet showed: return (cleaned_text ) which implies a string.
    """
    import re # Ensure re is imported if not at module level
    # from collections import Counter # Not used if only returning cleaned_text
    
    if not text or len(text.strip()) < 10: # Basic check for meaningful content
        return "" 
    
    # 1. Normalize text (e.g., Turkish character normalization)
    #    Your snippet included normalize_turkish_text, so we'll assume it's available
    processed_text = normalize_turkish_text(text)
    
    # 2. Date pattern adjustment (from your provided snippet)
    processed_text = re.sub(r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})(?=\d{1,2}[/.-])', r'\1 ', processed_text)
    
    # 3. Initial cleaning: remove non-alphanumeric (but keep specific chars), multiple spaces
    #    Keeping ' - and Turkish characters as per your snippet
    cleaned_text = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', processed_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip() # This is the line you mentioned
    
    # 4. Remove header snippets if provided
    #if header_snippets:
        # logging.debug(f"Attempting to remove headers. Text length before: {len(cleaned_text)}")
    cleaned_text = _remove_snippets_from_text_internal(cleaned_text, header_snippets)
        # logging.debug(f"Text length after header removal: {len(cleaned_text)}")
        
    # 5. Remove footer snippets if provided
    #if footer_snippets:
        # logging.debug(f"Attempting to remove footers. Text length before: {len(cleaned_text)}")
    cleaned_text = _remove_snippets_from_text_internal(cleaned_text, footer_snippets)
        # logging.debug(f"Text length after footer removal: {len(cleaned_text)}")
        
    # 6. Final clean-up of spaces that might have been introduced or left by removals
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text
