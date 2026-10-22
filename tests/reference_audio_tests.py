#!/usr/bin/env python3
"""Synthetic tests for the measurement tool, not hardware parity evidence."""
from array import array
import importlib.util
import math
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("reference_audio", Path(__file__).resolve().parents[1] / "tools/reference_audio.py")
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class ReferenceAudioTests(unittest.TestCase):
    def test_float_roundtrip_and_nonfinite_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.wav"
            values = array("f", [0, .5, -.25, .125])
            audio.write_wav(path, 48000, values)
            rate, result = audio.read_wav(path)
            self.assertEqual(rate, 48000)
            self.assertEqual(result, values)
            audio.write_wav(path, 48000, [float("nan"), 0])
            with self.assertRaisesRegex(ValueError, "Non-finite"):
                audio.read_wav(path)

    def test_pcm_24_mono(self):
        raw = b"\x00\x00\x00\x00\x00\x40\x00\x00\x80"
        fmt = struct.pack("<HHIIHH", 1, 1, 48000, 144000, 3, 24)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "pcm.wav"
            path.write_bytes(b"RIFF" + struct.pack("<I", 36 + len(raw)) + b"WAVEfmt "
                             + struct.pack("<I", 16) + fmt + b"data"
                             + struct.pack("<I", len(raw)) + raw + b"\0")
            self.assertEqual(list(audio.read_wav(path)[1]), [0, 0, .5, .5, -1, -1])

    def test_extensible_pcm(self):
        fmt = struct.pack("<HHIIHHHHI", 0xfffe, 2, 48000, 192000, 4, 16, 22, 16, 3)
        fmt += bytes.fromhex("0100000000001000800000aa00389b71")
        raw = struct.pack("<hh", 16384, -16384)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "extensible.wav"
            path.write_bytes(b"RIFF" + struct.pack("<I", 60 + len(raw)) + b"WAVEfmt "
                             + struct.pack("<I", 40) + fmt + b"data"
                             + struct.pack("<I", len(raw)) + raw)
            self.assertEqual(list(audio.read_wav(path)[1]), [.5, -.5])

    def test_gain_and_alignment(self):
        rate = 8000
        a = array("f", [math.sin(i * .071) * .2 for i in range(rate * 2)])
        b = array("f", [0]) * 74 + array("f", (x * .5 for x in a))
        report = audio.compare(a, b, rate, shift_frames=37, bands=False)
        self.assertAlmostEqual(report["candidate_minus_reference_rms_db"], -6.020599913, places=5)
        self.assertAlmostEqual(report["diagnostic_candidate_gain_to_reference"], 2)
        self.assertLess(report["gain_fitted_error_relative_db"], -120)
        self.assertAlmostEqual(report["sample_correlation"], 1)
        wrong = audio.compare(a, b, rate, bands=False)
        self.assertGreater(wrong["gain_fitted_error_relative_db"], -20)

    def test_silence_and_antiphase(self):
        silent = array("f", [0]) * 1600
        report = audio.compare(silent, silent, 8000, bands=False)
        self.assertIsNone(report["sample_correlation"])
        self.assertIsNone(report["candidate_minus_reference_rms_db"])
        self.assertIsNone(report["reference"]["left_right_level_db"])
        self.assertIsNone(report["reference"]["onset_seconds_5ms"])
        a = array("f", [v for i in range(800) for v in (.2, -.2)])
        self.assertAlmostEqual(audio.describe(a, 8000, False)["stereo_correlation"], -1)

    def test_decay_known_exponential(self):
        # A one-second amplitude decay to -60 dB, followed to its noise-free floor.
        env = [math.exp(-math.log(1000) * i * .005) for i in range(2000)]
        result = audio.decay_t20(env, .005)
        self.assertAlmostEqual(result["extrapolated_rt60_seconds"], 1, places=5)
        self.assertGreater(result["fit_r_squared"], .999)
        self.assertIsNone(audio.decay_t20([0] * 100, .005))

    def test_bypass_calibration_detects_shift_and_drift(self):
        rate = 8000
        a = array("f", [0]) * (rate * 8 * 2)
        a[rate * 2 * 2] = .5
        a[rate * 6 * 2 + 1] = .5
        b = array("f", [0]) * 46 + a
        result = audio.calibrate(a, b, rate)
        self.assertEqual(result["candidate_delay_frames"], 23)
        self.assertTrue(result["usable_integer_alignment"])
        b[rate * 6 * 2 + 1 + 46] = 0
        b[rate * 6 * 2 + 1 + 46 + 20] = .5
        result = audio.calibrate(a, b, rate)
        self.assertFalse(result["usable_integer_alignment"])
        self.assertGreater(result["interval_change_ppm"], 0)

    def test_generated_capture_plan_and_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = audio.generate(d, 8000)
            self.assertEqual(len(manifest["cases"]), 17)
            self.assertEqual(manifest["captures"], [])
            self.assertFalse(manifest["calibration"]["verified"])
            for item in manifest["stimuli"]:
                path = Path(d) / item["path"]
                self.assertEqual(audio.sha256(path), item["sha256"])
                rate, samples = audio.read_wav(path)
                self.assertEqual(len(samples) // 2, item["frames"])
                self.assertEqual(rate, item["rate"])
            first_hashes = [s["sha256"] for s in manifest["stimuli"]]
            with self.assertRaisesRegex(ValueError, "empty session"):
                audio.generate(d, 8000)
            again = audio.generate(Path(d) / "repeat", 8000)
            self.assertEqual(first_hashes, [s["sha256"] for s in again["stimuli"]])

    def test_invalid_alignment_and_truncated_data(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            audio.compare(array("f", [0]) * 1600, array("f", [0]) * 1600, 8000, 900, bands=False)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.wav"
            audio.write_wav(path, 48000, [0, 0])
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "Truncated"):
                audio.read_wav(path)


if __name__ == "__main__":
    unittest.main()
