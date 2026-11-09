"""Reject circuit or unrelated geometry changes hidden inside the R1040 move."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,first,children
from hardware.fabrication.audit_pot_filter_delta import verify_board_delta,copper,refs
ROOT=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'

class PotFilterDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=read_sexpr((ROOT/'digital-exact-regions-native-01/digital_core.kicad_pcb').read_text())
        cls.after=read_sexpr((ROOT/'digital-pot-filter-native-01/digital_core.kicad_pcb').read_text())
        cls.recipe=json.loads((ROOT/'digital-pot-filter-repack-04/construction.json').read_text())
        cls.template=read_sexpr((ROOT/'digital-pot-filter-templates-01/R1040-B-90.kicad_mod').read_text())
    def test_actual_native_delta_matches_the_declared_transfer(self):
        verify_board_delta(self.before,self.after,self.recipe,self.template)
    def test_only_declared_raw_spur_may_be_removed(self):
        changed=copy.deepcopy(self.after)
        uid=next(i for i in copper(self.before).keys()&copper(changed).keys() if first(copper(changed)[i],'net')[1]=='/PROCESSOR/POT_RAW_09')
        changed.remove(copper(changed)[uid])
        with self.assertRaises(AssertionError):verify_board_delta(self.before,changed,self.recipe,self.template)
    def test_unrelated_track_cannot_change(self):
        changed=copy.deepcopy(self.after);before=copper(self.before);after=copper(changed)
        ident=next(i for i in before.keys()&after.keys() if first(before[i],'net')[1]=='V3V3_IO' and before[i][0]=='segment')
        first(after[ident],'width')[1]=.1
        with self.assertRaises(AssertionError):verify_board_delta(self.before,changed,self.recipe,self.template)
    def test_resistor_pin_nets_cannot_be_swapped(self):
        changed=copy.deepcopy(self.after);pads=children(refs(changed)['R1040'],'pad')
        first(pads[0],'net')[1],first(pads[1],'net')[1]=first(pads[1],'net')[1],first(pads[0],'net')[1]
        with self.assertRaises(AssertionError):verify_board_delta(self.before,changed,self.recipe,self.template)
if __name__=='__main__':unittest.main()
