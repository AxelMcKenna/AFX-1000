"""Disk-exhaustion pause must stop renders before output files are created."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.reference_audio import check_output_storage, render, write_wav
from tools.rmx_factory_match import new_directory


class AudioStoragePause(unittest.TestCase):
    def test_paused_tree_blocks_directory_wav_and_renderer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".rmx-audio-output-paused").write_text("paused")
            directory = root / "new" / "case"
            wav = root / "out.wav"
            for operation in (
                lambda: new_directory(directory),
                lambda: write_wav(wav, 48000, [0.0, 0.0]),
                lambda: render(SimpleNamespace(output=directory)),
            ):
                with self.assertRaisesRegex(RuntimeError, "paused after disk exhaustion"):
                    operation()
            self.assertFalse(directory.exists())
            self.assertFalse(wav.exists())

    def test_unpaused_small_output_still_works(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = new_directory(Path(temporary) / "case")
            output = directory / "tiny.wav"
            check_output_storage(output)
            write_wav(output, 48000, [0.0, 0.0])
            self.assertEqual(output.read_bytes()[:4], b"RIFF")

    def test_symlink_into_paused_tree_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paused = root / "paused"
            paused.mkdir()
            (paused / ".rmx-audio-output-paused").write_text("paused")
            alias = root / "alias"
            alias.symlink_to(paused, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                write_wav(alias / "out.wav", 48000, [0.0, 0.0])
            self.assertFalse((paused / "out.wav").exists())


if __name__ == "__main__":
    unittest.main()
