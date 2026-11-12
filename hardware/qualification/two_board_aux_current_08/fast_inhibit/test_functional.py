import unittest
from .functional import run
class FunctionalTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=run()
 def test_unchanged_divider_fails_and_candidate_restores_valid_reference(self):
  self.assertLess(self.r['unchanged_reference_window']['margins'][0]['minimum_asserted_margin_v'],0)
  for x in self.r['corrected_reference_window']['margins']:self.assertGreater(x['minimum_asserted_margin_v'],.05)
 def test_restores_nominal_input_OV_not_just_reference_voltage(self):
  x=self.r['fast_OV']
  for key in ['VIN_IC_rising_V','VIN_IC_falling_V']:
   self.assertGreater(x['uncorrected'][key]-x['baseline'][key],3)
   self.assertLess(abs(x['corrected'][key]-x['baseline'][key]),.005)
  self.assertNotEqual(x['baseline']['reference_filter_tau_s'],x['corrected']['reference_filter_tau_s'])
 def test_all_direct_networks_and_caps_still_counted(self):
  self.assertEqual(len(self.r['direct_resistor_networks']),44)
  self.assertEqual(sum(len(x['roots']) for x in self.r['direct_resistor_networks']),45)
  self.assertEqual(len(self.r['capacitors']),87)
  self.assertTrue(all(x['voltage_rating_screen_pass'] for x in self.r['capacitors']))
  self.assertFalse(any(x['effective_capacitance_qualified'] for x in self.r['capacitors']))
 def test_thermal_requirements_are_not_measured_acceptance(self):
  x=next(x for x in self.r['thermal_sensitivities'] if x['ambient_C']==85 and x['VIN_V']==13.2 and x['load_A']==.1)
  self.assertGreater(x['JEDEC66p2_sensitivity_TJ_C'],150)
  self.assertLess(x['maximum_installed_theta_JA_for125_C_per_W'],41)
  self.assertFalse(x['actual_board_temperature_proven'])
