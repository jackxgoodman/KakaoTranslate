"""
Parse chat text copied out of a KakaoTalk PC chat window with Ctrl+A, Ctrl+C (v3).
See message_diff.py for detecting which messages are new.

Copied lines look like:
    [김민준] [오전 10:47] 언제가면되려나?
    [Alex] [10:49 AM] Every day is national galbi day for me
Lines without a "[name] [time]" prefix continue the previous message.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

_TIME = (
    r'(?:(?:오전|오후|AM|PM|am|pm)\s*\d{1,2}:\d{2}(?::\d{2})?'
    r'|\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|am|pm|오전|오후))?)'
)
_MESSAGE_RE = re.compile(r'^\[(?P<sender>[^\[\]]+)\]\s*\[(?P<time>' + _TIME + r')\]\s?(?P<text>.*)$')

_DATE_RE = re.compile(
    r'^[-=\s]*('
    r'\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일.*'
    r'|(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+\w+\s+\d{1,2},?\s+\d{4}.*'
    r'|\w+\s+\d{1,2},\s+\d{4}.*'
    r')[-=\s]*$'
)

_SYSTEM_RE = re.compile(
    r'(님이 들어왔습니다|님이 나갔습니다|님을 초대했습니다|님을 내보냈습니다|'
    r'joined this chatroom|left this chatroom|invited .+ to|has been removed from)',
    re.IGNORECASE,
)


@dataclass
class Message:
    sender: str
    time: str
    text: str

    @property
    def key(self) -> tuple:
        return (self.sender, self.time, self.text)


def parse_chat_text(raw: str) -> List[Message]:
    messages: List[Message] = []
    current: Optional[Message] = None

    for line in raw.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        match = _MESSAGE_RE.match(line)
        if match:
            current = Message(
                sender=match.group('sender').strip(),
                time=match.group('time').strip(),
                text=match.group('text'),
            )
            messages.append(current)
            continue

        stripped = line.strip()
        if _DATE_RE.match(stripped) or _SYSTEM_RE.search(stripped):
            current = None
            continue
        if current is not None:
            current.text += '\n' + line

    for m in messages:
        m.text = m.text.strip()
    return [m for m in messages if m.text]

