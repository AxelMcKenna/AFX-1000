"""Follow only an exposed warned branch, stopping at connected circuit copper."""
import unittest
from tests.tooling.test_e28_warning_cleanup import track,pad,via
from hardware.fabrication.e28_warning_cleanup import LocalCopper
from hardware.fabrication.e28_branch_cleanup import exposed,prune

class BranchCleanup(unittest.TestCase):
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

if __name__=='__main__':unittest.main()
