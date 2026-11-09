"""Protect existing copper and resistor pin identity during a placement change."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,first,children
from hardware.fabrication.audit_armed_repack_delta import verify_delta,refs
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
class ArmedRepackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=read_sexpr((ROOT/'digital-data-series-native-01/digital_core.kicad_pcb').read_text())
  cls.after=read_sexpr((ROOT/'digital-armed-native-02/digital_core.kicad_pcb').read_text())
  cls.recipe=json.loads((ROOT/'digital-armed-repack-01/construction.json').read_text())
 def test_exact_native_move_and_additions(self):verify_delta(self.before,self.after,self.recipe)
 def test_ground_junction_cannot_be_removed(self):
  changed=copy.deepcopy(self.after)
  n=next(n for n in children(changed,'segment') if first(n,'uuid')[1]=='b7ab85f8-ce9e-590a-acdc-bbbb0f008d70');changed.remove(n)
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
 def test_pin_nets_cannot_change(self):
  changed=copy.deepcopy(self.after);first(children(refs(changed)['R1005'],'pad')[0],'net')[1]='AGND'
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
 def test_existing_copper_cannot_move(self):
  changed=copy.deepcopy(self.after);first(children(changed,'segment')[0],'start')[1]=123
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
if __name__=='__main__':unittest.main()
