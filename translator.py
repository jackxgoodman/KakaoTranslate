import re
import time
from deep_translator import GoogleTranslator

_KOREAN_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def _translate_one(text: str) -> str:
    for attempt in range(3):
        try:
            return GoogleTranslator(source='ko', target='en').translate(text)
        except Exception as e:
            if 'too many requests' in str(e).lower() and attempt < 2:
                time.sleep(2 ** attempt)  # 1s then 2s backoff
                continue
            return f"[translation error: {e}]"


def translate_batch_to_english(texts: list) -> list:
    """Translate Korean strings one at a time with a delay to respect rate limits."""
    results = []
    for text in texts:
        results.append(_translate_one(text))
        time.sleep(0.3)  # max ~3 requests/s, well under Google's 5/s limit
    return results
