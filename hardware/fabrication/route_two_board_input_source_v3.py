"""Repack input blocking FETs and connect bounded gate, source and local power paths."""
import copy,json
from shapely.geometry import Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box,LineString
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.route_two_board_buck_cell import position,angle,mechanical_check,transform_object
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape
out=STAGING/'two-board-power-input-source-03'
assert not out.exists()
base=STAGING/'two-board-power-input-controls-native-02'
cap=json.loads((STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json').read_text())
for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
board=read_sexpr((base/'power_protection.kicad_pcb').read_text())
retired={'7ccbf019-f9b4-5f49-9234-a61f13f15194','294f9064-c9b3-5dee-bee7-8da6bce741ac','0b425873-3654-5049-a179-ee4ed5ca8199'}
retired_objects=[o for o in cap['objects'] if o['uuid'] in retired]
assert len(retired_objects)==3 and all(o['kind']=='PCB_TRACK' and o['net']=='/P_power_supply/POWER_READY' and set(o['layers'])=={'B.Cu'} for o in retired_objects)
board[:]=[n for n in board if not(isinstance(n,list) and n and n[0]=='segment' and str(first(n,'uuid')[1]) in retired)]

old={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(old)
moves={'P_Q101':([190.7,116.5],270),'P_Q102':([190.7,110.9],180),'P_C103':([218.5,121],0),'G_NT1':([198.7,132.2],0),'P_C104':([202.2,122.4],0)}
for o in cap['objects']:
 if o.get('ref') in moves and o.get('pin'):assert cap['all_groups'][o['group']]==[o['uuid']]
for r,(xy,rot) in moves.items():fps[r]=rotate_footprint(old[r],xy,rot)
# C104 uses the identical retained C102 package as a native back-side template.
assert old['P_C104'][1]==old['P_C102'][1]
f=rotate_footprint(old['P_C102'],moves['P_C104'][0],0)
for key in ['Reference','Value','Datasheet']:
 if prop(old['P_C104'],key) is not None:prop(f,key)[2]=prop(old['P_C104'],key)[2]
first(f,'uuid')[:]=first(old['P_C104'],'uuid')
f[:]=[n for n in f if not(isinstance(n,list) and n and n[0]=='path')]
f.extend(copy.deepcopy(children(old['P_C104'],'path')))
pads0={str(p[1]):p for p in children(old['P_C104'],'pad')}
for p in children(f,'pad'):
 first(p,'uuid')[:]=first(pads0[str(p[1])],'uuid');first(p,'net')[:]=first(pads0[str(p[1])],'net')
fps['P_C104']=f

placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text());records={r['id']:r for r in placement['parts']}
for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']: records['P_C204'][k]=copy.deepcopy(records['P_C205'][k])
assert len(children(old['G_NT1'],'model'))==0
placement['parts'].append(dict(id='G_NT1',height_mm=0.0,side='F',angle=0,body_relative_xy=[-1.2,-.8,1.2,.8],additional_planar_reserves=[],tails_relative_xy=[]))
for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']:records['P_C104'][k]=copy.deepcopy(records['P_C102'][k])
mechanical_check(fps,set(moves),placement)
objects=[]
for o in cap['objects']:
 if o['uuid'] in retired:continue
 if o.get('ref')=='P_C104':
  template=next(q for q in cap['objects'] if q.get('ref')=='P_C102' and q.get('pin')==o.get('pin'))
  n=transform_object(template,position(old['P_C102']),moves['P_C104'][0],0)
  for key in ['ref','uuid','net','group']:n[key]=o[key]
  objects.append(n)
 else:objects.append(transform_object(o,position(old[o['ref']]),*moves[o['ref']]) if o.get('ref') in moves else o)

geoms=[(o,l,shape(ps)) for o in objects for l,ps in o['layers'].items() if ps]
trees={l:([(o,g) for o,k,g in geoms if k==l],STRtree([g for o,k,g in geoms if k==l])) for l in cap['copper_layers']}
for o,l,g in geoms:
 if o.get('ref') not in moves:continue
 rows,t=trees[l]
 for i in t.query(g.buffer(.211)):
  q,h=rows[int(i)]
  if q.get('ref')!=o['ref'] and q['net']!=o['net']:assert g.distance(h)>=.21-1e-7,(o['ref'],o.get('pin'),q.get('ref'),q.get('pin'),g.distance(h))
 for z in cap['zones']:
  if z['layer']==l:assert g.distance(shape(z['authored_outline']))>.21,(o['ref'],o.get('pin'),'old zone',z['uuid'])
# The generic receiver check does not screen a moved through-hole part's
# new lead tails. Independently include C103's opposite-face lead envelopes.
receivers={'F':[],'B':[]}
for ref,f in fps.items():
 for side in ['F','B']:
  try:receivers[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
  except AssertionError:pass
 r=records.get(ref)
 if r:
  delta=angle(f)-r['angle'];x,y=position(f)
  def env(b):return translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
  receivers[r['side']].append((ref,env(r['body_relative_xy'])))
  for e in r['additional_planar_reserves']:receivers[e['side']].append((ref,env(e['bounds'])))
  for b in r['tails_relative_xy']:receivers['B'].append((ref,env(b)))
for ref in moves:
 r=records.get(ref)
 if not r:continue
 x,y=position(fps[ref]);delta=angle(fps[ref])-r['angle']
 for b in r['tails_relative_xy']:
  g=translate(rotate(box(*b),-delta,origin=(0,0)),x,y).buffer(.3,join_style=2)
  assert all(other==ref or g.intersection(h).area<1e-8 for other,h in receivers['B']),(ref,'opposite-face lead reserve')
outline=shape(cap['outline']).buffer(-.5)
mounts=[(Point(o['position_mm']),max(3.6,max(o['drill_mm'])/2+.5)) for o in objects
        if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
holes=[]
for o in objects:
 d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
 if radius:holes.append((o,Point(o['position_mm']),radius))
minimum_drill_gap=1e9
for ref in moves:
 f=fps[ref];g=box(*courtyard(f,first(f,'layer')[1][0]+'.CrtYd'))
 assert outline.covers(g)
 assert all(g.distance(p)>=radius+.3 for p,radius in mounts)
for o,l,g in geoms:
 if o.get('ref') not in moves:continue
 assert outline.covers(g)
 for h,p,r in holes:
  if o.get('ref')==h.get('ref'):continue
  gap=g.distance(p)-r
  assert gap>=.15-2e-6,(o.get('ref'),h.get('ref'),gap)
  minimum_drill_gap=min(minimum_drill_gap,gap)
for o,p,r in holes:
 if o.get('ref') not in moves:continue
 for q,l,g in geoms:
  if q.get('ref')==o.get('ref') or q['kind']!='PAD' or any(q['drill_mm']):continue
  assert g.distance(p)-r>=.15-2e-6,(o.get('ref'),q.get('ref'))
 for q,pos,radius in holes:
  if q['uuid']==o['uuid']:continue
  assert p.distance(pos)-r-radius>=.25-2e-6,(o.get('ref'),q.get('ref'))
def pad(ref,pin):return next(o for o in objects if o.get('ref')==ref and o.get('pin')==pin)
pairs=[(('P_Q102','3'),('P_Q101','4')),(('P_Q102','2'),('P_Q101','3')),
       (('P_Q102','1'),('P_U101','4')),(('P_Q101','5'),('P_U101','1')),
       (('P_C104','1'),('P_U101','18')),(('P_C103','1'),('P_U101','18'))]
distances=[dict(terminals=[a,b],straight_pad_center_distance_mm=Point(pad(*a)['position_mm']).distance(Point(pad(*b)['position_mm']))) for a,b in pairs]
# Construct only after the independent placement/drill screens above pass.
import shutil,uuid,math
from hardware.electronics.common.sexpr import a,sexpr
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
assert not out.exists()
for i,f in enumerate(board):
 if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in moves:board[i]=fps[prop(f,'Reference')[2]]
codes={str(n[2]):int(n[1]) for n in children(board,'net')}
routes=[];vias=[];added=[]
digest=sha(STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json')
def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPINPUTSOURCE03:'+digest+':'+label))
# Only these old planes may refill or change outline. Others must stay exact.
changed={z['uuid'] for z in cap['zones'] if z['uuid'] in ['d0572a8e-b95d-5c59-9a7c-1d3514a507b4','a147ef12-37f5-562e-9340-6c74b3790186','d41ab58e-16e9-5d76-8b14-dc335aff8371']}
assert len(changed)==3
routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2
screen=ViaScreen(dict(cap,objects=objects,zones=[]))
def via(label,net,xy):
 assert screen.via_legal(net,xy),(label,'via copper/drill screen')
 assert all(z['uuid'] in changed or Point(xy).distance(shape(z['authored_outline']))>.61 for z in cap['zones'])
 assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21-1e-7 for n,l,w,g in added)
 u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
 vias.append(dict(uuid=u,label=label,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
 screen.vias.append((net,xy))
 for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
def legal(net,layer,path,width):
 line=LineString(path)
 if not outline.buffer(-width/2-.01).covers(line):return False
 for z in cap['zones']:
  if z['uuid'] not in changed and z['layer']==layer and z['net']!=net and line.distance(shape(z['authored_outline']))<width/2+.21:return False
 rows,tree=trees[layer]
 for i in tree.query(line.buffer(width/2+.211)):
  o,g=rows[int(i)]
  if o['net']!=net and line.distance(g)<width/2+.21-1e-7:return False
 if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-7 for n,l,w,g in added):return False
 return all(line.distance(p)>=r+width/2+.01 for p,r in mounts)
def route(label,net,layer,path,width,limit):
 path=[p for i,p in enumerate(path) if not i or list(p)!=list(path[i-1])]
 assert len(path)>1 and legal(net,layer,path,width),(label,'copper screen')
 length=LineString(path).length;assert length<=limit,(label,length,limit)
 ids=[]
 for i,(p,q) in enumerate(zip(path,path[1:])):
  u=uid(label+str(i));ids.append(u);board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),u]])
 routes.append(dict(label=label,net=net,layer=layer,path_mm=path,width_mm=width,length_mm=length,maximum_length_mm=limit,segment_uuids=ids));added.append((net,layer,width,LineString(path)))
 print(label,round(length,4),flush=True)
def xy(ref,pin):return pad(ref,pin)['position_mm']
gate=pad('P_Q101','4')['net'];drv=pad('P_Q102','1')['net'];dc='PWR_DC_IN';ground='PWR_AGND';output='PWR_MODULE_FEED_IN';vin=pad('P_Q101','5')['net']
via('DRV-source',drv,[190.5,111.85]);via('DRV-receiver',drv,[192.6,122.2])
via('BGATE-source',gate,[187.9,113.83]);via('BGATE-receiver',gate,[192.6,121.2])
via('output-ceramic-ground',ground,[205.5,122.4]);via('output-ceramic-feed',output,[200,120.5])
route('pulldown-gate',gate,'F.Cu',[xy('P_Q101','4'),xy('P_Q102','3')],.25,3.5)
route('pulldown-source',dc,'F.Cu',[xy('P_Q102','2'),[193,109.95],[193,113.44],xy('P_Q101','1')],.4,6)
route('DRV-source-escape',drv,'F.Cu',[xy('P_Q102','1'),[190.5,111.85]],.2,1.5)
route('DRV-inner',drv,'In2.Cu',[[190.5,111.85],[193.3,120.8],[193.3,122.2],[192.6,122.2]],.2,12)
route('DRV-receiver-escape',drv,'F.Cu',[[192.6,122.2],[192.6,122.8],[194.1,122.8],xy('P_U101','4')],.2,3)
route('BGATE-source-escape',gate,'F.Cu',[[187.9,113.83],xy('P_Q101','4')],.2,1)
route('BGATE-inner',gate,'In2.Cu',[[187.9,113.83],[192.6,121.2]],.2,10)
route('BGATE-receiver-escape',gate,'F.Cu',[[192.6,121.2],[193.4,121.2],[193.4,122.25],xy('P_U101','3')],.2,3.5)
route('output-bulk-force',output,'F.Cu',[[201,121.2],[202,120.5],[218.5,120.5],xy('P_C103','1')],2,20)
route('output-ceramic-return',ground,'B.Cu',[xy('P_C104','2'),[205.5,122.4]],.5,2)
route('output-ceramic-feed',output,'B.Cu',[xy('P_C104','1'),[200,120.5]],.5,3)
route('retained-PG-back-detour','/P_power_supply/POWER_READY','B.Cu',[[199.5,122.5],[199.5,124.3],[206.6,124.3],[206.6,125.8]],.2,11)
new_outlines={
 'a147ef12-37f5-562e-9340-6c74b3790186':[[195.1,120.8],[197.9,120.8],[197.9,122.25],[199.8,122.25],[199.8,123.5],[200,123.5],[200,130.2],[195.2,130.2],[195.2,127.9],[193.5,127.9],[193.5,122.3],[195.1,122.3]],
 'd41ab58e-16e9-5d76-8b14-dc335aff8371':[[193.5,118.8],[223,118.8],[223,124.4],[200,124.4],[200,130.2],[195.2,130.2],[195.2,127.9],[193.5,127.9]]}
changed_records=[]
for z in children(board,'zone'):
 u=str(first(z,'uuid')[1])
 if u not in changed:continue
 old_ring=[list(map(float,p[1:3])) for p in children(first(first(z,'polygon'),'pts'),'xy')]
 if u in new_outlines:first(first(z,'polygon'),'pts')[:]=[a('pts'),*[[a('xy'),*p] for p in new_outlines[u]]]
 z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
 changed_records.append(dict(uuid=u,old_outline_mm=old_ring,new_outline_mm=new_outlines.get(u,old_ring)))
zones=[]
def zone(label,net,layer,ring):
 from shapely.geometry import Polygon
 g=Polygon(ring);assert g.is_valid and outline.covers(g)
 assert all(g.distance(p)>=r+.3 for p,r in mounts)
 u=uid(label)
 board.append([a('zone'),[a('net'),codes[net]],[a('net_name'),net],[a('layer'),layer],[a('uuid'),u],
  [a('hatch'),a('edge'),.5],[a('connect_pads'),a('yes'),[a('clearance'),.2]],
  [a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],
  [a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],
  [a('polygon'),[a('pts'),*[[a('xy'),*p] for p in ring]]]])
 zones.append(dict(uuid=u,label=label,net=net,layer=layer,outline_mm=ring))
zone('source-pin-bank',dc,'F.Cu',[[189.5,112.6],[193.3,112.6],[193.3,114.85],[189.5,114.85]])
zone('blocking-FET-to-IN',vin,'F.Cu',[[188,115.1],[193.4,115.1],[193.4,118.5],[194.8,118.5],[194.8,122],[193.4,122],[193.4,120.4],[188,120.4]])
zone('OUT-to-ceramic',output,'F.Cu',[[198.2,120.3],[201.5,120.3],[201.5,123.2],[200.1,123.2],[200.1,121.95],[198.2,121.95]])
shutil.copytree(base,out,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md'))
(out/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
p=out/'power_protection.kicad_sch';s=read_sexpr(p.read_text());first(first(s,'title_block'),'rev')[1]='TBP28';p.write_text(sexpr(s)+'\n')
paths=[Path(__file__),base/'power_protection.kicad_pcb',base/'input-controls-audit.json',STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json',STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_nf_surface.py','route_two_board_power_layer_detours.py']],REPO/'hardware/electronics/output_stage/check_placement.py']
result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},moves=[dict(ref=r,old_xy=position(old[r]),new_xy=xy,rotation_added_degrees=rot,final_angle=angle(fps[r])) for r,(xy,rot) in moves.items()],
 routes=routes,vias=vias,zones=zones,changed_existing_zones=changed_records,
 all_retained_tracks_vias_unchanged=True,retired_tracks=retired_objects,all_pin_nets_values_packages_unchanged=True,flipped_footprint=dict(ref='P_C104',template='P_C102',old_side='F.Cu',new_side='B.Cu'),
 mechanical_and_moved_pad_drill_screen=True,minimum_moved_pad_to_other_drill_edge_mm=minimum_drill_gap,
 new_routes=sum(len(r['segment_uuids']) for r in routes),new_vias=len(vias),new_zones=len(zones),
 source_cable_and_IN_SYS_bypass_routing_complete=False,
 actual_stack_current_capacity_and_thermal_qualified=False,
 loaded_reverse_blocking_and_transients_qualified=False,
 native_validation_pending=True,fabrication_released=False)
(out/'input-source-routing.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(moved=len(moves),tracks=result['new_routes'],vias=len(vias),new_zones=len(zones))))
