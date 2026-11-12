import unittest
from .preregulator import calculate_preregulator
class PreregulatorTest(unittest.TestCase):
 def test_headroom_and_dissipation_requirements(self):
  r=calculate_preregulator();lo,hi=r['conditional_output_interval_V']
  self.assertGreater(lo,4.8);self.assertLess(hi,5.2)
  self.assertGreater(r['LDO_accuracy_headroom_margin_at_prereg_min_V'],1)
  self.assertLess(r['maximum_LDO_loss_at_allocated100mA_W'],.2)
  self.assertFalse(r['thermal_qualified']);self.assertFalse(r['board_changed'])
 def test_startup_dependency_is_not_aux_controlled(self):
  r=calculate_preregulator()
  self.assertEqual(r['wiring']['3_EN'],'VIN_IC (always on)')
  self.assertNotIn('POWER_READY',str(r['wiring']))
