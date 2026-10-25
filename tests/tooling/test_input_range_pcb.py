"""E10 candidate must preserve the circuit and its actual local copper."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.reports import sha
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.input_range.pcb import check


class InputRangePcbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = read_sexpr((check.ROOT / "input_range.kicad_pcb").read_text())
        cls.parts, cls.pins = netlist(check.PARENT / "generated/netlist.xml")

    def changed(self, ref):
        tree = copy.deepcopy(self.tree)
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )
        return tree, fp

    def test_all_parts_and_feedback_paths_are_present(self):
        self.assertEqual(len(check.inspect(self.tree, self.parts, self.pins)), 28)
        self.assertEqual(len(check.feedback_contract(self.tree)), 6)

    def test_missing_relay_cannot_make_layout_appear_complete(self):
        tree, fp = self.changed("K1")
        tree.remove(fp)
        with self.assertRaisesRegex(AssertionError, "Missing component"):
            check.inspect(tree, self.parts, self.pins)

    def test_relay_contacts_and_supply_polarity_are_exact(self):
        for ref, pin in [("K1", "2"), ("J3", "3"), ("J4", "1")]:
            tree, fp = self.changed(ref)
            pad = next(p for p in children(fp, "pad") if p[1] == pin)
            first(pad, "net")[-1] = "/V5_REG"
            with self.subTest(ref=ref), self.assertRaisesRegex(AssertionError, "PCB pin mismatch"):
                check.inspect(tree, self.parts, self.pins)

    def test_mount_drill_and_keepouts_cannot_be_removed(self):
        tree, fp = self.changed("H1")
        first(children(fp, "pad")[0], "drill")[1] = 2.0
        with self.assertRaises(AssertionError):
            check.inspect(tree, self.parts, self.pins)
        tree = copy.deepcopy(self.tree)
        tree.remove(children(tree, "zone")[0])
        with self.assertRaisesRegex(AssertionError, "Missing fastener keepout"):
            check.inspect(tree, self.parts, self.pins)

    def test_missing_feedback_copper_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        code = next(n[1] for n in children(tree, "net") if n[2] == "/GAIN_FB_L")
        tree[:] = [
            n
            for n in tree
            if not (isinstance(n, list) and n and n[0] == "segment" and first(n, "net")[1] == code)
        ]
        with self.assertRaises(AssertionError):
            check.feedback_contract(tree)

    def test_undersized_feedback_copper_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        code = next(n[1] for n in children(tree, "net") if n[2] == "/GAIN_FB_R")
        for n in children(tree, "segment"):
            if first(n, "net")[1] == code:
                first(n, "width")[1] = 0.1
        with self.assertRaises(AssertionError):
            check.feedback_contract(tree)

    def test_native_record_is_current_and_remains_unqualified(self):
        record = json.loads((check.OUT / "verification.json").read_text())
        self.assertEqual(record["native_open_connections"], 0)
        self.assertEqual(record["native_drc_violations"], 0)
        self.assertEqual(record["schematic_parity_issues"], 0)
        self.assertFalse(record["build_ready"])
        self.assertFalse(record["integrated_in_a11"])
        self.assertFalse(record["continuous_ground_plane_implemented"])
        repo = Path(__file__).resolve().parents[2]
        for name, expected in record["source_sha256"].items():
            self.assertEqual(sha(repo / name), expected, name)


if __name__ == "__main__":
    unittest.main()
