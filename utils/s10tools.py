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
    """Normalizes a URL to its main page by ensuring a protocol and removing paths."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = 'https://' + url
        parsed = urlparse(url)
    normalized = urlunparse((parsed.scheme, parsed.netloc, '', '', '', ''))
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