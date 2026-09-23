"""Small Windows helpers shared by the v1/v2 messenger and the v2 monitor."""

import ctypes
from typing import Optional

import win32gui

_user32 = ctypes.windll.user32


def enable_dpi_awareness() -> None:
    """Make window coordinates and captures use physical pixels on scaled displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            _user32.SetProcessDPIAware()
        except Exception:
            pass


def find_window(title: str) -> Optional[int]:
    """Exact title match first (preferring KakaoTalk's EVA_ classes), then a unique partial match."""
    if not title:
        return None
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if text:
                windows.append((hwnd, text, win32gui.GetClassName(hwnd)))

    win32gui.EnumWindows(callback, None)
    exact = [w for w in windows if w[1] == title]
    partial = [w for w in windows if title in w[1] and w[1] != title]
    for group in (exact, partial if len(partial) == 1 else []):
        kakao = [w for w in group if w[2].startswith('EVA_')]
        if kakao:
            return kakao[0][0]
        if group:
            return group[0][0]
    return None


def foreground_window() -> int:
    return win32gui.GetForegroundWindow()
