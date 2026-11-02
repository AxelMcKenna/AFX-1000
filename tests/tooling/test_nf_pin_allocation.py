"""Check that coordinated escapes cannot overlap foreign copper or holes."""
import unittest
from hardware.fabrication.nf_swap_pin_allocation import compatible,solve

def row(net,start,end,cost=1):return dict(net=net,point=end,runs=[('F.Cu',[start,end])],cost=cost)

class Allocation(unittest.TestCase):
    def test_crossing_foreign_traces_conflict(self):self.assertFalse(compatible(row('a',(0,0),(3,3)),row('b',(0,3),(3,0))))
    def test_close_via_holes_conflict_even_on_same_net(self):self.assertFalse(compatible(row('a',(0,0),(2,2)),row('a',(0,1),(2.5,2))))
    def test_identical_same_net_via_can_be_shared(self):self.assertTrue(compatible(row('a',(0,0),(2,2)),row('a',(0,1),(2,2))))
    def test_allocation_chooses_compatible_alternative(self):
        opts={'a':[row('a',(0,0),(3,3))],'b':[row('b',(0,3),(3,0)),row('b',(5,0),(5,3))]}
        result,_=solve(opts);self.assertEqual(result,{'a':0,'b':1})
    def test_impossible_allocation_not_claimed_as_complete(self):
        result,_=solve({'a':[row('a',(0,0),(3,3))],'b':[row('b',(0,3),(3,0))]});self.assertIsNone(result)

if __name__=='__main__':unittest.main()
