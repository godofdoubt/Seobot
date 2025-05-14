import re
from collections import Counter
import logging
from datetime import datetime
import getpass
import os
from urllib.parse import urlparse
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
                    text: text
                    
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
def extract_text(text: str):
    """
    Extract top keywords and return cleaned text, along with other extracted information.
    Returns a tuple (list of top `max_keywords` keywords, cleaned_text, filtered_words_str, extracted_info_dict).
    Uses COMMON_STOP_WORDS from config.
    """
    import re
    from collections import Counter
    
    if not text or len(text.strip()) < 10:
        return ([], "", "", {})
    
    # Normalize text first
    text = normalize_turkish_text(text)
    text = re.sub(r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})(?=\d{1,2}[/.-])', r'\1 ', text)
    # Clean text after extraction is complete
    cleaned_text = re.sub(r'[^\w\s\'-çğıöşüÇĞİÖŞÜ]', ' ', text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()


    
    return (cleaned_text )
    
