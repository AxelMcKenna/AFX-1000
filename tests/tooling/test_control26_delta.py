"""Reject hidden changes in the declared three-control reconstruction."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,first,children
from hardware.fabrication.audit_control26_delta import verify_delta,copper
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'

class Control26DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=read_sexpr((ROOT/'digital-led-control-native-01/digital_core.kicad_pcb').read_text())
        cls.after=read_sexpr((ROOT/'digital-control26-native-01/digital_core.kicad_pcb').read_text())
        cls.recipe=json.loads((ROOT/'digital-control26-complete-comparison-01/construction.json').read_text())
    def test_actual_native_replacement_matches_the_declared_scope(self):
        verify_delta(self.before,self.after,self.recipe)
    def test_unrelated_power_track_cannot_change(self):
        changed=copy.deepcopy(self.after)
        track=next(n for n in children(changed,'segment') if first(n,'net')[1]=='V3V3_IO')
        first(track,'width')[1]=.1
        with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
    def test_control_pin_net_cannot_be_reassigned(self):
        changed=copy.deepcopy(self.after)
        fp=next(f for f in children(changed,'footprint') if any(p[1:3]==['Reference','U2002'] for p in children(f,'property')))
        pad=next(p for p in children(fp,'pad') if p[1]=='6')
        first(pad,'net')[1]='/CONTROLS/CONTROL_25'
        with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)
    def test_new_via_drill_cannot_be_reduced(self):
        changed=copy.deepcopy(self.after)
        via=copper(changed)[self.recipe['geometry_delta']['via']['added'][0]]
        first(via,'drill')[1]=.2
        with self.assertRaises(AssertionError):verify_delta(self.before,changed,self.recipe)

if __name__=='__main__':unittest.main()
