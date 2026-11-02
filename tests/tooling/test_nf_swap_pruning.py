"""Guard vacated branch pruning against loss of retained pad connections."""
import unittest
from shapely.geometry import Point,LineString
from hardware.fabrication.nf_logic_swap_prepare import prune_leaves

def polygons(g):return [dict(outer=list(g.exterior.coords),holes=[])]
def pad(uid,xy):return dict(uuid=uid,ref=uid,pin='1',kind='PAD',net='/TEST',position_mm=xy,layers={'F.Cu':polygons(Point(xy).buffer(.25))})
def track(uid,a,b):return dict(uuid=uid,kind='PCB_TRACK',net='/TEST',position_mm=a,end_mm=b,width_mm=.2,layers={'F.Cu':polygons(LineString([a,b]).buffer(.1))})
def via(uid,xy):return dict(uuid=uid,kind='PCB_VIA',net='/TEST',position_mm=xy,layers={l:polygons(Point(xy).buffer(.3)) for l in ['F.Cu','B.Cu']})

class VacatedLeaves(unittest.TestCase):
    def prune(self,objects):return prune_leaves(dict(objects=objects,zones=[]),{'/TEST'})
    def test_vacated_two_segment_branch_prunes_to_retained_pad(self):
        kept,removed,_=self.prune([pad('p',(10,0)),track('a',(0,0),(5,0)),track('b',(5,0),(10,0))])
        self.assertEqual({o['uuid'] for o in kept},{'p'});self.assertEqual(len(removed),2)
    def test_interior_junction_retained_when_whole_segment_is_needed(self):
        objects=[pad('p',(10,0)),pad('q',(5,3)),track('a',(0,0),(10,0)),track('b',(5,0),(5,3))]
        kept,removed,_=self.prune(objects);self.assertEqual(len(removed),0);self.assertEqual(len(kept),4)
    def test_single_layer_via_is_retained_if_it_bridges_two_tracks(self):
        objects=[pad('p',(0,0)),pad('q',(10,0)),track('a',(0,0),(4.8,0)),track('b',(5.2,0),(10,0)),via('v',(5,0))]
        kept,removed,_=self.prune(objects);self.assertIn('v',{o['uuid'] for o in kept});self.assertFalse(removed)
    def test_copper_zone_net_cannot_be_pruned_with_signal_graph(self):
        with self.assertRaises(AssertionError):prune_leaves(dict(objects=[],zones=[dict(net='/TEST',keepout=False)]),{'/TEST'})

class ShortEndCapLeaves(VacatedLeaves):
    def prune(self,objects):
        from hardware.fabrication.nf_logic_swap_leaf_finish import prune_leaves as finish
        return finish(dict(objects=objects,zones=[]),{'/TEST'})
    def test_short_tip_does_not_survive_only_due_to_end_cap_overlap(self):
        kept,removed,_=self.prune([pad('p',(10,0)),track('tip',(-.09,0),(0,0)),track('branch',(0,0),(10,0))])
        self.assertEqual({o['uuid'] for o in kept},{'p'})
        self.assertEqual(len(removed),2)

if __name__=='__main__':unittest.main()
