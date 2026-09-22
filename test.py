"""
Diagnostic script — run this to verify each component works before running main.py.

Usage:
    python test.py
"""

import sys


def test_ocr():
    print("\n── 1. OCR: what Korean text is visible right now ──────────────")
    try:
        from monitor import ChatMonitor
        monitor = ChatMonitor()
        texts = monitor._get_visible_korean()
        if texts:
            print(f"  Found {len(texts)} Korean string(s):")
            for t in texts:
                print(f"    • {t}")
        else:
            print("  None found. Is the KakaoTalk group chat window open and visible?")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_translation():
    print("── 2. Translation: Korean → English ───────────────────────────")
    sample = "안녕하세요, 오늘 모임은 몇 시예요?"
    print(f"  Input : {sample}")
    try:
        from translator import translate_batch_to_english
        result = translate_batch_to_english([sample])
        print(f"  Output: {result[0]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_dm():
    print("── 3. DM: send a test message to your self-chat window ────────")
    try:
        from messenger import send_self_dm
        ok = send_self_dm("[KakaoTranslate test] If you see this in My Chatroom, the DM step works!")
        if not ok:
            print("  DM not sent — check the warning above.")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


if __name__ == "__main__":
    print("KakaoTranslate — diagnostic test")
    print("Make sure KakaoTalk is open with the group chat AND My Chatroom visible.")
    test_ocr()
    test_translation()
    test_dm()
    print("Done. Check your My Chatroom window for the test DM.")
