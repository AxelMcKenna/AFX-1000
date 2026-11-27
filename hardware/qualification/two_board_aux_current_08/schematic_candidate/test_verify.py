"""Regression attacks for silent connectivity/provenance drift."""
import tempfile,unittest
from pathlib import Path
from .verify import check_pins,check_hashes,H
class NativeAudit(unittest.TestCase):
 def test_formerly_absent_existing_pin_newly_connected(self):
  with self.assertRaises(AssertionError):check_pins({'E_U1'},{('E_U1','1'):'rail'},{('E_U1','1'):'rail',('E_U1','2'):'rail'},{},[])
 def test_existing_pin_removed(self):
  with self.assertRaises(AssertionError):check_pins({'E_U1'},{('E_U1','1'):'rail'},{},{},[])
 def test_extra_added_part_pin(self):
  with self.assertRaises(AssertionError):check_pins(set(),{},{('P_U900','1'):'PWR_AGND',('P_U900','2'):'PWR_AGND'},{},[{'ref':'P_U900','pins':{'1':'PWR_AGND'}}])
 def test_added_nc_pin_short(self):
  with self.assertRaises(AssertionError):check_pins(set(),{},{('P_U900','1'):'PWR_AGND'},{},[{'ref':'P_U900','pins':{'1':None}}])
 def test_declared_move_and_exact_new_pinset(self):
  result=check_pins({'E_U1'},{('E_U1','1'):'old'},{('E_U1','1'):'new',('P_U900','1'):'PWR_AGND'},{('E_U1','1'):'new'},[{'ref':'P_U900','pins':{'1':'PWR_AGND'}}])
  self.assertEqual(result,{('E_U1','1'):'new'})
 def test_baseline_content_and_file_set_drift(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);f=p/'root.kicad_sch';f.write_text('original');h={f.name:H(f)};check_hashes(p,h)
   f.write_text('changed')
   with self.assertRaises(AssertionError):check_hashes(p,h)
   f.write_text('original');(p/'new.kicad_sym').write_text('new')
   with self.assertRaises(AssertionError):check_hashes(p,h)
if __name__=='__main__':unittest.main()
