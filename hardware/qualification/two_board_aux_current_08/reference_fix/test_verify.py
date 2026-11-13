import unittest
from .verify import position_gate,bounds_gate
class PositionTests(unittest.TestCase):
 def test_rotated_local(self):position_gate([187.5,126.6,180],[3,-2.4],[184.5,129])
 def test_global_mistaken_as_local_rejected(self):
  with self.assertRaises(AssertionError):position_gate([187.5,126.6,180],[184.5,129],[184.5,129])
 def test_wrong_rotation_rejected(self):
  with self.assertRaises(AssertionError):position_gate([187.5,126.6,0],[3,-2.4],[184.5,129])

 def test_inside_board_bounds(self):bounds_gate([182,128,187,130],[0,0,328,182])
 def test_off_board_text_rejected(self):
  with self.assertRaises(AssertionError):bounds_gate([0,-3,6,-1],[0,0,328,182])
