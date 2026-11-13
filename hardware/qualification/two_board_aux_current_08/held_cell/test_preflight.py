import unittest
from hardware.electronics.common.sexpr import read_sexpr
from .preflight import zone_coordinates
class ZonePreflightTests(unittest.TestCase):
 def test_correct_numeric_atoms(self):self.assertEqual(zone_coordinates(read_sexpr('(zone (polygon (pts (xy 136 158) (xy 158 158) (xy 158 180))))')),[[[136,158],[158,158],[158,180]]])
 def test_original_quoted_coordinates_rejected(self):
  with self.assertRaisesRegex(AssertionError,'unquoted'):zone_coordinates(read_sexpr('(zone (polygon (pts (xy "136" "158") (xy "158" "158") (xy "158" "180"))))'))
 def test_nonfinite_rejected(self):
  with self.assertRaisesRegex(AssertionError,'finite'):zone_coordinates(read_sexpr('(zone (polygon (pts (xy nan 158) (xy 158 158) (xy 158 180))))'))
if __name__=='__main__':unittest.main()
