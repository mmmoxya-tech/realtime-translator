import unittest

import numpy as np

from rttranslate.audio import AudioRingBuffer


class AudioBufferTests(unittest.TestCase):
    def test_ring_buffer_keeps_latest_audio(self):
        buffer = AudioRingBuffer(sample_rate=10, max_seconds=1)
        block = np.ones(5, dtype=np.int16).tobytes()
        buffer.append(block)
        buffer.append(block)
        buffer.append(block)
        blocks, version, dropped = buffer.blocks_after(0)
        self.assertEqual(sum(map(len, blocks)), 20)
        self.assertEqual(version, 3)
        self.assertEqual(dropped, 1)

    def test_blocks_after_returns_only_new_audio(self):
        buffer = AudioRingBuffer(sample_rate=10, max_seconds=1)
        first = np.ones(5, dtype=np.int16).tobytes()
        second = np.full(5, 2, dtype=np.int16).tobytes()
        buffer.append(first)
        buffer.append(second)
        blocks, version, dropped = buffer.blocks_after(1)
        self.assertEqual(blocks, [second])
        self.assertEqual(version, 2)
        self.assertEqual(dropped, 0)
        self.assertEqual(buffer.latest_version, 2)

    def test_reports_blocks_overwritten_before_read(self):
        buffer = AudioRingBuffer(sample_rate=10, max_seconds=1)
        block = np.ones(5, dtype=np.int16).tobytes()
        for _ in range(4):
            buffer.append(block)
        blocks, version, dropped = buffer.blocks_after(1)
        self.assertEqual(version, 4)
        self.assertEqual(dropped, 1)
        self.assertEqual(len(blocks), 2)
