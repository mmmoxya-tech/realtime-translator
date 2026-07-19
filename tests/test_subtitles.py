import json
import tempfile
import unittest
from pathlib import Path

from rttranslate.subtitles import SubtitleRecorder


class SubtitleRecorderTests(unittest.TestCase):
    def record_one(self, path):
        recorder = SubtitleRecorder(str(path), started_at=10.0)
        recorder.record(11.25, 13.5, "Hello world.", "你好，世界。")
        recorder.close()

    def test_writes_srt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.srt"
            self.record_one(path)
            content = path.read_text()
            self.assertIn("00:00:01,250 --> 00:00:03,500", content)
            self.assertIn("你好，世界。\nHello world.", content)

    def test_writes_vtt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.vtt"
            self.record_one(path)
            content = path.read_text()
            self.assertTrue(content.startswith("WEBVTT"))
            self.assertIn("00:00:01.250 --> 00:00:03.500", content)

    def test_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.jsonl"
            self.record_one(path)
            entry = json.loads(path.read_text())
            self.assertEqual(entry["original"], "Hello world.")
            self.assertEqual(entry["translation"], "你好，世界。")

    def test_rejects_unknown_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "扩展名"):
                SubtitleRecorder(str(Path(directory) / "captions.txt"))
