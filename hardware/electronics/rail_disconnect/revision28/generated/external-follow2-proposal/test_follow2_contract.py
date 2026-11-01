import json,hashlib,unittest
from pathlib import Path
R=Path(__file__).parent
class Follow2Contract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=json.loads((R/'follow2-proof.json').read_text());cls.n=json.loads((R/'follow2-native-connectivity.json').read_text())
 def test_actual_source_and_native_file_hash(self):
  self.assertEqual(hashlib.sha256((R/'follow2-only/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),self.p['candidate_pcb_sha256'])
  self.assertEqual(hashlib.sha256((R/'source-parent/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),self.p['source_pcb_sha256'])
 def test_strict_native_coverage_and_uncapped_count(self):
  d=json.loads((R/'follow2-drc.json').read_text());e=json.loads((R/'follow2-erc.json').read_text())
  self.assertEqual(d['ignored_checks'],[]);self.assertEqual(e['ignored_checks'],[]);self.assertEqual(d['schematic_parity'],[])
  self.assertFalse([v for v in d['violations'] if v['severity']=='error']);self.assertTrue(all(not s['violations'] for s in e['sheets']))
  self.assertEqual(len(d['unconnected_items']),29);self.assertEqual(self.n['uncapped_opens'],29)
 def test_actual_target_pad_component(self):
  target=['R116.1','U32.1','U34.3'];self.assertEqual(self.n['FOLLOW2_actual_pad_inventory'],target);self.assertEqual(self.n['FOLLOW2_actual_native_connected_components'],[target])
 def test_no_source_objects_removed_or_changed(self):
  o=self.p['object_preservation']
  for k in ['footprint','via','segment','gr_line','gr_arc']:
   self.assertEqual(o[k]['removed'],[]);self.assertEqual(o[k]['changed'],[])
  self.assertEqual(o['footprint']['added'],[]);self.assertEqual(o['via']['before'],1464);self.assertEqual(len(o['via']['added']),1);self.assertEqual(len(o['segment']['added']),80)
  self.assertTrue(self.p['original_schematic_components_project_bytes_exact']);self.assertEqual(self.p['native_pin_value_mismatches'],[])
 def test_real_force_fill_withdrawal_exposed(self):
  areas={(x['net'],x['layer']):x for x in self.p['actual_saved_fill_delta']}
  self.assertGreater(areas['/N19_SRC','B.Cu']['withdrawn_area_mm2'],11)
  self.assertGreater(areas['/V5_REG_SRC','In2.Cu']['withdrawn_area_mm2'],5)
  self.assertTrue(self.p['saved_fill_delta_not_resistance_or_noise_bound']);self.assertFalse(self.p['physical_qualified']);self.assertFalse(self.p['adoption']);self.assertFalse(self.p['full_routing_closed'])
 def test_only_control_net_added(self):
  for obj in self.p['added_segments']:
   self.assertIn('width 0.2',obj['source_object']);self.assertIn('/E28_ANA_FOLLOW2',obj['source_object'])
  self.assertEqual(self.p['removed_source_segments'],[]);self.assertTrue(self.p['FOLLOW2_closed']);self.assertTrue(self.p['ANA_PG1_still_open'])
if __name__=='__main__':unittest.main()
