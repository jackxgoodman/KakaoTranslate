"""
Direct Win32 access to KakaoTalk PC windows (v3).

Reading: posts Ctrl+A / Ctrl+C to the chat's message-list control and reads
the clipboard. Sending: puts text into the input box with window messages and
posts Enter. Both work without moving the mouse or stealing focus; if this
KakaoTalk build ignores posted keys, a focus-based keyboard fallback is used
and the previously active window is restored afterwards.
"""

import ctypes
import logging
import time
from typing import List, Optional

import win32api
import win32clipboard
import win32con
import win32gui
import win32process

from winutil import enable_dpi_awareness, find_window  # noqa: F401  (re-exported for main_v3/test_v3)

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32

_INPUT_CLASSES = {'RICHEDIT50W', 'RICHEDIT20W', 'RICHEDITD2DPT'}
_ENTER_LPARAM_DOWN = 0x001C0001
_ENTER_LPARAM_UP = 0xC01C0001


def list_kakao_windows() -> List[tuple]:
    """(hwnd, title, class) for visible top-level KakaoTalk windows."""
    found = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            cls = win32gui.GetClassName(hwnd)
            if cls.startswith('EVA_'):
                found.append((hwnd, win32gui.GetWindowText(hwnd), cls))

    win32gui.EnumWindows(callback, None)
    return found


def list_children(hwnd: int) -> List[tuple]:
    """(hwnd, class, visible, (left, top, right, bottom)) for every child window."""
    children = []

    def callback(child, _):
        children.append((
            child,
            win32gui.GetClassName(child),
            bool(win32gui.IsWindowVisible(child)),
            win32gui.GetWindowRect(child),
        ))

    try:
        win32gui.EnumChildWindows(hwnd, callback, None)
    except Exception:
        pass
    return children


def _area(rect) -> int:
    return max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])


def find_list_control(hwnd: int) -> Optional[int]:
    lists = [c for c in list_children(hwnd) if 'LIST' in c[1].upper()]
    if not lists:
        return None
    return max(lists, key=lambda c: (c[2], _area(c[3])))[0]


def find_input_control(hwnd: int) -> Optional[int]:
    edits = [
        c for c in list_children(hwnd)
        if c[1].upper() in _INPUT_CLASSES or 'RICHEDIT' in c[1].upper()
    ]
    visible = [c for c in edits if c[2]]
    pool = visible or edits
    return pool[-1][0] if pool else None


# ── Keyboard helpers ──────────────────────────────────────────────────────

def _post_key(hwnd: int, vk: int, ctrl: bool = False) -> None:
    """Post a key press to a window, making it see Ctrl held while it handles the message."""
    scan = win32api.MapVirtualKey(vk, 0)
    lparam_down = 1 | (scan << 16)
    lparam_up = lparam_down | 0xC0000000
    if not ctrl:
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam_down)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, lparam_up)
        return

    our_tid = win32api.GetCurrentThreadId()
    target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
    attached = bool(_user32.AttachThreadInput(our_tid, target_tid, True))
    try:
        KeyState = ctypes.c_ubyte * 256
        original = KeyState()
        _user32.GetKeyboardState(original)
        pressed = KeyState.from_buffer_copy(original)
        pressed[win32con.VK_CONTROL] = 0x80
        pressed[win32con.VK_LCONTROL] = 0x80
        _user32.SetKeyboardState(pressed)
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam_down)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, lparam_up)
        time.sleep(0.15)  # let KakaoTalk process the keys while Ctrl reads as held
        _user32.SetKeyboardState(original)
    finally:
        if attached:
            _user32.AttachThreadInput(our_tid, target_tid, False)


def _keybd(vk: int, up: bool = False) -> None:
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP if up else 0, 0)


def _press(vk: int, *modifiers: int) -> None:
    for m in modifiers:
        _keybd(m)
    _keybd(vk)
    _keybd(vk, up=True)
    for m in reversed(modifiers):
        _keybd(m, up=True)


