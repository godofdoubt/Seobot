

#s10tools.py
from dataclasses import dataclass
from typing import Callable, List, Optional
from urllib.parse import urlparse, urlunparse
import logging

logger = logging.getLogger(__name__)

@dataclass
class Tool:
    """A class to define tools with metadata and associated functions."""
    description: str
    function: Callable[..., str]
    parameters: Optional[List[str]] = None
    validation: bool = False
    prompt: Optional[str] = None

def normalize_url(url: str) -> str:
    """
    Normalizes a URL to a canonical form for database lookup:
    1. Forces the scheme to https.
    2. Lowercases the netloc (domain).
    3. Removes 'www.' prefix from netloc.
    4. Removes standard ports (80 for http, 443 for https) from netloc.
    5. Attempts to correct common minor malformations like leading dots in netloc.
    6. Removes a trailing dot from the netloc if present (common for FQDNs).
    7. Removes path, query, and fragment.
    Returns an empty string if the URL is empty or cannot be normalized to a valid domain form.
    """
    if not url or not url.strip():
        logger.debug("normalize_url received an empty or whitespace-only URL.")
        return ""

    original_url_for_logging = url # Keep original for logging on failure
    url_to_process = url.strip()

    # Ensure scheme is present and defaults to https for parsing
    if '://' not in url_to_process:
        url_to_process = 'https://' + url_to_process
    elif url_to_process.startswith('http://'):
        # Convert http to https for canonical form
        url_to_process = 'https://' + url_to_process[len('http://'):]
    elif url_to_process.startswith('//'):
        # Scheme-relative URL, make it https
        url_to_process = 'https://' + url_to_process[len('//'):]

    try:
        parsed = urlparse(url_to_process)
    except ValueError as e:
        logger.warning(f"ValueError during urlparse of '{url_to_process}' (original: '{original_url_for_logging}'): {e}. Returning empty.")
        return ""

    scheme = 'https' # Canonical scheme is https
    
    netloc = parsed.netloc.lower() if parsed.netloc else ''

    if not netloc:
        logger.info(f"URL '{original_url_for_logging}' resulted in empty netloc after parsing '{url_to_process}'. Cannot normalize.")
        return ""

    # Remove 'www.' prefix
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    
    # Remove standard ports
    if netloc.endswith(':443') or netloc.endswith(':80'):
        netloc = netloc.rsplit(':', 1)[0]
    
    # Correct leading single dot
    if netloc.startswith('.') and not netloc.startswith('..'):
        potential_domain_part = netloc[1:]
        if potential_domain_part and not potential_domain_part.startswith('.'):
            if '.' in potential_domain_part or potential_domain_part == 'localhost':
                 logger.debug(f"Correcting netloc '{netloc}' by removing leading dot to '{potential_domain_part}'.")
                 netloc = potential_domain_part
    
    # NEW: Remove trailing dot from netloc (for FQDNs like "example.com.")
    if netloc.endswith('.') and len(netloc) > 1: # Ensure it's not just "."
        # Check if it's not something like "..".
        # A simple check is if the part before the dot is not empty and not a dot itself.
        if netloc[:-1] and netloc[:-1] != '.':
            logger.debug(f"Removing trailing dot from netloc '{netloc}' to '{netloc[:-1]}'.")
            netloc = netloc[:-1]

    if not netloc: # Check again if netloc became empty after stripping
        logger.info(f"URL '{original_url_for_logging}' resulted in empty netloc after stripping operations. Cannot normalize.")
        return ""

    # Reconstruct the URL
    normalized = urlunparse((scheme, netloc, '', '', '', ''))
    
    logger.debug(f"Normalized '{original_url_for_logging}' to '{normalized}'")
    return normalized

FUNCTION_DECLARATIONS = [
    {
        "function_declarations": [
            {
                #"name": "generate_article",
                #"description": "Generate an article based on the SEO report and URL.",
                #"parameters": {
                 #   "type": "object",
                  #  "properties": {
                   #     "trigger": {
                    #        "type": "string",
                     #       "description": "A trigger parameter, can be any value."
                      #  }
                   # },
                   # "required": ["trigger"]
                #}
            },
            {
                "name": "generate_seo_suggestions",
                "description": "Provide SEO suggestions based on the full SEO report.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trigger": {
                            "type": "string",
                            "description": "A trigger parameter, can be any value."
                        }
                    },
                    "required": ["trigger"]
                }
            },
           # {
               # "name": "generate_product_description",
                #"description": "Generate a product description based on the SEO report.",
                #"parameters": {
                 #   "type": "object",
                  #  "properties": {
                   #     "trigger": {
                    #        "type": "string",
                     #       "description": "A trigger parameter, can be any value."
                      #  }
                    #},
                    #"required": ["trigger"]
             #   }
           # }
        ]
    }
]
