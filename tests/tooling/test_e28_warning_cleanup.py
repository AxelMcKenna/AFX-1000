"""Reject removal of a local bridge, including hidden drill/layer breaks."""
import unittest
from shapely.geometry import Point,LineString,box
from hardware.fabrication.e28_warning_cleanup import LocalCopper,contact_components

def polys(g):return [dict(outer=list(g.exterior.coords),holes=[])]
def track(uid,start,end,width=.2):
    return dict(uuid=uid,net='/TEST',kind='PCB_TRACK',position_mm=start,end_mm=end,width_mm=width,
                layers={'F.Cu':polys(LineString([start,end]).buffer(width/2))})
def pad(uid,xy,drill=0):
    return dict(uuid=uid,ref=uid,pin='1',net='/TEST',kind='PAD',position_mm=xy,
                drill_mm=[drill,drill],npth=bool(drill),layers={'F.Cu':polys(Point(xy).buffer(.25))})
def via(uid,xy):
    return dict(uuid=uid,net='/TEST',kind='PCB_VIA',position_mm=xy,
                layers={l:polys(Point(xy).buffer(.3)) for l in ['F.Cu','B.Cu']})

class LocalDeletion(unittest.TestCase):
    def screen(self,objects,zones=()):
        board=['kicad_pcb']+[['via',['uuid',o['uuid']],['drill',.3]] for o in objects if o['kind']=='PCB_VIA']
        return LocalCopper(dict(objects=objects,zones=zones),board,{'/TEST'})
    def test_via_bridging_two_same_layer_tracks_is_retained(self):
        s=self.screen([track('a',(-1,0),(-.2,0)),track('b',(.2,0),(1,0)),via('v',(0,0))])
        r=s.review('v',set());self.assertFalse(r['safe']);self.assertEqual(r['local_contact_components'],2)
    def test_single_layer_leaf_via_can_be_removed(self):
        s=self.screen([track('a',(-1,0),(0,0)),via('v',(0,0))])
        self.assertTrue(s.review('v',set())['safe'])
    def test_parallel_tracks_cannot_circularly_justify_both_deletions(self):
        s=self.screen([pad('p',(-1,0)),pad('q',(1,0)),track('a',(-1,0),(1,0)),track('b',(-1,0),(1,0))])
        self.assertTrue(s.review('a',set())['safe'])
        self.assertFalse(s.review('b',{'a'})['safe'])
    def test_two_zone_islands_are_not_a_common_contact(self):
        z=dict(uuid='zone',net='/TEST',layer='F.Cu',keepout=False,
               polygons=polys(box(-2,-1,-.2,1))+polys(box(.2,-1,2,1)))
        s=self.screen([track('a',(-1,0),(1,0))],[z])
        self.assertFalse(s.review('a',set())['safe'])
    def test_remaining_drill_breaks_apparent_copper_bridge(self):
        hole=pad('hole',(0,0),.6);hole['net']='';hole['layers']={}
        s=self.screen([track('a',(-1,0),(1,0)),track('b',(-1,0),(1,0)),hole])
        self.assertFalse(s.review('a',set())['safe'])
    def test_different_layers_do_not_connect_through_projection(self):
        nodes=[('a','F.Cu',False,box(0,0,1,1)),('b','B.Cu',False,box(0,0,1,1))]
        self.assertEqual(contact_components(nodes,{0,1})[0],2)
    def test_actual_plated_object_connects_layers(self):
        nodes=[('v','F.Cu',True,box(0,0,1,1)),('v','B.Cu',True,box(0,0,1,1))]
        self.assertEqual(contact_components(nodes,{0,1})[0],1)
    def test_unplated_same_id_cannot_connect_layers(self):
        nodes=[('z','F.Cu',False,box(0,0,1,1)),('z','B.Cu',False,box(0,0,1,1))]
        self.assertEqual(contact_components(nodes,{0,1})[0],2)

if __name__=='__main__':unittest.main()
