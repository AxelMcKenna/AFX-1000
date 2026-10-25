"""Negative target-amplifier bypass, local feedback and power-domain regressions."""

import math
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform
from hardware.electronics.power_supply.routing.check import ROOT, local_paths, via_lands
from hardware.electronics.power_supply.routing.negative_amp_check import component_faces
from hardware.electronics.power_supply.routing.negative_reference_check import reference_return


class NegativeTargetAmpRouting(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def footprint(self, tree, ref):
        return next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )

    def pad(self, tree, ref, pin):
        f = self.footprint(tree, ref)
        p = next(p for p in children(f, "pad") if str(p[1]) == str(pin))
        return p, transform(f, first(p, "at")[1:3])

    def disconnect(self, tree, ref, pin):
        _, point = self.pad(tree, ref, pin)
        for s in list(children(tree, "segment")):
            if first(s, "layer")[1] == "B.Cu" and any(
                math.dist(tuple(map(float, first(s, tag)[1:3])), point) < 1e-6 for tag in ("start", "end")
            ):
                tree.remove(s)

    def missing(self, ref, pin, expected):
        b = self.tree()
        self.disconnect(b, ref, pin)
        with self.assertRaisesRegex(AssertionError, expected):
            local_paths(b)

    def test_local_negative_supply_is_required(self):
        self.missing("U6", 4, "negative_amp_local_supply")

    def test_local_bypass_return_is_required(self):
        self.missing("U6", 8, "negative_amp_local_return")

    def test_bulk_bypass_supply_is_required(self):
        self.missing("C62", 1, "negative_amp_bulk_supply")

    def test_n19_local_feedback_output_is_required(self):
        self.missing("C49", 1, "n19_hf_feedback_out")

    def test_n19_local_feedback_inverting_input_is_required(self):
        self.missing("C49", 2, "n19_hf_feedback_inv")

    def test_n12_local_feedback_output_is_required(self):
        self.missing("C54", 1, "n12_hf_feedback_out")

    def test_n12_local_feedback_needs_its_layer_transition(self):
        b = self.tree()
        b.remove(
            next(v for v in children(b, "via") if list(map(float, first(v, "at")[1:3])) == [147.125, 119.375])
        )
        with self.assertRaisesRegex(AssertionError, "n12_hf_feedback_inv"):
            local_paths(b)

    def test_local_supply_cannot_be_thinned_to_a_signal_trace(self):
        b = self.tree()
        _, point = self.pad(b, "U6", 4)
        for s in children(b, "segment"):
            if (
                first(s, "layer")[1] == "B.Cu"
                and math.dist(tuple(map(float, first(s, "start")[1:3])), point) < 1e-6
            ):
                first(s, "width")[1] = 0.26
        with self.assertRaisesRegex(AssertionError, "negative_amp_local_supply"):
            local_paths(b)

    def test_amplifier_must_not_span_both_raw_rails(self):
        b = self.tree()
        p, _ = self.pad(b, "U6", 8)
        n = next(n for n in children(b, "net") if n[2] == "/RAW_P22")
        first(p, "net")[1:] = n[1:]
        with self.assertRaisesRegex(AssertionError, "must not span both raw rails"):
            component_faces(b)

    def test_compensation_capacitor_cannot_move_to_the_other_face(self):
        b = self.tree()
        first(self.footprint(b, "C54"), "layer")[1] = "F.Cu"
        with self.assertRaisesRegex(AssertionError, "negative target amplifier face changed"):
            component_faces(b)

    def test_supply_via_cannot_be_drilled_in_the_bypass_land(self):
        b = self.tree()
        _, point = self.pad(b, "C61", 1)
        v = next(v for v in children(b, "via") if list(map(float, first(v, "at")[1:3])) == [143, 116])
        first(v, "at")[1:3] = point
        with self.assertRaisesRegex(AssertionError, "conventional via drill too close"):
            via_lands(b)

    def test_n19_divider_midpoint_is_required(self):
        self.missing("R34", 2, "n19_ratio_middle")

    def test_n12_divider_midpoint_is_required(self):
        self.missing("R39", 2, "n12_ratio_middle")

    def test_amplifier_power_return_cannot_shunt_the_negative_reference(self):
        b = self.tree()
        n = next(n[1] for n in children(b, "net") if n[2] == "/AGND")
        _, start = self.pad(b, "C61", 2)
        _, end = self.pad(b, "U12", 6)
        b.append(
            read_sexpr(
                f'(segment (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (width .35) (layer "B.Cu") (net {n}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "return shunted to power ground"):
            reference_return(b)
