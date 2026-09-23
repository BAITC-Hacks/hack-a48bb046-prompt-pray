"""Best-effort language detection for the three offline question dictionaries.

The AI independently reads the original text, including languages outside these
dictionaries. This hint must never override the language of its input.
"""
import re

from ..schemas.domain import DraftLocale


def detect_draft_locale(description: str) -> DraftLocale:
    text = re.sub(r"https?://\S+|\S+@\S+", "", description.lower())
    words = re.findall(r"[^\W\d_]+", text)
    kazakh = set("әғқңөұүһі")
    if any(kazakh.intersection(word) for word in words):
        return "kk"
    # Kazakh can also be written without language-specific letters.
    if set(words).intersection({"керек", "бизге", "бизнеске", "жоба", "жасау", "бар"}):
        return "kk"
    cyrillic = sum(len(re.findall(r"[а-яё]", word)) for word in words)
    latin = sum(len(re.findall(r"[a-z]", word)) for word in words)
    return "ru" if cyrillic > latin else "en"
