from __future__ import annotations

import collections
import threading
from typing import Any


class TranslationQueue:
    """Coalescing queue that never discards final utterances.

    Hypotheses are best-effort latency updates, so only the newest pending one is
    useful. Finals are durable and remain ordered even when later speech arrives.
    """

    def __init__(self):
        self._items: collections.deque[Any] = collections.deque()
        self._closed = False
        self._condition = threading.Condition()

    def put(self, update: Any) -> bool:
        """Queue an update and return False when the queue is already closed."""
        with self._condition:
            if self._closed:
                return False
            if update.type == "final":
                self._items = collections.deque(
                    item for item in self._items
                    if not (item.type == "hypothesis" and
                            item.utterance_id == update.utterance_id)
                )
            else:
                self._items = collections.deque(
                    item for item in self._items if item.type != "hypothesis"
                )
            self._items.append(update)
            self._condition.notify()
            return True

    def get(self) -> Any | None:
        with self._condition:
            while not self._items and not self._closed:
                self._condition.wait()
            if self._items:
                return self._items.popleft()
            return None

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

