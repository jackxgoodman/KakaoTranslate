"""
Improved KakaoTalk chat monitor that parses sender name + message text.

Uses easyocr bounding boxes to read text in vertical order, then a
sequential parser that identifies sender names vs message content.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pygetwindow as gw
from PIL import ImageGrab

from config import CHAT_NAME
from translator import has_korean, korean_char_count

logger = logging.getLogger(__name__)

_KAKAO_TITLES = ('KakaoTalk', '카카오톡')

# Sentence-ending particles / endings that only appear in messages, not names
_SENTENCE_END = re.compile(
    r'(다|요|해|며|면|서|고|야|어|죠|까|니다|습니다|ㅋ|ㅎ|!|\?)\s*$'
)


@dataclass
class ChatMessage:
    sender: str  # display name ("" if could not be determined)
    text: str    # full original text, including any embedded English

    @property
    def key(self) -> tuple:
        return (self.sender, self.text)


# ── Heuristics ────────────────────────────────────────────────────────────

def _could_be_name(text: str) -> bool:
    """
    Return True if this OCR chunk looks like a sender name rather than a message.
    KakaoTalk sender names are typically 2-5 Korean syllables, optionally
    followed by an English display name (e.g. "오민경 Fhoebe Oh").
    """
    kcount = korean_char_count(text)
    if kcount < 2 or kcount > 6:
        return False
    if _SENTENCE_END.search(text):
        return False  # verb/adjective endings → message
    if len(text.split()) > 4:
        return False  # too many words to be a name
    return True


# ── Bounding-box helpers ──────────────────────────────────────────────────

def _top(bbox) -> float:
    return min(p[1] for p in bbox)


# ── OCR loading ───────────────────────────────────────────────────────────

def _load_reader():
    import easyocr
    logger.info("Loading OCR model…")
    return easyocr.Reader(['ko', 'en'], gpu=False)


# ── Message structure parser ──────────────────────────────────────────────

def _parse_messages(ocr_results) -> List[ChatMessage]:
    """
    Parse easyocr detail=1 results into ChatMessage objects.

    Algorithm:
      - Sort all text chunks by vertical position (top to bottom).
      - A chunk that *could* be a name is held as a "pending name".
      - The pending name is confirmed as the sender when the very next
        chunk looks like a message. If it is NOT followed by a message
        (e.g. it was itself a short message at the end of the visible area),
        it is emitted as a message instead.
    """
    if not ocr_results:
        return []

    sorted_items = sorted(ocr_results, key=lambda r: _top(r[0]))

    messages: List[ChatMessage] = []
    current_sender = ""
    pending_name: Optional[str] = None

    for bbox, text, _conf in sorted_items:
        text = text.strip()
        if not text:
            continue

        has_k = has_korean(text)
        kcount = korean_char_count(text)
        is_english_only = not has_k and len(text) > 3

        if has_k and _could_be_name(text):
            if pending_name is not None:
                # Previous candidate was not followed by a message → treat as message
                messages.append(ChatMessage(sender=current_sender, text=pending_name))
            pending_name = text

        elif (has_k and kcount >= 1) or is_english_only:
            if pending_name is not None:
                # Confirm the pending candidate as the sender for this message
                current_sender = pending_name
                pending_name = None
            messages.append(ChatMessage(sender=current_sender, text=text))

    # Anything still pending at the end had no following message → treat as message
    if pending_name is not None:
        messages.append(ChatMessage(sender=current_sender, text=pending_name))

    return messages


# ── Monitor class ─────────────────────────────────────────────────────────

class ChatMonitor:
    def __init__(self) -> None:
        self._reader = None
        self._seen: set = set()
        self._seeded: bool = False

    @property
    def reader(self):
        if self._reader is None:
            self._reader = _load_reader()
        return self._reader

    def _find_chat_window(self):
        if CHAT_NAME:
            wins = gw.getWindowsWithTitle(CHAT_NAME)
            if wins:
                return wins[0]
        for title in _KAKAO_TITLES:
            wins = gw.getWindowsWithTitle(title)
            if wins:
                return wins[0]
        return None

    def _screenshot_chat(self, window):
        try:
            left, top = window.left, window.top
            w, h = window.width, window.height
            title = window.title or ''
            x1 = left + int(w * 0.35) if title in _KAKAO_TITLES else left
            return ImageGrab.grab(bbox=(x1, top + 70, left + w, top + h - 80))
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None

    def _get_all_messages(self) -> List[ChatMessage]:
        window = self._find_chat_window()
        if not window:
            if self._seeded:
                logger.warning(f"KakaoTalk window not found — is '{CHAT_NAME}' open?")
            return []
        img = self._screenshot_chat(window)
        if img is None:
            return []
        results = self.reader.readtext(np.array(img), detail=1)
        return _parse_messages(results)

    def get_new_messages(self) -> List[ChatMessage]:
        """
        Return messages that appeared since the last call.
        On the first call, seeds the seen-set so old history is not re-sent.
        """
        all_messages = self._get_all_messages()

        if not self._seeded:
            self._seen.update(m.key for m in all_messages)
            self._seeded = True
            logger.info(
                f"Initialized. Skipped {len(self._seen)} existing messages. "
                "Watching for new ones…"
            )
            return []

        new = [m for m in all_messages if m.key not in self._seen]
        self._seen.update(m.key for m in new)

        if len(self._seen) > 2000:
            self._seen = set(list(self._seen)[-2000:])

        return new
