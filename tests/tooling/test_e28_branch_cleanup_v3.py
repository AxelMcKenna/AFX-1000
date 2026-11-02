"""Follow only an exposed warned branch, stopping at connected circuit copper."""
import unittest
from tests.tooling.test_e28_warning_cleanup import track,pad,via
from hardware.fabrication.e28_warning_cleanup import LocalCopper
from hardware.fabrication.e28_branch_cleanup_v3 import exposed,prune

class BranchCleanupV3(unittest.TestCase):
    def screen(self,objects):
        board=['kicad_pcb']+[['via',['uuid',o['uuid']],['drill',.3]] for o in objects if o['kind']=='PCB_VIA']
        return LocalCopper(dict(objects=objects,zones=[]),board,{'/TEST'})
    def test_cascade_stops_at_functional_t_junction(self):
        objects=[pad('p',(0,0)),pad('q',(4,0)),track('main',(0,0),(4,0)),track('stem',(2,0),(2,1)),track('tip',(2,1),(2,2))]
        removed,checks,_=prune(self.screen(objects),{'tip'})
        self.assertEqual(removed,{'tip','stem'});self.assertNotIn('main',removed)
    def test_unrelated_exposed_track_is_not_selected(self):
        objects=[pad('p',(0,0)),track('tip',(0,0),(1,0)),pad('q',(5,0)),track('other',(5,0),(6,0))]
        self.assertEqual(prune(self.screen(objects),{'tip'})[0],{'tip'})
    def test_free_endpoint_does_not_authorize_removing_a_bridge(self):
        objects=[pad('p',(0,0)),pad('q',(2,1)),track('main',(0,0),(4,0)),track('branch',(2,0),(2,1))]
        s=self.screen(objects);self.assertTrue(exposed(s,'main',set()))
        self.assertEqual(prune(s,{'main'})[0],set())
    def test_native_seed_cannot_remove_sole_via_bridge(self):
        objects=[track('a',(-1,0),(-.2,0)),track('b',(.2,0),(1,0)),via('v',(0,0))]
        self.assertEqual(prune(self.screen(objects),{'v'})[0],set())

    def test_short_cap_overlap_does_not_keep_a_single_contact_leaf(self):
        objects=[pad('p',(0,0)),track('stub',(0,0),(.2,0)),track('tip',(.2,0),(.3,0))]
        self.assertEqual(prune(self.screen(objects),{'tip'})[0],{'tip','stub'})

    def test_short_zigzag_caps_do_not_stop_centerline_leaf_following(self):
        objects=[pad('p',(0,0)),track('a',(0,0),(.25,0),.25),track('b',(.25,0),(.375,.125),.25),track('c',(.375,.125),(.5,.125),.25),track('tip',(.5,.125),(.625,.25),.25)]
        self.assertEqual(prune(self.screen(objects),{'tip'})[0],{'tip','a','b','c'})

if __name__=='__main__':unittest.main()
