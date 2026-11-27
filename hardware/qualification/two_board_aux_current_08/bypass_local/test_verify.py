import json,unittest
from .verify import H,local_geometry,verify
from .courtyards import extract
class BypassTests(unittest.TestCase):
 def setUp(self):
  self.p=json.loads((H/'plan.json').read_text());self.c=json.loads((H/'capture-01/capture.json').read_text());self.q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text())
 def test_checkpoint(self):verify();extract()
 def test_moved_cap_without_route_rejected(self):
  next(r['chosen'] for r in self.p['rows'] if r['chosen'])['position_mm'][0]+=1
  with self.assertRaises(AssertionError):local_geometry(self.p,self.c,self.q)
 def test_actual_gnd_pin_net_asserted(self):
  next(o for o in self.c['objects'] if o.get('ref')=='E_U4' and o.get('pin')=='4')['net']='/E_rail_disconnect/N12_TT'
  with self.assertRaises(AssertionError):local_geometry(self.p,self.c,self.q)
if __name__=='__main__':unittest.main()
