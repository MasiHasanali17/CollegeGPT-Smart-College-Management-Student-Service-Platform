"""
cache.py

Simple in-memory + file-backed cache for chatbot answers.

Purpose:
    If the same (or near-identical) question is asked again, return the
    saved answer instantly instead of calling Groq again. This saves
    API calls, reduces cost, and speeds up repeated/common questions
    (e.g. "what is the fee for btech" asked by hundreds of students).

Strategy:
    - Cache key = normalized question text (lowercase, stripped).
    - Cache is kept in memory (fast) AND saved to a JSON file on disk
      (so it survives server restarts).
    - This is a simple exact-match cache. It won't catch every phrasing
      variation, but combined with the embedding retrieval step (which
      already normalizes meaning), most repeat questions will hit it.
"""

import json
import os
import re

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "answer_cache.json")

_cache = {}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _load_cache():
    global _cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    else:
        _cache = {}


def _save_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[cache.py] WARNING: failed to save cache: {e}")


def get_cached_answer(question: str):
    """
    Returns the cached answer string if this question was asked before,
    else None.
    """
    key = _normalize(question)
    return _cache.get(key)


def set_cached_answer(question: str, answer: str):
    """
    Saves a question -> answer pair into the cache (memory + disk).
    """
    key = _normalize(question)
    _cache[key] = answer
    _save_cache()


def clear_cache():
    """Wipes the entire cache. Useful during development/testing."""
    global _cache
    _cache = {}
    _save_cache()
    print("[cache.py] Cache cleared.")


# Load existing cache from disk as soon as this module is imported
_load_cache()
print(f"[cache.py] Loaded {len(_cache)} cached answers.")


# Quick manual test - only runs if you execute this file directly:
#   python cache.py
if __name__ == "__main__":
    print("Current cached questions:")
    for q in _cache:
        print(" -", q)

    test_q = "what is the fee for btech"
    print(f"\nTesting get_cached_answer('{test_q}') ->", get_cached_answer(test_q))

    set_cached_answer(test_q, "This is a test cached answer.")
    print(f"After setting, get_cached_answer('{test_q}') ->", get_cached_answer(test_q))