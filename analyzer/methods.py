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
logger = logging.getLogger(__name__) # This will be 'analyzer.methods'
logger.debug(f"DEBUG LOGGING TEST FROM TOP OF methods.py. Effective level: {logger.getEffectiveLevel()}")


def remove_specific_fixed_phrases(text: str, phrases_to_remove: List[str]) -> str:
    """
    Removes a list of specific, fixed string phrases from text.
    Uses case-insensitive matching and handles surrounding whitespace.
    """
    modified_text = text
    if not phrases_to_remove or not text:
        return text

    for phrase in phrases_to_remove:
        if phrase and phrase.strip(): # Ensure phrase is not empty
            try:
                # Pattern to match the phrase, potentially surrounded by whitespace,
                # and replace it with a single space to avoid joining words.
                # re.escape is crucial if phrases can contain special regex characters.
                pattern = r'\s*' + re.escape(phrase.strip()) + r'\s*'
                modified_text = re.sub(pattern, ' ', modified_text, flags=re.IGNORECASE | re.UNICODE)
            except re.error as e:
                logger.warning(f"Regex error while trying to remove fixed phrase '{phrase[:50]}...': {e}")
                # Continue with the next phrase
    
    # Consolidate multiple spaces that might result from removals and trim the ends.
    return re.sub(r'\s{2,}', ' ', modified_text).strip()


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
    Uses case-insensitive matching. It intelligently decides whether to use strict
    word boundaries (for single words) or a more flexible substring match (for phrases).
    """
    modified_text = text
    if not snippets_to_remove or not text:
        return text

    actual_snippets_to_process = [s for s in snippets_to_remove if s and s.strip()]
    if not actual_snippets_to_process:
        logger.debug(f"In _remove_snippets_from_text_internal: Snippets list provided, but all are empty/whitespace. Original snippets: {snippets_to_remove}")
        return text

    for snippet_content in actual_snippets_to_process:
        try:
            escaped_snippet = re.escape(snippet_content)
            
            # Use strict word boundaries ONLY for single-word snippets.
            # For multi-word phrases, a simple substring match is more robust.
            if ' ' in snippet_content:
                # It's a phrase, do a direct substring match. More reliable for sentences.
                pattern = escaped_snippet
                logger.debug(f"Using PHRASE removal pattern for snippet: '{snippet_content[:70]}...'")
            else:
                # It's a single word, use strict word boundaries to avoid partial matches.
                pattern = r'(?<!\w)' + escaped_snippet + r'(?!\w)'
                logger.debug(f"Using WORD removal pattern: {pattern} for snippet: '{snippet_content[:70]}...'")

            original_len_before_sub = len(modified_text)

            # Perform the actual modification. Replace with a space to prevent merging adjacent words.
            modified_text = re.sub(pattern, ' ', modified_text, flags=re.IGNORECASE | re.UNICODE)

            if len(modified_text) != original_len_before_sub:
                logger.debug(f"Snippet '{snippet_content[:50]}...' REMOVED. Text length change: {original_len_before_sub} -> {len(modified_text)}")
            else:
                logger.debug(f"Snippet '{snippet_content[:50]}...' NOT found/removed with its pattern.")

        except re.error as e:
            logger.warning(f"Regex error while trying to remove snippet '{snippet_content[:50]}...': {e}")
            pass # Continue with the next snippet

    # Clean up multiple spaces that might result from removals and trim
    modified_text = re.sub(r'\s{2,}', ' ', modified_text).strip()
    return modified_text


def _remove_stop_words(text: str, stop_words: set) -> str:
    """
    Remove stop words and stop phrases from text while preserving word boundaries.
    Uses case-insensitive matching. Handles both individual words and longer phrases.
    """
    if not text or not stop_words:
        return text
    
    modified_text = text
    original_word_count = len(text.split())
    
    # Separate single words from phrases
    single_words = set()
    phrases = set()
    
    for item in stop_words:
        if ' ' in item.strip():
            phrases.add(item.strip().lower())
        else:
            single_words.add(item.strip().lower())
    
    # First, remove longer phrases (more specific matches first)
    if phrases:
        logger.debug(f"Removing {len(phrases)} stop phrases from text")
        for phrase in sorted(phrases, key=len, reverse=True):  # Process longer phrases first
            if phrase:
                try:
                    # Use word boundaries to ensure we don't match partial words
                    escaped_phrase = re.escape(phrase)
                    pattern = r'\b' + escaped_phrase + r'\b'
                    modified_text = re.sub(pattern, ' ', modified_text, flags=re.IGNORECASE | re.UNICODE)
                except re.error as e:
                    logger.warning(f"Regex error while removing stop phrase '{phrase}': {e}")
    
    # Then, remove individual stop words
    if single_words:
        logger.debug(f"Removing {len(single_words)} individual stop words from text")
        words = modified_text.split()
        filtered_words = []
        
        for word in words:
            # Clean the word for comparison (remove punctuation for checking)
            clean_word = re.sub(r'[^\w\'-çğıöşüÇĞİÖŞÜ]', '', word).lower()
            
            # Keep the word if it's not a stop word
            if clean_word and clean_word not in single_words:
                filtered_words.append(word)
        
        modified_text = ' '.join(filtered_words)
    
    # Clean up multiple spaces and trim
    modified_text = re.sub(r'\s+', ' ', modified_text).strip()
    
    final_word_count = len(modified_text.split()) if modified_text else 0
    logger.debug(f"Stop words filtering: {original_word_count} words -> {final_word_count} words remaining")
    
    return modified_text


def extract_text(text: str,
                 header_snippets: Optional[List[str]] = None,
                 footer_snippets: Optional[List[str]] = None,
                 needless_info_snippets: Optional[List[str]] = None,
                 remove_stop_words: bool = True) -> str:
    """
    Extracts and cleans text. First, it applies aggressive character stripping to match the
    cleaning level of LLM-derived snippets. Then, it removes provided header, footer,
    and needless_info snippets from this base-cleaned text. Finally, optionally removes
    common stop words.
    """
    # Import stop words from config
    try:
        from analyzer.config import COMMON_STOP_WORDS
    except ImportError:
        logger.warning("Could not import COMMON_STOP_WORDS from analyzer.config, using fallback set")
        COMMON_STOP_WORDS = set() # Fallback to an empty set
      
    
    logger.debug(f"extract_text CALLED. Original text length: {len(text)}. Has headers: {bool(header_snippets)}, Has footers: {bool(footer_snippets)}, Has needless_info: {bool(needless_info_snippets)}, Remove stop words: {remove_stop_words}")
    if header_snippets: logger.debug(f"Header snippets received: {[s[:100] + '...' if len(s) > 100 else s for s in header_snippets]}")
    if footer_snippets: logger.debug(f"Footer snippets received: {[s[:100] + '...' if len(s) > 100 else s for s in footer_snippets]}")
    if needless_info_snippets: logger.debug(f"Needless info snippets received: {[s[:100] + '...' if len(s) > 100 else s for s in needless_info_snippets]}")


    if not text or len(text.strip()) < 10:
        logger.debug("extract_text: Text is too short or empty, returning empty string.")
        return ""

    # --- START: CORRECTED LOGIC ---

    # Helper function to ensure snippets are cleaned identically to the main text.
    def _clean_snippet_list(snippets: Optional[List[str]]) -> Optional[List[str]]:
        if not snippets:
            return None
        cleaned_snippets = []
        for s in snippets:
            if s and s.strip():
                # **FIX**: Apply the exact same multi-step cleaning process to the snippet
                # Step 1: Normalize Turkish text and spacing (THIS WAS THE MISSING STEP)
                normalized_s = normalize_turkish_text(s)
                
                # Step 2: Aggressively strip characters, same as the main text
                cleaned_s = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', normalized_s)
                
                # Step 3: Consolidate whitespace
                cleaned_s = re.sub(r'\s+', ' ', cleaned_s).strip()

                if cleaned_s:
                    cleaned_snippets.append(cleaned_s)
        return cleaned_snippets

    # 1. Initial text processing (Normalization, specific regex fixes)
    processed_text = normalize_turkish_text(text)
    processed_text = re.sub(r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})(?=\d{1,2}[/.-])', r'\1 ', processed_text)
    logger.debug(f"Text after initial normalization (first 200 chars): '{processed_text[:200]}'")

    # 2. Aggressive character stripping on the main text
    # This brings the current 'text' to the same "cleaning level" as the snippets will be.
    text_after_aggressive_stripping = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', processed_text)
    text_after_aggressive_stripping = re.sub(r'\s+', ' ', text_after_aggressive_stripping).strip()
    logger.debug(f"Text after aggressive char stripping (first 200 chars): '{text_after_aggressive_stripping[:200]}'")

    # 3. Clean all incoming snippet lists to ensure a like-for-like comparison
    cleaned_header_snippets = _clean_snippet_list(header_snippets)
    cleaned_footer_snippets = _clean_snippet_list(footer_snippets)
    cleaned_needless_info_snippets = _clean_snippet_list(needless_info_snippets)
    
    # 4. Apply the CLEANED H/F/N snippets to the aggressively stripped text
    text_for_final_processing = text_after_aggressive_stripping
    original_length_for_debug = len(text_for_final_processing)
    
    if cleaned_header_snippets:
        logger.debug(f"Attempting to remove CLEANED headers. Text length before: {len(text_for_final_processing)}")
        text_for_final_processing = _remove_snippets_from_text_internal(text_for_final_processing, cleaned_header_snippets)
        logger.debug(f"Text length after header removal: {len(text_for_final_processing)}. Text sample: '{text_for_final_processing[:200]}'")

    if cleaned_footer_snippets:
        logger.debug(f"Attempting to remove CLEANED footers. Text length before: {len(text_for_final_processing)}")
        text_for_final_processing = _remove_snippets_from_text_internal(text_for_final_processing, cleaned_footer_snippets)
        logger.debug(f"Text length after footer removal: {len(text_for_final_processing)}. Text sample: '{text_for_final_processing[:200]}'")

    if cleaned_needless_info_snippets:
        logger.debug(f"Attempting to remove CLEANED needless info. Text length before: {len(text_for_final_processing)}")
        text_for_final_processing = _remove_snippets_from_text_internal(text_for_final_processing, cleaned_needless_info_snippets)
        logger.debug(f"Text length after needless info removal: {len(text_for_final_processing)}. Text sample: '{text_for_final_processing[:200]}'")
    
    # --- END: CORRECTED LOGIC ---
    
    if (header_snippets or footer_snippets or needless_info_snippets) and logger.isEnabledFor(logging.DEBUG):
        if original_length_for_debug != len(text_for_final_processing):
            logger.debug(f"Overall text length changed by H/F/needless_info removal: {original_length_for_debug} -> {len(text_for_final_processing)}")
        elif any(s and s.strip() for s in (header_snippets or [])) or \
             any(s and s.strip() for s in (footer_snippets or [])) or \
             any(s and s.strip() for s in (needless_info_snippets or [])):
            logger.debug(f"Text length ({original_length_for_debug}) not changed by H/F/needless_info removal, though non-empty snippets were provided (may indicate no matches, or snippets were all empty).")
    
    # 5. Remove stop words if requested
    if remove_stop_words:
        logger.debug(f"Attempting to remove stop words. Text length before: {len(text_for_final_processing)}")
        text_for_final_processing = _remove_stop_words(text_for_final_processing, COMMON_STOP_WORDS)
        logger.debug(f"Text length after stop words removal: {len(text_for_final_processing)}. Text sample: '{text_for_final_processing[:200]}'")
    
    # 6. Final text is already cleaned of extra spaces by previous functions
    final_cleaned_text = text_for_final_processing
    logger.debug(f"Final cleaned text length: {len(final_cleaned_text)}. Sample: '{final_cleaned_text[:200]}'")

    return final_cleaned_text