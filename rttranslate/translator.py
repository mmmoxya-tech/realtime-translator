from __future__ import annotations

from pathlib import Path
import re


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = PROJECT_DIR / "models/opus-mt-en-zh-ct2"
DEFAULT_SOURCE_SPM = PROJECT_DIR / "models/opus-mt-en-zh-source/source.spm"
DEFAULT_TARGET_SPM = PROJECT_DIR / "models/opus-mt-en-zh-source/target.spm"


class LocalTranslator:
    """Low-latency English-to-Chinese translation with OPUS-MT."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL,
                 threads: int = 6):
        import ctranslate2
        import sentencepiece as spm

        self.model_path = Path(model_path)
        self.threads = threads
        self.source_spm = spm.SentencePieceProcessor(
            model_file=str(DEFAULT_SOURCE_SPM))
        self.target_spm = spm.SentencePieceProcessor(
            model_file=str(DEFAULT_TARGET_SPM))
        self.model = ctranslate2.Translator(
            str(self.model_path), device="cpu", compute_type="int8",
            inter_threads=1, intra_threads=threads)

    def check(self) -> None:
        required = (self.model_path / "model.bin",
                    self.model_path / "config.json",
                    DEFAULT_SOURCE_SPM, DEFAULT_TARGET_SPM)
        if not all(path.is_file() for path in required):
            raise RuntimeError("缺少本地 OPUS-MT 英译中模型")

    def warmup(self) -> None:
        """Load weights and allocate runtime buffers before speech starts."""
        self.translate("Hello.")

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        source = [">>cmn_Hans<<"] + self.source_spm.encode(
            text.strip(), out_type=str)
        result = self.model.translate_batch(
            [source], beam_size=2, max_decoding_length=96,
            repetition_penalty=1.1)[0]
        translated = self.target_spm.decode(result.hypotheses[0]).strip()
        translated = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
                            "", translated)
        translated = re.sub(r"\s+([，。！？；：、,.!?;:])", r"\1", translated)
        return translated.translate(str.maketrans(",.!?;:", "，。！？；："))
