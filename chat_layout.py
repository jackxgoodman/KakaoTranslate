"""
Turn a KakaoTalk chat-window screenshot plus OCR boxes into messages (v2).

Instead of guessing from the words whether a piece of text is a name or a
message, this reads the window's visual structure:
  - message text sits inside bubbles (white for others, yellow for you),
    names/timestamps sit on the plain chat background;
  - reply quotes are drawn in grey, message text in black;
  - each new sender block starts with a profile picture on the left;
  - the header (chat title) and the input box / pinned notice are excluded
    by position and by their full-width white bands.
Pure numpy: no Windows or OCR dependencies, so it can be tested anywhere.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Callable, List, Optional, Tuple

import numpy as np


@dataclass
class OcrBox:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    conf: float = 1.0
    kind: str = ''     # label | bubble | own | quote | other | header | footer | band | noise
    contrast: float = 0.0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Bubble:
    left: int
    right: int
    own: bool
    boxes: List[OcrBox] = field(default_factory=list)
    top: int = 0
    bottom: int = 0
    cut: bool = False
    text: str = ''
    sender: str = ''


@dataclass
class Avatar:
    top: int
    bottom: int
    right: int
    cut: bool = False  # partly hidden at the top/bottom edge or under a pinned notice


@dataclass
class LayoutMessage:
    sender: str
    text: str
    top: int
    cut: bool = False
    own: bool = False


@dataclass
class Layout:
    messages: List[LayoutMessage]
    boxes: List[OcrBox]
    bubbles: List[Bubble]
    avatars: List[Avatar]
    header_bottom: int
    footer_top: int
    bands: List[Tuple[int, int]]
    background: Tuple[int, int, int]


MIN_CONF = 0.1
_BG_TOL = 30
_WHITE_MIN = 235
_QUOTE_CONTRAST = 175
_LABEL_MIN_CONTRAST = 80

_HANGUL = re.compile(r'[가-힣ㄱ-ㅎㅏ-ㅣ]')
_LETTER = re.compile(r'[가-힣ㄱ-ㅎㅏ-ㅣA-Za-z]')
_TIMESTAMP = re.compile(
    r'^((오전|오후|AM|PM)\s*)?\d{1,2}\s*[.:;,]\s*\d{2}(\s*[A-Za-z]{0,3})?$|^(오전|오후)\s*\d', re.IGNORECASE
)
_REPLY = re.compile(r'^(Reply\s+to|답장)\b', re.IGNORECASE)
_PLACEHOLDER = re.compile(r'^(enter\s*a?\s*message|메시지(를)?\s*입력)', re.IGNORECASE)


# ── Pixel helpers ─────────────────────────────────────────────────────────

def _lum(rgb) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=np.float32)
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _is_bg(pixels: np.ndarray, bg: np.ndarray) -> np.ndarray:
    return np.abs(pixels.astype(np.int16) - bg).max(axis=-1) <= _BG_TOL


def _is_white(pixels: np.ndarray) -> np.ndarray:
    return pixels.min(axis=-1) >= _WHITE_MIN


def _runs(mask: np.ndarray, max_gap: int = 0, min_len: int = 1) -> List[Tuple[int, int]]:
    """[start, end) runs of True values, merging gaps up to max_gap."""
    runs: List[List[int]] = []
    start = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append([start, i])
            start = None
    if start is not None:
        runs.append([start, len(mask)])
    merged: List[List[int]] = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= max_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a, b) for a, b in merged if b - a >= min_len]


def estimate_background(img: np.ndarray) -> np.ndarray:
    """Chat background colour, sampled from the thin strip left of the profile pictures."""
    h, w = img.shape[:2]
    x0 = max(1, int(w * 0.008))
    x1 = max(x0 + 2, int(w * 0.035))
    strip = img[int(h * 0.15):int(h * 0.85), x0:x1].reshape(-1, 3)
    return np.median(strip, axis=0).astype(np.int16)


def find_bands(img: np.ndarray) -> List[Tuple[int, int]]:
    """Full-width white bands: the input box and a pinned notice. Message bubbles are never this wide."""
    h, w = img.shape[:2]
    region = img[:, int(w * 0.03):int(w * 0.97)]
    frac = _is_white(region).mean(axis=1)
    return _runs(frac >= 0.85, max_gap=max(4, h // 35), min_len=max(6, h // 60))


def find_footer_top(bands: List[Tuple[int, int]], height: int) -> int:
    for start, _end in bands:
        if start >= height * 0.6:
            return start
    return height


# ── Region + box classification ───────────────────────────────────────────

def _norm(text: str) -> str:
    return re.sub(r'[\s\W_]+', '', text).lower()


def find_header_bottom(boxes: List[OcrBox], chat_name: str, height: int,
                       override: Optional[int] = None) -> int:
    if override:
        return int(override)
    target = _norm(chat_name)
    best, best_ratio = None, 0.0
    if target:
        for b in boxes:
            if b.cy < height * 0.3:
                ratio = SequenceMatcher(None, _norm(b.text), target).ratio()
                if ratio > best_ratio:
                    best, best_ratio = b, ratio
    if best is None or best_ratio < 0.6:
        return int(height * 0.12)
    bottom = best.y1
    for b in boxes:  # member-count line under the title
        if best.y1 - 2 <= b.y0 <= best.y1 + best.h * 1.2 and abs(b.x0 - best.x0) <= best.h * 1.5:
            bottom = max(bottom, b.y1)
    return int(bottom + best.h * 0.25)


def _classify(img: np.ndarray, box: OcrBox, bg: np.ndarray) -> None:
    x0, y0 = max(0, int(box.x0)), max(0, int(box.y0))
    x1, y1 = min(img.shape[1], int(np.ceil(box.x1))), min(img.shape[0], int(np.ceil(box.y1)))
    region = img[y0:y1, x0:x1].reshape(-1, 3)
    if region.size == 0:
        box.kind = 'noise'
        return
    local = np.median(region, axis=0)
    lum = _lum(region)
    box.contrast = float(np.percentile(np.abs(lum - _lum(local)), 97))

    if np.abs(local - bg).max() <= _BG_TOL:
        box.kind = 'label'
    elif local[0] > 200 and local[1] > 180 and local[2] < 120:
        box.kind = 'own'
    elif local.min() >= _WHITE_MIN or _lum(local) >= _lum(bg) + 25:
        box.kind = 'quote' if box.contrast < _QUOTE_CONTRAST else 'bubble'
    else:
        box.kind = 'other'  # date / system notice pills, reaction chips


# ── Bubbles ───────────────────────────────────────────────────────────────

def _bubble_edges(img: np.ndarray, box: OcrBox, bg: np.ndarray) -> Tuple[int, int]:
    y = int(box.cy)
    row = img[y]
    bg_mask = _is_bg(row, bg)
    left = int(box.x0)
    while left > 0 and not bg_mask[left - 1]:
        left -= 1
    right = int(box.x1)
    while right < len(row) - 1 and not bg_mask[right + 1]:
        right += 1
    return left, right


def _column_connected(img: np.ndarray, x: int, ya: int, yb: int, bg: np.ndarray) -> bool:
    if yb <= ya:
        return True
    return not _is_bg(img[ya:yb, x], bg).any()


def _vertical_extent(img, bubble: Bubble, bg, top_limit: int, bottom_limit: int,
                     bands: List[Tuple[int, int]]) -> None:
    inset = 3
    x = bubble.right - inset if not bubble.own else bubble.left + inset
    corner_x = bubble.right - 1 if not bubble.own else bubble.left + 1

    def in_band(y):
        return any(a <= y < b for a, b in bands)

    y = int(min(b.y0 for b in bubble.boxes))
    cut_top = False
    while True:
        if y - 1 < top_limit or in_band(y - 1):
            cut_top = True
            break
        if _is_bg(img[y - 1, x], bg):
            break
        y -= 1
    bubble.top = y
    if not cut_top and _is_white(img[y, corner_x]) and not bubble.own:
        cut_top = True  # square top corner: clipped by the chat viewport edge

    y = int(max(b.y1 for b in bubble.boxes))
    cut_bottom = False
    while True:
        if y + 1 >= bottom_limit or in_band(y + 1):
            cut_bottom = True
            break
        if _is_bg(img[y + 1, x], bg):
            break
        y += 1
    bubble.bottom = y
    bubble.cut = cut_top or cut_bottom


def _group_bubbles(img, boxes: List[OcrBox], bg) -> List[Bubble]:
    bubbles: List[Bubble] = []
    for box in sorted(boxes, key=lambda b: b.cy):
        left, right = _bubble_edges(img, box, bg)
        own = box.kind == 'own'
        for bub in reversed(bubbles):
            if (bub.own == own and abs(bub.left - left) <= 4 and abs(bub.right - right) <= 4
                    and _column_connected(img, left + 3, int(bub.boxes[-1].cy), int(box.cy), bg)):
                bub.boxes.append(box)
                break
        else:
            bubbles.append(Bubble(left=left, right=right, own=own, boxes=[box]))
    return bubbles


def _lines(boxes: List[OcrBox]) -> List[List[OcrBox]]:
    lines: List[List[OcrBox]] = []
    for box in sorted(boxes, key=lambda b: b.cy):
        for line in lines:
            ref = line[0]
            overlap = min(ref.y1, box.y1) - max(ref.y0, box.y0)
            if overlap >= 0.5 * min(ref.h, box.h):
                line.append(box)
                break
        else:
            lines.append([box])
    for line in lines:
        line.sort(key=lambda b: b.x0)
    lines.sort(key=lambda ln: min(b.y0 for b in ln))
    return lines


def _join_words(line: List[OcrBox], by_gap: bool) -> str:
    out = line[0].text.strip()
    for prev, cur in zip(line, line[1:]):
        gap = cur.x0 - prev.x1
        glue = '' if by_gap and gap < 0.22 * max(prev.h, cur.h) else ' '
        out += glue + cur.text.strip()
    return out


def _separator_row(img, bubble: Bubble, y_from: int) -> Optional[int]:
    """Thin grey rule that separates a reply's quote from its text."""
    pad = max(4, int(min(b.x0 for b in bubble.boxes)) - bubble.left)
    x0, x1 = bubble.left + pad, bubble.right - pad
    if x1 - x0 < 10:
        return None
    for y in range(y_from, bubble.bottom):
        row = img[y, x0:x1]
        if (_lum(row) < 235).mean() > 0.6 and not (_lum(img[y + 1, x0:x1]) < 235).mean() > 0.6 \
                and (_lum(img[y - 2, x0:x1]) >= 235).mean() > 0.9:
            return y
    return None


