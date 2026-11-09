import unittest
from shapely.geometry import Point,box
from hardware.fabrication.digital_native_route_cleanup import other_group_contacts,prune_single_face_vias

def polygons(g):return [dict(outer=list(g.exterior.coords),holes=[])]
def obj(uid,kind,group,point,face='B.Cu'):
    return dict(uuid=uid,kind=kind,group=group,net='signal',position_mm=point,layers={face:polygons(Point(point).buffer(.1))})

class CleanupTests(unittest.TestCase):
    def test_native_group_excludes_same_group_stub(self):
        source=obj('pad','PAD','isolated',[1,1]);stub=obj('stub','PCB_TRACK','isolated',[1,1]);stub['end_mm']=[2,1]
        target=obj('target','PAD','retained',[10,1])
        contacts=other_group_contacts(dict(objects=[source,stub,target]),source,['B.Cu'])
        self.assertEqual(contacts,{('B.Cu',(10,1))})
    def test_group_evidence_required(self):
        source=obj('pad','PAD',None,[1,1])
        with self.assertRaises(AssertionError):other_group_contacts(dict(objects=[source]),source,['B.Cu'])
    def test_same_face_join_does_not_need_via(self):
        route=dict(net='signal',runs=[('B.Cu',[(0,0),(1,0)]),('B.Cu',[(2,0),(1,0)])],new_vias_mm=[[1,0]])
        routes,removed=prune_single_face_vias(dict(objects=[]),[route])
        self.assertFalse(routes[0]['new_vias_mm']);self.assertEqual(len(removed),1)
        self.assertEqual(route['new_vias_mm'],[[1,0]])
    def test_real_layer_transition_keeps_via(self):
        route=dict(net='signal',runs=[('B.Cu',[(0,0),(1,0)]),('F.Cu',[(2,0),(1,0)])],new_vias_mm=[[1,0]])
        routes,removed=prune_single_face_vias(dict(objects=[]),[route])
        self.assertEqual(routes[0]['new_vias_mm'],[[1,0]]);self.assertFalse(removed)
    def test_touching_retained_other_layer_copper_keeps_via(self):
        route=dict(net='signal',runs=[('B.Cu',[(0,0),(1,0)])],new_vias_mm=[[1,0]])
        retained=obj('pad','PAD','retained',[1.2,0],'In3.Cu')
        routes,removed=prune_single_face_vias(dict(objects=[retained]),[route])
        self.assertEqual(routes[0]['new_vias_mm'],[[1,0]]);self.assertFalse(removed)
    def test_nearby_same_net_barrel_is_not_pruned(self):
        route=dict(net='signal',runs=[('B.Cu',[(0,0),(2,0)])],new_vias_mm=[[1,0],[1.58,0]])
        routes,removed=prune_single_face_vias(dict(objects=[]),[route])
        self.assertEqual(len(routes[0]['new_vias_mm']),2);self.assertFalse(removed)

if __name__=='__main__':unittest.main()
