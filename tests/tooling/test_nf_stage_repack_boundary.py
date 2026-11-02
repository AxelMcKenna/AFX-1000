"""Require an explicit watchdog copper exception and preserve its pad connections."""
import copy,json,unittest
from pathlib import Path
from hardware.fabrication.audit_nf_logic_swap_final import removed_nodes,verify_geometry,pad_review
from hardware.electronics.common.sexpr import children,first,read_sexpr

class StageRepackBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards=[read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text()) for n in ['nf-u37-multilayer-native-02','nf-stage-escape-repack-native-01']]
        cls.captures=[json.loads((root/n/'capture.json').read_text()) for n in ['nf-u37-multilayer-inputs-149','nf-stage-escape-repack-inputs-139']]
        cls.removed,proofs=removed_nodes()
        cls.allowed=set(json.loads(proofs[0].read_text())['affected_nets'])|{'/N12_WD_ARMED'}
    def test_documented_repack_scope(self):
        verify_geometry(*self.boards,self.removed,self.allowed)
    def test_unlisted_watchdog_exception_rejected(self):
        with self.assertRaises(AssertionError):
            verify_geometry(*self.boards,self.removed,self.allowed-{'/N12_WD_ARMED'})
    def test_incomplete_removal_inventory_rejected(self):
        with self.assertRaises(AssertionError):
            verify_geometry(*self.boards,self.removed[:-1],self.allowed)
    def test_watchdog_connections_survive_both_branch_rejoins(self):
        lost=pad_review(*self.captures)
        self.assertEqual({r['net'] for r in lost},{'/N12_STAGE_ENABLED'})
    def test_unrelated_power_change_rejected(self):
        changed=copy.deepcopy(self.boards[1])
        node=next(t for t in children(changed,'segment') if first(t,'net')[-1]=='/DIG5_FORCE')
        first(node,'width')[1]=.16
        with self.assertRaises(AssertionError):
            verify_geometry(self.boards[0],changed,self.removed,self.allowed)
