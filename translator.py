import re
from deep_translator import GoogleTranslator

_KOREAN_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def translate_batch_to_english(texts: list) -> list:
    """Translate a list of Korean strings in one API call to avoid rate limits."""
    if not texts:
        return []
    try:
        return GoogleTranslator(source='ko', target='en').translate_batch(texts)
    except Exception as e:
        return [f"[translation error: {e}]"] * len(texts)