def _focus(hwnd: int) -> None:
    root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) or hwnd
    if win32gui.IsIconic(root):
        win32gui.ShowWindow(root, win32con.SW_RESTORE)
    our_tid = win32api.GetCurrentThreadId()
    target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
    foreground = win32gui.GetForegroundWindow()
    fg_tid = win32process.GetWindowThreadProcessId(foreground)[0] if foreground else 0
    attached = []
    try:
        for tid in {target_tid, fg_tid}:
            if tid and tid != our_tid and _user32.AttachThreadInput(our_tid, tid, True):
                attached.append(tid)
        _user32.BringWindowToTop(root)
        _user32.SetForegroundWindow(root)
        _user32.SetFocus(hwnd)
    finally:
        for tid in attached:
            _user32.AttachThreadInput(our_tid, tid, False)
    time.sleep(0.15)


def _restore_foreground(hwnd: int) -> None:
    if hwnd and win32gui.IsWindow(hwnd):
        try:
            _focus(hwnd)
        except Exception:
            pass


def _type_unicode(text: str) -> bool:
    """Type text via SendInput Unicode events (no clipboard)."""
    ulong_ptr = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', ctypes.c_ushort), ('wScan', ctypes.c_ushort), ('dwFlags', ctypes.c_ulong),
                    ('time', ctypes.c_ulong), ('dwExtraInfo', ulong_ptr)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [('dx', ctypes.c_long), ('dy', ctypes.c_long), ('mouseData', ctypes.c_ulong),
                    ('dwFlags', ctypes.c_ulong), ('time', ctypes.c_ulong), ('dwExtraInfo', ulong_ptr)]

    class _U(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ('u',)
        _fields_ = [('type', ctypes.c_ulong), ('u', _U)]

    encoded = text.encode('utf-16-le')
    events = []
    for i in range(0, len(encoded), 2):
        unit = int.from_bytes(encoded[i:i + 2], 'little')
        events.append(INPUT(1, _U(ki=KEYBDINPUT(0, unit, 0x0004, 0, 0))))           # KEYEVENTF_UNICODE
        events.append(INPUT(1, _U(ki=KEYBDINPUT(0, unit, 0x0004 | 0x0002, 0, 0))))  # | KEYUP
    if not events:
        return True
    arr = (INPUT * len(events))(*events)
    return _user32.SendInput(len(arr), arr, ctypes.sizeof(INPUT)) == len(arr)


# ── Clipboard ─────────────────────────────────────────────────────────────

def _read_clipboard_text() -> Optional[str]:
    for _ in range(10):
        try:
            win32clipboard.OpenClipboard()
            break
        except Exception:
            time.sleep(0.05)
    else:
        return None
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        return None
    finally:
        win32clipboard.CloseClipboard()


def _write_clipboard_text(text: str) -> None:
    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass


def _wait_for_clipboard_change(seq: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _user32.GetClipboardSequenceNumber() != seq:
            time.sleep(0.05)  # let the owner finish writing
            return True
        time.sleep(0.03)
    return False


# ── Reading ───────────────────────────────────────────────────────────────

class ChatReader:
    """Copies all loaded messages out of a chat window. Remembers which method works."""

    def __init__(self, restore_clipboard: bool = True) -> None:
        self.restore_clipboard = restore_clipboard
        self.method: Optional[str] = None  # "post" or "focus" once known

    def copy_text(self, chat_hwnd: int) -> Optional[str]:
        list_hwnd = find_list_control(chat_hwnd)
        if not list_hwnd:
            logger.warning("Message list control not found in the chat window (run test_v3.py).")
            return None

        saved = _read_clipboard_text() if self.restore_clipboard else None
        try:
            for method in ([self.method] if self.method else ['post', 'focus']):
                text = self._copy_with(method, list_hwnd)
                if text:
                    if self.method != method:
                        logger.info(f"Chat reading method: {method}")
                        self.method = method
                    return text
                if method == 'post' and self.method is None:
                    # Unrecognised posted keys may have been typed into the input box
                    _clear_input(chat_hwnd)
            return None
        finally:
            if saved is not None:
                _write_clipboard_text(saved)

    @staticmethod
    def _copy_with(method: str, list_hwnd: int) -> Optional[str]:
        seq = _user32.GetClipboardSequenceNumber()
        if method == 'post':
            _post_key(list_hwnd, ord('A'), ctrl=True)
            _post_key(list_hwnd, ord('C'), ctrl=True)
            changed = _wait_for_clipboard_change(seq, 2.0)
        else:
            previous_fg = win32gui.GetForegroundWindow()
            try:
                _focus(list_hwnd)
                _press(ord('A'), win32con.VK_CONTROL)
                time.sleep(0.1)
                _press(ord('C'), win32con.VK_CONTROL)
                changed = _wait_for_clipboard_change(seq, 2.0)
            finally:
                _restore_foreground(previous_fg)
        return _read_clipboard_text() if changed else None


def _clear_input(window_hwnd: int) -> None:
    edit = find_input_control(window_hwnd)
    if edit:
        try:
            win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, '')
        except Exception:
            pass


# ── Sending ───────────────────────────────────────────────────────────────

def _set_text_by_message(edit_hwnd: int, text: str) -> None:
    text = text.replace('\r\n', '\n').replace('\n', '\r\n')
    win32gui.SendMessage(edit_hwnd, win32con.WM_SETTEXT, 0, text)
    if _user32.GetWindowTextLengthW(edit_hwnd) == 0:
        # Some builds ignore WM_SETTEXT but accept a replace-selection
        win32gui.SendMessage(edit_hwnd, win32con.EM_SETSEL, 0, -1)
        win32gui.SendMessage(edit_hwnd, win32con.EM_REPLACESEL, True, text)


def _send_by_message(edit_hwnd: int, text: str) -> None:
    _set_text_by_message(edit_hwnd, text)
    time.sleep(0.05)
    win32api.PostMessage(edit_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, _ENTER_LPARAM_DOWN)
    win32api.PostMessage(edit_hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, _ENTER_LPARAM_UP)


def _send_by_keyboard(edit_hwnd: int, text: str) -> None:
    previous_fg = win32gui.GetForegroundWindow()
    try:
        _focus(edit_hwnd)
        _press(ord('A'), win32con.VK_CONTROL)
        _press(win32con.VK_DELETE)
        lines = text.replace('\r\n', '\n').split('\n')
        for i, line in enumerate(lines):
            _type_unicode(line)
            if i < len(lines) - 1:
                _press(win32con.VK_RETURN, win32con.VK_SHIFT)  # newline without sending
        time.sleep(0.05)
        _press(win32con.VK_RETURN)
        time.sleep(0.2)
    finally:
        _restore_foreground(previous_fg)


class ChatSender:
    """
    Sends messages into a chat window. With method "auto", the first send uses
    window messages and is verified by reading the chat back; if the text
    didn't arrive, it switches to the keyboard method permanently.
    """

    def __init__(self, method: str = 'auto', reader: Optional[ChatReader] = None) -> None:
        self.method = method
        self.reader = reader or ChatReader()

    def send(self, hwnd: int, text: str) -> bool:
        edit = find_input_control(hwnd)
        if not edit:
            logger.warning("Input box not found in the self-chat window (run test_v3.py).")
            return False

        if self.method == 'keyboard':
            _send_by_keyboard(edit, text)
            return True
        if self.method == 'message':
            _send_by_message(edit, text)
            return True

        _send_by_message(edit, text)
        time.sleep(0.6)
        if self._arrived(hwnd, text):
            logger.info("DM sending method: message (no focus change needed)")
            self.method = 'message'
            return True
        logger.info("Window-message sending didn't work on this KakaoTalk build; switching to keyboard method")
        self.method = 'keyboard'
        _send_by_keyboard(edit, text)
        return True

    def _arrived(self, hwnd: int, text: str) -> bool:
        try:
            copied = self.reader.copy_text(hwnd)
        except Exception as exc:
            logger.warning(f"Couldn't read My Chatroom back to confirm the DM: {exc}")
            return False
        if not copied:
            return False
        tail = copied.replace('\r\n', '\n')[-(len(text) + 200):]
        first_line = text.strip().split('\n')[0].strip()
        return bool(first_line) and first_line in tail
