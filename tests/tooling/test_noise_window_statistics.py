import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from tools import noise_random_statistics as random_stats
from tools import noise_window_statistics as window
from tools.noise_statistics import float_wav, stereo_correlation
from tools.reference_audio import write_wav
from tools.rmx_noise_sidechain_stream import analyze as original_analyze


class ContinuousWindows(unittest.TestCase):
    def test_boundary_powers_and_stereo(self):
        self.compare(False)

    @unittest.skipUnless(os.environ.get('RMX_NOISE_RANDOM_PROBE'), 'Supply the built Random control probe')
    def test_boundary_random_control_bins(self):
        self.compare(True)

    def compare(self, random):
        # One ordinary run versus two adjacent windows. The cut crosses a
        # Hann window; the second file must include its 128 preceding frames.
        generator = np.random.default_rng(514)
        audio = generator.normal(0, .1, (84 * 48000, 2)).astype('<f4')
        probe = Path(os.environ['RMX_NOISE_RANDOM_PROBE']) if random else None
        pattern = np.zeros((48000, 2), dtype='<f4')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            full = root / 'full.wav'
            write_wav(full, 48000, audio.reshape(-1))
            old, old_profile = original_analyze(full, pattern)
            if random:
                old_profile = random_stats.profile(float_wav(full)[1], 223, probe)
            parts = []
            for index in range(2):
                start = (4 + index * 40) * 48000
                prefix = 4 * 48000 if index == 0 else 128
                segment = root / f'{index}.wav'
                write_wav(segment, 48000, audio[start - prefix:start + 40 * 48000].reshape(-1))
                parts.append(window.analyze(segment, start, 40, pattern, 223, probe))
            current, profile = window.combine(parts)
            for key in ['bands', 'total']:
                np.testing.assert_array_equal(current[key], old[key])
            for key in ['bands', 'total', 'exposure']:
                np.testing.assert_array_equal(profile[key], old_profile[key])
            self.assertAlmostEqual(current['correlation'], stereo_correlation(audio[4 * 48000:]), places=13)


if __name__ == '__main__':
    unittest.main()
