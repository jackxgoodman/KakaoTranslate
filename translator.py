import logging
import re

logger = logging.getLogger(__name__)

# Suppress verbose internal logging from argostranslate and stanza
for _noisy in ('argostranslate', 'stanza', 'ctranslate2'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

_KOREAN_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')
_model_ready = False


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def korean_char_count(text: str) -> int:
    return len(_KOREAN_RE.findall(text))


def _ensure_model() -> None:
    global _model_ready
    if _model_ready:
        return
    import argostranslate.package
    import argostranslate.translate

    installed = argostranslate.translate.get_installed_languages()
    for lang in installed:
        if lang.code == 'ko':
            if any(t.to_lang.code == 'en' for t in lang.translations_from):
                _model_ready = True
                return

    logger.info("Downloading Korean→English translation model (~150 MB) — please wait…")
    argostranslate.package.update_package_index()
    pkgs = argostranslate.package.get_available_packages()
    pkg = next((p for p in pkgs if p.from_code == 'ko' and p.to_code == 'en'), None)
    if pkg is None:
        raise RuntimeError("Korean→English model not found. Check your internet connection.")
    argostranslate.package.install_from_path(pkg.download())
    _model_ready = True


def translate_batch_to_english(texts: list) -> list:
    """Translate Korean strings offline via Argos Translate — no rate limits."""
    if not texts:
        return []
    _ensure_model()
    import argostranslate.translate
    results = []
    for text in texts:
        try:
            results.append(argostranslate.translate.translate(text, 'ko', 'en'))
        except Exception as e:
            results.append(f"[translation error: {e}]")
    return results
