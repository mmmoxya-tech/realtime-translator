import json
import tempfile
import unittest
from pathlib import Path

from rttranslate.terminology import Terminology


class TerminologyTests(unittest.TestCase):
    def write_config(self, directory, name, data):
        path = Path(directory) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_applies_rules_in_file_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(
                directory, "terms.json", {"潜伏": "延迟", "吞吐": "吞吐量"})
            terminology = Terminology([path])
            self.assertEqual(
                terminology.apply("潜伏和吞吐的区别"), "延迟和吞吐量的区别")

    def test_multiple_files_are_applied_in_argument_order(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.write_config(directory, "first.json", {"A": "B"})
            second = self.write_config(directory, "second.json", {"B": "C"})
            self.assertEqual(Terminology([first, second]).apply("A"), "C")

    def test_missing_file_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, "无法读取术语配置"):
            Terminology(["does-not-exist.json"])

    def test_invalid_shape_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, "terms.json", ["not", "a", "map"])
            with self.assertRaisesRegex(RuntimeError, "JSON 对象"):
                Terminology([path])

    def test_empty_configuration_does_not_change_text(self):
        self.assertEqual(Terminology().apply("保持原样"), "保持原样")
