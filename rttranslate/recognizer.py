from __future__ import annotations

from pathlib import Path

import numpy as np


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = PROJECT_DIR / "models/sherpa-onnx-streaming-zipformer-en-2023-06-21"


class StreamingRecognizer:
    """Stateful English streaming ASR; each audio sample is decoded once."""

    def __init__(self, model_dir: str | Path = DEFAULT_MODEL,
                 threads: int = 4):
        import sherpa_onnx

        model = Path(model_dir)
        self.model_dir = model
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(model / "tokens.txt"),
            encoder=str(model / "encoder-epoch-99-avg-1.int8.onnx"),
            decoder=str(model / "decoder-epoch-99-avg-1.int8.onnx"),
            joiner=str(model / "joiner-epoch-99-avg-1.int8.onnx"),
            num_threads=threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=1.0,
            rule2_min_trailing_silence=0.6,
            rule3_min_utterance_length=15.0,
        )
        self.stream = self.recognizer.create_stream()

    def check(self) -> None:
        required = (
            "tokens.txt",
            "encoder-epoch-99-avg-1.int8.onnx",
            "decoder-epoch-99-avg-1.int8.onnx",
            "joiner-epoch-99-avg-1.int8.onnx",
        )
        if not all((self.model_dir / name).is_file() for name in required):
            raise RuntimeError("缺少 Zipformer 英语流式语音模型")

    def accept(self, raw: bytes) -> None:
        if raw:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            self.stream.accept_waveform(16000, samples / 32768.0)

    def decode(self) -> str:
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        result = self.recognizer.get_result(self.stream)
        return (result if isinstance(result, str) else result.text).strip()

    @property
    def is_endpoint(self) -> bool:
        return self.recognizer.is_endpoint(self.stream)

    def reset(self) -> None:
        self.recognizer.reset(self.stream)
