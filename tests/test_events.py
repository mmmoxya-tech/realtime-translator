import json
import unittest

from rttranslate.events import Event


class EventTests(unittest.TestCase):
    def test_unicode_round_trip(self):
        event = Event("translation", 3, "hello", "你好", 12.0)
        self.assertEqual(json.loads(event.encode())["translation"], "你好")

    def test_translation_metrics_are_encoded(self):
        event = Event("translation", queue_ms=12.5, translation_ms=34.2,
                      asr_ms=8.1, end_to_end_ms=54.8)
        encoded = json.loads(event.encode())
        self.assertEqual(encoded["queue_ms"], 12.5)
        self.assertEqual(encoded["translation_ms"], 34.2)
        self.assertEqual(encoded["asr_ms"], 8.1)
        self.assertEqual(encoded["end_to_end_ms"], 54.8)
