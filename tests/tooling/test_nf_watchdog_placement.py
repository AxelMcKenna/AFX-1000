"""Reject unrelated geometry/copper changes in the timing-capacitor revision."""
import copy
import json
import unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_nf_watchdog import verify_geometry


class WatchdogPlacementBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.before=read_sexpr((base/'nf-six-net-native-01/negative_startup_physical.kicad_pcb').read_text())
        cls.after=read_sexpr((base/'nf-watchdog-routed-native-02/negative_startup_physical.kicad_pcb').read_text())
        cls.removed=json.loads((base/'nf-watchdog-stub-cleanup-01/removed-objects.json').read_text())

    def test_actual_placement_change_is_bounded(self):
        verify_geometry(self.before,self.after,self.removed)

    def test_unrelated_component_move_rejected(self):
        after=copy.deepcopy(self.after)
        fp=next(f for f in children(after,'footprint') if any(p[1]=='Reference' and p[2]=='U3' for p in children(f,'property')))
        at=first(fp,'at');at[1]=float(at[1])+.1
        with self.assertRaises(AssertionError):verify_geometry(self.before,after,self.removed)

    def test_added_route_cannot_be_relabelled_as_force_power(self):
        after=copy.deepcopy(self.after)
        route=next(s for s in children(after,'segment') if first(s,'net')[-1]=='/N19_CWD')
        first(route,'net')[-1]='/DIG5_FORCE'
        with self.assertRaises(AssertionError):verify_geometry(self.before,after,self.removed)

    def test_extra_ground_copper_removal_rejected(self):
        after=copy.deepcopy(self.after)
        oldids={first(s,'uuid')[1] for s in children(self.before,'segment')}
        route=next(s for s in children(after,'segment') if first(s,'net')[-1]=='/AGND' and first(s,'uuid')[1] in oldids)
        after.remove(route)
        with self.assertRaises(AssertionError):verify_geometry(self.before,after,self.removed)


if __name__=='__main__':unittest.main()
