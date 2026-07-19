import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rttranslate import translator


class TranslatorTests(unittest.TestCase):
    def test_missing_model_is_reported(self):
        instance = object.__new__(translator.LocalTranslator)
        with tempfile.TemporaryDirectory() as directory:
            instance.model_path = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "OPUS-MT"):
                instance.check()

    def test_translation_uses_simplified_chinese_token(self):
        instance = object.__new__(translator.LocalTranslator)
        instance.source_spm = mock.Mock()
        instance.source_spm.encode.return_value = ["▁hello"]
        instance.target_spm = mock.Mock()
        instance.target_spm.decode.return_value = "你好"
        result = mock.Mock()
        result.hypotheses = [["▁你好"]]
        instance.model = mock.Mock()
        instance.model.translate_batch.return_value = [result]
        self.assertEqual(instance.translate("hello"), "你好")
        source = instance.model.translate_batch.call_args.args[0][0]
        self.assertEqual(source[0], ">>cmn_Hans<<")
