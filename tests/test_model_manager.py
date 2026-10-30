from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from companera.application.commands import CommandAction, handle_command
from companera.application.reply_parser import parse_reply
from companera.application.quota import classify_quota
from companera.infrastructure.pacific_time import pacific_offset_hours, pacific_day_key, next_pacific_midnight
from companera.infrastructure.usage_tracker import format_tokens


class ModelManagerTests(unittest.TestCase):
    def test_typed_commands_and_aliases(self):
        for text, action in (("/clear", CommandAction.CLEAR_HISTORY), ("/limpiar", CommandAction.CLEAR_HISTORY), ("/mute voice", CommandAction.MUTE_VOICE), ("/exit", CommandAction.EXIT), ("/modelo", CommandAction.OPEN_MODEL_PICKER)):
            self.assertEqual(handle_command(text).action, action)
        self.assertIsNone(handle_command("hola"))
        self.assertEqual(handle_command("/model gemini-lite").action, CommandAction.SET_MODEL)

    def test_pacific_rules(self):
        self.assertEqual(pacific_offset_hours(datetime(2026, 3, 8, 9, 59, tzinfo=timezone.utc)), -8)
        self.assertEqual(pacific_offset_hours(datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)), -7)
        self.assertEqual(pacific_offset_hours(datetime(2026, 11, 1, 8, 59, tzinfo=timezone.utc)), -7)
        self.assertEqual(pacific_offset_hours(datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)), -8)
        utc = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(pacific_day_key(utc), "2026-10-30")
        self.assertEqual(next_pacific_midnight(utc), datetime(2026, 10, 31, 7, 0, tzinfo=timezone.utc))

    def test_parser_and_tokens(self):
        reply = parse_reply('ruido {"text":"hola","expression":"xyz","mood":"calm","topic":"general","title":"","target":"none","target_label":""} fin')
        self.assertEqual(reply.text, "hola")
        self.assertEqual(reply.expression, "calm")
        self.assertEqual(format_tokens(999), "999")
        self.assertEqual(format_tokens(1300), "1,3k")
        self.assertEqual(format_tokens(41200), "41,2k")
        self.assertEqual(format_tokens(1200000), "1,2M")

    def test_quota_classification(self):
        self.assertEqual(classify_quota("perday limit exceeded retryDelay 32s").kind, "day")
        self.assertEqual(classify_quota("per minute limit").kind, "minute")
        self.assertEqual(classify_quota("retryDelay: 32s").retry_after, 32)


if __name__ == "__main__":
    unittest.main()
