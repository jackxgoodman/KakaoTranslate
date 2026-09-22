"""
Send a message to the '나와의 채팅' (Note to Self) KakaoTalk window.

The user must have that chat open as a standalone pop-out window
(double-click the chat in the KakaoTalk sidebar to pop it out).
Messages sent here sync automatically to the user's iPhone.
"""

import logging
import time
from typing import Optional

import pyautogui
import pyperclip
import pygetwindow as gw

from config import INPUT_BOX_Y_OFFSET

logger = logging.getLogger(__name__)

_SELF_CHAT_TITLE = '나와의 채팅'
# pyautogui safety: move mouse to corner to abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def _find_self_chat() -> Optional[object]:
    windows = gw.getWindowsWithTitle(_SELF_CHAT_TITLE)
    return windows[0] if windows else None


def send_self_dm(message: str) -> bool:
    """
    Click the input box in the '나와의 채팅' window, paste the message, and send.
    Returns True on success, False if the window is not found or an error occurs.
    """
    window = _find_self_chat()
    if not window:
        logger.warning(
            "Could not find '나와의 채팅' window. "
            "Open KakaoTalk → right-click your own name or find '나와의 채팅' "
            "→ double-click to pop it out as a separate window."
        )
        return False

    try:
        window.activate()
        time.sleep(0.4)

        # Click the message input area (bottom-centre of the chat window)
        x = window.left + window.width // 2
        y = window.top + window.height - INPUT_BOX_Y_OFFSET
        pyautogui.click(x, y)
        time.sleep(0.2)

        # Use clipboard paste so Unicode / Korean labels in the prefix survive
        pyperclip.copy(message)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.15)
        pyautogui.press('enter')
        time.sleep(0.3)

        logger.info(f"DM sent: {message[:100]}")
        return True

    except Exception as e:
        logger.error(f"Failed to send DM: {e}")
        return False
