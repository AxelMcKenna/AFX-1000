"""Reject broken power copper and a missing inter-layer logic transition."""

import copy
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.input_protection.inlet_revision2.check import connected
from hardware.electronics.input_protection.inlet_revision2.generate import ROOT


class RearInletCopper(unittest.TestCase):
    def setUp(self):
        self.tree = read_sexpr((ROOT / "rear_inlet.kicad_pcb").read_text())
        self.names = {str(n[1]): str(n[2]).lstrip("/") for n in children(self.tree, "net")}

    def test_actual_power_return_uses_wide_back_copper(self):
        self.assertTrue(connected(self.tree, "AGND", ("J1", 2), ("J2", 2), 3)["connected"])

    def test_narrowed_return_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        for segment in children(tree, "segment"):
            if self.names[str(first(segment, "net")[1])] == "AGND" and float(first(segment, "width")[1]) == 3:
                first(segment, "width")[1] = 0.4
        with self.assertRaises(AssertionError):
            connected(tree, "AGND", ("J1", 2), ("J2", 2), 3)

    def test_missing_run_via_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        for via in list(children(tree, "via")):
            if self.names[str(first(via, "net")[1])] == "POWER_RUN":
                tree.remove(via)
        with self.assertRaises(AssertionError):
            connected(tree, "POWER_RUN", ("S1", 2), ("J3", 2), 0.3)

    def test_gap_in_live_feed_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        feed = [s for s in children(tree, "segment") if self.names[str(first(s, "net")[1])] == "DC_IN"]
        tree.remove(max(feed, key=lambda s: float(first(s, "width")[1])))
        with self.assertRaises(AssertionError):
            connected(tree, "DC_IN", ("F1", 2), ("J2", 1), 1.2)


if __name__ == "__main__":
    unittest.main()
