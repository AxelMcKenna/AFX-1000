import copy,json,unittest
from .verify import H,geometry,verify
class GeometryTests(unittest.TestCase):
 def setUp(self):
  self.p=json.loads((H/'plan.json').read_text());self.c=json.loads((H/'capture-01/capture.json').read_text());self.q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text())
 def test_checkpoint(self):verify()
 def test_timing_pin_is_not_ground(self):
  o=next(o for o in self.c['objects'] if o.get('ref')=='E_U1' and o.get('pin')=='2');self.p['routes'][1]['source_uuid']=o['uuid']
  with self.assertRaises(AssertionError):geometry(self.p,self.c,self.q)
 def test_quiet_target_rejected_even_when_main_connected(self):
  self.q['retained_object_uuids'].append(self.p['routes'][0]['target_uuid'])
  with self.assertRaises(AssertionError):geometry(self.p,self.c,self.q)
 def test_reference_gap_rejected(self):
  self.p['routes'][0]['path_mm'].insert(1,[0,0])
  with self.assertRaises(AssertionError):geometry(self.p,self.c,self.q)
if __name__=='__main__':unittest.main()
