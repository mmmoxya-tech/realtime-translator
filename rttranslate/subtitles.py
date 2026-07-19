from __future__ import annotations

import dataclasses
import json
import threading
import time
from pathlib import Path


@dataclasses.dataclass(slots=True)
class SubtitleEntry:
    start: float
    end: float
    original: str
    translation: str


class SubtitleRecorder:
    """Collect final bilingual subtitles and export them when the app exits."""

    def __init__(self, output_path: str | None, started_at: float | None = None):
        self.path = Path(output_path).expanduser() if output_path else None
        if self.path and self.path.suffix.lower() not in (".jsonl", ".srt", ".vtt"):
            raise RuntimeError("字幕输出扩展名必须是 .jsonl、.srt 或 .vtt")
        self.started_at = started_at if started_at is not None else time.monotonic()
        self.entries: list[SubtitleEntry] = []
        self.lock = threading.Lock()

    def record(self, captured_at: float, audio_at: float,
               original: str, translation: str) -> None:
        if not self.path:
            return
        start = max(0.0, captured_at - self.started_at)
        end = max(start + 0.5, audio_at - self.started_at)
        with self.lock:
            self.entries.append(SubtitleEntry(start, end, original, translation))

    def close(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            entries = list(self.entries)
        suffix = self.path.suffix.lower()
        if suffix == ".srt":
            content = self._srt(entries)
        elif suffix == ".vtt":
            content = self._vtt(entries)
        elif suffix == ".jsonl":
            content = self._jsonl(entries)
        self.path.write_text(content, encoding="utf-8")

    @staticmethod
    def _timestamp(seconds: float, decimal: str) -> str:
        milliseconds = round(max(0.0, seconds) * 1000)
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole_seconds, milliseconds = divmod(remainder, 1000)
        return (f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}"
                f"{decimal}{milliseconds:03d}")

    @classmethod
    def _srt(cls, entries: list[SubtitleEntry]) -> str:
        blocks = []
        for index, entry in enumerate(entries, 1):
            blocks.append(
                f"{index}\n{cls._timestamp(entry.start, ',')} --> "
                f"{cls._timestamp(entry.end, ',')}\n"
                f"{entry.translation}\n{entry.original}\n"
            )
        return "\n".join(blocks)

    @classmethod
    def _vtt(cls, entries: list[SubtitleEntry]) -> str:
        blocks = ["WEBVTT\n"]
        for entry in entries:
            blocks.append(
                f"{cls._timestamp(entry.start, '.')} --> "
                f"{cls._timestamp(entry.end, '.')}\n"
                f"{entry.translation}\n{entry.original}\n"
            )
        return "\n".join(blocks)

    @staticmethod
    def _jsonl(entries: list[SubtitleEntry]) -> str:
        return "".join(
            json.dumps(dataclasses.asdict(entry), ensure_ascii=False) + "\n"
            for entry in entries
        )
