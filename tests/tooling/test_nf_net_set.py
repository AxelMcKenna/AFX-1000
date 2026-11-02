"""Reject protected-circuit edits in the scoped NF routing handoff."""
import copy
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_net_set import unchanged_outside_nets


class NetSetProtection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.before=read_sexpr((base/'nf-arm-only-native-01/negative_startup_physical.kicad_pcb').read_text())
        cls.after=read_sexpr((base/'nf-five-net-native-01/negative_startup_physical.kicad_pcb').read_text())
        cls.nets={'/N19_WD_ENABLE','/N12_START','/N19_START_DELAY_N','/CLAMP_SUPPLY_ENABLE','/N12_ARM_CONDITIONED'}

    def test_actual_five_net_composition_preserves_all_other_objects(self):
        self.assertTrue(unchanged_outside_nets(self.before,self.after,self.nets))

    def test_component_motion_is_rejected(self):
        changed=copy.deepcopy(self.after)
        at=first(children(changed,'footprint')[0],'at')
        at[1]=float(at[1])+.1
        self.assertFalse(unchanged_outside_nets(self.before,changed,self.nets))

    def test_force_copper_width_change_is_rejected(self):
        changed=copy.deepcopy(self.after)
        force=next(t for t in children(changed,'segment') if first(t,'net')[-1]=='/DIG5_FORCE')
        first(force,'width')[1]=.16
        self.assertFalse(unchanged_outside_nets(self.before,changed,self.nets))

    def test_relabelling_protected_copper_as_logic_is_rejected(self):
        changed=copy.deepcopy(self.after)
        force=next(t for t in children(changed,'segment') if first(t,'net')[-1]=='/DIG5_FORCE')
        first(force,'net')[-1]='/N12_START'
        self.assertFalse(unchanged_outside_nets(self.before,changed,self.nets))


if __name__=='__main__':
    unittest.main()
