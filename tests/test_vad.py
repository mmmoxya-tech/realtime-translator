import unittest

from rttranslate.vad import UtteranceBoundary, VoiceActivityDetector


class VadTests(unittest.TestCase):
    def test_silence_is_not_speech(self):
        detector = VoiceActivityDetector()
        self.assertFalse(detector.is_speech(bytes(3200)))

    def test_incomplete_frame_is_ignored(self):
        detector = VoiceActivityDetector()
        self.assertFalse(detector.is_speech(bytes(10)))


class UtteranceBoundaryTests(unittest.TestCase):
    def test_starts_on_first_speech(self):
        boundary = UtteranceBoundary()
        self.assertEqual(boundary.observe(True, 10.0, 10.1), (True, False))
        self.assertTrue(boundary.active)

    def test_continuous_speech_does_not_restart(self):
        boundary = UtteranceBoundary()
        boundary.observe(True, 10.0, 10.0)
        self.assertEqual(boundary.observe(True, 10.5, 10.5), (False, False))

    def test_silence_triggers_endpoint(self):
        boundary = UtteranceBoundary(silence_seconds=0.8)
        boundary.observe(True, 10.0, 10.0)
        self.assertEqual(boundary.observe(False, 10.8, 10.81), (False, True))

    def test_maximum_duration_triggers_endpoint_during_speech(self):
        boundary = UtteranceBoundary(max_seconds=5.0)
        boundary.observe(True, 10.0, 10.0)
        self.assertEqual(boundary.observe(True, 15.0, 15.01), (False, True))

    def test_reset_allows_next_utterance(self):
        boundary = UtteranceBoundary()
        boundary.observe(True, 10.0, 10.0)
        boundary.reset()
        self.assertEqual(boundary.observe(True, 20.0, 20.0), (True, False))
