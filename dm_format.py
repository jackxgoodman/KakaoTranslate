"""Build the self-chat DMs from new messages (shared by v2 and v3)."""

from typing import List, Sequence

from translator import has_korean, translate_batch_to_english

_MAX_DM_CHARS = 3000


def translate_messages(messages: Sequence) -> List[str]:
    """One translation per message ('' for messages without Korean), in the same order."""
    korean = [i for i, m in enumerate(messages) if has_korean(m.text)]
    translations = translate_batch_to_english([messages[i].text for i in korean])
    out = [''] * len(messages)
    for i, t in zip(korean, translations):
        out[i] = t
    return out


def format_message(msg, translation: str) -> str:
    """
    [김지은 Jenny Kim] 4시까지 한다고 함니다
    → It's until 4 o'clock.
    """
    sender = f"[{msg.sender}] " if msg.sender else ""
    if translation:
        return f"{sender}{msg.text}\n→ {translation}"
    return f"{sender}{msg.text}"


def build_dms(messages: Sequence, translations: Sequence[str], batch: bool) -> List[str]:
    blocks = [format_message(m, t) for m, t in zip(messages, translations)]
    if not batch:
        return blocks
    dms: List[str] = []
    current = ''
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if current and len(candidate) > _MAX_DM_CHARS:
            dms.append(current)
            current = block
        else:
            current = candidate
    if current:
        dms.append(current)
    return dms
