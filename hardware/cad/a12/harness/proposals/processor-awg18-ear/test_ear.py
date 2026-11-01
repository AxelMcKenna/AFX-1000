"""Read-only interface/geometry mutation tests for the private ear proposal."""

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import review

from hardware.electronics.common.sexpr import children, first, read_sexpr


class EarProposalTests(unittest.TestCase):
    def test_actual_native_package_is_current_and_unqualified(self):
        data = json.loads((review.ROOT / "generated/package-review.json").read_text())
        self.assertEqual(
            data["candidate_pcb_sha256"],
            hashlib.sha256((review.ROOT / "processor_carrier.kicad_pcb").read_bytes()).hexdigest(),
        )
        self.assertEqual(data["component_count"], 77)
        self.assertFalse(data["physical_qualified"])
        self.assertFalse(data["fabrication_released"])
        self.assertTrue(all(v == 0 for v in data["native_counts"].values()))

    def test_pin_swap_bad_drill_old_filter_move_and_broken_outline_are_rejected(self):
        old = read_sexpr((review.SOURCE / "processor_carrier.kicad_pcb").read_text())
        actual = read_sexpr((review.ROOT / "processor_carrier.kicad_pcb").read_text())
        for mode in ["swap_input", "small_bore", "move_quiet_filter", "broken_outline"]:
            bad = copy.deepcopy(actual)
            j = next(f for f in children(bad, "footprint") if review.ref(f) == "J13")
            p = children(j, "pad")[0]
            if mode == "swap_input":
                first(p, "net")[-1] = "/AGND"
            elif mode == "small_bore":
                first(p, "drill")[1] = "1.0"
            elif mode == "move_quiet_filter":
                fp = next(f for f in children(bad, "footprint") if review.ref(f) == "R40")
                first(fp, "at")[1] = str(float(first(fp, "at")[1]) + 1)
            else:
                edge = next(g for g in children(bad, "gr_line") if first(g, "layer")[1] == "Edge.Cuts")
                bad.remove(edge)
            with self.subTest(mode=mode), patch.object(review, "read_sexpr", side_effect=[old, bad]):
                with self.assertRaises(AssertionError):
                    review.run()


if __name__ == "__main__":
    unittest.main()
