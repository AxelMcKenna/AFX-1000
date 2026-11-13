import copy,gzip,json,unittest
from hardware.qualification.two_board_aux_current_08.ldo_feed.verify import H,semantics
class LDOFeedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.e=json.loads(gzip.decompress((H/'review-02/native-evidence.json.gz').read_bytes()));cls.p=json.loads((H/'manifest-IN-slot-01.json').read_text())
 def test_native_reference(self):semantics(self.e,self.p)
 def test_return_net_mutation(self):
  e=copy.deepcopy(self.e);v=next(v for v in self.p['vias'] if v['net']=='PWR_AGND');e['candidate']['objects'][v['uuid']][1]='/P_power_supply/AUX_PREREG5'
  with self.assertRaises(AssertionError):semantics(e,self.p)
 def test_original_pad_resize(self):
  e=copy.deepcopy(self.e);next(p for p in e['candidate']['pad_identities'].values() if p['ref']=='E_U4')['size_nm'][0]+=1
  with self.assertRaises(AssertionError):semantics(e,self.p)
 def test_unrelated_group_merge(self):
  e=copy.deepcopy(self.e);gs=e['candidate']['groups'];gs[0]['members'].append(gs[1]['members'][0])
  with self.assertRaises(AssertionError):semantics(e,self.p)
if __name__=='__main__':unittest.main()
