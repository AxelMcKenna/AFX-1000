"""Guard the declared ground-spur retirement and identity of all three pull-downs."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,first,children
from hardware.fabrication.audit_control_pulldowns_delta import verify_delta,refs
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
class ControlPulldownTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=read_sexpr((ROOT/'digital-armed-native-02/digital_core.kicad_pcb').read_text())
  cls.after=read_sexpr((ROOT/'digital-control-pulldowns-native-01/digital_core.kicad_pcb').read_text())
  cls.recipe=json.loads((ROOT/'digital-control-pulldowns-repack-05/construction.json').read_text())
 def test_exact_native_delta(self):verify_delta(self.before,self.after,self.recipe)
 def test_retained_ground_junction_cannot_be_removed(self):
  changed=copy.deepcopy(self.after);node=next(n for n in children(changed,'segment') if first(n,'uuid')[1]=='d72a6010-70f6-5e59-8292-ff9170a11e08');changed.remove(node)
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
 def test_pull_down_net_cannot_change(self):
  changed=copy.deepcopy(self.after);first(children(refs(changed)['R1003'],'pad')[0],'net')[1]='AGND'
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
 def test_unrelated_component_cannot_move(self):
  changed=copy.deepcopy(self.after);first(refs(changed)['R1005'],'at')[1]=100
  with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
if __name__=='__main__':unittest.main()
