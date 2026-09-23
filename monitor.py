"""
Read Korean chat messages from the KakaoTalk window via screenshot + OCR.

KakaoTalk uses custom rendering that bypasses the Windows Accessibility API,
so we capture the chat area as an image and run easyocr over it.
"""

import logging
from collections import OrderedDict
from typing import List, Optional

import numpy as np
import pygetwindow as gw
from PIL import ImageGrab, Image

from config import CHAT_NAME
from translator import has_korean, korean_char_count

# Sender names in KakaoTalk are typically 2–3 Korean syllables.
# Only translate strings with at least this many Korean characters.
_MIN_KOREAN_CHARS = 4

logger = logging.getLogger(__name__)

_KAKAO_TITLES = ('KakaoTalk', '카카오톡')


def _load_reader():
    import easyocr
    logger.info("Loading OCR model — first run downloads ~1.5 GB, please wait…")
    return easyocr.Reader(['ko', 'en'], gpu=False)


class ChatMonitor:
    def __init__(self) -> None:
        self._reader = None  # lazy-loaded on first scan
        self._seen: 'OrderedDict[str, None]' = OrderedDict()  # insertion-ordered, so trimming drops the oldest
        self._seeded: bool = False

    @property
    def reader(self):
        if self._reader is None:
            self._reader = _load_reader()
        return self._reader

    def _find_chat_window(self):
        """Find the KakaoTalk window that shows the group chat."""
        # Prefer a pop-out window whose title contains the chat name
        if CHAT_NAME:
            wins = gw.getWindowsWithTitle(CHAT_NAME)
            if wins:
                return wins[0]
        # Fall back to the main KakaoTalk window
        for title in _KAKAO_TITLES:
            wins = gw.getWindowsWithTitle(title)
            if wins:
                return wins[0]
        return None

    def _screenshot_chat(self, window) -> Optional[Image.Image]:
        """Capture just the message area of the chat window."""
        try:
            left, top = window.left, window.top
            w, h = window.width, window.height
            title = window.title or ''
            # Main KakaoTalk window has a left sidebar; pop-out chat windows don't
            x1 = left + int(w * 0.35) if title in _KAKAO_TITLES else left
            # Crop out the header (~70 px) and the input box (~80 px)
            bbox = (x1, top + 70, left + w, top + h - 80)
            return ImageGrab.grab(bbox=bbox)
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None

    def _get_visible_korean(self) -> Optional[List[str]]:
        """Visible Korean messages, or None if the chat couldn't be captured."""
        window = self._find_chat_window()
        if not window:
            if self._seeded:
                logger.warning(f"KakaoTalk window not found — is '{CHAT_NAME}' open?")
            return None

        img = self._screenshot_chat(window)
        if img is None:
            return None

        results = self.reader.readtext(np.array(img), detail=0, paragraph=False)
        texts = [
            r.strip() for r in results
            if has_korean(r.strip()) and korean_char_count(r.strip()) >= _MIN_KOREAN_CHARS
        ]

        # Deduplicate while preserving order
        seen_local: set = set()
        unique = []
        for t in texts:
            if t not in seen_local:
                seen_local.add(t)
                unique.append(t)
        return unique

    def get_new_messages(self) -> List[str]:
        """
        Return Korean messages that appeared since the last call.
        On the very first call, seeds the seen-set from current chat history
        so old messages are not translated on startup.
        """
        messages = self._get_visible_korean()
        if messages is None:
            return []  # don't seed until the chat has actually been read

        if not self._seeded:
            self._seen.update(dict.fromkeys(messages))
            self._seeded = True
            logger.info(
                f"Initialized. Skipped {len(self._seen)} existing messages. "
                "Watching for new ones…"
            )
            return []

        new = [m for m in messages if m not in self._seen]
        self._seen.update(dict.fromkeys(new))

        while len(self._seen) > 2000:
            self._seen.popitem(last=False)

        return new
