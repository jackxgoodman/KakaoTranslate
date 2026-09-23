"""
Capture a window's own pixels (v2).

PrintWindow asks the window to draw itself into a bitmap, so it works even
when other windows (such as the My Chatroom window we type DMs into) cover
the chat. Falls back to a plain screen grab if PrintWindow returns nothing.
"""

import ctypes
import logging
from typing import Optional

import numpy as np
import win32gui
import win32ui
from PIL import Image, ImageGrab

logger = logging.getLogger(__name__)

_PW_RENDERFULLCONTENT = 2


def _print_window(hwnd: int, width: int, height: int) -> Optional[Image.Image]:
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    try:
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        if not ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), _PW_RENDERFULLCONTENT):
            return None
        info = bitmap.GetInfo()
        data = bitmap.GetBitmapBits(True)
        return Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']), data, 'raw', 'BGRX', 0, 1)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


def _trim_black_edges(img: Image.Image) -> Image.Image:
    """Drop the black strips some windows report for their invisible resize borders."""
    arr = np.asarray(img)
    dark_rows = arr.max(axis=(1, 2)) < 8
    dark_cols = arr.max(axis=(0, 2)) < 8
    top = int(np.argmax(~dark_rows)) if (~dark_rows).any() else 0
    bottom = len(dark_rows) - int(np.argmax(~dark_rows[::-1]))
    left = int(np.argmax(~dark_cols)) if (~dark_cols).any() else 0
    right = len(dark_cols) - int(np.argmax(~dark_cols[::-1]))
    if (top, left, bottom, right) == (0, 0, arr.shape[0], arr.shape[1]):
        return img
    return img.crop((left, top, right, bottom))


def capture_window(hwnd: int) -> Optional[Image.Image]:
    if not win32gui.IsWindow(hwnd):
        return None
    if win32gui.IsIconic(hwnd):
        logger.warning("The chat window is minimised — restore it (it can stay behind other windows).")
        return None
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None

    img = None
    try:
        img = _print_window(hwnd, width, height)
    except Exception as exc:
        logger.debug(f"PrintWindow failed: {exc}")
    if img is None or np.asarray(img.convert('L')).mean() < 3:
        img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    return _trim_black_edges(img.convert('RGB'))
