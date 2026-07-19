import unittest

from rttranslate.display import LatestUpdateGate


class LatestUpdateGateTests(unittest.TestCase):
    def test_first_update_is_immediate(self):
        gate = LatestUpdateGate(0.9)
        self.assertEqual(gate.submit("first", 10.0), "first")

    def test_rapid_updates_are_coalesced_to_latest(self):
        gate = LatestUpdateGate(0.9)
        gate.submit("first", 10.0)
        self.assertIsNone(gate.submit("second", 10.2))
        self.assertIsNone(gate.submit("latest", 10.4))
        self.assertIsNone(gate.pop_due(10.8))
        self.assertEqual(gate.pop_due(10.9), "latest")

    def test_zero_interval_disables_rate_limit(self):
        gate = LatestUpdateGate(0)
        self.assertEqual(gate.submit("first", 10.0), "first")
        self.assertEqual(gate.submit("second", 10.1), "second")

    def test_discards_pending_previous_utterance(self):
        gate = LatestUpdateGate(1.0)
        gate.submit({"utterance_id": 1}, 10.0)
        gate.submit({"utterance_id": 1, "revision": 2}, 10.1)
        gate.discard_before(2)
        self.assertIsNone(gate.pop_due(11.1))
