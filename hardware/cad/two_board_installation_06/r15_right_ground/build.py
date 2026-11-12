"""Formed scene/selector ground chain and explicit receiving splice location."""
from pathlib import Path
import json,math,hashlib,sys
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];BASE=HERE.parent
sys.path.insert(0,str(HERE))
from curves import Wire,unit
old=json.loads((BASE/'r12_ground/ground-routes.json').read_text());endpoints=old['endpoints_mm'].copy()
endpoints.update({'GROUND_SCENE:IN':[280.5,32,29.5],'GROUND_SCENE:OUT_A':[305.5,31,29.5],'GROUND_SCENE:OUT_B':[305.5,33,29.5]})
paths=[]
def add(a,b,w):
 assert np.linalg.norm(w.points[0]-endpoints[a])<1e-7
 assert np.linalg.norm(w.p-endpoints[b])<1e-7,(b,w.p,endpoints[b])
 paths.append({'id':'R'+str(len(paths)+1).zfill(2),'from':a,'to':b,'wire':'Alpha5853 26AWG7/34','points_mm':[p.tolist() for p in w.points],'primitives':w.primitives})
# Source16 escape matches the full-assembly-screened r13 choice.
a='D_J2002:16';b='button_scene_2:4';w=Wire(endpoints[a]);w.arc([0,0,1],[0,-1,0],12,90)
w.s_curve([0,-1,0],[0,0,-1],12,39.04-31.6)
w.arc([0,-1,0],[1,0,0],12,90);w.arc([1,0,0],[0,1,0],12,180)
offset=endpoints[b][1]-w.p[1];assert offset>0
w.s_curve([-1,0,0],[0,1,0],12,offset);w.line(endpoints[b]);add(a,b,w)
order=[(2,'4','3'),(1,'3','4'),(0,'4','3'),(5,'3','4'),(6,'4','3'),(7,'3','4'),(8,'4','3'),(9,'3','4'),(4,'4','3'),(3,'3','4')]
for previous,current in zip(order,order[1:]):
 a='button_scene_'+str(previous[0])+':'+previous[2];b='button_scene_'+str(current[0])+':'+current[1];w=Wire(endpoints[a])
 if previous[0]==9:
  T=unit(np.array(endpoints[b])-np.array(endpoints[a]));offset=2.4
  run=math.sqrt(4*12*offset-offset*offset);total=float(np.linalg.norm(np.array(endpoints[b])-np.array(endpoints[a])))
  w.s_curve(T,[0,0,1],12,offset)
  start=np.array(endpoints[a])+T*(total-run-12);start[2]=34;w.line(start)
  w.s_curve(T,[0,0,-1],12,offset);w.line(endpoints[b])
 else:w.line(endpoints[b])
 add(a,b,w)
a='button_scene_3:4';b='GROUND_SCENE:IN';w=Wire(endpoints[a]);delta=np.array(endpoints[b])-w.p;offset=float(np.linalg.norm(delta[1:]));w.s_curve([1,0,0],[0,delta[1],delta[2]],12,offset);w.line(endpoints[b]);add(a,b,w)
# Settings output makes a supported-in-principle loop with generous radius.
# It is a static formed path, not opening/service slack qualification.
a='GROUND_SCENE:OUT_A';b='settings:W2.1';w=Wire(endpoints[a]);R=13;center=w.p[:2]+[0,-R];V=np.array(endpoints[b][:2])-center
angle=(math.atan2(V[0],V[1])-math.acos(R/np.linalg.norm(V)))%(2*math.pi)
first=0;w.arc([1,0,0],[0,-1,0],R,math.degrees(angle));w.change_height(first,len(w.points)-1,4.5);w.line(endpoints[b]);add(a,b,w)
a='GROUND_SCENE:OUT_B';b='release:W3.1';w=Wire(endpoints[a]);w.arc([1,0,0],[0,1,0],12,90);w.s_curve([0,1,0],[.5,0,4.5],12,math.hypot(.5,4.5));w.line(endpoints[b]);add(a,b,w)
assert len(paths)==13
sources=[Path(__file__),HERE/'curves.py',BASE/'r12_ground/ground-routes.json',BASE/'r13_formed_ground/exit-contract.json',BASE/'r11_distribution/reference/panel-contract.json',BASE/'r11_distribution/reference/signal-netlist.xml']
out={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'root':'D_J2002:16','net':'LINK_AGND','order':[{'button':'scene_'+str(n),'incoming_terminal':i,'outgoing_terminal':o} for n,i,o in order],'endpoints_mm':{k:v for k,v in endpoints.items() if k in {p for e in paths for p in (e['from'],e['to'])}},'edges':paths,'splices':[{'id':'GROUND_SCENE','hardware':'TE34130','insulation':'TE505872P034','center_mm':[293,32,29.5],'axis':'X','length_mm':25,'diameter_mm':6.2,'supplier_envelope_verified':False}], 'wire_model_radius_mm':.6,'minimum_required_centerline_radius_mm':12,'replaces_splice_location':'r12 location [310,42,29.5] is not used. r15 moves only the ground splice to [293,32,29.5].','terminal_approach':'Wire paths stop at declared joint/connector receiving interfaces. Soldered stripped tails and actual connector emergence remain unqualified.','complete_harness':False,'support_retention_qualified':False,'service_slack_included':False,'fabrication_released':False}
(HERE/'right-routes.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['// Formed scene/selector receiving candidate; no fabrication release.','module right_segment(a,b){hull(){translate(a)sphere(r=.6,$fn=24);translate(b)sphere(r=.6,$fn=24);}}']
for e in paths:
 lines.append('module panel_ground_'+e['id']+'(){')
 for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('right_segment('+json.dumps(a)+','+json.dumps(b)+');')
 lines.append('}')
for group,rows in [('feed',paths[:1]),('links',paths[1:10]),('selector_wires',paths[10:]),('right_formed',paths)]:lines.append('module panel_ground_'+group+'(){'+''.join('panel_ground_'+e['id']+'();' for e in rows)+'}')
lines.append('module panel_ground_right_splice(){translate([280.5,32,29.5])rotate([0,90,0])cylinder(d=6.2,h=25,$fn=48);}')
(HERE/'right.scad').write_text('\n'.join(lines)+'\n');print('13 right wires;10 scene buttons,2 selector returns,1 receiving splice')
