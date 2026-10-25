"""E25 mutations must fail independent component, pin, polarity and outline checks."""

import unittest

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.rail_disconnect.placement.check import OUT, ROOT, mechanical


class DisconnectPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.pins = netlist(OUT / "netlist.xml")

    def tree(self):
        return read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text())

    def fp(self, b, ref):
        return next(
            f
            for f in children(b, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )

    def test_removed_parallel_fet_is_rejected(self):
        b = self.tree()
        b.remove(self.fp(b, "Q13"))
        with self.assertRaises(AssertionError):
            mechanical(b, self.parts, self.pins)

    def test_gate_source_swap_is_rejected(self):
        b = self.tree()
        f = self.fp(b, "Q11")
        p = next(p for p in children(f, "pad") if str(p[1]) == "2")
        first(p, "net")[-1] = "/5V_DIG_COMMON"
        with self.assertRaises(AssertionError):
            mechanical(b, self.parts, self.pins)

    def test_missing_physical_source_land_is_rejected(self):
        b = self.tree()
        f = self.fp(b, "Q11")
        f.remove(next(p for p in children(f, "pad") if str(p[1]) == "1"))
        with self.assertRaisesRegex(AssertionError, "physical grouped"):
            mechanical(b, self.parts, self.pins)

    def test_negative_electrolytic_reversal_is_rejected(self):
        b = self.tree()
        p = children(self.fp(b, "C8"), "pad")
        first(p[0], "net")[-1], first(p[1], "net")[-1] = first(p[1], "net")[-1], first(p[0], "net")[-1]
        with self.assertRaisesRegex(AssertionError, "polarity"):
            mechanical(b, self.parts, self.pins)

    def test_tall_capacitor_cannot_flip_to_bottom(self):
        b = self.tree()
        first(self.fp(b, "C24"), "layer")[1] = "B.Cu"
        with self.assertRaises(AssertionError):
            mechanical(b, self.parts, self.pins)

    def test_value_change_is_rejected(self):
        b = self.tree()
        p = next(p for p in children(self.fp(b, "C24"), "property") if p[1] == "Value")
        p[2] = "220uF 16V"
        with self.assertRaisesRegex(AssertionError, "value/footprint"):
            mechanical(b, self.parts, self.pins)

    def test_mount_drill_change_is_rejected(self):
        b = self.tree()
        first(children(self.fp(b, "H3"), "pad")[0], "drill")[1] = 2.0
        with self.assertRaises(AssertionError):
            mechanical(b, self.parts, self.pins)

    def test_case_relief_change_is_rejected(self):
        b = self.tree()
        e = children(b, "gr_line")[4]
        first(e, "start")[1] = 255
        with self.assertRaisesRegex(AssertionError, "outline|relief"):
            mechanical(b, self.parts, self.pins)

    def test_routed_copper_cannot_use_placed_only_evidence(self):
        b = self.tree()
        b.append(read_sexpr('(segment (start 110 110) (end 111 110) (width .25) (layer "F.Cu") (net 1))'))
        with self.assertRaisesRegex(AssertionError, "Placed-only"):
            mechanical(b, self.parts, self.pins)
