import hashlib,json,unittest
from pathlib import Path
R=Path(__file__).parent
class C84Contract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=json.loads((R/'c84-functional-proof.json').read_text());cls.n=json.loads((R/'native-audit.json').read_text())
 def test_complete_native_check_coverage(self):
  d=json.loads((R/'candidate-drc.json').read_text());e=json.loads((R/'candidate-erc.json').read_text())
  self.assertEqual(d['ignored_checks'],[]);self.assertEqual(e['ignored_checks'],[]);self.assertEqual(d['schematic_parity'],[])
  self.assertEqual([v for v in d['violations'] if v['severity']=='error'],[])
  self.assertTrue(all(not s['violations'] for s in e['sheets']))
  self.assertEqual(len(d['unconnected_items']),30);self.assertEqual(self.n['uncapped_opens'],30)
 def test_literal_delta_is_only_bypass_and_one_pose(self):
  o=self.p['object_preservation'];self.assertEqual(o['footprint']['changed'],['C84'])
  for k in ['removed','added','changed']:self.assertEqual(o['via'][k],[])
  self.assertEqual(o['via']['before'],1464);self.assertEqual(o['segment']['changed'],[])
  self.assertEqual(len(o['segment']['removed']),4);self.assertEqual(len(o['segment']['added']),4)
  self.assertEqual(sorted(x['net'] for x in self.p['removed_source_segments']),['AGND','AGND','V2V5_AUX','V2V5_AUX'])
 def test_actual_cap_pin_roles_and_ground_overlap(self):
  self.assertTrue(self.n['C84_GND_existing_via_centre_inside_actual_native_pad'])
  for actual,want in zip(self.n['C84_pose_mm'][:2],[62.8,52.4]):self.assertAlmostEqual(actual,want)
  self.assertEqual(self.n['C84_pose_mm'][2]%360,270)
  ps={x['pin']:x for x in self.n['C84_pads']};self.assertEqual(ps['1']['net'],'/V2V5_AUX');self.assertEqual(ps['2']['net'],'/AGND')
  self.assertTrue(self.n['actual_pad_components']['V2V5_AUX']['closed'])
 def test_netlist_and_parent_integrity(self):
  self.assertEqual(self.p['native_component_count'],269);self.assertEqual(self.p['native_pin_value_mismatches'],[])
  self.assertTrue(self.p['original_schematic_components_project_bytes_exact'])
  self.assertEqual(hashlib.sha256((R/'candidate-paired/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),self.p['candidate_pcb_sha256'])
 def test_receivers_remain_unclosed(self):
  self.assertFalse(self.n['actual_pad_components']['ANA_PG1']['closed']);self.assertFalse(self.n['actual_pad_components']['E28_ANA_FOLLOW2']['closed'])
  self.assertFalse(self.p['full_routing_closed']);self.assertFalse(self.p['physical_qualified']);self.assertFalse(self.p['adoption'])
 def test_P03_all_ERC_checks_and_frozen_parent(self):
  p=json.loads((R/'p03-erc-audit.json').read_text());d=json.loads((R/'p03-strict-erc.json').read_text())
  self.assertEqual(p['parent_sealed_files_verified'],81);self.assertEqual(p['parent_files_changed'],[])
  self.assertEqual(d['ignored_checks'],[]);self.assertTrue(all(not s['violations'] for s in d['sheets']))
if __name__=='__main__':unittest.main()
