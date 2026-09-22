"""
Diagnostic script for v2 — run this to verify sender parsing, translation,
and DM formatting before running main_v2.py.

Usage:
    python test_v2.py
"""


def test_ocr_and_parsing():
    print("\n── 1. OCR + sender parsing: what is visible right now ─────────")
    try:
        from monitor_v2 import ChatMonitor
        monitor = ChatMonitor()
        messages = monitor._get_all_messages()
        if messages:
            print(f"  Found {len(messages)} item(s):\n")
            for msg in messages:
                sender_label = f"[{msg.sender}]" if msg.sender else "[unknown sender]"
                print(f"  {sender_label}")
                print(f"    {msg.text}")
                print()
        else:
            print("  Nothing found. Is the KakaoTalk group chat window open and visible?")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_translation():
    print("── 2. Translation ──────────────────────────────────────────────")
    sample = "4시까지 한다고 함니다"
    print(f"  Input : {sample}")
    try:
        from translator import translate_batch_to_english
        result = translate_batch_to_english([sample])
        print(f"  Output: {result[0]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_dm_format():
    print("── 3. DM format preview ────────────────────────────────────────")
    try:
        from monitor_v2 import ChatMessage
        from translator import translate_batch_to_english, has_korean
        from main_v2 import _format_dm

        samples = [
            ChatMessage(sender="오민경 Fhoebe Oh", text="4시까지 한다고 함니다"),
            ChatMessage(sender="양영환",            text="네시에 딱 끝나는데 튀어가야디.--"),
            ChatMessage(sender="박지수",            text="ATW meeting at 3pm!"),
        ]

        korean_samples = [m for m in samples if has_korean(m.text)]
        translations = translate_batch_to_english([m.text for m in korean_samples])
        trans_map = {m.text: t for m, t in zip(korean_samples, translations)}

        for msg in samples:
            translation = trans_map.get(msg.text, "")
            dm = _format_dm(msg, translation)
            print("  ┌─ DM preview ──────────────────────")
            for line in dm.splitlines():
                print(f"  │ {line}")
            print("  └───────────────────────────────────")
            print()
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


def test_dm_send():
    print("── 4. DM send ──────────────────────────────────────────────────")
    try:
        from messenger import send_self_dm
        ok = send_self_dm(
            "[KakaoTranslate v2 test]\n"
            "[오민경 Fhoebe Oh] 4시까지 한다고 함니다\n"
            "→ It says until 4 o'clock."
        )
        if not ok:
            print("  DM not sent — check the warning above.")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()


if __name__ == "__main__":
    print("KakaoTranslate v2 — diagnostic test")
    print("Make sure KakaoTalk is open with the group chat AND My Chatroom visible.")
    test_ocr_and_parsing()
    test_translation()
    test_dm_format()
    test_dm_send()
    print("Done. Check your My Chatroom window for the test DM.")
