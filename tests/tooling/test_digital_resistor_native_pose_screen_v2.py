import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from shapely.geometry import box
from hardware.fabrication.digital_resistor_native_pose_screen_v2 import candidates, polygons
import hardware.fabrication.route_nf_surface as surface


def footprint(ref, side, x=0, y=0, angle=0):
    return ['footprint','test',['layer',side+'.Cu'],['at',x,y,angle],
            ['property','Reference',ref],
            ['fp_rect',['start',-1.5,-.8],['end',1.5,.8],['layer',side+'.CrtYd']]]


class NativeResistorPoseTests(unittest.TestCase):
    def setUp(self):
        self.board=['kicad_pcb',footprint('R1','B',30,30)]
        self.pads=[dict(ref='R1',pin=str(i),uuid='pad'+str(i),net='n'+str(i),
                       kind='PAD',position_mm=[30+x,30],layers={'B.Cu':polygons(box(30+x-.3,29.7,30+x+.3,30.3))})
                   for i,x in [(1,-.8),(2,.8)]]
        self.cap=dict(objects=copy.deepcopy(self.pads),outline=polygons(box(0,0,114,60)))
        self.template=dict(ref='R1',side='F',angle=90,file='native-F-90.kicad_mod',
                           footprint=footprint('R1','F',angle=90),
                           pads=[dict(pin=str(i),uuid='pad'+str(i),net='n'+str(i),position_mm=[0,y],
                                      polygons=polygons(box(-.3,y-.3,.3,y+.3))) for i,y in [(1,.8),(2,-.8)]])
        self.fixed=[];self.drilled=[]

    def poses(self):
        with patch('hardware.fabrication.digital_resistor_native_pose_screen_v2.CloseMarginViaScreen',return_value=SimpleNamespace(drilled=self.drilled)):
            return candidates(self.cap,self.board,'R1',self.fixed,[30],[30],lambda p:0,[self.template])[0]

    def test_native_rotation_and_identity_survive_side_change(self):
        poses=self.poses();self.assertEqual(len(poses),1)
        p=poses[0];self.assertEqual(p['side'],'F');self.assertEqual(p['angle'],90)
        self.assertEqual(p['pads'][0]['position_mm'],[30,30.8])
        self.assertEqual(p['pads'][0]['uuid'],'pad1')
        self.assertEqual(set(p['pads'][0]['layers']),{'F.Cu'})
        self.assertEqual(self.cap['objects'],self.pads)

    def test_wrong_native_net_is_rejected(self):
        self.template['pads'][0]['net']='wrong'
        with self.assertRaises(AssertionError):self.poses()

    def test_courtyard_uses_destination_face(self):
        self.board.append(footprint('R2','B',30,30))
        self.assertEqual(len(self.poses()),1)
        self.board[-1]=footprint('R2','F',30,30)
        self.assertEqual(self.poses(),[])

    def test_opposite_face_through_hole_shadow_blocks(self):
        f=footprint('J1','B',30,30)
        f.append(['pad','1','thru_hole','circle',['at',0,0],['size',1,1]])
        self.board.append(f)
        self.assertEqual(self.poses(),[])

    def test_native_copper_uses_destination_face(self):
        obstacle=dict(net='foreign',layers={'B.Cu':polygons(box(29.7,30.5,30.3,31.1))})
        self.cap['objects'].append(obstacle)
        self.assertEqual(len(self.poses()),1)
        obstacle['layers']={'F.Cu':obstacle['layers']['B.Cu']}
        self.assertEqual(self.poses(),[])

    def test_planned_tracks_use_destination_face(self):
        self.fixed=[dict(net='foreign',runs=[('B.Cu',[[29,30.8],[31,30.8]])],new_vias_mm=[])]
        self.assertEqual(len(self.poses()),1)
        self.fixed[0]['runs'][0]=('F.Cu',[[29,30.8],[31,30.8]])
        self.assertEqual(self.poses(),[])

    def test_planned_via_blocks_both_faces(self):
        self.fixed=[dict(net='foreign',runs=[],new_vias_mm=[[30,30.8]])]
        self.assertEqual(self.poses(),[])

    def test_drill_to_smd_guard_applies_on_destination_face(self):
        self.drilled=[('n1',[30,30.8],.15,None)]
        self.assertEqual(self.poses(),[])


if __name__=='__main__':unittest.main()
