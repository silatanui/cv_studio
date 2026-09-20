"""
Typography and Character Sanitization Module.

Normalizes non-standard Unicode punctuation, typographic quotes, em/en dashes,
and bullet symbols to plain ASCII equivalents, preventing parser exceptions
and corruption in legacy and modern ATS platforms.
"""

import re
import unicodedata


def sanitize_text(text: str) -> str:
    """
    Normalizes typography by replacing non-ASCII and typographic characters
    with standard ATS-safe equivalents.
    """
    if not text:
        return ""

    # Replace curly double quotes
    text = re.sub(r'[\u201c\u201d\u201e\u201f\u00ab\u00bb]', '"', text)
    # Replace curly single quotes / apostrophes / backticks
    text = re.sub(r'[\u2018\u2019\u201a\u201b\u0060\u00b4]', "'", text)
    # Replace dashes (em-dash, en-dash, figure dash, horizontal bar)
    text = re.sub(r'[\u2012\u2013\u2014\u2015\u2212]', '-', text)
    # Replace various bullet characters with standard hyphen/space
    text = re.sub(r'[\u2022\u2023\u25e6\u2043\u2219\u25aa\u25ab\u25cf\u25cb]', '-', text)
    # Replace non-breaking spaces and thin spaces
    text = re.sub(r'[\u00a0\u2000-\u200b\u202f\u205f\u3000]', ' ', text)
    # Replace ellipses
    text = re.sub(r'\u2026', '...', text)
    # Normalize unicode forms (NFKD) while keeping standard characters
    text = unicodedata.normalize('NFKC', text)

    # Clean up duplicate whitespace while preserving single spaces
    text = re.sub(r'[ \t]+', ' ', text)

    return text.strip()


def sanitize_list(items: list[str]) -> list[str]:
    """Applies sanitize_text to a list of strings, removing empty entries."""
    if not items:
        return []
    return [cleaned for item in items if (cleaned := sanitize_text(item))]
