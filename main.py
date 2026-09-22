import logging
import sys
import time

from config import CHAT_NAME, POLL_INTERVAL
from monitor import ChatMonitor
from messenger import send_self_dm
from translator import translate_to_english

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
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
    logger.info("    2. '나와의 채팅' open as a separate pop-out window")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 60)

    monitor = ChatMonitor()

    while True:
        try:
            for korean_text in monitor.get_new_messages():
                logger.info(f"KO  {korean_text}")
                english = translate_to_english(korean_text)
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
