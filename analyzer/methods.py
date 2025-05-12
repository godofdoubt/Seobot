import re
from collections import Counter
import logging
from datetime import datetime
import getpass
import os
from urllib.parse import urlparse
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

# Download required NLTK data files if missing
def ensure_nltk_resource(resource_name, download_name=None):
    try:
        nltk.data.find(resource_name)
    except LookupError:
        nltk.download(download_name or resource_name.split('/')[-1])

# Ensure critical resources
ensure_nltk_resource('tokenizers/punkt', 'punkt')
ensure_nltk_resource('tokenizers/punkt_tab', 'punkt')  # punkt_tab is part of punkt
ensure_nltk_resource('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger')
ensure_nltk_resource('taggers/averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger_eng')  # NEW
ensure_nltk_resource('corpora/wordnet', 'wordnet')
ensure_nltk_resource('corpora/omw-1.4', 'omw-1.4')


import analyzer.config as config 


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


async def analyze_headings(page):
    """Extract and analyze heading tags from a page with their text content"""
    headings_data = await page.evaluate("""
        () => {
            const result = {
                h1: [],
                h2: [],
                h3: [],
                h4: [],
                h5: [],
                h6: []
            };
            
            const getHeadingInfo = (element) => {
                const text = element.textContent.trim();
                const id = element.id ? element.id : '';
                const classes = element.className ? element.className : '';
                return {
                    text: text,
                    id: id,
                    classes: classes
                };
            };
            
            for (let i = 1; i <= 6; i++) {
                const headings = document.querySelectorAll(`h${i}`);
                headings.forEach(heading => {
                    const headingInfo = getHeadingInfo(heading);
                    if (headingInfo.text) {
                        result[`h${i}`].push(headingInfo);
                    }
                });
            }
            
            return result;
        }
    """)
    
    headings_count = {
        'h1_count': len(headings_data.get('h1', [])),
        'h2_count': len(headings_data.get('h2', [])),
        'h3_count': len(headings_data.get('h3', [])),
        'h4_count': len(headings_data.get('h4', [])),
        'h5_count': len(headings_data.get('h5', [])),
        'h6_count': len(headings_data.get('h6', [])),
        'total_count': sum(len(headings_data.get(f'h{i}', [])) for i in range(1, 7))
    }
    
    return {
        'headings': headings_data,
        'stats': headings_count
    }


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


