"""Build the translated DMs from new messages and decide who receives them."""

import logging
from typing import List, Sequence

from config import CHAT_NAME, EXTRA_RECIPIENTS, SELF_CHAT_TITLE
from translator import has_korean, translate_batch_to_english

logger = logging.getLogger(__name__)

_MAX_DM_CHARS = 3000
_warned_group_recipient = False


def dm_recipients() -> List[str]:
    """Window titles that get every DM: your My Chatroom first, then EXTRA_RECIPIENTS."""
    global _warned_group_recipient
    titles: List[str] = []
    for title in [SELF_CHAT_TITLE, *EXTRA_RECIPIENTS]:
        title = (title or '').strip()
        if not title or title in titles:
            continue
        if title == CHAT_NAME:
            # Never post translations back into the group chat being monitored
            if not _warned_group_recipient:
                logger.warning(f"Ignoring recipient '{title}': that's the group chat being translated.")
                _warned_group_recipient = True
            continue
        titles.append(title)
    return titles


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
