"""Guard unrelated copper and existing pad connectivity in the CT revision."""
import copy
import json
import unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_ct import verify_geometry,verify_pad_connectivity


class CTPlacementBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.before=read_sexpr((base/'nf-watchdog-routed-native-02/negative_startup_physical.kicad_pcb').read_text())
        cls.after=read_sexpr((base/'nf-ct-local-native-01/negative_startup_physical.kicad_pcb').read_text())
        cls.removed=[n for name in ['nf-ct-routes-01','nf-ct-finish-01','nf-ct-clean-reference-01'] for n in json.loads((base/name/'construction.json').read_text())['removed_leaf_objects']]
        cls.removed.append(next(n for n in children(cls.before,'segment') if first(n,'uuid')[1]=='ec29140f-e434-4f05-8433-92fc43c4fb2a'))
        cls.captures=[json.loads((base/name/'capture.json').read_text()) for name in ['nf-watchdog-routed-inputs-168','nf-ct-local-inputs-166']]

    def test_actual_ct_revision_preserves_other_geometry_and_connections(self):
        verify_geometry(self.before,self.after,self.removed)
        verify_pad_connectivity(*self.captures)

    def test_force_track_width_change_rejected(self):
        changed=copy.deepcopy(self.after)
        track=next(n for n in children(changed,'segment') if first(n,'net')[-1]=='/DIG5_FORCE')
        first(track,'width')[1]=.16
        with self.assertRaises(AssertionError):verify_geometry(self.before,changed,self.removed)

    def test_unmoved_reference_pin_disconnection_rejected(self):
        changed=copy.deepcopy(self.captures[1])
        pin=next(o for o in changed['objects'] if o.get('ref')=='U25' and o.get('pin')=='2')
        pin['group']='disconnected'
        with self.assertRaises(AssertionError):verify_pad_connectivity(self.captures[0],changed)

    def test_relabelling_local_reference_as_AGND_rejected(self):
        changed=copy.deepcopy(self.captures[1])
        pin=next(o for o in changed['objects'] if o.get('ref')=='C35' and o.get('pin')=='2')
        pin['net']='/AGND'
        with self.assertRaises(AssertionError):verify_pad_connectivity(self.captures[0],changed)


if __name__=='__main__':unittest.main()
