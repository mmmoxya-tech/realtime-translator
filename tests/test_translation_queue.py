import threading
import unittest
from types import SimpleNamespace

from rttranslate.translation_queue import TranslationQueue


def update(kind, utterance_id, revision=1):
    return SimpleNamespace(type=kind, utterance_id=utterance_id,
                           revision=revision)


class TranslationQueueTests(unittest.TestCase):
    def test_hypotheses_are_coalesced_to_latest(self):
        pending = TranslationQueue()
        pending.put(update("hypothesis", 1, 1))
        pending.put(update("hypothesis", 1, 2))
        self.assertEqual(pending.get().revision, 2)

    def test_final_replaces_same_utterance_hypothesis(self):
        pending = TranslationQueue()
        pending.put(update("hypothesis", 1))
        pending.put(update("final", 1, 2))
        item = pending.get()
        self.assertEqual((item.type, item.revision), ("final", 2))

    def test_later_hypothesis_cannot_discard_final(self):
        pending = TranslationQueue()
        pending.put(update("final", 1))
        pending.put(update("hypothesis", 2))
        self.assertEqual(pending.get().type, "final")
        self.assertEqual(pending.get().utterance_id, 2)

    def test_multiple_finals_remain_in_order(self):
        pending = TranslationQueue()
        pending.put(update("final", 1))
        pending.put(update("final", 2))
        self.assertEqual(pending.get().utterance_id, 1)
        self.assertEqual(pending.get().utterance_id, 2)

    def test_close_unblocks_waiter(self):
        pending = TranslationQueue()
        result = []
        waiter = threading.Thread(target=lambda: result.append(pending.get()))
        waiter.start()
        pending.close()
        waiter.join(timeout=1)
        self.assertFalse(waiter.is_alive())
        self.assertEqual(result, [None])

    def test_close_drains_final_before_stopping(self):
        pending = TranslationQueue()
        pending.put(update("final", 1))
        pending.close()
        self.assertEqual(pending.get().type, "final")
        self.assertIsNone(pending.get())


if __name__ == "__main__":
    unittest.main()
