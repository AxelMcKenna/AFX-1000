"""Ensure routing progress cannot hide unrelated edits or split prior nets."""
import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_pin_escape import verify_geometry,verify_pad_connections

class EscapeBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards=[read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text()) for n in ['nf-softstart-cell-native-02','nf-pin-escape-native-02']]
        cls.captures=[json.loads((root/n/'capture.json').read_text()) for n in ['nf-softstart-cell-inputs-163','nf-pin-escape-inputs-159']]
    def test_actual_additions_preserve_geometry_and_pad_groups(self):
        verify_geometry(*self.boards);verify_pad_connections(*self.captures,['1','8','9','12'])
    def test_unrelated_force_width_edit_rejected(self):
        b=copy.deepcopy(self.boards[1]);n=next(n for n in children(b,'segment') if first(n,'net')[-1]=='/DIG5_FORCE');first(n,'width')[1]=.16
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],b)
    def test_missing_previous_return_connection_rejected(self):
        c=copy.deepcopy(self.captures[1]);next(o for o in c['objects'] if o.get('ref')=='U23' and o.get('pin')=='1')['group']='split'
        with self.assertRaises(AssertionError):verify_pad_connections(self.captures[0],c)
    def test_unclosed_u44_connection_rejected(self):
        with self.assertRaises(AssertionError):verify_pad_connections(*self.captures,['11'])
    def test_added_trace_on_reference_plane_rejected(self):
        b=copy.deepcopy(self.boards[1]);old={first(n,'uuid')[1] for n in children(self.boards[0],'segment')}
        n=next(n for n in children(b,'segment') if first(n,'uuid')[1] not in old);first(n,'layer')[1]='In1.Cu'
        with self.assertRaises(AssertionError):verify_geometry(self.boards[0],b)

if __name__=='__main__':unittest.main()