def _bubble_text(img, bubble: Bubble, by_gap: bool) -> str:
    lines = _lines(bubble.boxes)
    reply_idx = [i for i, ln in enumerate(lines) if _REPLY.match(_join_words(ln, by_gap))]
    if reply_idx:
        sep = _separator_row(img, bubble, int(max(b.y1 for b in lines[reply_idx[0]])))
        keep = []
        for i, ln in enumerate(lines):
            if i <= reply_idx[0]:
                continue
            if sep is not None and max(b.y1 for b in ln) <= sep:
                continue  # quoted text above the separator
            keep.append(ln)
        lines = keep
    lines = [[b for b in ln if b.kind != 'quote'] for ln in lines]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ''

    pad = min(b.x0 for b in bubble.boxes) - bubble.left
    text_right = bubble.right - pad
    text = _join_words(lines[0], by_gap)
    for prev, cur in zip(lines, lines[1:]):
        prev_text, cur_text = _join_words(prev, by_gap), _join_words(cur, by_gap)
        full_width = max(b.x1 for b in prev) >= text_right - 1.5 * max(b.h for b in prev)
        mid_word = full_width and _HANGUL.match(cur_text[:1] or ' ') and _HANGUL.search(prev_text[-1:] or ' ')
        text += ('' if mid_word else ' ') + cur_text
    return text.strip()