#text i intial page content olarak değiştirebiliriz
def extract_keywords(text: str, max_keywords: int = 20):
    """
    Extract top keywords and return cleaned text, along with other extracted information.
    Keywords are derived from text after removing identified entities (phones, emails, etc.).

    Returns a tuple (list of top `max_keywords` keywords, cleaned_text, filtered_words_str, extracted_info_dict).
    Uses COMMON_STOP_WORDS from config.
    """
    import re # Should be at the module level, but included here for function self-containment if copied
    from collections import Counter # Same as above

    if not text or len(text.strip()) < 10:
        logging.debug("Input text is too short or empty for keyword extraction.")
        return ([], "", "", {})

    # Step 1: Normalize the input text
    # This function should handle Turkish character normalization and basic spacing.
    normalized_text = normalize_turkish_text(text)
    logging.debug(f"Normalized text: {normalized_text[:200]}...")

    # Step 2: Extract informational content (phone numbers, emails, URLs, etc.)
    # These entities will be removed from the text before keyword tokenization.
    extracted_info = {
        'phone_numbers': [], 'emails': [], 'urls': [],
        'numbers': [], 'prices': [], 'dates': []
    }

    # Regex patterns for extraction
    phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?(?:\d{3}[-.\s]?)?\d{4}' # General phone pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[/\w\.-=%&]*)?'
    www_pattern = r'www\.(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[/\w\.-=%&]*)?' # URLs starting with www
    price_pattern = r'(?:[$€£¥₺]\s*\d+(?:[.,]\d+){0,2})|(?:\d+(?:[.,]\d+){0,2}\s*[$€£¥₺])|(?:\d+(?:[.,]\d+){0,2}\s*(?:USD|EUR|GBP|JPY|TRY|TL|usd|eur|gbp|jpy|try|tl))'
    date_pattern_numeric = r'\b(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})|(?:\d{4}[/.-]\d{1,2}[/.-]\d{1,2})\b'
    date_pattern_month = r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|Oca(?:k)?|Şub(?:at)?|Mar(?:t)?|Nis(?:an)?|May(?:ıs)?|Haz(?:iran)?|Tem(?:muz)?|Ağu(?:stos)?|Eyl(?:ül)?|Eki(?:m)?|Kas(?:ım)?|Ara(?:lık)?)[.,\s]+\s*\d{1,2}(?:[.,\s]+\s*\d{2,4})?\b'
    number_pattern = r'\b\d{1,3}(?:[,.]\d{3})*(?:[.,]\d+)?\b' # General number pattern

    extracted_info['phone_numbers'] = list(set(re.findall(phone_pattern, normalized_text)))
    extracted_info['emails'] = list(set(re.findall(email_pattern, normalized_text)))
    extracted_info['urls'] = list(set(re.findall(url_pattern, normalized_text) + re.findall(www_pattern, normalized_text)))
    extracted_info['prices'] = list(set(re.findall(price_pattern, normalized_text, re.IGNORECASE)))
    extracted_info['dates'] = list(set(re.findall(date_pattern_numeric, normalized_text) + re.findall(date_pattern_month, normalized_text, re.IGNORECASE)))
    
    # Extract general numbers and filter out those already part of prices, dates, or phones
    potential_numbers = re.findall(number_pattern, normalized_text)
    specific_numbers_as_text = set()
    for category in ['phone_numbers', 'prices', 'dates']:
        for item in extracted_info[category]:
            # Add all number-like substrings from these specific extractions
            specific_numbers_as_text.update(re.findall(r'\d[\d.,]*\d|\d', item))

    filtered_numbers = []
    for num_match in potential_numbers:
        is_part_of_specific = False
        for specific_num_text in specific_numbers_as_text:
            if num_match in specific_num_text : # Check if num_match is a substring of a number found in a price/date/phone
                is_part_of_specific = True
                break
        if not is_part_of_specific:
            # Further check: standalone number should not be just a component of a larger extracted entity string
            is_substring_of_any_entity = False
            for cat_key in ['phone_numbers', 'prices', 'dates', 'urls', 'emails']:
                 for entity_str in extracted_info[cat_key]:
                     if num_match in entity_str and num_match != entity_str: # if it's a true substring
                         # Example: if num_match is "2023" and a date is "01/01/2023"
                         # We want to keep "2023" if it also appears standalone.
                         # This check is tricky. The current logic is to remove numbers that are *part of* other entities.
                         # If a number is "555" and phone is "555-1234", "555" might be filtered.
                         # The goal is to get *other* numbers not captured.
                         pass # This part of logic might need refinement based on desired behavior.
            filtered_numbers.append(num_match)
    extracted_info['numbers'] = list(set(filtered_numbers))
    logging.debug(f"Extracted info: {extracted_info}")

    # Step 3: Prepare text for keyword extraction by removing the string literals of extracted entities.
    # Start with the normalized text.
    text_for_keyword_processing = normalized_text
    
    # Flatten all extracted items and sort by length (longest first) to handle overlapping cases.
    all_extracted_items_flat = []
    for category_values in extracted_info.values():
        all_extracted_items_flat.extend(category_values)
    
    all_extracted_items_flat.sort(key=len, reverse=True) # Replace longer strings first

    for item_to_remove in all_extracted_items_flat:
        if item_to_remove: # Ensure item is not empty
            # Replace with spaces to maintain structure roughly, then collapse spaces
            text_for_keyword_processing = text_for_keyword_processing.replace(item_to_remove, ' ' * len(item_to_remove))
    logging.debug(f"Text after removing entities: {text_for_keyword_processing[:200]}...")

    # Step 4: Clean this entity-removed text (remove punctuation, extra spaces, to lower) for keyword tokenization
    text_cleaned_for_keywords = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', text_for_keyword_processing)
    text_cleaned_for_keywords = re.sub(r'\s+', ' ', text_cleaned_for_keywords).strip().lower()
    logging.debug(f"Text cleaned for keywords: {text_cleaned_for_keywords[:200]}...")

    # Step 5: Extract words for keywords from this heavily cleaned and entity-removed text
    # The regex finds sequences of word characters (including Turkish), hyphens, or apostrophes.
    words = re.findall(r'\b[\w\'-çğıöşüÇĞİÖŞÜ]+\b', text_cleaned_for_keywords)
    logging.debug(f"Initial words for keywords ({len(words)}): {words[:20]}")

    # Step 6: Create the general `cleaned_text` for return (normalized, punctuation removed, but entities NOT removed)
    # This is useful for other NLP tasks like semantic analysis that need fuller context.
    cleaned_text = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', normalized_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # Step 7: Filter words (from entity-removed text) using stop words, length, etc.
    filtered_words = [
        word for word in words
        if word not in config.COMMON_STOP_WORDS
        and len(word) > 2
        and not word.isdigit()
        # Redundant check if URLs are properly removed, but safe:
        and not word.startswith(('http', 'www', 'https')) 
    ]
    logging.debug(f"Filtered words ({len(filtered_words)}): {filtered_words[:20]}")
    word_counts = Counter(filtered_words)

    # Step 8: Process bigrams from the same `words` list (derived from entity-removed text)
    bigrams = []
    # Use `words` list which is already tokenized from `text_cleaned_for_keywords` (and is lowercase)
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        # Apply stop word and validity checks for components of bigrams
        if w1 not in config.COMMON_STOP_WORDS and w2 not in config.COMMON_STOP_WORDS:
            valid_w1 = len(w1) > 2 and not w1.isdigit() and not w1.startswith(('http', 'www', 'https'))
            valid_w2 = len(w2) > 2 and not w2.isdigit() and not w2.startswith(('http', 'www', 'https'))
            if valid_w1 and valid_w2:
                bigrams.append(f"{w1} {w2}")
    bigram_counts = Counter(bigrams)
    logging.debug(f"Bigram counts ({len(bigram_counts)}): {bigram_counts.most_common(5)}")

    # Step 9: Combine single word and bigram counts, weighting bigrams more
    combined_counts = word_counts.copy()
    for bigram, count in bigram_counts.items():
        if count > 1:  # Consider only bigrams that appear more than once
            combined_counts[bigram] = count * 1.5  # Weight bigrams

    # Get more candidates than `max_keywords` initially
    raw_keywords_with_counts = combined_counts.most_common(max_keywords * 2)
    
    # Step 10: Refine keyword list to get unique keywords (using original seen_roots logic)
    # This logic aims to avoid very similar keywords (e.g., "seo" and "seo analysis")
    # if one is a substring of the other and has already been added.
    unique_keywords = []
    seen_roots_phrases = set() # Store phrases/words already effectively included
    
    for keyword_phrase, count in raw_keywords_with_counts:
        is_redundant = False
        for seen_item in seen_roots_phrases:
            # Check if the new keyword is a substring of an existing one, or vice-versa
            # Only apply if one is a clear substring of the other to avoid over-filtering.
            # And ensure a minimum length for the 'seen_item' to be considered a "root".
            if len(seen_item) >=3 and (keyword_phrase in seen_item or seen_item in keyword_phrase):
                is_redundant = True
                break
        
        if not is_redundant:
            unique_keywords.append(keyword_phrase)
            seen_roots_phrases.add(keyword_phrase) # Add the current phrase itself
            if len(unique_keywords) >= max_keywords:
                break
    
    # If the list is still shorter than max_keywords, fill with remaining raw keywords if any
    if len(unique_keywords) < max_keywords:
        remaining_candidates = [kw for kw, _ in raw_keywords_with_counts if kw not in unique_keywords]
        needed = max_keywords - len(unique_keywords)
        unique_keywords.extend(remaining_candidates[:needed])

    logging.debug(f"Final unique keywords ({len(unique_keywords)}): {unique_keywords}")

    # Step 11: Prepare the string of filtered words (for context or other uses)
    filtered_words_str = " ".join(filtered_words)

    # Step 12: Return the results
    return (unique_keywords, cleaned_text, filtered_words_str, extracted_info)





