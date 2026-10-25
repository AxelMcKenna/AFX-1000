"""Reject the wrong land width for the newly selected raw-supply inductor."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.power_supply import check_placement


class PowerInductorLandTests(unittest.TestCase):
    def test_wrong_33uh_land_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(check_placement.ROOT / "RMX_Power.pretty", root / "RMX_Power.pretty")
            path = root / "RMX_Power.pretty/SRP7050WA.kicad_mod"
            fp = read_sexpr(path.read_text())
            first(children(fp, "pad")[0], "size")[1] = 2.5
            path.write_text(sexpr(fp) + "\n")
            with patch.object(check_placement, "ROOT", root), self.assertRaises(AssertionError):
                check_placement.audit_inductors()

    def test_through_hole_header_cannot_occupy_thermal_region(self):
        root = check_placement.ROOT
        _, pins = netlist(root / "generated/placement-netlist.xml")
        tree = read_sexpr((root / "power_supply.kicad_pcb").read_text())
        header = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "J4"] for p in children(fp, "property"))
        )
        first(header, "at")[1] = 151.5
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad-header.kicad_pcb"
            path.write_text(sexpr(tree) + "\n")
            with self.assertRaisesRegex(AssertionError, "bottom thermal region occupied"):
                check_placement.mechanical(path, pins)


if __name__ == "__main__":
    unittest.main()
