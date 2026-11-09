import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import copy,json,math
from pathlib import Path
from shapely.geometry import box,Point
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import first,children,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop
from hardware.fabrication.route_two_board_buck_cell import position,angle,transform_object,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-digital-reference-native-02'
c=json.loads((STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json').read_text())
board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')}
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
side_reconciliations=[]
for r in placement['parts']:
 if r['id'] in fps and r['side']!=first(fps[r['id']],'layer')[1][0]:
  assert r['id'].startswith(('P_R','P_C','E_R','E_C')) and not r['tails_relative_xy']
  b=r['body_relative_xy'];assert abs(b[0]+b[2])<1e-7 and abs(b[1]+b[3])<1e-7
  side_reconciliations.append(dict(ref=r['id'],old_side=r['side'],current_side=first(fps[r['id']],'layer')[1][0]))
  r['side']=first(fps[r['id']],'layer')[1][0]
records={r['id']:r for r in placement['parts']}
moving={'E_R103','E_R107','E_R111','E_R119','E_R108','E_R112','E_R120'};retire=set()
for o in c['objects']:
 if o.get('ref') in moving:assert len(c['all_groups'][o['group']])==1,o['ref']
fanout=json.loads(Path('/private/tmp/digital-startup-fanout.json').read_text());assert not fanout['deferred']
retire.update(fanout['retired_objects'])
from shapely.geometry import LineString
for idx,r in enumerate(fanout['routes']+fanout['fixed_routes']):
 g=LineString(r['path_mm']).buffer(r['width_mm']/2)
 c['objects'].append(dict(uuid='planned-track-'+str(idx),net=r['net'],kind='PCB_TRACK',position_mm=r['path_mm'][0],layers={r['layer']:[dict(outer=list(g.exterior.coords),holes=[])]}))
for idx,v in enumerate(fanout['vias']+fanout['extra_quiet_vias']+[dict(net='PWR_AGND',position_mm=fanout['relocated_star']['position_mm'])]):
 g=Point(v['position_mm']).buffer(.3);c['objects'].append(dict(uuid='planned-via-'+str(idx),net=v['net'],kind='PCB_VIA',position_mm=v['position_mm'],drill_mm=.3,layers={l:[dict(outer=list(g.exterior.coords),holes=[])] for l in c['copper_layers']}))
objects=[o for o in c['objects'] if o.get('ref') not in moving and o['uuid'] not in retire]
obstacles={'F':[],'B':[]}
for ref,f in fps.items():
 if ref in moving:continue
 for side in ['F','B']:
  try:obstacles[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
  except AssertionError:pass
 r=records.get(ref)
 if r:
  delta=angle(f)-r['angle'];x,y=position(f)
  mb=lambda b:translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
  obstacles[r['side']].append((ref,mb(r['body_relative_xy'])))
  if r['tails_relative_xy']:obstacles['B'].extend((ref,mb(b)) for b in r['tails_relative_xy'])
  for e in r['additional_planar_reserves']:obstacles[e['side']].append((ref,mb(e['bounds'])))
trees={s:STRtree([g for r,g in obs]) for s,obs in obstacles.items()};added=[];newobjects=[];moves={}
geo={l:[(o,shape(o['layers'][l])) for o in objects if o['layers'].get(l)] for l in c['copper_layers']};gt={l:STRtree([g for o,g in rows]) for l,rows in geo.items()}
holes=[(Point(o['position_mm']),(max(o['drill_mm']) if isinstance(o.get('drill_mm'),list) else o.get('drill_mm',0))/2) for o in objects if o.get('drill_mm') and (any(o['drill_mm']) if isinstance(o['drill_mm'],list) else True)]

def flip_layers(f):
 f=copy.deepcopy(f)
 def visit(n):
  if not isinstance(n,list):return
  for i,v in enumerate(n):
   if isinstance(v,list):visit(v)
   elif isinstance(v,str) and v.startswith(('F.','B.')):n[i]=('B.' if v.startswith('F.') else 'F.')+v[2:]
  if n and n[0]=='justify':
   n[:]=[v for v in n if v!='mirror']
 visit(f)
 return f

def trial(ref,xy,rot,flip=False):
 f=rotate_footprint(fps[ref],xy,rot)
 if flip:f=flip_layers(f)
 side=first(f,'layer')[1][0];g=box(*courtyard(f,side+'.CrtYd'));q=g.buffer(.3,join_style=2)
 if any(q.intersection(obstacles[side][int(i)][1]).area>1e-8 for i in trees[side].query(q)):return
 if any(s==side and q.intersection(h).area>1e-8 for s,h in added):return
 os=[transform_object(o,position(fps[ref]),xy,rot) for o in c['objects'] if o.get('ref')==ref]
 if flip:
  for o in os:o['layers']={('B.Cu' if l=='F.Cu' else 'F.Cu' if l=='B.Cu' else l):ps for l,ps in o['layers'].items()}
 for o in os:
  for l,ps in o['layers'].items():
   h=shape(ps)
   for i in gt[l].query(h.buffer(.211)):
    other,gg=geo[l][int(i)]
    if other['net']!=o['net'] and h.distance(gg)<.21-1e-7:return
   if any(h.distance(p)-r<.15 for p,r in holes):return
   for other in newobjects:
    if other['net']!=o['net'] and other['layers'].get(l) and h.distance(shape(other['layers'][l]))<.21:return
 return f,g,os


from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing
routing.SIGNAL_LAYERS=('F.Cu','B.Cu');screen=MountScreen(dict(c,objects=objects,zones=[]))
owner={'E_R103':'E_U15','E_R107':'E_U16','E_R111':'E_U17','E_R119':'E_U33','E_R108':'E_U16','E_R112':'E_U17','E_R120':'E_U33'}
local=json.loads((STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json').read_text());allowed={chip:set() for chip in owner.values()}
for chip,refs in [('E_U15',['E_R105','E_C43']),('E_U16',['E_R109','E_C45']),('E_U17',['E_R113','E_C47']),('E_U33',['E_R121','E_C51'])]:
 allowed[chip].update(o['uuid'] for o in objects if o.get('ref') in [chip,*refs] and o['net']=='PWR_AGND')
 for r in local['routes']:
  if r['net']=='PWR_AGND' and r.get('chip',r.get('ref'))==chip:allowed[chip].update(r['segment_uuids'])
 for q in local['quiet_ground_islands']:
  if q['ref']==chip:allowed[chip].add(q['star_via']['uuid'])
for i,r in enumerate(fanout['routes']+fanout['fixed_routes']):
 if r['net']=='PWR_AGND':allowed[r.get('chip',r.get('ref'))].add('planned-track-'+str(i))
for i,v in enumerate([dict(v,owner=r['ref']) for r,v in zip(fanout['routes'],fanout['vias'])]+fanout['extra_quiet_vias']+[dict(net='PWR_AGND',owner='E_U17',position_mm=fanout['relocated_star']['position_mm'])]):
 if v['net']=='PWR_AGND':allowed[v['owner']].add('planned-via-'+str(i))
accepted=[];allroutes=[]
def paths(ref,os,targets,allow_grid=False):
 chosen=[];chip=owner[ref];length_limit=24 if ref in {'E_R103','E_R107','E_R111','E_R119'} else 14
 localpads=[(o,l,shape(ps)) for o in [*newobjects,*os] for l,ps in o['layers'].items() if ps]
 routegeos=[(r,LineString(r['path_mm'])) for r in accepted]
 def legal(net,layer,ps):
  if not screen.legal(net,layer,ps):return False
  line=LineString(ps)
  for o,l,g in localpads:
   if l==layer and (o['net']!=net or net=='PWR_AGND' and owner.get(o.get('ref'))!=chip) and line.distance(g)<.31:return False
  for r,g in routegeos+[(r,LineString(r['path_mm'])) for r in chosen]:
   if r['layer']==layer and (r['net']!=net or net=='PWR_AGND' and r['owner']!=chip) and line.distance(g)<.41:return False
  if net=='PWR_AGND':
   for i in gt[layer].query(line.buffer(.311)):
    o,g=geo[layer][int(i)]
    if o['net']=='PWR_AGND' and o['uuid'] not in allowed[chip] and line.distance(g)<.31:return False
  return True
 for pin,ends in targets:
  o=next(o for o in os if o['pin']==pin);net=o['net'];opts=[]
  for end in ends:
   for ps in routing.candidate_paths(o['position_mm'],end):
    ps=[list(v) for i,v in enumerate(ps) if not i or list(v)!=list(ps[i-1])]
    if len(ps)>1 and LineString(ps).length<length_limit and legal(net,'B.Cu',ps):opts.append((LineString(ps).length,ps))
  if not opts and allow_grid:
   original=screen.legal;screen.legal=lambda n,l,ps:original(n,l,ps)
   # Use a separate bound-method wrapper so the custom legal check can still
   # call the original screen without recursively calling itself.
   from types import SimpleNamespace
   grid=SimpleNamespace(legal=legal)
   for end in sorted(ends,key=lambda v:math.dist(v,o['position_mm']))[:2]:
    ps=routing.Screen.grid_path(grid,net,'B.Cu',o['position_mm'],end,budget=10000)
    if ps and LineString(ps).length<length_limit:opts.append((LineString(ps).length,ps));break
   screen.legal=original
  if not opts:return
  length,ps=min(opts);chosen.append(dict(ref=ref,pin=pin,owner=chip,label=ref+'.'+pin,net=net,layer='B.Cu',width_mm=.2,path_mm=ps,length_mm=length))
 return chosen

from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
vscreen=ViaScreen(dict(c,objects=objects,zones=[]));extra_vias=[]
backquiet={z['ref']:shape(next(q['authored_outline'] for q in c['zones'] if q['uuid']==z['uuid'])) for z in json.loads((BASE/'digital-reference-routing.json').read_text())['new_zones'] if z['ref']!='main' and z['layer']=='In6.Cu'}
allground=[(o,shape(ps)) for o in objects if o['net']=='PWR_AGND' for ps in o['layers'].values() if ps];groundtree=STRtree([g for o,g in allground])
def local_return(ref,os,targets):
 if ref!='E_R112':return
 chip=owner[ref];pad=next(o for o in os if o['pin']=='2');x,y=pad['position_mm']
 signal=paths(ref,os,targets[:1])
 if not signal:return
 for d,xy in sorted((math.hypot(i*.2,j*.2),[round(x+i*.2,4),round(y+j*.2,4)]) for i in range(-12,13) for j in range(-12,13) if .6<=math.hypot(i*.2,j*.2)<=2.4):
  pt=Point(xy)
  if pt.distance(backquiet[chip])>2 or not vscreen.via_legal('PWR_AGND',xy):continue
  if any(allground[int(i)][0]['uuid'] not in allowed[chip] and pt.distance(allground[int(i)][1])<.51 for i in groundtree.query(pt.buffer(.511))):continue
  if any(pt.distance(shape(o['layers']['B.Cu']))<(.51 if o['net']!='PWR_AGND' or owner.get(o.get('ref'))!=chip else .31) for o in [*newobjects,*os]):continue
  if any((r['net']!='PWR_AGND' or r['owner']!=chip) and pt.distance(LineString(r['path_mm']))<.61 for r in [*accepted,*signal]):continue
  rr=paths(ref,os,[targets[0],('2',[xy])])
  if rr:return rr,dict(ref=ref,pin='2',owner=chip,net='PWR_AGND',position_mm=xy)


def choose(ref,pin):
 chip=owner[ref];anchor=next(v['position_mm'] for r,v in zip(fanout['routes'],fanout['vias']) if r['ref']==chip and r['pin']==pin)
 targets=[('1',[anchor])]
 if pin=='1':
  ends=[v['position_mm'] for r,v in zip(fanout['routes'],fanout['vias']) if r['ref']==chip and r['pin'] in ['2','4']]
  for obj in objects:
   if obj['uuid'] in allowed[chip] and obj['net']=='PWR_AGND' and obj['layers'].get('B.Cu'):
    ends.append(obj['position_mm'])
    if obj.get('end_mm'):ends.append(obj['end_mm'])
  targets.append(('2',[list(p) for p in sorted(set(tuple(p) for p in ends))]))
 radius=15 if pin=='3' else 10;steps=int(radius/.25)
 sites=sorted((math.hypot(ix*.25,iy*.25),[round(anchor[0]+ix*.25,4),round(anchor[1]+iy*.25,4)],rot) for ix in range(-steps,steps+1) for iy in range(-steps,steps+1) if math.hypot(ix*.25,iy*.25)<=radius for rot in [0,90,180,270])
 options=[];backup=[]
 for d,xy,rot in sites:
  t=trial(ref,xy,rot,False)
  if not t:continue
  f,g,os=t
  if any(o['net']!=r['net'] and shape(o['layers']['B.Cu']).distance(LineString(r['path_mm']))<.31 for o in os for r in accepted):continue
  backup.append((d,xy,rot,t));rr=paths(ref,os,targets);extra=None
  if rr is None and ref=='E_R112':
   local=local_return(ref,os,targets)
   if local:rr,extra=local
  if len(backup)%250==0:print('SEARCH',ref,'legal',len(backup),'radius',round(d,2),flush=True)
  if rr:options.append((sum(r['length_mm'] for r in rr),d,xy,rot,t,rr,extra))
  if len(options)>=12 or len(backup)>=6000:break
 if not options:
  for d,xy,rot,t in backup[::max(1,len(backup)//80)]:
   extra=None;rr=paths(ref,t[2],targets,True)
   if rr:options.append((sum(r['length_mm'] for r in rr),d,xy,rot,t,rr,extra))
 if not options:raise RuntimeError((ref,'no jointly placed and routed cell',len(backup)))
 score,d,xy,rot,(f,g,os),rr,extra=min(options,key=lambda x:x[:2]);added.append(('B',g));newobjects.extend(os);moves[ref]=[xy,rot,False];accepted.extend(rr);allroutes.extend(rr)
 Path('/private/tmp/digital-startup-partial-placement.json').write_text(json.dumps(dict(moves=moves,routes=allroutes),indent=2))
 if extra:
  extra_vias.append(extra);h=Point(extra['position_mm']).buffer(.3)
  newobjects.append(dict(uuid='extra-resistor-ground-'+ref,net='PWR_AGND',owner=chip,position_mm=extra['position_mm'],layers={l:[dict(outer=list(h.exterior.coords),holes=[])] for l in c['copper_layers']}))
 print('DONE',ref,xy,rot,'routes',[(r['pin'],round(r['length_mm'],3)) for r in rr],flush=True)
choose('E_R108','1')
seed=json.loads(Path('/private/tmp/startup-local-return-probe.json').read_text())[0]
ref='E_R112';xy=seed['xy'];rot=seed['rot'];t=trial(ref,xy,rot,False);assert t
f,g,os=t;v=seed['via'];h=Point(v['position_mm']).buffer(.3)
vobj=dict(ref=ref,pin='return-via',net='PWR_AGND',layers={'B.Cu':[dict(outer=list(h.exterior.coords),holes=[])]})
rr=paths(ref,[*os,vobj],[('2',[v['position_mm']]),('1',[[132.54,119.625]])],True);assert json.dumps(rr)==json.dumps(seed['routes'])
added.append(('B',g));newobjects.extend(os);moves[ref]=[xy,rot,False];accepted.extend(rr);allroutes.extend(rr);extra_vias.append(v)
newobjects.append(dict(uuid='extra-resistor-ground-'+ref,net='PWR_AGND',owner='E_U17',position_mm=v['position_mm'],layers={l:[dict(outer=list(h.exterior.coords),holes=[])] for l in c['copper_layers']}))
print('DONE',ref,xy,rot,'local quiet via',v['position_mm'],flush=True)
for ref,pin in [('E_R120','1'),('E_R111','3'),('E_R107','3'),('E_R103','3'),('E_R119','3')]:choose(ref,pin)
updated=dict(fps)
for ref,(xy,rot,flip) in moves.items():updated[ref]=rotate_footprint(fps[ref],xy,rot)
mechanical_check(updated,set(moves),placement)
Path('/private/tmp/digital-startup-placement.json').write_text(json.dumps(dict(moves=moves,retired_objects=sorted(retire),reconciled_existing_passive_sides=side_reconciliations),indent=2))
Path('/private/tmp/digital-startup-resistor-routes.json').write_text(json.dumps(dict(routes=allroutes,extra_quiet_vias=extra_vias,deferred=[]),indent=2))
