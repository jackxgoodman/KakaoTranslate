"""Layout analysis on a synthetic KakaoTalk-style screenshot."""

import unittest

import numpy as np
from PIL import Image, ImageDraw

from chat_layout import OcrBox, analyze

BG = (186, 206, 224)
WHITE = (255, 255, 255)
YELLOW = (254, 229, 0)


def _ink(draw, box, colour):
    """Fake glyph strokes: vertical bars covering about a third of the box."""
    x0, y0, x1, y1 = box
    for x in range(x0 + 1, x1 - 1, 6):
        draw.rectangle([x, y0 + 3, x + 1, y1 - 3], fill=colour)


def build_screen():
    img = Image.new('RGB', (600, 900), BG)
    d = ImageDraw.Draw(img)
    boxes = []

    def text(box, s, colour=(0, 0, 0)):
        _ink(d, box, colour)
        boxes.append(OcrBox(*box, text=s, conf=0.9))

    text((100, 30, 220, 55), '스터디 그룹')
    text((110, 60, 130, 75), '38', (90, 90, 90))

    # 김민준: avatar, name, one bubble, timestamp
    d.rectangle([25, 110, 80, 170], fill=(120, 160, 90))
    text((95, 112, 160, 130), '김민준')
    d.rounded_rectangle([90, 138, 300, 175], radius=8, fill=WHITE)
    text((105, 146, 280, 168), '언제가면되려나?')
    text((305, 160, 360, 172), '10:47 AM', (60, 60, 60))

    # Y: avatar, name drawn but missed by OCR, two bubbles
    d.rectangle([25, 200, 80, 260], fill=(150, 205, 225))
    d.rectangle([30, 215, 75, 250], fill=(240, 250, 255))
    _ink(d, (95, 202, 106, 218), (20, 20, 20))
    d.rounded_rectangle([90, 228, 250, 265], radius=8, fill=WHITE)
    text((105, 236, 230, 258), '고마워 미리')
    d.rounded_rectangle([90, 272, 330, 309], radius=8, fill=WHITE)
    text((105, 280, 310, 302), 'second bubble')

    # Alex: reply bubble with grey quote, separator, wrapped two-chunk line
    d.rectangle([25, 330, 80, 390], fill=(90, 140, 200))
    text((95, 332, 130, 350), 'Alex')
    d.rounded_rectangle([90, 358, 420, 480], radius=8, fill=WHITE)
    text((105, 366, 240, 384), 'Reply to 이서연')
    text((105, 392, 300, 410), 'National Galbi Day', (120, 120, 120))
    d.line([105, 420, 405, 420], fill=(225, 225, 225))
    text((105, 432, 300, 450), 'Every day is')
    text((305, 432, 400, 450), 'national')
    text((105, 456, 200, 474), 'galbi day')

    # Your own message
    d.rounded_rectangle([400, 500, 560, 535], radius=8, fill=YELLOW)
    text((415, 508, 545, 528), '내 메시지')

    # Input box
    d.rectangle([0, 790, 600, 900], fill=WHITE)
    text((20, 810, 150, 830), 'Enter a message', (150, 150, 150))
    return np.asarray(img), boxes


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.img, self.boxes = build_screen()
        self.name_requests = []

        def read_name(rect):
            self.name_requests.append(rect)
            return 'Y'

        self.layout = analyze(self.img, self.boxes, chat_name='스터디 그룹', read_name=read_name)

    def test_messages_and_senders(self):
        got = [(m.sender, m.text, m.own) for m in self.layout.messages]
        self.assertEqual(got, [
            ('김민준', '언제가면되려나?', False),
            ('Y', '고마워 미리', False),
            ('Y', 'second bubble', False),
            ('Alex', 'Every day is national galbi day', False),
            ('Me', '내 메시지', True),
        ])

    def test_regions(self):
        self.assertGreaterEqual(self.layout.header_bottom, 75)
        self.assertLess(self.layout.header_bottom, 110)
        self.assertEqual(self.layout.footer_top, 790)
        self.assertEqual(len(self.layout.avatars), 3)

    def test_missing_name_is_read_from_tight_crop(self):
        self.assertEqual(len(self.name_requests), 1)
        x0, y0, x1, y1 = self.name_requests[0]
        self.assertTrue(85 <= x0 <= 96 and 105 <= x1 <= 115 and 195 <= y0 <= 203 and 217 <= y1 <= 225)

    def test_kinds(self):
        kinds = {b.text: b.kind for b in self.boxes}
        self.assertEqual(kinds['스터디 그룹'], 'header')
        self.assertEqual(kinds['10:47 AM'], 'noise')
        self.assertEqual(kinds['National Galbi Day'], 'quote')
        self.assertEqual(kinds['Enter a message'], 'footer')
        self.assertEqual(kinds['김민준'], 'label')

    def test_word_level_joining(self):
        img, boxes = build_screen()
        for b in boxes:
            if b.text == 'national':
                b.x0 = 301  # touching the previous word → same word for a word-level engine
        layout = analyze(img, boxes, chat_name='스터디 그룹', by_gap=True, read_name=lambda r: 'Y')
        alex = [m for m in layout.messages if m.sender == 'Alex'][0]
        self.assertEqual(alex.text, 'Every day isnational galbi day')


if __name__ == '__main__':
    unittest.main()