def get_wordnet_pos(treebank_tag: str):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return None


def semantic_analyze(text: str) -> dict:
    """Perform semantic analysis on cleaned text using NLTK."""
    # Ensure tokenizer resources
    try:
        tokens = word_tokenize(text)
    except LookupError as e:
        # Attempt to download punkt or punkt_tab
        nltk.download('punkt')
        nltk.download('punkt_tab')
        tokens = word_tokenize(text)

    try:
        pos_tags = nltk.pos_tag(tokens)
    except LookupError:
        nltk.download('averaged_perceptron_tagger')
        nltk.download('averaged_perceptron_tagger_eng')
        pos_tags = nltk.pos_tag(tokens)
    
    # Lemmatization
    lemmatizer = WordNetLemmatizer()
    lemmas = []
    for word, tag in pos_tags:
        wn_tag = get_wordnet_pos(tag)
        if wn_tag:
            lemmas.append(lemmatizer.lemmatize(word, wn_tag))
        else:
            lemmas.append(lemmatizer.lemmatize(word))

    # Synonyms lookup for each lemma
    synonyms = {}
    for lemma in set(lemmas):
        synsets = wordnet.synsets(lemma)
        synonyms[lemma] = list({syn.name().split('.')[0] for syn in synsets})

    return {
        'tokens': tokens,
        'pos_tags': pos_tags,
        'lemmas': lemmas,
        'synonyms': synonyms
    }
