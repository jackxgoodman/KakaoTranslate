"""
KakaoTranslate v2 — includes sender name and preserves English in DMs.

Run alongside or instead of main.py for testing.
Logs go to kakaotranslate_v2.log.
"""

import logging
import sys
import time
from pathlib import Path

from config import CHAT_NAME, POLL_INTERVAL, SELF_CHAT_TITLE
from monitor_v2 import ChatMonitor, ChatMessage
from messenger import send_self_dm
from translator import translate_batch_to_english, has_korean

_LOG_FILE = Path(__file__).parent / 'kakaotranslate_v2.log'
_fmt = logging.Formatter('%(asctime)s  %(levelname)-8s  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_fh = logging.FileHandler(_LOG_FILE, encoding='utf-8')
_fh.setFormatter(_fmt)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_fh, _ch])
logger = logging.getLogger(__name__)


def _format_dm(msg: ChatMessage, translation: str) -> str:
    """
    Format a single translated message for the self-chat DM.

    Example output:
        [오민경 Fhoebe Oh] 4시까지 한다고 함니다
        → It says until 4 o'clock.
    """
    sender_part = f"[{msg.sender}] " if msg.sender else ""
    if has_korean(msg.text):
        return f"{sender_part}{msg.text}\n→ {translation}"
    # English-only message: no translation needed, just pass through
    return f"{sender_part}{msg.text}"


def main() -> None:
    if not CHAT_NAME:
        logger.error("Set CHAT_NAME in config.py before running.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("KakaoTranslate v2  (sender names + English passthrough)")
    logger.info(f"  Monitoring : {CHAT_NAME}")
    logger.info(f"  Poll every : {POLL_INTERVAL}s")
    logger.info(f"  Self-chat  : {SELF_CHAT_TITLE or '(not set)'}")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 60)

    monitor = ChatMonitor()

    while True:
        try:
            new_messages = monitor.get_new_messages()
            if new_messages:
                # Translate only messages that contain Korean
                korean_msgs = [m for m in new_messages if has_korean(m.text)]
                english_only = [m for m in new_messages if not has_korean(m.text)]

                translations = translate_batch_to_english([m.text for m in korean_msgs])

                for msg, translation in zip(korean_msgs, translations):
                    logger.info(f"Sender  : {msg.sender or '(unknown)'}")
                    logger.info(f"KO      : {msg.text}")
                    logger.info(f"EN      : {translation}")
                    send_self_dm(_format_dm(msg, translation))

                for msg in english_only:
                    logger.info(f"Sender  : {msg.sender or '(unknown)'}")
                    logger.info(f"EN only : {msg.text}")
                    send_self_dm(_format_dm(msg, ""))

        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception:
            logger.exception("Unexpected error in main loop — continuing.")

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
