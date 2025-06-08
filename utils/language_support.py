# SeoTree/utils/language_support.py
import logging

# Attempt to import translations from sibling files.
# These files (keys_en.py, keys_tr.py) are expected to be in the same directory.
try:
    from .keys_en import translations as en_translations
except ImportError:
    logging.error("Failed to import English translations from keys_en.py. Ensure the file exists and is correctly placed.")
    en_translations = {} # Fallback to empty dict if import fails

try:
    from .keys_tr import translations as tr_translations
except ImportError:
    logging.error("Failed to import Turkish translations from keys_tr.py. Ensure the file exists and is correctly placed.")
    tr_translations = {} # Fallback to empty dict if import fails

class LanguageSupport:
    """Class to manage multi-language support in the application"""

    def __init__(self):
        self.translations = {
            "en": en_translations,
            "tr": tr_translations
            # Add more languages here by importing their respective key files
            # For example: "es": es_translations,
        }
        
        if not self.translations["en"]:
            logging.critical(
                "CRITICAL: English translations ('en') are missing or failed to load. "
                "The application's text display will be severely affected."
            )

    def get_text(self, key, lang="en", *args, fallback=None, **kwargs):
        """
        Get translated text for the given key in the specified language.

        Parameters:
            key (str): The translation key to look up.
            lang (str): The language code (e.g., "en", "tr"). Defaults to "en".
            *args: Positional arguments to format into the translated string.
            fallback (str, optional): Fallback text if the key is not found.
            **kwargs: Keyword arguments to format into the translated string.

        Returns:
            str: Translated and formatted text.
        """
        chosen_lang = lang
        current_lang_translations = self.translations.get(chosen_lang)

        if current_lang_translations is None:
            if chosen_lang != "en": # Log if a specific non-English lang was requested but not found
                logging.warning(f"Language '{chosen_lang}' not found in translations. Defaulting to 'en'.")
            chosen_lang = "en" # Default to English if language not supported or not loaded
            current_lang_translations = self.translations.get("en", {}) # Ensure we get a dict even if 'en' is somehow missing

        translation_template = current_lang_translations.get(key)

        # If key not found in current_lang_translations, and current lang is not 'en',
        # try fetching from 'en' as a primary fallback.
        if translation_template is None and chosen_lang != "en":
            english_translations = self.translations.get("en", {})
            translation_template = english_translations.get(key)
        
        if translation_template is None:
            # If still not found, use the provided fallback or the key itself.
            text_to_format = fallback if fallback is not None else key
            
            if fallback is None: # Only log missing key if no explicit fallback was given
                 logging.warning(
                    f"Translation key '{key}' not found for language '{lang}' (or English fallback). "
                    f"Returning key or provided fallback. Args: {args}, Kwargs: {kwargs}"
                )
            
            # Attempt to format the fallback text or key
            if isinstance(text_to_format, str):
                try:
                    if args and kwargs:
                        return text_to_format.format(*args, **kwargs)
                    elif args:
                        return text_to_format.format(*args)
                    elif kwargs:
                        return text_to_format.format(**kwargs)
                    return text_to_format # No arguments to format with
                except (KeyError, IndexError, TypeError) as e:
                    logging.error(
                        f"Failed to format fallback/key string for key '{key}'. "
                        f"String: '{text_to_format}', Args: {args}, Kwargs: {kwargs}. Error: {e}"
                    )
                    return text_to_format # Return unformatted string on error
            return text_to_format # If not a string (e.g. int, bool), return as is

        # Format the found translation template
        if isinstance(translation_template, str):
            try:
                if args and kwargs:
                    return translation_template.format(*args, **kwargs)
                elif args:
                    return translation_template.format(*args)
                elif kwargs:
                    return translation_template.format(**kwargs)
                return translation_template # No arguments to format with
            except (KeyError, IndexError, TypeError) as e:
                logging.error(
                    f"Failed to format translation for key '{key}' in language '{chosen_lang}'. "
                    f"Template: '{translation_template}', Args: {args}, Kwargs: {kwargs}. Error: {e}"
                )
                # Return the unformatted template so the user/dev sees the placeholder issue
                return translation_template 
        return translation_template # If not a string (e.g. from a misconfigured translation file), return as is

    def get_available_languages(self):
        """Return a list of available language codes."""
        return list(self.translations.keys())


# Create a singleton instance
language_manager = LanguageSupport()