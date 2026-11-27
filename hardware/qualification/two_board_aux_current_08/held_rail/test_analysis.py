import math,unittest
from .analyze import analyze
class HoldRail(unittest.TestCase):
 def test_early_5V_monitor_is_required(self):
  r=analyze();s=r['five_volt_supervisor'];h=r['hard_5V_source_short']
  self.assertGreater(s['healthy_low_margin_V'],0);self.assertGreater(s['healthy_high_margin_V'],0)
  self.assertLess(h['initial_RC_node_min_at_worst_detection_V'],4.0)
  self.assertGreater(h['minimum_regulated_hold_s_under_allocations'],80e-6)
 def test_rc_bound_against_time_domain_integration(self):
  r=analyze();a=r['receiving_allocations'];h=r['hard_5V_source_short'];v=h['initial_RC_node_min_at_worst_detection_V'];dt=1e-9;t=0
  # Independent forward time-domain integration of capacitor current.
  while v>h['LDO_required_input_floor_V']:
   v-=(v/(4.7*(1-a['total_feed_R_error']))+a['total_reservoir_drain_A'])*dt/a['effective_C_min_F'];t+=dt
  self.assertLess(abs(t-h['minimum_regulated_hold_s_under_allocations']),2*dt)
 def test_current_and_gate_limits_are_not_claimed_as_guarantees(self):
  r=analyze();self.assertFalse(r['current_bound_proven']);self.assertFalse(r['timing_qualified']);self.assertEqual(len(r['static_resistor_branches']),8)
  self.assertIn('100pF',r['gate_load_qualification']);self.assertTrue(any('E_J6' in x for x in r['missing_current_bounds']))
 def test_regulator_minimum_load_is_enforced(self):
  r=analyze();self.assertGreater(r['LDO']['minimum_bleeder_current_A'],.001);self.assertGreater(r['LDO']['regulated_output_V'][0],3.)
if __name__=='__main__':unittest.main()
