from __future__ import annotations

import dataclasses

import webrtcvad


class VoiceActivityDetector:
    """WebRTC VAD over 20 ms, 16 kHz mono PCM frames."""

    def __init__(self, sample_rate: int = 16000, mode: int = 2,
                 speech_ratio: float = 0.3):
        self.sample_rate = sample_rate
        self.frame_bytes = int(sample_rate * 0.02 * 2)
        self.speech_ratio = speech_ratio
        self.vad = webrtcvad.Vad(mode)

    def is_speech(self, raw: bytes) -> bool:
        frames = [raw[index:index + self.frame_bytes]
                  for index in range(0, len(raw), self.frame_bytes)]
        frames = [frame for frame in frames if len(frame) == self.frame_bytes]
        if not frames:
            return False
        voiced = sum(self.vad.is_speech(frame, self.sample_rate)
                     for frame in frames)
        return voiced / len(frames) >= self.speech_ratio


@dataclasses.dataclass(slots=True)
class UtteranceBoundary:
    """Track speech activity and decide when an utterance must be committed."""

    silence_seconds: float = 0.8
    max_seconds: float = 15.0
    started_at: float = 0.0
    last_speech_at: float = 0.0

    @property
    def active(self) -> bool:
        return self.started_at > 0.0

    def observe(self, speech: bool, audio_at: float, now: float) -> tuple[bool, bool]:
        started = False
        if speech:
            self.last_speech_at = audio_at
            if not self.active:
                self.started_at = audio_at
                started = True
        endpoint = (
            self.active and
            (now - self.last_speech_at >= self.silence_seconds or
             now - self.started_at >= self.max_seconds)
        )
        return started, endpoint

    def reset(self) -> None:
        self.started_at = 0.0
        self.last_speech_at = 0.0