# ── Avatars + senders ─────────────────────────────────────────────────────

def find_avatars(img, bg, band_right: int, top: int, bottom: int, min_height: float,
                 bands: List[Tuple[int, int]]) -> List[Avatar]:
    w = img.shape[1]
    x0 = max(1, int(w * 0.008))
    if band_right - x0 < 8:
        return []
    region = img[top:bottom, x0:band_right]
    rows = (~_is_bg(region, bg)).mean(axis=1) > 0.3
    blocked = np.zeros(len(rows), dtype=bool)
    for a, b in bands:
        blocked[max(0, a - top):max(0, b - top)] = True
    rows &= ~blocked

    def edge(i):
        return i < 0 or i >= len(rows) or blocked[i]

    avatars = []
    for a, b in _runs(rows, max_gap=2):
        cut = edge(a - 1) or edge(b)
        if b - a >= min_height or (cut and b - a >= 4):
            cols = (~_is_bg(region[a:b], bg)).mean(axis=0)
            filled = np.nonzero(cols > 0.3)[0]
            right = x0 + int(filled.max()) if len(filled) else band_right
            avatars.append(Avatar(top=top + a, bottom=top + b, right=right, cut=cut))
    return avatars


def _ink_rect(img, bg, rect: Tuple[int, int, int, int]) -> Optional[Tuple[int, int, int, int]]:
    """Tight box around the first line of text inside rect (single letters defeat OCR text detectors)."""
    x0, y0, x1, y1 = rect
    region = img[y0:y1, x0:x1]
    if region.size == 0:
        return None
    ink = np.abs(_lum(region) - _lum(bg)) > 60
    rows = _runs(ink.any(axis=1), max_gap=2)
    if not rows:
        return None
    ra, rb = rows[0]
    cols = np.nonzero(ink[ra:rb].any(axis=0))[0]
    pad = 4
    return (max(0, x0 + int(cols.min()) - pad), max(0, y0 + ra - pad),
            min(img.shape[1], x0 + int(cols.max()) + pad + 1), min(img.shape[0], y0 + rb + pad))


