import re
from collections import Counter
import logging
from datetime import datetime
import getpass
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

COMMON_STOP_WORDS = {
    'a', 'an', 'the', 'in', 'on', 'at', 'and', 'or', 'of', 'to', 'for',
    'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'this',
    'that', 'it', 'its', 'they', 'we', 'you', 'he', 'she', 'has', 'have',
    'had', 'do', 'does', 'did', 'but', 'from', 'what', 'when', 'where',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'some', 'such',
    'no', 'nor', 'too', 'very', 'can', 'will', 'just', 'com', 'www'
}

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
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
        return url
    except Exception:
        raise ValueError("Invalid URL format")

def extract_keywords(text):
    """Extract and count keywords from text"""
    if not text:
        return {}
    
    words = re.findall(r'\b\w+\b', text.lower())
    words = [word for word in words if word not in COMMON_STOP_WORDS and len(word) > 2]
    word_counts = Counter(words)
    return dict(word_counts.most_common(20))

def save_history(history):
    """Save analysis history (disabled)"""
    pass

def load_history():
    """Load analysis history (disabled)"""
    return {}