"""Worst-case conditional H_NEW5 stack; preserve original nut pocket and feet."""
import json,hashlib,copy
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def calc(c):
 assert c['mount']=='H_NEW5'
 q=c['receiving_mm'];parts=c['supplier_mm'];lo=sum(q[k][0] for k in ['post_seat_z','pcb_thickness','tab_thickness'])+parts['washer_thickness'][0];hi=sum(q[k][1] for k in ['post_seat_z','pcb_thickness','tab_thickness'])+parts['washer_thickness'][1]
 tip=[lo-c['standard_derived_screw_length_mm'][1],hi-c['standard_derived_screw_length_mm'][0]];bottom=q['original_nut_roof_z'][0]-parts['nut_height'][1];protrusion=bottom-tip[1];full=protrusion-q['incomplete_screw_tip_max'];table=q['loaded_local_floor_to_table_min']+tip[0]
 assert full>=.19 and table>=1 and q['post_and_board_bore_min']>q['screw_major_max']+2*q['screw_radial_registration_max']
 return {'under_head_z_mm':[lo,hi],'tip_z_mm':tip,'minimum_nut_bottom_z_mm':bottom,'minimum_end_beyond_nut_mm':protrusion,'minimum_full_thread_beyond_nut_mm':full,'minimum_table_clearance_mm':table,'maximum_head_top_z_mm':hi+parts['head_height'][1],'minimum_shank_bore_radial_clearance_mm':(q['post_and_board_bore_min']-q['screw_major_max'])/2-q['screw_radial_registration_max']}
c={'status':'CONDITIONAL_SOURCED_STACK_NOT_SELECTED','mount':'H_NEW5','parts':{'screw':'Accu SSCF-M2-14-A2','washer':'Accu HPW-M2-A2-BL','nut':'Accu HPN-M2-A2'},'supplier_mm':{'washer_thickness':[.25,.35],'washer_OD':[4.7,5.0],'washer_ID':[2.2,2.34],'nut_AF':[3.82,4.0],'nut_height':[1.35,1.6],'head_diameter':[3.62,3.8],'head_height':[1.86,2.]},'standard_derived_screw_length_mm':[13.65,14.35],'standard_basis':'DIN912 js15, 10–18 mm ±0.35 from retained Unbrako engineering guide; confirm delivered screw conforms, supplier sheet states nominal14 only','receiving_mm':{'post_seat_z':[7.8,8.0],'pcb_thickness':[1.5,1.7],'tab_thickness':[2.9,3.1],'original_nut_roof_z':[1.7,1.9],'post_and_board_bore_min':2.35,'screw_major_max':2.0,'screw_radial_registration_max':.1,'incomplete_screw_tip_max':.4,'loaded_local_floor_to_table_min':6.0,'washer_counterbore_min':5.4},'replaces_original':{'only_mount':'H_NEW5','screw':'M2x10 proposed pan head','washer_thickness_nominal_mm':.5,'head_washer_reservation_mm':{'diameter':4.5,'z':[9.5,12.0]}},'nut_pocket_changed':False,'sensor_owned_mounts_changed':False,'physical_qualified':False,'receiving_basis':'All printed/PCB/placement/tip/loaded-clearance ranges are project acceptance conditions, not supplier guarantees. Original at-least6mm feet authority is preserved; actual compression, floor bow and placement must leave measured local clearance≥6mm.'}
c['budget']=calc(c);mutations=[]
for k in ['short_screw','low_feet','thick_washer','wrong_mount']:
 b=copy.deepcopy(c)
 if k=='short_screw':b['standard_derived_screw_length_mm']=[11.65,12.35]
 if k=='low_feet':b['receiving_mm']['loaded_local_floor_to_table_min']=1.5
 if k=='thick_washer':b['supplier_mm']['washer_thickness']=[.95,1.05]
 if k=='wrong_mount':b['mount']='D_H2'
 try:calc(b)
 except AssertionError:mutations.append(k)
 else:raise AssertionError(k)
c['mutations_rejected']=mutations
paths=[Path(__file__),H/'hardware.scad',H/'reference/SSCF-M2-14-A2.pdf',H.parent/'r26_touch_mount/sources/HPW-M2-A2-BL.pdf',H.parent/'r26_touch_mount/sources/HPN-M2-A2.pdf',H.parent/'r26_touch_mount/sources/unbrako-engguide.pdf',R/'hardware/cad/two_board_print_01/README.md',R/'hardware/cad/two_board_print_01/housing.scad',R/'hardware/cad/two_board_print_01/captured.scad']
c['source_sha256']={str(p.relative_to(R)):sha(p) for p in paths};(H/'hardware-budget.json').write_text(json.dumps(c,indent=2)+'\n');print(json.dumps(c['budget']))
