from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def gemini_ready() -> bool:
    key = api_key()
    return bool(key) and not key.startswith("your_")


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


@lru_cache(maxsize=1)
def client():
    from google import genai

    return genai.Client(api_key=api_key())
