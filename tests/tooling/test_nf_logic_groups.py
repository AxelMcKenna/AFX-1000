"""Guard generic additive routing from power, analog and connectivity regressions."""
import copy,json,unittest
from collections import Counter
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_logic_groups import eligible_logic,verify_geometry,verify_pads,verify_counts

class LogicGroupBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards=[read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text()) for n in ['nf-pin-escape-native-03','nf-pin-escape-native-04']]
        cls.captures=[json.loads((root/n/'capture.json').read_text()) for n in ['nf-pin-escape-inputs-158','nf-pin-escape-inputs-156']]
    def test_actual_additive_candidate_preserves_prior_pads(self):verify_geometry(*self.boards);verify_pads(*self.captures)
    def test_power_analog_and_timer_nets_excluded(self):
        for n in ['/DIG5_FORCE','/NF_STARTUP_SAFE_REF','/N12_START_CT','/N12_START_CT_PULL','/N12_BIAS_SENSE','/N12_SS','/N12_TMR']:
            self.assertFalse(eligible_logic(n),n)
        for n in ['/N19_PERMIT','/N12_COMPLETE_CLK','/N12_OUTPUT_UV_GOOD']:self.assertTrue(eligible_logic(n))
    def test_changed_original_copper_rejected(self):
        b=copy.deepcopy(self.boards[1]);first(children(b,'segment')[0],'width')[1]=.01
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],b)
    def test_added_trace_on_plane_rejected(self):
        b=copy.deepcopy(self.boards[1]);old={first(n,'uuid')[1] for n in children(self.boards[0],'segment')}
        n=next(n for n in children(b,'segment') if first(n,'uuid')[1] not in old);first(n,'layer')[1]='In4.Cu'
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],b)
    def test_pad_partition_split_rejected(self):
        c=copy.deepcopy(self.captures[1]);next(o for o in c['objects'] if o.get('ref')=='U23' and o.get('pin')=='1')['group']='split'
        with self.assertRaises(AssertionError):verify_pads(self.captures[0],c)
    def test_other_net_regression_rejected_despite_total_improvement(self):
        with self.assertRaises(AssertionError):verify_counts(Counter(a=5,b=1),Counter(a=2,b=2),{'a'})

if __name__=='__main__':unittest.main()
