import unittest
from hardware.fabrication.digital_joint_escape_packing import pack


def domains(n=3,count=2):
    return {str(i):dict(net=str(i),options=[dict(domain=i,value=j,point=[j,i],cost=j+1) for j in range(count)]) for i in range(n)}


class JointPackingTests(unittest.TestCase):
    def test_pairwise_nonempty_does_not_imply_a_joint_solution(self):
        # Three binary values cannot all differ, although each pair can.
        r=pack(domains(),predicate=lambda a,b:a['value']!=b['value'])
        self.assertEqual(list(r['pair_compatible_counts'].values()),[2,2,2])
        self.assertEqual(r['choices'],[])
        self.assertTrue(r['complete_enumeration'])

    def test_finds_all_global_solutions_and_preserves_domain_order(self):
        r=pack(domains(),predicate=lambda a,b:a['value']==b['value'])
        self.assertEqual([v['indices'] for v in r['choices']],[[0,0,0],[1,1,1]])
        self.assertEqual([v['cost'] for v in r['choices']],[3,6])
        self.assertTrue(r['complete_enumeration'])

    def test_bounded_search_does_not_claim_exhaustion(self):
        r=pack(domains(),limit=1,predicate=lambda a,b:True)
        self.assertEqual(len(r['choices']),1)
        self.assertFalse(r['complete_enumeration'])

    def test_empty_domain_has_no_solution(self):
        d=domains();d['1']['options']=[]
        self.assertEqual(pack(d,predicate=lambda a,b:True)['choices'],[])

    def test_spatial_duplicate_packs_are_collapsed(self):
        d=domains(n=2)
        for v in d.values():v['options'][1]['point']=v['options'][0]['point']
        r=pack(d,predicate=lambda a,b:True)
        self.assertEqual(len(r['choices']),1)
        self.assertTrue(r['complete_enumeration'])

    def test_real_geometry_rejects_shared_through_via(self):
        d={n:dict(net=n,options=[dict(point=[1,1],vias=[[1,1]],runs=[],cost=1)]) for n in ('a','b')}
        self.assertEqual(pack(d)['choices'],[])

    def test_rejects_duplicate_net_domains(self):
        d=domains();d['1']['net']='0'
        with self.assertRaises(AssertionError):pack(d)


if __name__=='__main__':unittest.main()
