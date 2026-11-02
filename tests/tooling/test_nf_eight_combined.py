"""Guard composed timing cells, reference groups and the layer/keepout map."""
import copy
import json
import unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_eight_combined import verify_geometry,verify_connections,removed_from_source


class CombinedBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards=[read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text()) for n in ['nf-softstart-cell-native-02','nf-eight-combined-native-02']]
        cls.removed,_=removed_from_source(cls.boards[0])
        cls.captures=[json.loads((root/n/'capture.json').read_text()) for n in ['nf-softstart-cell-inputs-163','nf-eight-combined-inputs-161']]

    def test_current_combination_preserves_boundaries_and_all_pad_connections(self):
        verify_geometry(*self.boards,self.removed)
        verify_connections(*self.captures)

    def test_lost_controller_reference_join_rejected(self):
        changed=copy.deepcopy(self.captures[1])
        for o in changed['objects']:
            if o.get('ref')=='U23' and o.get('pin') in {'1','3','10','11','13'}:o['group']='lost-reference'
        with self.assertRaises(AssertionError):verify_connections(self.captures[0],changed)

    def test_missing_added_layer_keepout_rejected(self):
        changed=copy.deepcopy(self.boards[1])
        z=next(z for z in children(changed,'zone') if children(z,'keepout') and children(z,'layer') and first(z,'layer')[1]=='In5.Cu')
        changed.remove(z)
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],changed,self.removed)

    def test_changed_existing_force_copper_rejected(self):
        changed=copy.deepcopy(self.boards[1])
        s=next(s for s in children(changed,'segment') if first(s,'net')[-1]=='/DIG5_FORCE')
        first(s,'width')[1]=.16
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],changed,self.removed)

    def test_new_reference_route_narrowing_rejected(self):
        changed=copy.deepcopy(self.boards[1]);old={first(n,'uuid')[1] for n in children(self.boards[0],'segment')}
        s=next(s for s in children(changed,'segment') if first(s,'net')[-1]=='/N12_P03_SRC' and first(s,'uuid')[1] not in old)
        first(s,'width')[1]=.16
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],changed,self.removed)


if __name__=='__main__':unittest.main()
