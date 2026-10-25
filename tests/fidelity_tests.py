#!/usr/bin/env python3
"""Known-signal measurement regressions; these do not establish RMX sound matching."""
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from tools import fidelity
from tools.reference_audio import write_wav


class FidelityTests(unittest.TestCase):
    rate = 48000

    def calibration(self, delay=0, rate=None):
        return {'kind': 'fractional-bypass-calibration', 'schema_version': 1,
                'verified': True, 'eligible_for_review': True,
                'sample_rate': rate or self.rate, 'candidate_delay_frames': delay}

    def signal(self, frames=24000):
        t = np.arange(frames) / self.rate
        return np.column_stack((.2 * np.sin(2 * np.pi * 997 * t), .15 * np.sin(2 * np.pi * 3001 * t)))

    def test_identical_and_gain_mismatch_are_not_confused_by_correlation(self):
        x = self.signal()
        same = fidelity.compare(x, x, self.rate, self.calibration())
        self.assertEqual(same['waveform_verdict'], 'pass')
        half = fidelity.compare(x, x * .5, self.rate, self.calibration())
        self.assertEqual(half['waveform_verdict'], 'fail')
        for channel in half['channels']:
            self.assertAlmostEqual(channel['relative_rms_error'], .5)
            self.assertAlmostEqual(channel['sample_correlation'], 1)
            self.assertAlmostEqual(channel['level_difference_db'], -6.020599913)

    def test_one_percent_amplitude_error_has_minus_40_db_residual(self):
        x = self.signal()
        report = fidelity.compare(x, x * .991, self.rate, self.calibration())
        self.assertEqual(report['waveform_verdict'], 'pass')
        report = fidelity.compare(x, x * .989, self.rate, self.calibration())
        self.assertEqual(report['waveform_verdict'], 'fail')
        self.assertAlmostEqual(report['channels'][0]['error_relative_db'], 20 * math.log10(.011))

    def test_effect_delay_is_retained_without_new_wet_alignment(self):
        rng = np.random.default_rng(22)
        x = rng.normal(0, .1, (12000, 2))
        y = np.vstack((np.zeros((23, 2)), x))
        aligned = fidelity.compare(x, y, self.rate, self.calibration(23))
        self.assertEqual(aligned['waveform_verdict'], 'pass')
        unaligned = fidelity.compare(x, y, self.rate, self.calibration())
        self.assertEqual(unaligned['waveform_verdict'], 'fail')
        negative = fidelity.compare(y, x, self.rate, self.calibration(-23))
        self.assertEqual(negative['waveform_verdict'], 'pass')

    def test_fractional_alignment_does_not_wrap_recording_edges(self):
        x = self.signal()
        delay = 17.375
        t = (np.arange(len(x) + 40) - delay) / self.rate
        y = np.column_stack((.2 * np.sin(2 * np.pi * 997 * t), .15 * np.sin(2 * np.pi * 3001 * t)))
        report = fidelity.compare(x, y, self.rate, self.calibration(delay))
        self.assertEqual(report['waveform_verdict'], 'pass')
        self.assertLess(max(c['relative_rms_error'] for c in report['channels']), 1e-5)
        self.assertEqual(report['alignment']['fractional_interpolation'], '129-tap Blackman sinc')

    def test_broadband_bypass_delay_estimation(self):
        rng = np.random.default_rng(3)
        x = np.pad(rng.normal(0, .1, (16000, 2)), ((1000, 1000), (0, 0)))
        y = np.pad(x, ((29, 0), (0, 0)))
        result = fidelity.calibrate(x, y, self.rate)
        self.assertAlmostEqual(result['candidate_delay_frames'], 29, places=8)
        self.assertTrue(result['eligible_for_review'])
        self.assertFalse(result['verified'])

    def test_fractional_bypass_delay_estimation(self):
        rng = np.random.default_rng(4)
        x = np.pad(rng.normal(0, .1, (16000, 2)), ((1000, 1000), (0, 0)))
        n = 1 << 16
        delay = 12.25
        spectrum = np.fft.rfft(x, n=n, axis=0)
        spectrum[np.fft.rfftfreq(n) > .35] = 0
        x = np.fft.irfft(spectrum, n=n, axis=0)
        y = np.fft.irfft(spectrum * np.exp(-2j * np.pi * np.fft.rfftfreq(n)[:, None] * delay), n=n, axis=0)
        result = fidelity.calibrate(x, y, self.rate)
        self.assertAlmostEqual(result['candidate_delay_frames'], delay, places=4)
        self.assertTrue(result['eligible_for_review'])

    def test_channel_mismatch_and_inverted_polarity_fail_calibration_review(self):
        rng = np.random.default_rng(2)
        x = rng.normal(0, .1, (16000, 2))
        y = np.pad(x, ((30, 0), (0, 0)))
        y[:, 1] = np.roll(y[:, 1], 2)
        result = fidelity.calibrate(x, y, self.rate)
        self.assertFalse(result['eligible_for_review'])
        result = fidelity.calibrate(x, -x, self.rate)
        self.assertFalse(result['eligible_for_review'])
        self.assertEqual(result['channels'][0]['polarity'], -1)

    def test_calibration_cannot_be_silently_promoted_or_used_at_another_rate(self):
        x = self.signal()
        for calibration in [self.calibration() | {'verified': False},
                            self.calibration() | {'eligible_for_review': False},
                            self.calibration(rate=44100), self.calibration(float('nan'))]:
            with self.assertRaises(ValueError):
                fidelity.compare(x, x, self.rate, calibration)
        with self.assertRaisesRegex(ValueError, 'bandwidth'):
            fidelity.calibrate(x, x, self.rate)

    def test_silent_channel_is_not_an_automatic_waveform_pass(self):
        x = self.signal()
        x[:, 1] = 0
        result = fidelity.compare(x, x, self.rate, self.calibration())
        self.assertEqual(result['waveform_verdict'], 'not_assessable')
        self.assertIsNone(result['channels'][1]['relative_rms_error'])

    def test_stochastic_pair_never_receives_a_waveform_pass(self):
        x = self.signal()
        report = fidelity.compare(x, x, self.rate, self.calibration(), mode='stochastic')
        self.assertEqual(report['waveform_verdict'], 'diagnostic_only')
        self.assertTrue(report['spectral_diagnostics'])
        for level in report['spectral_diagnostics']:
            self.assertEqual(level['magnitude_relative_error'], 0)

    def test_harmonics_match_a_known_cubic_waveshaper(self):
        # y = x + a*x^3: fundamental = 1 + 3a/4, third = a/4.
        a = .12
        t = np.arange(24000) / self.rate
        tone = np.sin(2 * np.pi * 997 * t)
        values = tone + a * tone ** 3
        report = fidelity.harmonics(np.column_stack((values, values)), self.rate, 997)
        expected = (a / 4) / (1 + 3 * a / 4)
        for channel in report['channels']:
            self.assertAlmostEqual(channel['thd_ratio'], expected, places=8)
            self.assertAlmostEqual(channel['fundamental_peak'], 1 + 3 * a / 4, places=8)

    def test_cli_reports_are_exclusive_and_invalid_audio_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            input_path = root / 'tone.wav'
            report = root / 'tone.json'
            values = self.signal()
            values[:, 1] = values[:, 0]
            write_wav(input_path, self.rate, values.ravel())
            command = [sys.executable, '-m', 'tools.fidelity', 'harmonics', str(input_path),
                       '--fundamental', '997', '--report', str(report)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            saved = report.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(report.read_bytes(), saved)
        with self.assertRaises(ValueError):
            fidelity.stereo([float('nan'), 0])
        with self.assertRaises(ValueError):
            fidelity.align(self.signal(), self.signal(), 50000)


if __name__ == '__main__':
    unittest.main()
