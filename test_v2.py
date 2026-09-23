"""
Diagnostic script for v2 — run this before main_v2.py.

Usage:
    python test_v2.py            # all checks, including a test DM
    python test_v2.py --no-send  # skip the DM
Saves debug_v2.png: coloured boxes show how each piece of text was classified.
"""

import sys
from pathlib import Path

from winutil import enable_dpi_awareness

enable_dpi_awareness()

from PIL import ImageDraw  # noqa: E402

from config import BATCH_DMS, CHAT_NAME  # noqa: E402

_COLOURS = {
    'label': (0, 90, 255), 'bubble': (0, 170, 0), 'own': (255, 140, 0), 'quote': (220, 0, 220),
    'other': (0, 200, 200), 'noise': (230, 0, 0), 'header': (130, 130, 130),
    'footer': (130, 130, 130), 'band': (130, 130, 130),
}
_DEBUG_IMAGE = Path(__file__).parent / 'debug_v2.png'


def _save_debug_image(img, layout) -> None:
    img = img.copy()
    draw = ImageDraw.Draw(img)
    for b in layout.boxes:
        draw.rectangle([b.x0, b.y0, b.x1, b.y1], outline=_COLOURS.get(b.kind, (0, 0, 0)), width=2)
    for a in layout.avatars:
        draw.rectangle([2, a.top, a.right, a.bottom], outline=(255, 215, 0), width=2)
    for bub in layout.bubbles:
        draw.rectangle([bub.left, bub.top, bub.right, bub.bottom], outline=(255, 0, 0) if bub.cut else (0, 255, 0))
    for y in (layout.header_bottom, layout.footer_top):
        draw.line([0, y, img.width, y], fill=(255, 0, 0), width=2)
    img.save(_DEBUG_IMAGE)


def test_ocr_and_parsing():
    print("\n── 1. Screen reading: what is visible right now ─────────────────")
    try:
        import ocr_engines
        from monitor_v2 import ChatMonitor

        monitor = ChatMonitor()
        messages = monitor.read_screen(force=True)
        if messages is None:
            print(f"  Could not capture '{CHAT_NAME}'. Is it open as its own window (not minimised)?")
            return
        print(f"  OCR engine: {monitor.engine.name}")
        print(f"  Header ends at y={monitor.last_layout.header_bottom}, "
              f"input box starts at y={monitor.last_layout.footer_top}, "
              f"{len(monitor.last_layout.avatars)} profile picture(s) found\n")
        for msg in messages:
            flags = ' (partly off-screen — ignored)' if msg.cut else ''
            flags += ' (you)' if msg.own else ''
            print(f"  [{msg.sender or 'unknown sender'}]{flags}")
            print(f"    {msg.text}\n")
        if not messages:
            print("  No messages found.")
        _save_debug_image(monitor.last_image, monitor.last_layout)
        print(f"  Saved {_DEBUG_IMAGE.name} — blue=names, green=message text, magenta=reply quotes (dropped),")
        print("  red=ignored, yellow=profile pictures, red lines=header/input-box limits.")

        if monitor.engine.name == 'windows':
            try:
                other = ocr_engines.EasyOcrEngine()
            except Exception:
                other = None
            if other:
                from chat_layout import analyze
                import numpy as np
                arr = np.asarray(monitor.last_image)
                layout = analyze(arr, other.read(monitor.last_image), CHAT_NAME,
                                 read_name=lambda r: other.read_line(monitor.last_image.crop(r)))
                print("\n  For comparison, easyocr reads:")
                for m in layout.messages:
                    print(f"    [{m.sender or 'unknown sender'}] {m.text}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ERROR: {e}")
    print()


def test_translation():
    print("── 2. Translation ──────────────────────────────────────────────")
    samples = ["4시까지 한다고 함니다", "허얼 조져야지", "내셔널 쿼사디아 데이가 있는줄은 꿈에도 몰랐네"]
    try:
        from translator import backend_name, translate_batch_to_english
        print(f"  Backend: {backend_name()}")
        for src, dst in zip(samples, translate_batch_to_english(samples)):
            print(f"  {src}\n    → {dst}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_dm_format():
    print("── 3. DM format preview ────────────────────────────────────────")
    try:
        from dm_format import build_dms, translate_messages
        from monitor_v2 import ChatMessage

        samples = [
            ChatMessage(sender="김지은 Jenny Kim", text="4시까지 한다고 함니다"),
            ChatMessage(sender="김민준", text="네시에 딱 끝나는데 튀어가야디.--"),
            ChatMessage(sender="Alex", text="Every day is national galbi day for me"),
        ]
        for dm in build_dms(samples, translate_messages(samples), BATCH_DMS):
            print("  ┌─ DM preview ──────────────────────")
            for line in dm.splitlines():
                print(f"  │ {line}")
            print("  └───────────────────────────────────\n")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_dm_send():
    print("── 4. DM send ──────────────────────────────────────────────────")
    try:
        from messenger import send_self_dm
        if not send_self_dm("[KakaoTranslate v2 test]\n[김지은 Jenny Kim] 4시까지 한다고 함니다\n→ It's until 4 o'clock."):
            print("  DM not sent — check the warning above.")
        else:
            print("  Sent. Check My Chatroom.")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


if __name__ == "__main__":
    print("KakaoTranslate v2 — diagnostic test")
    print("The group chat and My Chatroom must be open as their own windows (they can overlap).")
    test_ocr_and_parsing()
    test_translation()
    test_dm_format()
    if '--no-send' not in sys.argv:
        test_dm_send()
    print("Done.")
