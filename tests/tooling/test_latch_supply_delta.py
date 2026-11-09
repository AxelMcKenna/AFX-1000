"""Protect component identity, supply width and unrelated copper in the latch repair."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.fabrication.audit_latch_supply_delta import verify_delta,refs
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
class LatchSupplyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=read_sexpr((ROOT/'digital-blank-pullup-native-01/digital_core.kicad_pcb').read_text())
  cls.after=read_sexpr((ROOT/'digital-latch-supply-native-02/digital_core.kicad_pcb').read_text())
  cls.recipe=json.loads((ROOT/'digital-latch-supply-repack-01/construction.json').read_text())
  cls.cleanup=json.loads((ROOT/'digital-latch-supply-clean-01/construction.json').read_text())
 def reject(self,board):
  with self.assertRaises(AssertionError):verify_delta(self.before,board,self.recipe,self.cleanup)
 def test_exact_final_native_delta(self):verify_delta(self.before,self.after,self.recipe,self.cleanup)
 def test_supply_cannot_be_narrowed(self):
  changed=copy.deepcopy(self.after);ids=set(self.recipe['geometry_delta']['segment']['added'])
  n=next(n for n in children(changed,'segment') if first(n,'uuid')[1] in ids and first(n,'net')[1]=='V3V3_IO');first(n,'width')[1]=.2;self.reject(changed)
 def test_series_value_cannot_change(self):
  changed=copy.deepcopy(self.after);next(p for p in children(refs(changed)['R3017'],'property') if p[1]=='Value')[2]='0R';self.reject(changed)
 def test_new_source_via_cannot_be_grounded(self):
  changed=copy.deepcopy(self.after);ids=set(self.recipe['geometry_delta']['via']['added'])
  n=next(n for n in children(changed,'via') if first(n,'uuid')[1] in ids);first(n,'net')[1]='AGND';self.reject(changed)
 def test_unrelated_clock_copper_cannot_be_removed(self):
  changed=copy.deepcopy(self.after);n=next(n for n in children(changed,'segment') if first(n,'net')[1]=='/LED/CLOCK_5V_SRC');changed.remove(n);self.reject(changed)
if __name__=='__main__':unittest.main()
