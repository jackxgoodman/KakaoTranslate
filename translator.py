import re
from deep_translator import GoogleTranslator

_KOREAN_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def translate_to_english(text: str) -> str:
    try:
        return GoogleTranslator(source='ko', target='en').translate(text)
    except Exception as e:
        return f"[translation error: {e}]"
