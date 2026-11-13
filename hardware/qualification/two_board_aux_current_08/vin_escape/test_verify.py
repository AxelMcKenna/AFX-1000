import unittest,json
from shapely.geometry import box,Point
from .verify import verify,semantics,local_cutback,ground_contacts,H,SRC
class EscapeTests(unittest.TestCase):
 def test_main_mount_copper_rejected(self):
  from .verify import main_mount_check
  f=next(f for f in json.loads((H/'main-mount-keepouts.json').read_text())['features'] if f['properties']['board']=='power');x,y=f['properties']['center_mm'];ring=[[round((x+dx)*1e6),round((y+dy)*1e6)] for dx,dy in [(-.1,-.1),(.1,-.1),(.1,.1),(-.1,.1)]]
  with self.assertRaises(AssertionError):main_mount_check({'objects':[],'zones':[]},{'objects':[{'layers_nm':{'F.Cu':[{'outer':ring,'holes':[]}]}}]})
 def test_native_checkpoint(self):self.assertEqual(verify()['opens'],1944)
 def test_rejected_fill_side_effects_remain_rejected(self):
  from .verify import nmshape,shape,EXPECTED
  c=json.loads((SRC/'capture-01/capture.json').read_text());old={z['uuid']:z for z in c['zones']}
  for dirname in ['native-01','native-02']:
   g=json.loads((H/dirname/'geometry.json').read_text());vin=next(o for o in g['objects'] if o['kind']=='PCB_VIA' and o['net']=='/P_power_supply/VIN_IC');rejected=0
   for z in g['zones']:
    try:local_cutback(shape(old[z['uuid']]['polygons']),nmshape(z['polygons_nm']),nmshape(vin['layers_nm'][z['layer']]))
    except AssertionError:rejected+=1
   self.assertGreater(rejected,0)
 def test_return_gate_cannot_relax(self):
  p=json.loads((H/'plan.json').read_text());c=json.loads((SRC/'capture-01/capture.json').read_text());p['new_vias'][1]['position_mm']=[200,120]
  with self.assertRaises(AssertionError):semantics(p,c)
 def test_nonlocal_fill_removal_rejected(self):
  old=box(0,0,10,10);new=old.difference(box(8,8,9,9))
  with self.assertRaises(AssertionError):local_cutback(old,new,Point(1,1).buffer(.3))
 def test_added_fill_rejected(self):
  with self.assertRaises(AssertionError):local_cutback(box(0,0,10,10),box(0,0,11,10),Point(1,1).buffer(.3))
 def test_partial_contact_loss_rejected(self):
  old=box(0,0,10,10);new=old.difference(box(4.5,4,5.5,5));c={'objects':[{'net':'PWR_AGND','uuid':'return','layers':{'In1.Cu':[{'outer':[[4,4],[5,4],[5,5],[4,5]],'holes':[]}]}}]}
  with self.assertRaises(AssertionError):ground_contacts(old,new,c,'In1.Cu')
if __name__=='__main__':unittest.main()
