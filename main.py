import logging
import sys
import time
from pathlib import Path

from config import CHAT_NAME, POLL_INTERVAL, SELF_CHAT_TITLE
from monitor import ChatMonitor
from messenger import send_self_dm
from translator import translate_batch_to_english

_LOG_FILE = Path(__file__).parent / 'kakaotranslate.log'

_fmt = logging.Formatter('%(asctime)s  %(levelname)-8s  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

_file_handler = logging.FileHandler(_LOG_FILE, encoding='utf-8')
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])
logger = logging.getLogger(__name__)


def main() -> None:
    if not CHAT_NAME:
        logger.error(
            "CHAT_NAME is not set. "
            "Open config.py and set it to the exact name of the group chat."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("KakaoTranslate")
    logger.info(f"  Monitoring : {CHAT_NAME}")
    logger.info(f"  Poll every : {POLL_INTERVAL}s")
    logger.info("  Make sure KakaoTalk is open with:")
    logger.info(f"    1. The group chat '{CHAT_NAME}' visible")
    logger.info(f"    2. My Chatroom ('{SELF_CHAT_TITLE}') open as a separate pop-out window")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 60)

    monitor = ChatMonitor()

    while True:
        try:
            new_messages = monitor.get_new_messages()
            if new_messages:
                translations = translate_batch_to_english(new_messages)
                for korean_text, english in zip(new_messages, translations):
                    logger.info(f"KO  {korean_text}")
                    logger.info(f"EN  {english}")
                    send_self_dm(f"[번역] {english}")
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception:
            logger.exception("Unexpected error in main loop — continuing.")

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
