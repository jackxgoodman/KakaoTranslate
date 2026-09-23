"""
Diagnostic script for v3 — run this before main_v3.py.

Usage:
    python test_v3.py            # all checks, including a test DM
    python test_v3.py --no-send  # skip the DM
Writes v3_clipboard_dump.txt with the raw copied chat text.
"""

import sys
from pathlib import Path

from kakao_win32 import (
    ChatReader, ChatSender, enable_dpi_awareness, find_input_control, find_list_control,
    find_window, list_children, list_kakao_windows,
)

enable_dpi_awareness()

from config import BATCH_DMS, CHAT_NAME, RESTORE_CLIPBOARD, SELF_CHAT_TITLE, SEND_METHOD_V3  # noqa: E402

_DUMP = Path(__file__).parent / 'v3_clipboard_dump.txt'


def test_windows():
    print("\n── 1. KakaoTalk windows and controls ──────────────────────────")
    windows = list_kakao_windows()
    if not windows:
        print("  No KakaoTalk windows found. Is KakaoTalk running?")
    for hwnd, title, cls in windows:
        print(f"  {title or '(no title)'!r:40} class={cls}")
    for label, title in (("Group chat", CHAT_NAME), ("Self-chat", SELF_CHAT_TITLE)):
        hwnd = find_window(title)
        print(f"\n  {label} ({title!r}): {'found' if hwnd else 'NOT FOUND'}")
        if not hwnd:
            continue
        for child, cls, visible, rect in list_children(hwnd):
            print(f"    child class={cls:32} visible={visible} size={rect[2]-rect[0]}x{rect[3]-rect[1]}")
        print(f"    → message list: {'found' if find_list_control(hwnd) else 'NOT FOUND'}, "
              f"input box: {'found' if find_input_control(hwnd) else 'NOT FOUND'}")
    print()


def test_read():
    print("── 2. Reading the group chat ───────────────────────────────────")
    try:
        from chat_parser import parse_chat_text
        chat = find_window(CHAT_NAME)
        if not chat:
            print(f"  Group chat {CHAT_NAME!r} not found.")
            return
        reader = ChatReader(restore_clipboard=RESTORE_CLIPBOARD)
        raw = reader.copy_text(chat)
        if not raw:
            print("  Could not copy the chat text. Please send the output of section 1.")
            return
        _DUMP.write_text(raw, encoding='utf-8')
        lines = raw.splitlines()
        print(f"  Method: {reader.method}. Copied {len(lines)} lines → {_DUMP.name}")
        print("  Last 8 raw lines:")
        for line in lines[-8:]:
            print(f"    | {line}")
        messages = parse_chat_text(raw)
        print(f"\n  Parsed {len(messages)} messages. Last 6:")
        for m in messages[-6:]:
            print(f"    [{m.sender}] [{m.time}] {m.text}")
        if not messages:
            print("  Nothing parsed — please send v3_clipboard_dump.txt (or a few lines of it).")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ERROR: {e}")
    print()


def test_translation_and_format():
    print("── 3. Translation + DM preview ─────────────────────────────────")
    try:
        from chat_parser import Message
        from dm_format import build_dms, translate_messages
        from translator import backend_name
        print(f"  Backend: {backend_name()}")
        samples = [
            Message("김민준", "10:47 AM", "언제가면되려나?"),
            Message("Y", "10:47 AM", "허얼 조져야지"),
            Message("Alex", "10:49 AM", "Every day is national galbi day for me"),
        ]
        for dm in build_dms(samples, translate_messages(samples), BATCH_DMS):
            print("  ┌─ DM preview ──────────────────────")
            for line in dm.splitlines():
                print(f"  │ {line}")
            print("  └───────────────────────────────────")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_send():
    print("── 4. DM send ──────────────────────────────────────────────────")
    hwnd = find_window(SELF_CHAT_TITLE)
    if not hwnd:
        print(f"  Self-chat {SELF_CHAT_TITLE!r} not found.")
        return
    try:
        sender = ChatSender(method=SEND_METHOD_V3, reader=ChatReader(restore_clipboard=RESTORE_CLIPBOARD))
        ok = sender.send(hwnd, "[KakaoTranslate v3 test]\n[김민준] 언제가면되려나?\n→ When should I go?")
        print(f"  {'Sent' if ok else 'Not sent'} using method: {sender.method}. Check My Chatroom "
              "(the message should appear exactly once).")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ERROR: {e}")
    print()


if __name__ == "__main__":
    print("KakaoTranslate v3 — diagnostic test")
    print("Open the group chat and My Chatroom as their own windows (they can be behind other windows).")
    test_windows()
    test_read()
    test_translation_and_format()
    if '--no-send' not in sys.argv:
        test_send()
    print("Done.")
