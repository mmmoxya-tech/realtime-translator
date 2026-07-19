from __future__ import annotations

import ctypes.util
import hashlib
import importlib.util
import shutil
import pathlib

from .audio import default_sink


def models_verified(project: pathlib.Path) -> bool:
    manifest = project / "MODEL_SHA256SUMS"
    try:
        entries = manifest.read_text().splitlines()
        for entry in entries:
            expected, relative = entry.split(maxsplit=1)
            path = project / relative
            digest = hashlib.sha256()
            with path.open("rb") as model_file:
                while chunk := model_file.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                return False
    except (OSError, ValueError):
        return False
    return bool(entries)


def report() -> int:
    project = pathlib.Path(__file__).resolve().parent.parent
    checks = [
        ("pw-record", shutil.which("pw-record") is not None),
        ("wpctl", shutil.which("wpctl") is not None),
        ("PipeWire default sink", bool(default_sink())),
        ("sherpa-onnx", importlib.util.find_spec("sherpa_onnx") is not None),
        ("NumPy", importlib.util.find_spec("numpy") is not None),
        ("SentencePiece", importlib.util.find_spec("sentencepiece") is not None),
        ("GTK4 layer-shell library", bool(ctypes.util.find_library("gtk4-layer-shell"))),
        ("OPUS-MT en-zh model",
         (project / "models/opus-mt-en-zh-ct2/model.bin").is_file()),
        ("Zipformer streaming ASR",
         (project / "models/sherpa-onnx-streaming-zipformer-en-2023-06-21/encoder-epoch-99-avg-1.int8.onnx").is_file()),
        ("Streaming English punctuation",
         (project / "models/sherpa-onnx-online-punct-en-2024-08-06/model.int8.onnx").is_file()),
        ("Model checksums", models_verified(project)),
    ]
    for name, ok in checks:
        print(f"{'OK  ' if ok else 'WARN'} {name}")
    return 0 if all(ok for _, ok in checks) else 1
