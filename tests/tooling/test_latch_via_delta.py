"""Reject unintended net, copper and placement changes in the latch escape repair."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,first,children
from hardware.fabrication.audit_latch_via_delta import verify_delta
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
class LatchViaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=read_sexpr((ROOT/'digital-control-pulldowns-native-01/digital_core.kicad_pcb').read_text())
  cls.after=read_sexpr((ROOT/'digital-latch-via-native-01/digital_core.kicad_pcb').read_text())
  cls.recipe=json.loads((ROOT/'digital-latch-via-repack-01/construction.json').read_text())
 def test_exact_native_delta(self):verify_delta(self.before,self.after,self.recipe)
 def test_retained_ground_cannot_be_removed(self):
  changed=copy.deepcopy(self.after);node=next(n for n in children(changed,'segment') if first(n,'uuid')[1]=='d72a6010-70f6-5e59-8292-ff9170a11e08');changed.remove(node)
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
 def test_new_latch_via_cannot_be_grounded(self):
  changed=copy.deepcopy(self.after);node=next(n for n in children(changed,'via') if first(n,'uuid')[1] in self.recipe['geometry_delta']['via']['added']);first(node,'net')[1]='AGND'
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
 def test_component_pose_cannot_change(self):
  changed=copy.deepcopy(self.after);first(children(changed,'footprint')[0],'at')[1]=100
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
if __name__=='__main__':unittest.main()
