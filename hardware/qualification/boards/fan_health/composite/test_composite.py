"""Actual native composition, interface and destructive-mutation regressions."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import a, children, first, read_sexpr
from hardware.qualification.boards.fan_health.composite.review import (
    ROOT,
    by_ref,
    native_pins,
    sha,
    validate_tree,
)


class CompositeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text())

    def test_actual_native_closed_and_source_bound(self):
        report = json.loads((ROOT / "generated/final-review.json").read_text())
        for name, digest in report["sources_sha256"].items():
            self.assertEqual(sha(ROOT / name), digest, name)
        self.assertEqual(validate_tree(self.tree)["parts"], 84)
        for n in ["schematic_ERC_errors", "PCB_hard_DRC", "warnings", "opens", "schematic_parity"]:
            self.assertEqual(report[n], 0)
        self.assertFalse(report["physical_qualified"])
        self.assertFalse(report["fabrication_released"])

    def test_exact_parent_pin_equivalence_except_declared_headers(self):
        parts = json.loads((ROOT / "components.json").read_text())
        for parent in ["FH02", "FP01"]:
            original = {
                c["ref"]: c for c in json.loads((ROOT / "sources" / parent / "components.json").read_text())
            }
            for c in [c for c in parts if c["parent"] == parent]:
                old = original[c["parent_ref"]]
                expected = {
                    p["number"]: (
                        None
                        if parent == "FP01" and p["net"] in ["FAN_L_FAULT_N", "FAN_R_FAULT_N"]
                        else "GND"
                        if parent == "FP01" and p["net"] == "FAN_GND"
                        else p["net"]
                    )
                    for p in old["pins"]
                }
                self.assertEqual({p["number"]: p["net"] for p in c["pins"]}, expected, c["ref"])
        self.assertEqual(len(parts), 68 + 18 - 2)

    def test_raw_fault_latch_independent_of_mcu_reset(self):
        pins = native_pins(self.tree)
        self.assertEqual(pins["U8"]["8"], "FAN5V_IN")
        self.assertEqual(pins["U8"]["1"], "FAULT_CLK")
        self.assertEqual(pins["U8"]["6"], "RAW_CLEAR_FAST")
        self.assertNotEqual(pins["U8"]["6"], pins["U1"]["4"])
        self.assertEqual(pins["U8"]["3"], "HW_NOFAULT_5")

    def test_same_value_smaller_timing_cap_and_retained_poses(self):
        parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
        self.assertIn("2.7nF", parts["C7"]["part"])
        self.assertIn("C0603C272J5GACTU", parts["C7"]["part"])
        review = json.loads((ROOT / "generated/final-review.json").read_text())
        self.assertEqual(review["unchanged_complete_footprints"], 83)
        self.assertTrue(review["all84_poses_preserved"])

    def test_sensor_swap_rejected(self):
        t = copy.deepcopy(self.tree)
        p = next(p for p in children(by_ref(t)["U1"], "pad") if p[1] == "13")
        first(p, "net")[1] = a("/TEMP_R_ADC")
        with self.assertRaises(AssertionError):
            validate_tree(t)

    def test_signal_plane_cut_rejected(self):
        t = copy.deepcopy(self.tree)
        track = copy.deepcopy(children(t, "segment")[0])
        first(track, "layer")[1] = a("In1.Cu")
        t.append(track)
        with self.assertRaisesRegex(AssertionError, "Dedicated return"):
            validate_tree(t)

    def test_removed_pad_via_exclusion_rejected(self):
        t = copy.deepcopy(self.tree)
        zone = next(
            z
            for z in children(t, "zone")
            if children(z, "name") and first(z, "name")[1] == "NO_UNFILLED_VIP_C7_1"
        )
        t.remove(zone)
        with self.assertRaisesRegex(AssertionError, "via exclusion"):
            validate_tree(t)

    def test_clock_route_deletion_rejected(self):
        t = copy.deepcopy(self.tree)
        track = next(s for s in children(t, "segment") if first(s, "net")[1] == "/XTAL1")
        t.remove(track)
        with self.assertRaisesRegex(AssertionError, "Lost literal"):
            validate_tree(t)

    def test_wrong_power_run_leaf_rejected(self):
        t = copy.deepcopy(self.tree)
        p = next(p for p in children(by_ref(t)["J4"], "pad") if p[1] == "2")
        first(p, "net")[1] = a("/E28_MASTER_ENABLE")
        with self.assertRaises(AssertionError):
            validate_tree(t)


if __name__ == "__main__":
    unittest.main()
