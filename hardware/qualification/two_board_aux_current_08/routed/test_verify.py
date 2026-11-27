import unittest,json,copy
from .verify import HERE,audit_groups,uid
class NativeConnectivityTests(unittest.TestCase):
 def setUp(self):
  self.report=json.loads((HERE/'native-04/review.json').read_text());self.plan=json.loads((HERE/'plan.json').read_text())
 def test_all_original_groups_and_local_paths(self):self.assertEqual(audit_groups(self.report,self.plan),2674)
 def test_unrelated_original_group_merge_rejected(self):
  groups=self.report['after_groups'];old={u for g in self.report['before_groups'] for u in g['members']};indices=[i for i,g in enumerate(groups) if old.intersection(g['members'])];i,j=indices[:2];groups[i]['members']+=groups[j]['members'];groups.pop(j)
  with self.assertRaisesRegex(AssertionError,'connectivity delta'):audit_groups(self.report,self.plan)
 def test_ground_via_lost_plane_contact_rejected(self):
  u=uid('via:'+self.plan['new_vias'][0]['name']);g=next(g for g in self.report['after_groups'] if u in g['members']);g['members'].remove(u);self.report['after_groups'].append({'net':'PWR_AGND','members':[u]})
  with self.assertRaisesRegex(AssertionError,'main-ground contact'):audit_groups(self.report,self.plan)
if __name__=='__main__':unittest.main()
