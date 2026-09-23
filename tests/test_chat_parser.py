import unittest

from chat_parser import Message, parse_chat_text
from message_diff import find_new_messages, fuzzy_same

SAMPLE = """2026년 9월 23일 화요일
[김민준] [오전 10:47] 언제가면되려나?
[이서연] [오전 10:47] LA를 안가봐서 못해주겠습니다
홍길동님이 들어왔습니다.
[Alex] [10:49 AM] Every day is national galbi day for me
second line of Alex's message
[Y] [PM 1:05] 고마워 미리
"""


class ParseTests(unittest.TestCase):
    def test_parses_senders_times_and_continuations(self):
        msgs = parse_chat_text(SAMPLE)
        self.assertEqual([m.sender for m in msgs], ['김민준', '이서연', 'Alex', 'Y'])
        self.assertEqual(msgs[0].time, '오전 10:47')
        self.assertEqual(msgs[2].text, "Every day is national galbi day for me\nsecond line of Alex's message")
        self.assertEqual(msgs[1].text, 'LA를 안가봐서 못해주겠습니다')  # system line not appended

    def test_windows_line_endings(self):
        msgs = parse_chat_text(SAMPLE.replace('\n', '\r\n'))
        self.assertEqual(len(msgs), 4)

    def test_garbage_gives_nothing(self):
        self.assertEqual(parse_chat_text('hello\nworld'), [])


def _m(i, text=None):
    return Message(f's{i % 3}', f'10:{i:02d}', text or f'msg {i}')


class DiffTests(unittest.TestCase):
    def test_appended_messages_are_new(self):
        prev = [_m(i) for i in range(10)]
        curr = prev + [_m(10), _m(11)]
        self.assertEqual(find_new_messages(prev, curr), [_m(10), _m(11)])

    def test_older_history_loaded_above_is_not_new(self):
        prev = [_m(i) for i in range(5, 15)]
        curr = [_m(i) for i in range(0, 16)]
        self.assertEqual(find_new_messages(prev, curr), [_m(15)])

    def test_identical_repeated_messages(self):
        prev = [_m(1), _m(2, 'ㅋㅋ'), _m(3)]
        curr = prev + [Message('s1', '10:04', 'ㅋㅋ')]
        self.assertEqual(len(find_new_messages(prev, curr)), 1)

    def test_nothing_new(self):
        prev = [_m(i) for i in range(6)]
        self.assertEqual(find_new_messages(prev, list(prev)), [])

    def test_edited_last_message_does_not_resend_everything(self):
        prev = [_m(i) for i in range(8)]
        curr = [_m(i) for i in range(7)] + [_m(7, '삭제된 메시지입니다.'), _m(8)]
        self.assertEqual(find_new_messages(prev, curr), [_m(8)])

    def test_fuzzy_comparison_for_ocr(self):
        prev = ['언제가면되려나?', 'LA틀 안가화서 못해주켓습니다', '고마위 미리']
        curr = ['언제가면되려나?', 'LA를 안가화서 못해주켓습니다', '고마위 미리', '새 메시지']
        new = find_new_messages(prev, curr, same=fuzzy_same)
        self.assertEqual(new, ['새 메시지'])


if __name__ == '__main__':
    unittest.main()
