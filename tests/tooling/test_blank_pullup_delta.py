"""Protect supply identity, retained copper and the one permitted pull-up move."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,first,children
from hardware.fabrication.audit_candidate import geometry_delta
from hardware.fabrication.audit_blank_pullup_delta import verify_delta,refs
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
class BlankPullupTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=read_sexpr((ROOT/'digital-latch-via-native-01/digital_core.kicad_pcb').read_text())
  cls.after=read_sexpr((ROOT/'digital-blank-pullup-native-01/digital_core.kicad_pcb').read_text())
  cls.recipe=json.loads((ROOT/'digital-blank-pullup-repack-01/construction.json').read_text())
 def reject(self,changed):
  recipe=copy.deepcopy(self.recipe);recipe['geometry_delta']=geometry_delta(self.before,changed)
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,recipe)
 def test_exact_native_delta(self):verify_delta(self.before,self.after,self.recipe)
 def test_supply_cannot_be_substituted_with_ground(self):
  changed=copy.deepcopy(self.after)
  node=next(n for n in children(changed,'segment') if first(n,'uuid')[1] in self.recipe['geometry_delta']['segment']['added'] and first(n,'net')[1]=='V3V3_IO')
  first(node,'net')[1]='AGND';self.reject(changed)
 def test_retained_supply_junction_cannot_be_removed(self):
  changed=copy.deepcopy(self.after)
  node=next(n for n in children(changed,'segment') if first(n,'uuid')[1]=='42392d9d-d51b-5595-9812-4330a9fb323b')
  changed.remove(node);self.reject(changed)
 def test_pullup_value_cannot_change(self):
  changed=copy.deepcopy(self.after)
  next(p for p in children(refs(changed)['R3010'],'property') if p[1]=='Value')[2]='1k'
  self.reject(changed)
 def test_unrelated_component_pose_cannot_change(self):
  changed=copy.deepcopy(self.after);first(refs(changed)['R1002'],'at')[1]=100;self.reject(changed)
if __name__=='__main__':unittest.main()
