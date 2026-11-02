"""Guard the pose-swap scope and expose connectivity losses during rework."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_logic_swap import verify_geometry,pad_review
from hardware.fabrication.source_audit_tools import removed_logic_swap_nodes as removed_nodes

class SwapBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards=[read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text()) for n in ['nf-u37-multilayer-native-02','nf-logic-swap-prepared-native-03']]
        cls.captures=[json.loads((root/n/'capture.json').read_text()) for n in ['nf-u37-multilayer-inputs-149','nf-logic-swap-clean-inputs-165']]
        cls.removed,_=removed_nodes();cls.allowed=set(json.loads((root/'nf-logic-swap-prepared-01/construction.json').read_text())['affected_nets'])
    def test_only_documented_pose_and_copper_changes(self):verify_geometry(*self.boards,self.removed,self.allowed)
    def test_prepared_trial_does_not_claim_prior_connections_preserved(self):self.assertEqual(len(pad_review(*self.captures)),15)
    def test_unrelated_component_move_rejected(self):
        b=copy.deepcopy(self.boards[1]);fp=next(f for f in children(b,'footprint') if any(p[1]=='Reference' and p[2]=='U23' for p in children(f,'property')));first(fp,'at')[1]='30'
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],b,self.removed,self.allowed)
    def test_original_power_copper_change_rejected(self):
        b=copy.deepcopy(self.boards[1]);t=next(t for t in children(b,'segment') if first(t,'net')[-1]=='/DIG5_FORCE');first(t,'width')[1]=.16
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],b,self.removed,self.allowed)
    def test_swapped_pad_net_change_rejected(self):
        c=copy.deepcopy(self.captures[1]);next(o for o in c['objects'] if o.get('ref')=='U38' and o.get('pin')=='1')['net']='/WRONG'
        with self.assertRaises(AssertionError):pad_review(self.captures[0],c)

if __name__=='__main__':unittest.main()
