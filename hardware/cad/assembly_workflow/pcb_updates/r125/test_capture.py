"""Challenge the exact rigid-footprint equivalence gate with physical changes."""
import copy
import unittest
from hardware.cad.assembly_workflow.pcb_updates.r125.build import physical_signature, SIGNAL
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness as bridge


class RigidFootprintGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = bridge.snapshot(w.ROOT / 'hardware/cad/two_board_sensor_05/signal_dac/native-r107/signal_main.kicad_pcb')['footprints']['A_D101']['physical']
        cls.after = bridge.snapshot(w.ROOT / SIGNAL)['footprints']['A_D101']['physical']

    def test_real_rigid_move_and_serialization_order(self):
        self.assertEqual(physical_signature(self.before, 90), physical_signature(self.after))

    def test_pad_dimension_and_position_changes_rejected(self):
        for field in ['size', 'at']:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.after)
                pad = next(c for c in changed if isinstance(c, list) and c[0] == 'pad')
                value = next(c for c in pad if isinstance(c, list) and c[0] == field)
                value[1] = str(float(value[1]) + .1)
                self.assertNotEqual(physical_signature(self.before, 90), physical_signature(changed))

    def test_courtyard_change_rejected(self):
        changed = copy.deepcopy(self.after)
        line = next(c for c in changed if isinstance(c, list) and c[0] == 'fp_line' and ['layer', 'B.CrtYd'] in c)
        start = next(c for c in line if isinstance(c, list) and c[0] == 'start')
        start[1] = str(float(start[1]) + .1)
        self.assertNotEqual(physical_signature(self.before, 90), physical_signature(changed))

    def test_unrotated_pad_rejected(self):
        changed = copy.deepcopy(self.after)
        pad = next(c for c in changed if isinstance(c, list) and c[0] == 'pad')
        at = next(c for c in pad if isinstance(c, list) and c[0] == 'at')
        at[3] = '0'
        self.assertNotEqual(physical_signature(self.before, 90), physical_signature(changed))


if __name__ == '__main__':
    unittest.main()
