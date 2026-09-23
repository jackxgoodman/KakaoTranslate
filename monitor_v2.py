"""
v2 monitor: captures the group chat window, OCRs it, and reads the chat's
visual layout (bubbles, names, profile pictures) to get sender + text.
See chat_layout.py for the layout rules.
"""

import hashlib
import logging
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from capture import capture_window
from chat_layout import analyze, quick_regions
from config import CHAT_NAME, HEADER_HEIGHT, INCLUDE_OWN_MESSAGES, OCR_ENGINE
from message_diff import find_new_messages, fuzzy_same
from ocr_engines import create_engine
from winutil import find_window

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    sender: str  # display name; "" if above the visible area, "?" if unreadable
    text: str
    cut: bool = False  # partly scrolled out of view
    own: bool = False  # sent by you

    @property
    def key(self) -> tuple:
        return (self.sender, self.text)


def _same_message(a: ChatMessage, b: ChatMessage) -> bool:
    return fuzzy_same(a.text, b.text)


class ChatMonitor:
    def __init__(self) -> None:
        self._engine = None
        self._previous: List[ChatMessage] = []
        self._recent_texts: deque = deque(maxlen=500)
        self._seeded = False
        self._last_hash: Optional[str] = None
        self._warned_missing = False
        self.last_image = None
        self.last_layout = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(OCR_ENGINE)
        return self._engine

    def read_screen(self, force: bool = False) -> Optional[List[ChatMessage]]:
        """
        Every message currently visible, top to bottom.
        Returns None if the window isn't available, or if nothing has changed
        since the last call (the OCR is skipped in that case).
        """
        hwnd = find_window(CHAT_NAME)
        if not hwnd:
            if not self._warned_missing:
                logger.warning(f"Chat window '{CHAT_NAME}' not found — open it as its own window.")
                self._warned_missing = True
            return None
        self._warned_missing = False

        img = capture_window(hwnd)
        if img is None:
            return None
        arr = np.asarray(img)
        _, footer_top = quick_regions(arr)
        digest = hashlib.md5(arr[:footer_top].tobytes()).hexdigest()
        if digest == self._last_hash and not force:
            return None

        engine = self.engine
        boxes = engine.read(img)
        layout = analyze(
            arr, boxes,
            chat_name=CHAT_NAME,
            header_override=HEADER_HEIGHT,
            by_gap=engine.word_level,
            read_name=lambda rect: engine.read_line(img.crop(rect)),
        )
        self._last_hash = digest
        self.last_image, self.last_layout = img, layout
        return [ChatMessage(m.sender, m.text, m.cut, m.own) for m in layout.messages]

    def get_new_messages(self) -> List[ChatMessage]:
        """
        Messages that appeared since the last call. The first successful read
        only records what's already on screen.
        """
        messages = self.read_screen()
        if messages is None:
            return []
        complete = [m for m in messages if not m.cut]

        if not self._seeded:
            self._seeded = True
            self._remember(complete)
            logger.info(
                f"Initialized. Skipped {len(complete)} message(s) already on screen. Watching for new ones…"
            )
            return []

        new = find_new_messages(self._previous, complete, same=_same_message)
        if self._previous and complete and len(new) == len(complete):
            # Nothing on screen matched the last snapshot (scrolled, or a big
            # burst): don't resend anything seen recently.
            new = [m for m in new if not any(fuzzy_same(m.text, t) for t in self._recent_texts)]
            if new:
                logger.warning("Lost track of the previous messages (was the chat scrolled?). "
                               "Keep the chat scrolled to the bottom.")
        self._remember(complete)

        if not INCLUDE_OWN_MESSAGES:
            new = [m for m in new if not m.own]
        return new

    def _remember(self, messages: List[ChatMessage]) -> None:
        if messages:
            self._previous = messages
        for m in messages:
            if m.text not in self._recent_texts:
                self._recent_texts.append(m.text)
