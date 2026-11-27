import json,unittest
from .candidate import calculate,HERE
class CandidateTest(unittest.TestCase):
 def test_requirement_is_not_qualification(self):
  r=calculate()
  self.assertFalse(r['shutdown_qualified']);self.assertFalse(r['board_changed'])
  self.assertIsNone(r['supervisor']['startup_correct_state_max_s'])
  self.assertGreater(r['derived_requirements']['effective_capacitance_min_F'],5.7e-6)
  self.assertLess(r['derived_requirements']['effective_capacitance_min_F'],5.9e-6)
 def test_current_and_delay_cost_capacitance(self):
  a=calculate();b=calculate(current_allocation_A=.2)
  self.assertAlmostEqual(b['derived_requirements']['effective_capacitance_min_F'],2*a['derived_requirements']['effective_capacitance_min_F'])
  self.assertGreater(calculate(logic_delay_allocation_s=10e-6)['derived_requirements']['effective_capacitance_min_F'],a['derived_requirements']['effective_capacitance_min_F'])
 def test_impossible_drop_rejected(self):
  with self.assertRaises(AssertionError):calculate(distribution_allocation_V=.6)
 def test_supply_screen_and_cap_inventory(self):
  r=calculate();s=json.loads((HERE/'supply_voltage_screen.json').read_text())
  refs=[ref for x in s['families'] for ref in x['references']]
  self.assertEqual(len(refs),81);self.assertEqual(len(set(refs)),81)
  lo,hi=r['regulator']['conditional_interval_V']
  for x in s['families']:
   self.assertGreater(lo,x['recommended_supply_screen_V'][0]);self.assertLess(hi,x['recommended_supply_screen_V'][1])
  self.assertEqual(len(r['AUX_caps_to_requalify']),87)
 def test_artifact_reproduces(self):
  self.assertEqual(calculate(),json.loads((HERE/'candidate.json').read_text()))
