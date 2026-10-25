"""Regression checks for recessed inlet/switch placement in the rear cassette."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.cad import input_power
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr


class RearPowerFitTests(unittest.TestCase):
    def rejected_recess(self, reference, old_y, message):
        source = input_power.ROOT
        tree = read_sexpr((source / "input_protection.kicad_pcb").read_text())
        footprint = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1:3] == ["Reference", reference] for p in children(fp, "property"))
        )
        first(footprint, "at")[2] = old_y
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "generated").mkdir()
            pcb = root / "input_protection.kicad_pcb"
            pcb.write_text(sexpr(tree) + "\n")
            placement = json.loads((source / "generated/placement.json").read_text())
            placement["pcb_sha256"] = hashlib.sha256(pcb.read_bytes()).hexdigest()
            (root / "generated/placement.json").write_text(json.dumps(placement))
            with patch.object(input_power, "ROOT", root), self.assertRaisesRegex(AssertionError, message):
                input_power.packet()

    def test_previous_jack_position_is_rejected(self):
        self.rejected_recess("J1", 114.3, "Jack mating face")

    def test_previous_switch_position_is_rejected(self):
        self.rejected_recess("S1", 104.5, "Switch actuator")


if __name__ == "__main__":
    unittest.main()
