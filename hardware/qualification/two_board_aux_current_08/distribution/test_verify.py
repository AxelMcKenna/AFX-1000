import copy,json,unittest
from .verify import verify,semantic,H
class DistributionTests(unittest.TestCase):
 def setUp(self):self.p=json.loads((H/'plan.json').read_text());self.c=json.loads((H/'capture-02/capture.json').read_text())
 def test_native_checkpoint(self):self.assertEqual(verify()['opens'],1945)
 def test_wrong_input_node_rejected(self):
  self.p['routes'][0]['target']='P_R902.2'
  with self.assertRaises(AssertionError):semantic(self.p,self.c)
 def test_narrower_feed_rejected(self):
  self.p['routes'][0]['width_mm']=.2
  with self.assertRaises(AssertionError):semantic(self.p,self.c)
if __name__=='__main__':unittest.main()
