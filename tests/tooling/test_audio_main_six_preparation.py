"""Mutation checks for preserving geometry while adding two copper layers."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_six_preparation as audit


class SixLayerPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.prepared = read_sexpr((audit.OUT / "prepared-input.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "preparation-record.json").read_text())

    def test_saved_preparation(self):
        audit.verify_preparation(self.source, self.prepared, self.record)

    def test_reject_widened_keepout_opening(self):
        prepared = copy.deepcopy(self.prepared)
        area = next(z for z in children(prepared, "zone") if children(z, "keepout"))
        xy = children(first(first(area, "polygon"), "pts"), "xy")[0]
        xy[1] = float(xy[1]) + .1
        with self.assertRaisesRegex(AssertionError, "undeclared geometry"):
            audit.verify_preparation(self.source, prepared, self.record)

    def test_reject_new_layer_excluded_from_keepout(self):
        prepared = copy.deepcopy(self.prepared)
        area = next(z for z in children(prepared, "zone") if children(z, "keepout"))
        first(area, "layers").remove("In3.Cu")
        with self.assertRaisesRegex(AssertionError, "undeclared geometry"):
            audit.verify_preparation(self.source, prepared, self.record)

    def test_reject_changed_wide_supply(self):
        prepared = copy.deepcopy(self.prepared)
        supply = next(n for n in children(prepared, "segment") if float(first(n, "width")[1]) == .6)
        first(supply, "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "undeclared geometry"):
            audit.verify_preparation(self.source, prepared, self.record)

    def test_reject_ground_clearance_change(self):
        prepared = copy.deepcopy(self.prepared)
        ground = next(z for z in children(prepared, "zone") if not children(z, "keepout") and first(z, "layer")[1] == "In4.Cu")
        first(first(ground, "connect_pads"), "clearance")[1] = .1
        with self.assertRaisesRegex(AssertionError, "undeclared geometry"):
            audit.verify_preparation(self.source, prepared, self.record)

    def test_reject_changed_new_layer_annulus(self):
        old = json.loads((audit.SOURCE / "current-native-pads.json").read_text())
        new = json.loads((audit.OUT / "current-native-pads.json").read_text())
        pad = next(p for p in new["objects"] if p["layers"].get("In3.Cu"))
        pad["layers"]["In3.Cu"] = []
        with self.assertRaisesRegex(AssertionError, "annuli differ"):
            audit.verify_native_pads(old, new)


if __name__ == "__main__":
    unittest.main()
