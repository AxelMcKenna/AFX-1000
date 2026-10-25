import tempfile
from pathlib import Path
import unittest

import numpy as np

from tools.noise_statistics import float_wav, mean_variance, measure, stereo_correlation
from tools.reference_audio import write_wav


class NoiseStatisticsTests(unittest.TestCase):
    def test_large_float_reader_preserves_stereo_and_rejects_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'probe.wav'
            x = np.array([[.2, -.3], [.4, .5]], dtype=np.float32)
            write_wav(path, 48000, x.ravel())
            rate, actual = float_wav(path)
            self.assertEqual(rate, 48000)
            np.testing.assert_array_equal(actual, x)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaises(ValueError):
                float_wav(path)

    def test_gain_errors_are_assessed_per_channel(self):
        x = np.random.default_rng(719).normal(0, .1, (8000*40, 2)).astype(np.float32)
        result = measure(x, x*np.array([1.1, .9]), 8000)
        self.assertFalse(result['whole_level_passed'])
        self.assertEqual(result['verdict'], 'different')
        self.assertAlmostEqual(result['whole_level'][0]['candidate_minus_reference_db'], 20*np.log10(1.1), places=5)
        self.assertAlmostEqual(result['whole_level'][1]['candidate_minus_reference_db'], 20*np.log10(.9), places=5)

    def test_silence_cannot_pass_a_noise_equivalence_screen(self):
        with self.assertRaises(ValueError):
            measure(np.zeros((8000*40, 2)), np.zeros((8000*40, 2)), 8000)

    def test_positive_block_correlation_inflates_mean_uncertainty(self):
        rng = np.random.default_rng(41)
        series = np.zeros((1000, 1))
        for n in range(1, len(series)):
            series[n] = series[n-1]*.9+rng.normal()
        self.assertGreater(float(mean_variance(series)[0]), np.var(series, ddof=1)/len(series)*2)

    def test_streaming_stereo_correlation_matches_direct_calculation(self):
        x = np.random.default_rng(32).normal(0, 1, (200013, 2)).astype(np.float32)
        x[:, 1] += x[:, 0]*.4
        self.assertAlmostEqual(stereo_correlation(x), np.corrcoef(x.T)[0, 1], places=10)


if __name__ == '__main__':
    unittest.main()
