

#s10tools.py
from dataclasses import dataclass
from typing import Callable, List, Optional
from urllib.parse import urlparse, urlunparse

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
    Normalizes a URL by ensuring a scheme, removing 'www.' prefix, 
    and removing paths, queries, and fragments.
    """
    parsed = urlparse(url)
    
    # Ensure a scheme (default to https)
    scheme = parsed.scheme
    if not scheme:
        url = 'https://' + url
        parsed = urlparse(url)
        scheme = parsed.scheme # Re-assign scheme after re-parsing

    netloc = parsed.netloc
    # Remove 'www.' prefix if it exists
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    
    # Reconstruct the URL with the scheme, modified netloc, and no path/query/fragment
    normalized = urlunparse((scheme, netloc, '', '', '', ''))
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
