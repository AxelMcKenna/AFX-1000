"""The E28 cleanup exception permits only the listed copper removals."""
import copy,unittest
from pathlib import Path
from hardware.fabrication.audit_e28_cleanup import verify_geometry
from hardware.electronics.common.sexpr import children,first,read_sexpr

class RemovalBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging/e28-covered-stubs-native/rail_disconnect.kicad_pcb'
        source=read_sexpr(path.read_text())
        cls.before=[source[0],first(source,'general'),*children(source,'footprint')[:1],*children(source,'segment')[:2],*children(source,'via')[:1],*children(source,'zone')[:1]]
        cls.removed=[children(cls.before,'segment')[0]]
        cls.after=copy.deepcopy(cls.before);cls.after.remove(cls.removed[0])
    def test_explicit_removal_only(self):verify_geometry(self.before,self.after,self.removed)
    def test_missing_removal_record_rejected(self):
        with self.assertRaises(AssertionError):verify_geometry(self.before,self.after,[])
    def test_retained_track_width_change_rejected(self):
        changed=copy.deepcopy(self.after);first(children(changed,'segment')[0],'width')[1]=.111
        with self.assertRaises(AssertionError):verify_geometry(self.before,changed,self.removed)
    def test_retained_drill_change_rejected(self):
        changed=copy.deepcopy(self.after);first(children(changed,'via')[0],'drill')[1]=.111
        with self.assertRaises(AssertionError):verify_geometry(self.before,changed,self.removed)
    def test_component_pose_change_rejected(self):
        changed=copy.deepcopy(self.after);first(children(changed,'footprint')[0],'at')[1]=0
        with self.assertRaises(AssertionError):verify_geometry(self.before,changed,self.removed)
    def test_stack_change_rejected(self):
        changed=copy.deepcopy(self.after);first(first(changed,'general'),'thickness')[1]=1.2
        with self.assertRaises(AssertionError):verify_geometry(self.before,changed,self.removed)

if __name__=='__main__':unittest.main()
