import json,unittest
from unittest.mock import patch
from . import analyze as bounds
from . import routes

class OperatingBoundsTests(unittest.TestCase):
    def test_source_specific_voltage_coverage(self):
        r=bounds.analyze()
        self.assertEqual((r['table_voltage_covered_packages'],r['table_voltage_uncovered_packages']),(39,42))
        d={f['part']:f for f in r['families']}
        self.assertTrue(d['OPA2333AID']['table_voltage_domain_covers_actual_rail'])
        self.assertFalse(d['TLV1824DR']['table_voltage_domain_covers_actual_rail'])
        self.assertFalse(d['SN74HCS08PWR']['table_voltage_domain_covers_actual_rail'])
        self.assertIsNone(r['full_current_bound_A'])
    def test_traced_inhibit_is_not_timing_qualification(self):
        r=bounds.analyze()
        self.assertEqual(len(r['shutdown_chain']['drivers']),4)
        self.assertIsNone(r['shutdown_chain']['actual_TPS3890_max_assertion_delay_s'])
        self.assertIsNone(r['shutdown_chain']['actual_total_shutdown_max_s'])
        self.assertFalse(r['shutdown_chain']['independent_aux_valid_inhibit_proven'])
        self.assertLess(r['capacitor_hold_sensitivity']['proposed_threshold_zero_drop_hold_s'],18e-6)
    def test_native_contact_graph_and_reservoir(self):
        r=routes.analyze()
        self.assertEqual((r['source_connected_ICs'],r['unconnected_ICs']),(9,72))
        self.assertEqual(r['source_group_object_count'],188)
        self.assertAlmostEqual(r['nominal_source_and_main_ground_connected_capacitance_F'],11e-6)
        self.assertEqual(r['paths'][0]['ref'],'E_U31')
        self.assertIsNone(r['whole_board_distribution_drop_bound_V'])
    def test_capture_corruption_rejected(self):
        with patch.object(routes,'sha',return_value='corrupt'):
            with self.assertRaises(AssertionError):routes.analyze()
    def test_reports_match_live_calculations(self):
        self.assertEqual(json.loads((bounds.HERE/'analysis.json').read_text()),bounds.analyze())
        self.assertEqual(json.loads((routes.HERE/'routes.json').read_text()),routes.analyze())

if __name__=='__main__':unittest.main()
