"""E26 variants must preserve the circuit and report all unfinished native work."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.rail_disconnect.placement.check import mechanical
from hardware.electronics.rail_disconnect.revision26.check import preserved_geometry
from hardware.electronics.rail_disconnect.revision26.replay import replay_bytes

ROOT = Path(__file__).resolve().parents[2] / "hardware/electronics/rail_disconnect"


class Revision26Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = ROOT / "revision26"
        cls.board = read_sexpr((cls.folder / "rail_disconnect.kicad_pcb").read_text())
        cls.base = read_sexpr((ROOT / "placement/rail_disconnect.kicad_pcb").read_text())
        cls.parts, cls.pins = netlist(ROOT / "placement/generated/netlist.xml")

    def test_original_bulk_mounts_outline_and_stack_are_retained(self):
        preserved_geometry(self.board, self.base)
        stripped = [
            n
            for n in self.board
            if not isinstance(n, list) or not n or n[0] not in ("segment", "via", "zone")
        ]
        self.assertEqual(mechanical(stripped, self.parts, self.pins)["circuit_components"], 164)

    def test_moving_a_frozen_bulk_capacitor_is_rejected(self):
        board = copy.deepcopy(self.board)
        fp = next(
            f
            for f in children(board, "footprint")
            if any(p[1:3] == ["Reference", "C24"] for p in children(f, "property"))
        )
        first(fp, "at")[1] = float(first(fp, "at")[1]) + 0.1
        with self.assertRaises(AssertionError):
            preserved_geometry(board, self.base)

    def test_changing_an_existing_mount_is_rejected(self):
        board = copy.deepcopy(self.board)
        fp = next(
            f
            for f in children(board, "footprint")
            if any(p[1:3] == ["Reference", "H1"] for p in children(f, "property"))
        )
        first(children(fp, "pad")[0], "drill")[1] = 3.0
        with self.assertRaises(AssertionError):
            preserved_geometry(board, self.base)

    def test_gate_source_swap_still_violates_original_pin_contract(self):
        board = copy.deepcopy(self.board)
        fp = next(
            f
            for f in children(board, "footprint")
            if any(p[1:3] == ["Reference", "Q9"] for p in children(f, "property"))
        )
        pad = next(p for p in children(fp, "pad") if str(p[1]) == "2")
        first(pad, "net")[-1] = "/V5_REG_COMMON"
        stripped = [
            n for n in board if not isinstance(n, list) or not n or n[0] not in ("segment", "via", "zone")
        ]
        with self.assertRaises(AssertionError):
            mechanical(stripped, self.parts, self.pins)

    def test_resistor_escape_reservations_are_staggered(self):
        packet = json.loads((self.folder / "generated/placement-inputs.json").read_text())
        ports = [p for p in packet["ports"] if p["ref"].startswith("R")]
        self.assertEqual(len(ports), 188)
        for p in ports:
            x, y = packet["placements"][p["ref"]][:2]
            self.assertAlmostEqual(abs(p["xy"][0] - x), 2)
            self.assertAlmostEqual(abs(p["xy"][1] - y), 0.7)

    def test_replay_reproduces_actual_pilot_bytes(self):
        recipe = json.loads((self.folder / "reviewed-pilot.json").read_text())
        self.assertEqual(replay_bytes(recipe), (self.folder / "rail_disconnect.kicad_pcb").read_bytes())

    def test_proposed_ground_attachments_are_not_claimed_implemented(self):
        proposed = json.loads((self.folder / "attachment-candidates.json").read_text())
        self.assertFalse(proposed["implemented_in_pcb"])
        refs = {
            next(p[2] for p in children(f, "property") if p[1] == "Reference")
            for f in children(self.board, "footprint")
        }
        self.assertEqual(refs, set(self.parts) | {"H1", "H2", "H3", "H4"})

    def test_native_warnings_and_opens_are_preserved(self):
        native = json.loads((self.folder / "generated/drc.json").read_text())
        report = json.loads((self.folder / "generated/pilot-findings.json").read_text())
        self.assertEqual(report["native_drc_violations"], len(native["violations"]))
        self.assertEqual(report["native_open_connections"], len(native["unconnected_items"]))
        self.assertFalse(report["build_ready"])
        self.assertEqual(
            report["strict_native_check_passed"], not native["violations"] and not native["schematic_parity"]
        )


if __name__ == "__main__":
    unittest.main()
