from __future__ import annotations

import collections
import re
import subprocess
import threading


def default_sink() -> str | None:
    try:
        result = subprocess.run(
            ["wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r'node\.name\s*=\s*"([^"]+)"', result.stdout)
    return match.group(1) if match else None


class AudioRingBuffer:
    """Thread-safe rolling PCM buffer; capture continues during inference."""

    def __init__(self, sample_rate: int, max_seconds: float):
        self.max_bytes = int(sample_rate * max_seconds * 2)
        self.blocks = collections.deque()
        self.size = 0
        self.version = 0
        self.lock = threading.Lock()

    def append(self, raw: bytes) -> None:
        with self.lock:
            self.version += 1
            self.blocks.append((raw, self.version))
            self.size += len(raw)
            while self.blocks and self.size - len(self.blocks[0][0]) >= self.max_bytes:
                removed, _ = self.blocks.popleft()
                self.size -= len(removed)

    def blocks_after(self, version: int) -> tuple[list[bytes], int, int]:
        """Return new blocks, high-water mark, and overwritten block count."""
        with self.lock:
            dropped = 0
            if self.blocks and version >= 0:
                oldest_sequence = self.blocks[0][1]
                dropped = max(0, oldest_sequence - version - 1)
            return ([raw for raw, sequence in self.blocks
                     if sequence > version], self.version, dropped)

    @property
    def latest_version(self) -> int:
        with self.lock:
            return self.version


class AudioCapture:
    def __init__(self, target: str, buffer: AudioRingBuffer,
                 sample_rate: int = 16000, block_seconds: float = 0.1):
        self.sample_rate = sample_rate
        self.block_seconds = block_seconds
        self.chunk_bytes = int(sample_rate * block_seconds * 2)
        self.buffer = buffer
        self.stopping = threading.Event()
        self.error = ""
        try:
            self.process = subprocess.Popen(
                ["pw-record", "--target", target,
                 "--properties", "stream.capture.sink=true",
                 "--latency", "50ms", "--rate", str(sample_rate),
                 "--channels", "1", "--format", "s16", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise RuntimeError(f"无法启动 pw-record：{exc}") from exc
        self.thread = threading.Thread(target=self._read, daemon=True)

    @property
    def alive(self) -> bool:
        return self.thread.is_alive() and self.process.poll() is None

    def start(self) -> None:
        self.thread.start()

    def _read(self) -> None:
        while not self.stopping.is_set():
            raw = self.process.stdout.read(self.chunk_bytes)
            if not raw:
                break
            self.buffer.append(raw)
        if not self.stopping.is_set() and self.process.stderr:
            self.error = self.process.stderr.read().decode(errors="replace").strip()

    def stop(self) -> None:
        self.stopping.set()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.thread.join(timeout=1)
