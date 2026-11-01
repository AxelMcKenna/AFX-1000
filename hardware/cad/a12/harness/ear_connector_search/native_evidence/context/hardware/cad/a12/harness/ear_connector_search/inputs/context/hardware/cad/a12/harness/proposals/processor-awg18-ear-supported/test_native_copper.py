"""Actual KiCad copper audit must reject a pad moved into the metal contact."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import native_copper
import pcbnew


class NativeCopperTests(unittest.TestCase):
    def test_foreign_live_pad_in_the_contact_disk_is_rejected(self):
        source = native_copper.ROOT
        with tempfile.TemporaryDirectory(prefix="afx-H9-pad-mutation-") as name:
            base = Path(name)
            work = base / "supported"
            (work / "generated").mkdir(parents=True)
            parent = base / "processor-awg18-ear/generated"
            parent.mkdir(parents=True)
            shutil.copy2(source / "processor_carrier.kicad_pcb", work / "processor_carrier.kicad_pcb")
            shutil.copy2(
                source.parent / "processor-awg18-ear/generated/filled.kicad_pcb", parent / "filled.kicad_pcb"
            )
            b = pcbnew.LoadBoard(str(source / "generated/filled.kicad_pcb"))
            j = next(f for f in b.GetFootprints() if f.GetReference() == "J13")
            j.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(252), pcbnew.FromMM(155.2)))
            pcbnew.SaveBoard(str(work / "generated/filled.kicad_pcb"), b)
            with patch.object(native_copper, "ROOT", work):
                with self.assertRaises(AssertionError):
                    native_copper.run()


if __name__ == "__main__":
    unittest.main()
