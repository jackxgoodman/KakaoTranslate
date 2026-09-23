"""
Send a message to your "My Chatroom" KakaoTalk window (v1 and v2).

The self-chat must be open as its own pop-out window; its title is
SELF_CHAT_TITLE. Messages sent here sync to your phone. After sending, the
window you were using and your clipboard are put back.
"""

import ctypes
import logging
import time

import pyautogui
import pyperclip
import win32con
import win32gui

from config import INPUT_BOX_Y_OFFSET, SELF_CHAT_TITLE
from winutil import find_window

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

pyautogui.FAILSAFE = True  # move the mouse to a screen corner to abort
pyautogui.PAUSE = 0.05


def _bring_to_foreground(hwnd: int) -> None:
    """SetForegroundWindow is refused unless we attach to the foreground thread first."""
    if win32gui.IsIconic(hwnd):
        _user32.ShowWindow(hwnd, win32con.SW_RESTORE)
    fg_tid = _user32.GetWindowThreadProcessId(_user32.GetForegroundWindow(), None)
    our_tid = _kernel32.GetCurrentThreadId()
    if fg_tid and fg_tid != our_tid:
        _user32.AttachThreadInput(fg_tid, our_tid, True)
        _user32.SetForegroundWindow(hwnd)
        _user32.AttachThreadInput(fg_tid, our_tid, False)
    else:
        _user32.SetForegroundWindow(hwnd)
    time.sleep(0.35)


def send_self_dm(message: str) -> bool:
    """Paste `message` into the self-chat and press Enter. Returns True on success."""
    if not SELF_CHAT_TITLE:
        logger.warning(
            "SELF_CHAT_TITLE is not set in config.py. Open 'My Chatroom' in KakaoTalk, pop it out, "
            "and set SELF_CHAT_TITLE to the exact text shown in the window's title bar."
        )
        return False

    hwnd = find_window(SELF_CHAT_TITLE)
    if not hwnd:
        logger.warning(
            f"Could not find window titled '{SELF_CHAT_TITLE}'. "
            "Make sure 'My Chatroom' is open as a separate pop-out window."
        )
        return False

    previous_window = win32gui.GetForegroundWindow()
    try:
        previous_clipboard = pyperclip.paste()
    except Exception:
        previous_clipboard = None

    try:
        _bring_to_foreground(hwnd)
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        pyautogui.click((left + right) // 2, bottom - INPUT_BOX_Y_OFFSET)
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
    finally:
        if previous_clipboard is not None:
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                pass
        if previous_window and previous_window != hwnd and win32gui.IsWindow(previous_window):
            try:
                _bring_to_foreground(previous_window)
            except Exception:
                pass
