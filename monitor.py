"""
Read Korean chat messages from a running KakaoTalk window using the
Windows UI Automation accessibility tree — no OCR required.
"""

import logging
from typing import List, Optional

import uiautomation as auto

from config import CHAT_NAME
from translator import has_korean

logger = logging.getLogger(__name__)

_KAKAO_TITLES = {'KakaoTalk', '카카오톡'}


def _find_kakao_window() -> Optional[auto.Control]:
    """Return the KakaoTalk window that shows the group chat."""
    root = auto.GetRootControl()
    try:
        children = root.GetChildren()
    except Exception:
        return None

    # Prefer a standalone pop-out window whose title matches the chat name
    if CHAT_NAME:
        for w in children:
            try:
                if CHAT_NAME in (w.Name or ''):
                    return w
            except Exception:
                pass

    # Fall back to the main KakaoTalk window
    for w in children:
        try:
            if (w.Name or '') in _KAKAO_TITLES:
                return w
        except Exception:
            pass

    return None


def _collect_korean(control: auto.Control, results: List[str], depth: int = 0) -> None:
    """Recursively walk the UI tree and collect strings that contain Korean."""
    if depth > 25:
        return
    try:
        name = (control.Name or '').strip()
        if name and has_korean(name):
            results.append(name)
    except Exception:
        pass
    try:
        for child in control.GetChildren():
            _collect_korean(child, results, depth + 1)
    except Exception:
        pass


class ChatMonitor:
    def __init__(self) -> None:
        self._seen: set = set()
        self._seeded: bool = False

    def _get_visible_korean(self) -> List[str]:
        window = _find_kakao_window()
        if not window:
            if self._seeded:  # only warn after initial setup to avoid startup noise
                logger.warning(
                    f"KakaoTalk window not found. "
                    f"Is KakaoTalk open with '{CHAT_NAME}'?"
                )
            return []

        raw: List[str] = []
        _collect_korean(window, raw)
        # Deduplicate while preserving order
        seen_local: set = set()
        unique = []
        for item in raw:
            if item not in seen_local:
                seen_local.add(item)
                unique.append(item)
        return unique

    def get_new_messages(self) -> List[str]:
        """
        Return Korean messages that have appeared since the last call.
        On the very first call, seeds the 'seen' set from current chat history
        so that old messages are not translated on startup.
        """
        messages = self._get_visible_korean()

        if not self._seeded:
            self._seen.update(messages)
            self._seeded = True
            logger.info(
                f"Initialized. Skipped {len(self._seen)} existing messages. "
                "Watching for new ones…"
            )
            return []

        new = [m for m in messages if m not in self._seen]
        self._seen.update(new)

        # Trim the set to avoid unbounded memory growth
        if len(self._seen) > 2000:
            self._seen = set(list(self._seen)[-2000:])

        return new
