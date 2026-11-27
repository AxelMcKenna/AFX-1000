import unittest,json
from .verify import H,semantic,verify
class FeedTests(unittest.TestCase):
 def test_native_reserialization_rejected(self):
  from .verify import BASE,read_sexpr,children,first,zone_preservation
  trees=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,H/'native-02']];az,bz=[{first(z,'uuid')[1]:z for z in children(t,'zone')} for t in trees]
  with self.assertRaises(AssertionError):zone_preservation(az,bz,'bc76c316-2c04-5ecb-85b7-3e5f80b26bf1')
 def test_checkpoint(self):self.assertEqual(verify()['opens'],1943)
 def test_wrong_source_net_rejected(self):
  c=json.loads((H/'capture-01/capture.json').read_text());p=json.loads((H/'plan.json').read_text());next(o for o in c['objects'] if o.get('ref')=='P_C901' and o.get('pin')=='1')['net']='WRONG'
  with self.assertRaises(AssertionError):semantic(p,c)
 def test_wrong_target_rejected(self):
  c=json.loads((H/'capture-01/capture.json').read_text());p=json.loads((H/'plan.json').read_text());p['routes'][0]['target']='P_C102.2'
  with self.assertRaises(AssertionError):semantic(p,c)
if __name__=='__main__':unittest.main()
