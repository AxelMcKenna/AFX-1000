import unittest,json,copy
from .identity import reconcile
from .verify import HERE
class AnonymousIdentityTests(unittest.TestCase):
 def setUp(self):
  self.snapshot=json.loads((HERE/'native-04/pad-identities.json').read_text());m=json.loads((HERE/'anonymous-pad-mapping.json').read_text());self.capture={'objects':[]}
  # Reconstitute only the frozen-capture fields used for identity matching.
  for r in m['mappings']:
   i=r['full_physical_identity'];self.capture['objects'].append({'uuid':r['capture_uuid'],'ref':i['ref'],'pin':i['pin'],'net':i['net'],'position_mm':[v/1e6 for v in i['position_nm']],'orientation_degrees':i['orientation_degrees'],'drill_mm':[v/1e6 for v in i['drill_nm']],'layers':{l:[{'outer':[[v/1e6 for v in xy] for xy in p['outer']],'holes':[[[v/1e6 for v in xy] for xy in ring] for ring in p['holes']]} for p in polys] for l,polys in i['copper_polygons_nm'].items()}})
 def test_original_mapping(self):self.assertEqual(len(reconcile(self.snapshot,self.capture)),55)
 def test_moved_pad_rejected(self):
  self.snapshot['candidate_relevant_pads'][0]['identity']['position_nm'][0]+=100000
  with self.assertRaisesRegex(AssertionError,'identity changed'):reconcile(self.snapshot,self.capture)
 def test_resized_pad_rejected(self):
  self.snapshot['candidate_relevant_pads'][0]['identity']['size_nm'][0]+=100000
  with self.assertRaisesRegex(AssertionError,'identity changed'):reconcile(self.snapshot,self.capture)
 def test_renetted_pad_rejected(self):
  self.snapshot['candidate_relevant_pads'][0]['identity']['net']='UNEXPECTED'
  with self.assertRaisesRegex(AssertionError,'identity changed'):reconcile(self.snapshot,self.capture)
 def test_duplicate_identity_rejected(self):
  row=copy.deepcopy(self.snapshot['candidate_relevant_pads'][0]);row['uuid']='unexpected';self.snapshot['candidate_relevant_pads'].append(row)
  with self.assertRaisesRegex(AssertionError,'duplicate pad identity'):reconcile(self.snapshot,self.capture)
if __name__=='__main__':unittest.main()
