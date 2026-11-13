import copy,gzip,json,unittest
from hardware.qualification.two_board_aux_current_08.c13_receiving.verify import H,semantics
class C13ReceivingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.e=json.loads(gzip.decompress((H/'review-02/native-evidence.json.gz').read_bytes()));cls.r=json.loads((H/'native-02/review.json').read_text())
 def test_reference_evidence(self):semantics(self.e,self.r)
 def test_tt_pin_cannot_be_ground(self):
  e=copy.deepcopy(self.e);p=next(p for p in e['candidate']['pad_identities'].values() if p['ref']=='E_U4' and p['pin']=='2');p['net']='PWR_AGND'
  with self.assertRaises(AssertionError):semantics(e,self.r)
 def test_unrelated_pad_resize_rejected(self):
  e=copy.deepcopy(self.e);p=next(p for p in e['candidate']['pad_identities'].values() if p['ref']=='E_C16');p['size_nm'][0]+=1
  with self.assertRaises(AssertionError):semantics(e,self.r)
 def test_unintended_group_merge_rejected(self):
  e=copy.deepcopy(self.e);gs=e['candidate']['groups'];gs[0]['members'].append(gs[1]['members'][0])
  with self.assertRaises(AssertionError):semantics(e,self.r)
if __name__=='__main__':unittest.main()
