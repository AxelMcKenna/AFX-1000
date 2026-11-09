import copy
import unittest
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.digital_serial1_native_footprint_repair import repair


class NativeFootprintRepair(unittest.TestCase):
    def setUp(self):
        self.before = read_sexpr('(kicad_pcb (footprint "R" (layer "B.Cu") (at 75 21) (property "Reference" "R3015") (pad "1" smd rect (at 0 0) (size 1 1) (layers "B.Cu"))))')
        self.candidate = copy.deepcopy(self.before)
        first(children(self.candidate, 'footprint')[0], 'at')[1:3] = [75.25, 21.]
        # JSON destroys the Atom subtype, reproducing the failed export.
        import json
        self.candidate = json.loads(json.dumps(self.candidate))
        self.pose = dict(position_mm=[75.25, 21.], angle=0, side='B', footprint=copy.deepcopy(children(self.candidate, 'footprint')[0]))
        # Keep only the footprint JSON-derived, as in the real constructor.
        self.candidate[0] = self.before[0]
        self.candidate = read_sexpr(sexpr(self.candidate))

    def test_native_keywords_restored_without_geometry_changes(self):
        result = repair(self.before, self.candidate, self.pose)
        self.assertEqual(result, self.candidate)
        self.assertIn('(footprint ', sexpr(result))
        self.assertNotIn('("footprint" ', sexpr(result))
        self.assertIn('(pad "1" smd rect ', sexpr(result))

    def test_extra_pad_change_rejected(self):
        first(children(self.pose['footprint'], 'pad')[0], 'size')[1] = 2
        with self.assertRaises(AssertionError):
            repair(self.before, self.candidate, self.pose)

    def test_undeclared_position_rejected(self):
        self.pose['position_mm'][0] = 75.5
        with self.assertRaises(AssertionError):
            repair(self.before, self.candidate, self.pose)

    def test_candidate_footprint_mismatch_rejected(self):
        first(children(self.candidate, 'footprint')[0], 'at')[1] = 76
        with self.assertRaises(AssertionError):
            repair(self.before, self.candidate, self.pose)


if __name__ == '__main__':
    unittest.main()