def _is_name_label(label: OcrBox, bubbles: List[Bubble], width: int) -> bool:
    for bub in bubbles:
        if bub.own:
            continue
        if label.y1 - 0.3 * label.h <= bub.top <= label.y1 + 2.0 * label.h \
                and abs(bub.left - label.x0) <= max(12, 0.03 * width):
            return True
    return False


# ── Main entry point ──────────────────────────────────────────────────────

def analyze(
    img: np.ndarray,
    boxes: List[OcrBox],
    chat_name: str = '',
    header_override: Optional[int] = None,
    by_gap: bool = False,
    read_name: Optional[Callable[[Tuple[int, int, int, int]], str]] = None,
) -> Layout:
    """
    img: HxWx3 uint8 RGB screenshot of the chat window.
    boxes: OCR results in the same pixel coordinates.
    by_gap: join word boxes using pixel gaps (word-level OCR engines).
    read_name: optional callback OCR-ing a (x0, y0, x1, y1) crop, used when a
               profile picture has no readable name next to it.
    """
    img = np.ascontiguousarray(img[..., :3])
    height, width = img.shape[:2]
    bg = estimate_background(img)
    bands = find_bands(img)
    footer_top = find_footer_top(bands, height)
    header_bottom = find_header_bottom(boxes, chat_name, height, header_override)
    inner_bands = [(a, b) for a, b in bands if b <= footer_top]

    kept: List[OcrBox] = []
    for box in boxes:
        box.text = box.text.strip()
        if box.cy < header_bottom:
            box.kind = 'header'
        elif box.cy >= footer_top:
            box.kind = 'footer'
        elif any(a <= box.cy < b for a, b in inner_bands):
            box.kind = 'band'
        elif box.conf < MIN_CONF or not _LETTER.search(box.text) or _PLACEHOLDER.match(box.text):
            box.kind = 'noise'
        else:
            _classify(img, box, bg)
            if box.kind == 'label' and (box.contrast < _LABEL_MIN_CONTRAST or _TIMESTAMP.match(box.text)):
                box.kind = 'noise'
        if box.kind in ('label', 'bubble', 'own', 'quote'):
            kept.append(box)

    bubbles = _group_bubbles(img, [b for b in kept if b.kind in ('bubble', 'own', 'quote')], bg)
    for bub in bubbles:
        _vertical_extent(img, bub, bg, header_bottom, footer_top, inner_bands)
        bub.text = _bubble_text(img, bub, by_gap)
    bubbles = [b for b in bubbles if b.text and _LETTER.search(b.text)]

    labels = [b for b in kept if b.kind == 'label']
    names = [lb for lb in labels if _is_name_label(lb, bubbles, width)]
    for lb in labels:
        if lb not in names:
            lb.kind = 'noise'
    for nm in names:
        edges = [header_bottom] + [b for _a, b in inner_bands]
        if any(nm.y0 - e <= 0.25 * nm.h and nm.y1 > e for e in edges):
            nm.text = '?'  # partly hidden under the header or a pinned notice

    others = [b for b in bubbles if not b.own]
    median_h = float(np.median([b.h for b in kept])) if kept else 20.0
    avatars: List[Avatar] = []
    if others:
        band_right = int(min([b.left for b in others] + [n.x0 for n in names])) - 4
        avatars = find_avatars(img, bg, band_right, header_bottom, footer_top, 1.5 * median_h, inner_bands)

    # Sender blocks: each profile picture or name label starts a new sender.
    starts: List[List] = []  # [y, name or None, avatar or None]
    for av in avatars:
        starts.append([av.top, None, av])
    for nm in names:
        for s in starts:
            av = s[2]
            if av and s[1] is None and abs(nm.y0 - av.top) <= 0.6 * (av.bottom - av.top) + median_h:
                s[1] = nm.text
                break
        else:
            starts.append([nm.y0, nm.text, None])
    starts.sort(key=lambda s: s[0])

    for s in starts:
        if s[1] is None and s[2] is not None and not s[2].cut and read_name is not None:
            av = s[2]
            below = [b.top for b in others if b.top > av.top]
            y1 = min(below) if below else av.top + (av.bottom - av.top) // 2
            rect = _ink_rect(img, bg, (av.right + 2, max(header_bottom, av.top - 4),
                                       min(width, av.right + int(width * 0.5)), y1))
            if rect:
                s[1] = (read_name(rect) or '').strip() or None

    for bub in bubbles:
        if bub.own:
            bub.sender = 'Me'
            continue
        owner = [s for s in starts if s[0] <= bub.top + 0.5 * median_h]
        bub.sender = (owner[-1][1] or '?') if owner else ''

    messages = [
        LayoutMessage(sender=b.sender, text=b.text, top=b.top, cut=b.cut, own=b.own)
        for b in sorted(bubbles, key=lambda b: b.top)
    ]
    return Layout(
        messages=messages, boxes=boxes, bubbles=bubbles, avatars=avatars,
        header_bottom=header_bottom, footer_top=footer_top, bands=inner_bands,
        background=tuple(int(v) for v in bg),
    )


def quick_regions(img: np.ndarray) -> Tuple[int, int]:
    """(0, footer_top) without OCR — used to hash the chat area and skip unchanged frames."""
    bands = find_bands(np.ascontiguousarray(img[..., :3]))
    return 0, find_footer_top(bands, img.shape[0])
