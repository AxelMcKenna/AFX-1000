import json,copy,unittest
from .verify_local import H,semantic,verify
class LocalCellTests(unittest.TestCase):
 def setUp(self):self.p=json.loads((H/'local-routes.json').read_text());self.c=json.loads((H/'capture-04/capture.json').read_text())
 def test_native_checkpoint(self):verify()
 def test_off_center_return_rejected(self):
  next(r for r in self.p['routes'] if r['target'].startswith('via:'))['path_mm'][-1][0]+=.01
  with self.assertRaisesRegex(AssertionError,'centered'):semantic(self.p,self.c)
 def test_regulator_enable_not_ground(self):
  next(o for o in self.c['objects'] if o.get('ref')=='P_U901' and o.get('pin')=='2')['net']='/P_power_supply/AUX_HELD_IN'
  with self.assertRaises(AssertionError):semantic(self.p,self.c)
 def test_reset_not_supply(self):
  next(o for o in self.c['objects'] if o.get('ref')=='P_U902' and o.get('pin')=='4')['net']='PWR_AUX_HELD3V3'
  with self.assertRaises(AssertionError):semantic(self.p,self.c)
 def test_missing_local_link_rejected(self):
  self.p['routes'].pop()
  with self.assertRaises(AssertionError):semantic(self.p,self.c)
if __name__=='__main__':unittest.main()
