"""
Module for any generic tool helpers
"""

import hashlib
import logging
import re

logger = logging.getLogger("hercules")

URL_RE = re.compile(r"https?://[^\s,;\)\]\}'\"]+")


def hash_user_id(user_id: str | int) -> str:
    """Return a SHA-256 hash for the given user identifier."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()


def extract_urls_from_rows(rows: list, max_urls_per_sheet: int) -> list[str]:
    """
    Extract URLs from a list of rows, where each row is a list of cell values.
    Returns a list of unique URLs found in the rows, up to MAX_URLS_PER_SHEET.
    """
    urls = []
    seen = set()
    for row in rows:
        for cell in row:
            if isinstance(cell, str):
                for m in URL_RE.findall(cell):
                    if m not in seen:
                        seen.add(m)
                        urls.append(m)
                        if len(urls) >= max_urls_per_sheet:
                            break
            if len(urls) >= max_urls_per_sheet:
                break
        if len(urls) >= max_urls_per_sheet:
            break
    return urls
