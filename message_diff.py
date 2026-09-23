"""Work out which messages are new between two snapshots of a chat (used by v2 and v3)."""

from collections import Counter
from difflib import SequenceMatcher
from typing import Callable, List, Optional, Sequence, TypeVar

T = TypeVar('T')

_ANCHOR_LEN = 5
_MAX_EDITED_TAIL = 5


def fuzzy_same(a: str, b: str, threshold: float = 0.85) -> bool:
    """Treat OCR readings of the same text as equal despite small misreads."""
    if a == b:
        return True
    if not a or not b:
        return False
    matcher = SequenceMatcher(None, a, b)
    return matcher.quick_ratio() >= threshold and matcher.ratio() >= threshold


def find_new_messages(
    previous: Sequence[T],
    current: Sequence[T],
    same: Optional[Callable[[T, T], bool]] = None,
) -> List[T]:
    """
    Return the items of `current` that come after everything in `previous`.

    The last few previous items are located in the current snapshot (an
    "anchor") and everything after them is new, so older history that appears
    when someone scrolls up is ignored. A few trailing items may differ, in
    case a message was deleted or re-read differently.
    `same` compares two items; default is `a.key == b.key`.
    """
    if not previous:
        return list(current)
    eq = same or (lambda a, b: a.key == b.key)

    def matches_at(start: int, anchor: Sequence[T]) -> bool:
        return all(eq(p, current[start + i]) for i, p in enumerate(anchor))

    for skipped in range(0, min(_MAX_EDITED_TAIL, len(previous) - 1) + 1):
        end = len(previous) - skipped
        for length in range(min(_ANCHOR_LEN, end), 0, -1):
            anchor = previous[end - length:end]
            for start in range(len(current) - length, -1, -1):
                if matches_at(start, anchor):
                    return list(current[start + length + skipped:])
            if length <= 2 and end - length > 0:
                break  # a 1–2 item anchor with more history available is too ambiguous

    # Anchor lost (e.g. a burst bigger than one snapshot): return items that
    # previous doesn't account for.
    if same is None:
        remaining = Counter(p.key for p in previous)
        new = []
        for item in current:
            if remaining[item.key] > 0:
                remaining[item.key] -= 1
            else:
                new.append(item)
        return new
    unused = list(previous)
    new = []
    for item in current:
        for i, p in enumerate(unused):
            if eq(p, item):
                del unused[i]
                break
        else:
            new.append(item)
    return new
