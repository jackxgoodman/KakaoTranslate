"""
Offline Korean → English translation.

Backends (config.TRANSLATOR):
  "nllb"  – Meta NLLB-200 distilled 600M via Hugging Face transformers.
            Much better on casual/chat Korean. ~2.5 GB one-time download,
            ~2.5 GB RAM. Falls back to Argos if it can't be loaded.
  "argos" – Argos Translate. Small (~150 MB) and light, lower quality.
"""

import logging
import os
import re
from collections import OrderedDict
from typing import List

from config import TRANSLATOR

logger = logging.getLogger(__name__)

os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
for _noisy in ('argostranslate', 'stanza', 'ctranslate2', 'transformers'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
logging.getLogger('huggingface_hub').setLevel(logging.ERROR)

_KOREAN_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')
_CACHE_SIZE = 1000


def has_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def korean_char_count(text: str) -> int:
    return len(_KOREAN_RE.findall(text))


class _ArgosBackend:
    name = 'Argos Translate'

    def __init__(self) -> None:
        import argostranslate.package
        import argostranslate.translate

        installed = argostranslate.translate.get_installed_languages()
        ready = any(
            lang.code == 'ko' and any(t.to_lang.code == 'en' for t in lang.translations_from)
            for lang in installed
        )
        if not ready:
            logger.info("Downloading Korean→English Argos model (~150 MB) — please wait…")
            argostranslate.package.update_package_index()
            pkg = next(
                (p for p in argostranslate.package.get_available_packages()
                 if p.from_code == 'ko' and p.to_code == 'en'),
                None,
            )
            if pkg is None:
                raise RuntimeError("Korean→English model not found. Check your internet connection.")
            argostranslate.package.install_from_path(pkg.download())
        self._translate = argostranslate.translate.translate

    def translate(self, texts: List[str]) -> List[str]:
        return [self._translate(t, 'ko', 'en') for t in texts]


class _NllbBackend:
    name = 'NLLB-200 (600M)'
    _MODEL = 'facebook/nllb-200-distilled-600M'
    _BATCH = 8

    def __init__(self) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from transformers.utils import logging as hf_logging

        hf_logging.set_verbosity_error()
        logger.info("Loading NLLB translation model (first run downloads ~2.5 GB)…")
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(self._MODEL, src_lang='kor_Hang')
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self._MODEL)
        self._model.eval()
        self._english = self._tokenizer.convert_tokens_to_ids('eng_Latn')

    def translate(self, texts: List[str]) -> List[str]:
        out: List[str] = []
        for i in range(0, len(texts), self._BATCH):
            batch = texts[i:i + self._BATCH]
            inputs = self._tokenizer(batch, return_tensors='pt', padding=True, truncation=True, max_length=400)
            with self._torch.inference_mode():
                generated = self._model.generate(
                    **inputs, forced_bos_token_id=self._english, max_new_tokens=400, num_beams=4,
                )
            out.extend(self._tokenizer.batch_decode(generated, skip_special_tokens=True))
        return out


_backend = None
_cache: 'OrderedDict[str, str]' = OrderedDict()


def _get_backend():
    global _backend
    if _backend is None:
        choice = (TRANSLATOR or 'argos').lower()
        if choice == 'nllb':
            try:
                _backend = _NllbBackend()
            except Exception as exc:
                logger.warning(f"NLLB unavailable ({exc}); falling back to Argos Translate.")
        if _backend is None:
            _backend = _ArgosBackend()
        logger.info(f"Translator: {_backend.name}")
    return _backend


def backend_name() -> str:
    return _get_backend().name


def translate_batch_to_english(texts: List[str]) -> List[str]:
    """Translate Korean strings offline; results line up with the input list."""
    if not texts:
        return []
    backend = _get_backend()
    fresh = {}
    todo = [t for t in dict.fromkeys(texts) if t not in _cache]
    if todo:
        try:
            fresh = dict(zip(todo, backend.translate(todo)))
        except Exception:
            logger.exception("Batch translation failed; retrying one at a time")
            for t in todo:
                try:
                    fresh[t] = backend.translate([t])[0]
                except Exception as exc:
                    fresh[t] = None
                    logger.error(f"Could not translate {t[:40]!r}: {exc}")
        for src, dst in fresh.items():
            if dst is not None:
                _cache[src] = dst
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)

    out = []
    for t in texts:
        if t in _cache:
            _cache.move_to_end(t)
            out.append(_cache[t])
        else:
            out.append(fresh.get(t) or '[translation failed]')
    return out
