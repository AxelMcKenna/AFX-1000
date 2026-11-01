import hashlib
import json
import unittest
from pathlib import Path

R = Path(__file__).parent

class ReceiverContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads((R / 'final-delta-proof.json').read_text())

    def test_actual_source_and_candidate_identity(self):
        for path, key in [('source-parent/rail_disconnect.kicad_pcb', 'source_pcb_sha256'), ('candidate-paired/rail_disconnect.kicad_pcb', 'candidate_pcb_sha256')]:
            self.assertEqual(hashlib.sha256((R / path).read_bytes()).hexdigest(), self.p[key])

    def test_complete_strict_native_coverage(self):
        d = json.loads((R / 'candidate-drc.json').read_text())
        self.assertIn('ignored_checks', d)
        self.assertEqual(d['ignored_checks'], [])
        self.assertEqual(d['schematic_parity'], [])
        self.assertFalse([v for v in d['violations'] if v['severity'] == 'error'])
        self.assertEqual(len(d['unconnected_items']), self.p['uncapped_opens'])

    def test_every_old_via_and_remaining_track_exact(self):
        o = self.p['object_preservation']
        self.assertEqual(o['via']['removed'], [])
        self.assertEqual(o['via']['changed'], [])
        self.assertEqual(o['segment']['changed'], [])
        self.assertEqual(len(o['via']['added']), 1)
        self.assertEqual(len(o['segment']['removed']), 10)
        self.assertEqual(len(o['segment']['added']), 16)
        self.assertTrue(self.p['original_physical_FP_semantics_ignoring_regenerated_UUIDs_all_vias_all_remaining_tracks_setup_layers_outline_zone_contracts_exact'])

    def test_native_full_target_pad_components_not_just_ratsnest_absence(self):
        rows = self.p['native_actual_pad_connectivity']
        for net, number in [('P12_OV_OK', 4), ('E28_MASTER_ENABLE', 20), ('P19_OV_OK_SCHMITT', 2)]:
            self.assertEqual(len(rows[net]['actual_pads']), number)
            self.assertEqual(rows[net]['native_connected_pad_components'], [rows[net]['actual_pads']])
        self.assertFalse(rows['V5_REG_OV_OK_SCHMITT']['all_actual_pads_connected'])
        self.assertTrue(self.p['V5_buffered_debt_remains'])

    def test_only_declared_control_fragments_withdrawn(self):
        counts = {}
        for item in self.p['removed_source_segments']:
            n = item['geometry']['net']
            counts[n] = counts.get(n, 0) + 1
        self.assertEqual(counts, {'E28_MASTER_ENABLE': 1, 'P19_OV_OK_SCHMITT': 3, 'V5_REG_OV_OK_SCHMITT': 6})
        self.assertEqual(self.p['native_pin_value_mismatches'], [])
        self.assertEqual(self.p['native_ERC_violations'], 0)

    def test_fill_changes_and_release_holds_visible(self):
        self.assertTrue(self.p['actual_saved_fill_delta'])
        self.assertTrue(self.p['saved_fill_delta_not_resistance_or_noise_bound'])
        self.assertFalse(self.p['full_routing_closed'])
        self.assertFalse(self.p['physical_qualified'])
        self.assertFalse(self.p['adoption'])

if __name__ == '__main__':
    unittest.main()
