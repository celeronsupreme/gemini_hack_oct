from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings

log = logging.getLogger("gemini")


@lru_cache(maxsize=1)
def get_client():
    """A google-genai client, or None when running in mock mode."""
    if not settings.gemini_enabled:
        return None
    from google import genai
    return genai.Client(api_key=settings.gemini_api_key)


def is_mock() -> bool:
    return get_client() is None
