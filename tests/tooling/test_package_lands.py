"""Independent manufacturer-drawing dimensions and pin/net correction checks."""

import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first
from hardware.fabrication.correct_watchdog_lands import replace_footprint
from hardware.fabrication.package_lands import DCT, DRB, footprint

ROOT = Path(__file__).resolve().parents[2]/"hardware/fabrication"


class PackageLands(unittest.TestCase):
    def test_terminal_positions_sizes_and_pin_order_follow_independent_contract(self):
        contract = json.loads((ROOT/"package-contract.json").read_text())
        for kind in (DRB,DCT):
            expected = contract[kind]
            pads = {str(p[1]):p for p in children(footprint(kind),"pad") if str(p[1])}
            self.assertEqual(set(pads),{str(i) for i in range(1,10 if kind == DRB else 9)})
            for number in range(1,9):
                row = 0 if number <= 4 else 1
                rank = number-1 if row == 0 else 8-number
                x = expected["lead_row_centres_x_mm"][row]
                y = -.975+rank*expected["lead_pitch_mm"]
                actual = list(map(float,first(pads[str(number)],"at")[1:3]))
                self.assertAlmostEqual(actual[0],x)
                self.assertAlmostEqual(actual[1],y)
                self.assertEqual(list(map(float,first(pads[str(number)],"size")[1:3])),expected["lead_pad_size_mm"])

    def test_central_copper_and_paste_are_distinct_and_no_thermal_holes_are_invented(self):
        pads = children(footprint(DRB),"pad")
        copper = next(p for p in pads if p[1] == "9")
        paste = next(p for p in pads if p[1] == "")
        self.assertEqual(list(map(float,first(copper,"size")[1:3])),[1.5,1.75])
        self.assertEqual(list(map(float,first(paste,"size")[1:3])),[1.34,1.55])
        self.assertNotIn("F.Paste",first(copper,"layers")[1:])
        self.assertEqual(first(paste,"layers")[1:],["F.Paste"])
        self.assertTrue(all(not children(p,"drill") for p in pads))

    def test_dct_courtyard_receives_maximum_flash_plus_assembly_margin(self):
        tree = footprint(DCT)
        boundary = next(p for p in children(tree,"fp_rect") if first(p,"layer")[1] == "F.CrtYd")
        x,y = map(float,first(boundary,"end")[1:3])
        self.assertGreaterEqual(x,3.6/2+.25)
        self.assertGreaterEqual(y,3.4/2+.25)

    def test_land_replacement_keeps_pose_properties_and_numbered_pin_nets(self):
        from hardware.electronics.common.sexpr import read_sexpr

        old = read_sexpr('(footprint "OLD:VSON" (layer "F.Cu") (at 12 34 90) (uuid "same") (property "Reference" "U1") (property "Value" "TPS3431SDRBR"))')
        old += [read_sexpr(f'(pad "{i}" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net "/PIN_{i}"))') for i in range(1,10)]
        new = replace_footprint(old)
        self.assertEqual(first(old,"at"),first(new,"at"))
        self.assertEqual(children(old,"property"),children(new,"property"))
        self.assertEqual({str(p[1]):first(p,"net") for p in children(old,"pad")},
                         {str(p[1]):first(p,"net") for p in children(new,"pad") if str(p[1])})


if __name__ == "__main__":
    unittest.main()
