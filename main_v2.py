"""
KakaoTranslate v2 — reads the group chat from the screen (OCR + layout
analysis) and DMs translations, with sender names, to My Chatroom.

Logs go to kakaotranslate_v2.log.
"""

import logging
import sys
import time
from pathlib import Path

from winutil import enable_dpi_awareness

enable_dpi_awareness()

from config import BATCH_DMS, CHAT_NAME, OCR_ENGINE, POLL_INTERVAL, SELF_CHAT_TITLE  # noqa: E402
from dm_format import build_dms, translate_messages  # noqa: E402
from messenger import send_self_dm  # noqa: E402
from monitor_v2 import ChatMonitor  # noqa: E402
from translator import backend_name  # noqa: E402

_LOG_FILE = Path(__file__).parent / 'kakaotranslate_v2.log'
_fmt = logging.Formatter('%(asctime)s  %(levelname)-8s  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_fh = logging.FileHandler(_LOG_FILE, encoding='utf-8')
_fh.setFormatter(_fmt)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_fh, _ch])
logger = logging.getLogger(__name__)


def main() -> None:
    if not CHAT_NAME:
        logger.error("Set CHAT_NAME in config.py (or config_local.py) before running.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("KakaoTranslate v2  (screen OCR + layout analysis)")
    logger.info(f"  Monitoring : {CHAT_NAME}")
    logger.info(f"  Poll every : {POLL_INTERVAL}s")
    logger.info(f"  Self-chat  : {SELF_CHAT_TITLE or '(not set)'}")
    logger.info(f"  OCR engine : {OCR_ENGINE}")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 60)

    backend_name()  # load the translation model up front
    monitor = ChatMonitor()

    while True:
        try:
            new_messages = monitor.get_new_messages()
            if new_messages:
                translations = translate_messages(new_messages)
                for msg, translation in zip(new_messages, translations):
                    logger.info(f"[{msg.sender or '?'}] {msg.text}" + (f"  →  {translation}" if translation else ""))
                for dm in build_dms(new_messages, translations, BATCH_DMS):
                    send_self_dm(dm)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception:
            logger.exception("Unexpected error in main loop — continuing.")

        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break


if __name__ == '__main__':
    main()
