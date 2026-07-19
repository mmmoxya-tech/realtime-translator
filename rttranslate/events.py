from __future__ import annotations

import dataclasses
import json
import time


@dataclasses.dataclass(slots=True)
class Event:
    type: str
    utterance_id: int = 0
    original: str = ""
    translation: str = ""
    captured_at: float = 0.0
    message: str = ""
    revision: int = 0
    queue_ms: float = 0.0
    translation_ms: float = 0.0
    asr_ms: float = 0.0
    end_to_end_ms: float = 0.0

    def encode(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False,
                          separators=(",", ":"))

    @classmethod
    def status(cls, message: str) -> "Event":
        return cls(type="status", message=message, captured_at=time.monotonic())
