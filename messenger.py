"""
Send a message to the '나와의 채팅' (Note to Self) KakaoTalk window.

The user must have that chat open as a standalone pop-out window
(double-click the chat in the KakaoTalk sidebar to pop it out).
Messages sent here sync automatically to the user's iPhone.
"""

import ctypes
import ctypes.wintypes
import logging
import time
from typing import Optional

import pyautogui
import pyperclip
import pygetwindow as gw

from config import INPUT_BOX_Y_OFFSET, SELF_CHAT_TITLE

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

# pyautogui safety: move mouse to corner to abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def _bring_to_foreground(hwnd: int) -> None:
    """
    Reliably bring a window to the foreground on Windows.
    pygetwindow's activate() uses SetForegroundWindow directly, which Windows
    blocks unless the calling process is attached to the foreground thread.
    This function attaches first, then sets the foreground window.
    """
    # Restore if minimised
    _user32.ShowWindow(hwnd, 9)  # SW_RESTORE

    fg_hwnd = _user32.GetForegroundWindow()
    fg_tid = _user32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = _kernel32.GetCurrentThreadId()

    if fg_tid and fg_tid != our_tid:
        _user32.AttachThreadInput(fg_tid, our_tid, True)
        _user32.SetForegroundWindow(hwnd)
        _user32.AttachThreadInput(fg_tid, our_tid, False)
    else:
        _user32.SetForegroundWindow(hwnd)

    time.sleep(0.35)


def _find_self_chat() -> Optional[object]:
    if not SELF_CHAT_TITLE:
        return None
    windows = gw.getWindowsWithTitle(SELF_CHAT_TITLE)
    return windows[0] if windows else None


def send_self_dm(message: str) -> bool:
    """
    Bring the self-chat window to the foreground, click its input box,
    paste the message, and send. Returns True on success.
    """
    if not SELF_CHAT_TITLE:
        logger.warning(
            "SELF_CHAT_TITLE is not set in config.py. "
            "Open 'My Chatroom' in KakaoTalk, pop it out, and set SELF_CHAT_TITLE "
            "to the exact text shown in the window's title bar."
        )
        return False

    window = _find_self_chat()
    if not window:
        logger.warning(
            f"Could not find window titled '{SELF_CHAT_TITLE}'. "
            "Make sure 'My Chatroom' is open as a separate pop-out window."
        )
        return False

    try:
        _bring_to_foreground(window._hWnd)

        # Click the message input area (bottom-centre of the chat window)
        x = window.left + window.width // 2
        y = window.top + window.height - INPUT_BOX_Y_OFFSET
        pyautogui.click(x, y)
        time.sleep(0.2)

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
