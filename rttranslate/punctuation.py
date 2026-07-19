from __future__ import annotations

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = PROJECT_DIR / "models/sherpa-onnx-online-punct-en-2024-08-06"


class StreamingPunctuator:
    """Fast punctuation and casing restoration for cumulative ASR text."""

    def __init__(self, model_dir: str | Path = DEFAULT_MODEL):
        import sherpa_onnx

        self.model_dir = Path(model_dir)
        model = sherpa_onnx.OnlinePunctuationModelConfig(
            str(self.model_dir / "model.int8.onnx"),
            str(self.model_dir / "bpe.vocab"),
            num_threads=1,
        )
        self.punctuator = sherpa_onnx.OnlinePunctuation(
            sherpa_onnx.OnlinePunctuationConfig(model))

    def check(self) -> None:
        if not all((self.model_dir / name).is_file()
                   for name in ("model.int8.onnx", "bpe.vocab")):
            raise RuntimeError("缺少英语在线标点模型")

    def apply(self, text: str, final: bool = False) -> str:
        if not text.strip():
            return ""
        result = self.punctuator.add_punctuation_with_case(text.lower()).strip()
        if final and result[-1:] not in ".!?":
            result += "."
        return result
