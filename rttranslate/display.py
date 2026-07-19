from __future__ import annotations


class LatestUpdateGate:
    """Rate-limit display changes while retaining only the newest update."""

    def __init__(self, interval: float):
        self.interval = interval
        self.last_shown_at: float | None = None
        self.pending = None

    def submit(self, value, now: float):
        if (self.last_shown_at is None or self.interval == 0 or
                now - self.last_shown_at >= self.interval):
            self.last_shown_at = now
            self.pending = None
            return value
        self.pending = value
        return None

    def pop_due(self, now: float):
        if (self.pending is not None and self.last_shown_at is not None and
                now - self.last_shown_at >= self.interval):
            value = self.pending
            self.pending = None
            self.last_shown_at = now
            return value
        return None

    def discard_before(self, utterance_id: int) -> None:
        if (self.pending is not None and
                int(self.pending.get("utterance_id", 0)) < utterance_id):
            self.pending = None
