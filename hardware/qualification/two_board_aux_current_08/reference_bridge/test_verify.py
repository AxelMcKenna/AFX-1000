import json,unittest
from shapely.affinity import translate
from .verify import verify,physical_bridge,H,OUT,nmshape
class ReferenceTests(unittest.TestCase):
 def setUp(self):self.c=json.loads((H/'capture-01/capture.json').read_text());self.p=json.loads((H/'plan.json').read_text());self.g=nmshape(json.loads((OUT/'new-zone-geometry.json').read_text())['polygons_nm'])
 def test_native_checkpoint(self):self.assertEqual(verify()['opens'],1945)
 def test_unanchored_fill_rejected(self):
  with self.assertRaises(AssertionError):physical_bridge(self.c,self.p,translate(self.g,xoff=50))
 def test_wrong_source_ground_group_rejected(self):
  uid=self.p['other_main_zone_contacts'][0]['uuid'];next(x for x in self.c['objects'] if x['uuid']==uid)['group']='wrong-group'
  with self.assertRaises(AssertionError):physical_bridge(self.c,self.p,self.g)
if __name__=='__main__':unittest.main()
