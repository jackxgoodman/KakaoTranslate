import unittest
from unittest import mock

import dm_format


class RecipientTests(unittest.TestCase):
    def recipients(self, me, extra, group='스터디 그룹'):
        with mock.patch.multiple(dm_format, SELF_CHAT_TITLE=me, EXTRA_RECIPIENTS=extra, CHAT_NAME=group):
            return dm_format.dm_recipients()

    def test_self_then_extra_people(self):
        self.assertEqual(self.recipients('Me', ['홍길동', 'Alex']), ['Me', '홍길동', 'Alex'])

    def test_blank_and_duplicate_names_skipped(self):
        self.assertEqual(self.recipients('Me', ['', ' 홍길동 ', '홍길동', 'Me']), ['Me', '홍길동'])

    def test_group_chat_is_never_a_recipient(self):
        self.assertEqual(self.recipients('Me', ['스터디 그룹', '홍길동']), ['Me', '홍길동'])

    def test_works_without_self_chat(self):
        self.assertEqual(self.recipients('', ['홍길동']), ['홍길동'])


if __name__ == '__main__':
    unittest.main()
