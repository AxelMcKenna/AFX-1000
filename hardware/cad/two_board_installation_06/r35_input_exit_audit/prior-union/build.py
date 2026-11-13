"""Bound an initial vertical wire exit before crossing the holder-base plane."""
import hashlib,json,math,re,shutil
from pathlib import Path
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
inventory=json.loads((B/'r19_panel_inventory/inventory.json').read_text())
start_z=27.04;plane=33.21;thickness=.01;bend=12
radius=bend-math.sqrt(bend*bend-(plane+thickness-start_z)**2)
records=[];scad=['use <../r21_adjacent_signals/control_obstacles.scad>','part="auto_remaining";','$fn=128;']
for target,ident in [('button_tap:1','tap'),('button_auto:1','auto')]:
 e=next(e for e in inventory['wires'] if e['target']==target)
 source=e['source_xy_mm']+[start_z];w=Wire(source);w.arc([0,0,1],[0,1,0],bend,90)
 records.append({'id':ident,'source':e['source'],'target':target,'net':e['net'],'source_mm':source,'reachable_disk_radius_mm':radius})
 scad.append('module '+ident+'_reachable(){translate('+json.dumps(source[:2]+[plane])+')cylinder(r='+repr(radius/math.cos(math.pi/128))+',h=.01,$fn=128);}')
 scad.append('module '+ident+'_trial(){')
 for a,b in zip(w.points,w.points[1:]):scad.append('hull(){translate('+json.dumps(a.tolist())+')rotate([11,7,3])sphere(r=.6,$fn=24);translate('+json.dumps(b.tolist())+')rotate([11,7,3])sphere(r=.6,$fn=24);}')
 scad.append('}')
 scad.append('if(part=="'+ident+'_positive")'+ident+'_reachable();')
 scad.append('if(part=="'+ident+'_remaining")difference(){'+ident+'_reachable();adjacent_controls_mechanisms();}')
 scad.append('if(part=="'+ident+'_trial_collision")intersection(){'+ident+'_trial();adjacent_controls_obstacles();}')
(H/'probe.scad').write_text('\n'.join(scad)+'\n')
report={'status':'UNVERIFIED_INITIAL_EXIT_BOUND','initial_tangent':[0,0,1],'source_z_mm':start_z,'minimum_curvature_radius_mm':bend,'test_plane_z_mm':plane,'test_slice_top_z_mm':plane+thickness,'reachable_disk_radius_mm':radius,'rows':records,'assumptions':['Vertical initial exit at frozen project receiving source datum','Curvature magnitude at most1/12 per mm','Wire must reach target beyond this sub-plane reachable disk; fixed remote target cannot terminate inside it'],'bound':'For height h<R before the first crossing, maximum horizontal displacement is R-sqrt(R^2-h^2). The extremal curve uses maximum curvature in one plane from the start. A straight continuation at smaller angle cannot increase this bound; non-planar heading changes cannot increase horizontal norm.','selected_source_changed':False,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),B/'r19_panel_inventory/inventory.json',B/'r10_interfaces/mate-envelopes.json',B/'r13_formed_ground/exit-contract.json',R/'hardware/cad/two_board_print_01/housing.scad',R/'hardware/cad/a11/controls.scad',R/'hardware/cad/a11/generated/button-fixture.scad']}}
(H/'bound.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(records))
