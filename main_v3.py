"""
KakaoTranslate v3 — reads the group chat directly from the KakaoTalk window
(select-all + copy on the message list) instead of OCR, and types DMs into
My Chatroom with window messages.

Exact text and sender names, no OCR models, near-zero CPU, and the chat
windows can be covered by other windows. Logs go to kakaotranslate_v3.log.
"""

import logging
import sys
import time
from pathlib import Path

from kakao_win32 import ChatReader, ChatSender, enable_dpi_awareness, find_window

enable_dpi_awareness()

from chat_parser import parse_chat_text  # noqa: E402
from config import (  # noqa: E402
    BATCH_DMS, CHAT_NAME, INCLUDE_OWN_MESSAGES, POLL_INTERVAL_V3, RESTORE_CLIPBOARD,
    SELF_CHAT_TITLE, SEND_METHOD_V3,
)
from dm_format import build_dms, translate_messages  # noqa: E402
from message_diff import find_new_messages  # noqa: E402
from translator import backend_name  # noqa: E402

_LOG_FILE = Path(__file__).parent / 'kakaotranslate_v3.log'
_fmt = logging.Formatter('%(asctime)s  %(levelname)-8s  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_fh = logging.FileHandler(_LOG_FILE, encoding='utf-8')
_fh.setFormatter(_fmt)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_fh, _ch])
logger = logging.getLogger(__name__)


class Translator3:
    def __init__(self) -> None:
        self.reader = ChatReader(restore_clipboard=RESTORE_CLIPBOARD)
        self.sender = ChatSender(method=SEND_METHOD_V3, reader=self.reader)
        self.previous = None  # messages from the last successful read
        self._warned = set()

    def _warn_once(self, key: str, text: str) -> None:
        if key not in self._warned:
            logger.warning(text)
            self._warned.add(key)

    def poll(self) -> None:
        chat = find_window(CHAT_NAME)
        if not chat:
            self._warn_once('chat', f"Chat window '{CHAT_NAME}' not found — open it as its own window.")
            return
        self._warned.discard('chat')

        raw = self.reader.copy_text(chat)
        if not raw:
            self._warn_once('read', "Couldn't copy the chat's messages (run test_v3.py for details).")
            return
        self._warned.discard('read')

        current = parse_chat_text(raw)
        if not current:
            self._warn_once('parse', "Copied text had no recognisable messages (run test_v3.py and "
                                     "check v3_clipboard_dump.txt).")
            return
        self._warned.discard('parse')

        if self.previous is None:
            self.previous = current
            logger.info(f"Initialized. Skipped {len(current)} existing message(s). Watching for new ones…")
            return

        new = find_new_messages(self.previous, current)
        self.previous = current
        if not INCLUDE_OWN_MESSAGES and SELF_CHAT_TITLE:
            new = [m for m in new if m.sender != SELF_CHAT_TITLE]
        if not new:
            return

        translations = translate_messages(new)
        for msg, translation in zip(new, translations):
            logger.info(f"[{msg.sender}] {msg.text}" + (f"  →  {translation}" if translation else ""))

        self_chat = find_window(SELF_CHAT_TITLE)
        if not self_chat:
            logger.warning(f"Self-chat window '{SELF_CHAT_TITLE}' not found — DM not sent.")
            return
        for dm in build_dms(new, translations, BATCH_DMS):
            if self.sender.send(self_chat, dm):
                logger.info(f"DM sent: {dm[:100]}")


def main() -> None:
    if not CHAT_NAME or not SELF_CHAT_TITLE:
        logger.error("Set CHAT_NAME and SELF_CHAT_TITLE in config.py (or config_local.py) before running.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("KakaoTranslate v3  (direct window access, no OCR)")
    logger.info(f"  Monitoring : {CHAT_NAME}")
    logger.info(f"  Poll every : {POLL_INTERVAL_V3}s")
    logger.info(f"  Self-chat  : {SELF_CHAT_TITLE}")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 60)

    backend_name()  # load the translation model up front
    app = Translator3()
    while True:
        try:
            app.poll()
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception:
            logger.exception("Unexpected error in main loop — continuing.")
        try:
            time.sleep(POLL_INTERVAL_V3)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break


if __name__ == '__main__':
    main()
