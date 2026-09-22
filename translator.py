import re
import time
from deep_translator import GoogleTranslator

_KOREAN_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')
# Separator unlikely to appear in Korean text or its translation
_SEP = " ||| "


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def translate_batch_to_english(texts: list) -> list:
    """
    Translate a list of Korean strings using a single API call by joining
    them with a separator. One request per scan regardless of message count.
    """
    if not texts:
        return []

    combined = _SEP.join(texts)
    for attempt in range(4):
        try:
            result = GoogleTranslator(source='ko', target='en').translate(combined)
            parts = result.split(_SEP)
            # Align output length to input in case the separator got mangled
            if len(parts) == len(texts):
                return [p.strip() for p in parts]
            # Fallback: return the whole translation as the first item
            return [result] + [""] * (len(texts) - 1)
        except Exception as e:
            if attempt < 3:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
                continue
            return [f"[translation error: {e}]"] * len(texts)
