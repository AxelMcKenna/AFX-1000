"""Protect the selected cell boundaries and ordinary via-joint behavior."""
import copy
import json
import unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_softstart import verify_geometry,verify_connections,MOVED
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen


class SoftstartBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards=[read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text()) for n in ['nf-ct-local-native-01','nf-softstart-cell-native-02']]
        cls.captures=[json.loads((root/n/'capture.json').read_text()) for n in ['nf-ct-local-inputs-166','nf-softstart-cell-inputs-163']]
        cls.removed=json.loads((root/'nf-softstart-cell-routes-01/construction.json').read_text())['removed_leaf_objects']
        plan=json.loads((root/'nf-remote-timing-plan-01/plan.json').read_text())
        ids={t['uuid'] for r in plan['placements'] if r['selected']['ref'] in MOVED for t in r['selected']['displaced_logic_tracks']}
        cls.removed += [n for n in children(cls.boards[0],'segment') if first(n,'uuid')[1] in ids]

    def test_actual_candidate_preserves_geometry_and_connections(self):
        verify_geometry(*self.boards,self.removed)
        verify_connections(*self.captures)

    def test_unrelated_force_width_change_rejected(self):
        changed=copy.deepcopy(self.boards[1])
        n=next(n for n in children(changed,'segment') if first(n,'net')[-1]=='/DIG5_FORCE')
        first(n,'width')[1]=.16
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],changed,self.removed)

    def test_existing_fault_pad_disconnection_rejected(self):
        changed=copy.deepcopy(self.captures[1])
        pad=next(o for o in changed['objects'] if o['kind']=='PAD' and o['net']=='/NF_NO_FAULT')
        pad['group']='broken'
        with self.assertRaises(AssertionError):verify_connections(self.captures[0],changed)

    def test_softstart_reference_relabelled_AGND_rejected(self):
        changed=copy.deepcopy(self.captures[1])
        pad=next(o for o in changed['objects'] if o.get('ref')=='C53' and o.get('pin')=='2')
        pad['net']='/AGND'
        with self.assertRaises(AssertionError):verify_connections(self.captures[0],changed)

    def test_existing_via_reuse_precedes_new_drill_spacing(self):
        screen=ExistingViaScreen.__new__(ExistingViaScreen)
        screen.vias=[('/other',(1.7,1.)),('/wanted',(1.,1.))];screen.new_vias=[]
        self.assertTrue(screen.via_legal('/wanted',(1.,1.)))
        self.assertFalse(screen.via_legal('/other',(1.,1.)))


if __name__=='__main__':unittest.main()
