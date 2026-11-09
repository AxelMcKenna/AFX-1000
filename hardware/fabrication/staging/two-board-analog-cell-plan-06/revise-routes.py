import sys,time,heapq
from pathlib import Path

sys.path.insert(0,str(Path.cwd()))
import json, math
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
import hardware.fabrication.route_nf_surface as routing
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
from hardware.fabrication.integrate_two_board_signal import STAGING
c=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text())
from hardware.electronics.common.sexpr import children,read_sexpr
from hardware.fabrication.integrate_two_board_signal import prop
from hardware.fabrication.route_two_board_buck_cell import transform_object,position
pl=json.loads((STAGING/'two-board-analog-cell-plan-06/placement.json').read_text());moving=set(pl['moves']);retire=set(pl['retired_objects'])
fps={prop(f,'Reference')[2]:f for f in children(read_sexpr((STAGING/'two-board-power-permission-native-04/power_protection.kicad_pcb').read_text()),'footprint')}
retire.update(['060da70b-0be4-5c1a-8b25-362a41dd9b31','22f270f5-732b-5f2b-a335-03c0f93aa129','48d8f331-7c64-5ba4-acc2-d912cba60c61','e9b04eb9-c729-5b23-9527-58294bdd7768','08450e2a-310e-5fa3-8197-9f54febbc0c7'])
objects=[]
for o in c['objects']:
 if o['uuid'] in retire:continue
 if o.get('ref') in moving:
  xy,rot,flip=pl['moves'][o['ref']];o=transform_object(o,position(fps[o['ref']]),xy,rot)
  if flip:o['layers']={('B.Cu' if l=='F.Cu' else 'F.Cu' if l=='B.Cu' else l):ps for l,ps in o['layers'].items()}
 objects.append(o)
c['objects']=objects
routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
screen=ViaScreen(dict(c,zones=[]))
rows={l:[(o,routing.shape(o['layers'][l])) for o in c['objects'] if o['layers'].get(l)] for l in c['copper_layers']}
trees={l:STRtree([g for o,g in r]) for l,r in rows.items()};added=[];routes=[];vias=[]
def legal(net,layer,points,width):
 line=LineString(points)
 if not screen.via_outline.buffer(.3-width/2).covers(line):return False
 for i in trees[layer].query(line.buffer(width/2+.211)):
  o,g=rows[layer][int(i)]
  if (o['net']!=net or (net=='PWR_AGND' and o['uuid'] not in allowed[owner])) and line.distance(g)<width/2+.21-1e-8:return False
 if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-8 for n,l,w,g in added):return False
 if net=='PWR_AGND':
  for r,v in zip(routes,vias):
   if r['net']=='PWR_AGND' and r['owner']!=owner:
    if line.distance(Point(v['position_mm']))<width/2+.51:return False
    if r['layer']==layer and line.distance(LineString(r['path_mm']))<width/2+r['width_mm']/2+.21:return False
 return True

def candidates(ref,pin,limit=16,width=.2):
 o=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin);net=o['net'];layer=next(iter(o['layers']));x,y=o['position_mm']
 sites=sorted((math.hypot(i*.2,j*.2),[round(x+i*.2,4),round(y+j*.2,4)]) for i in range(-20,21) for j in range(-20,21))
 candidates=[]
 for d,xy in sites:
  if d<.5 or d>4:continue
  if not via_ok(net,xy):continue
  if any(n!=net and Point(xy).distance(g)<.3+w/2+.21 for n,l,w,g in added):continue
  paths=[]
  for ps in routing.candidate_paths([x,y],xy):
   ps=[p for i,p in enumerate(ps) if not i or list(p)!=list(ps[i-1])]
   if len(ps)<2:continue
   ln=LineString(ps).length
   if ln<=5 and legal(net,layer,ps,width):paths.append((ln,ps))
  if paths:
   length,ps=min(paths,key=lambda a:a[0]);candidates.append((length,dict(ref=ref,pin=pin,owner=owner,net=net,layer=layer,width_mm=width,path_mm=ps),dict(net=net,position_mm=xy)))
  if len(candidates)>=limit:break

 if not candidates:
  origin=(x,y);queue=[(0.,(0,0))];cost={(0,0):0.};parent={};edgecache={};visits=0
  xyof=lambda k:[round(x+k[0]*.1,4),round(y+k[1]*.1,4)]
  def edge(a,b):
   key=tuple(sorted((a,b)))
   if key not in edgecache:edgecache[key]=legal(net,layer,[xyof(a),xyof(b)],width)
   return edgecache[key]
  while queue and visits<6000:
   dist,key=heapq.heappop(queue)
   if dist>cost[key]+1e-9:continue
   if dist>6:break
   visits+=1;xy=xyof(key)
   if dist>.6 and key[0]%2==0 and key[1]%2==0 and via_ok(net,xy) and not any(n!=net and Point(xy).distance(g)<.3+w/2+.21 for n,l,w,g in added):
    chain=[key]
    while chain[-1]!=(0,0):chain.append(parent[chain[-1]])
    points=[xyof(k) for k in reversed(chain)];simple=[points[0]];i=0
    while i<len(points)-1:
     j=len(points)-1
     while j>i+1 and not legal(net,layer,[points[i],points[j]],width):j-=1
     simple.append(points[j]);i=j
    length=LineString(simple).length
    candidates.append((length,dict(ref=ref,pin=pin,owner=owner,net=net,layer=layer,width_mm=width,path_mm=simple),dict(net=net,position_mm=xy)))
    if len(candidates)>=limit:break
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
    k=(key[0]+dx,key[1]+dy);d=dist+.1*math.hypot(dx,dy)
    if d>=cost.get(k,1e9)-1e-9 or not edge(key,k):continue
    cost[k]=d;parent[k]=key;heapq.heappush(queue,(d,k))
 return sorted(candidates,key=lambda a:a[0])
def push(r,v):
 routes.append(r);vias.append(v);screen.vias.append((v['net'],v['position_mm']))
 added.append((r['net'],r['layer'],r['width_mm'],LineString(r['path_mm'])))
 for l in c['copper_layers']:added.append((v['net'],l,.6,Point(v['position_mm'])))
def pop():
 routes.pop();vias.pop();screen.vias.pop();del added[-(1+len(c['copper_layers'])):]
def cell(ref,pins):
 if not pins:return True
 choices=candidates(ref,pins[0],16 if len(pins)>1 else 1)
 for length,r,v in choices:
  push(r,v)
  if cell(ref,pins[1:]):return True
  pop()
 return False


seed=json.loads((STAGING/'two-board-analog-cell-plan-02/seed.json').read_text())
allowed={chip:{o['uuid'] for o in c['objects'] if o.get('ref') in [chip,ilm,dvdt,cap,pulldown] and o['net']=='PWR_AGND'} for chip,ilm,dvdt,cap,pulldown in seed['cells']}
grounds=[(o['uuid'],routing.shape(ps)) for o in c['objects'] if o['net']=='PWR_AGND' for ps in o['layers'].values() if ps]
gtree=STRtree([g for u,g in grounds])
def via_ok(net,xy):
 if not screen.via_legal(net,xy):return False
 if net=='PWR_AGND':
  pt=Point(xy)
  if any(grounds[int(i)][0] not in allowed[owner] and pt.distance(grounds[int(i)][1])<.51 for i in gtree.query(pt.buffer(.511))):return False
  if any(r['net']==net and r['owner']!=owner and math.dist(xy,v['position_mm'])<.81 for r,v in zip(routes,vias)):return False
 return True

import heapq,itertools
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.prepared import prep
full=json.loads((STAGING/'two-board-analog-cell-plan-06/fixed.json').read_text())
assert not full['deferred']
for r,v in zip(full['routes'],full['vias']):
 owner=r['owner'];assert via_ok(v['net'],v['position_mm']);assert legal(r['net'],r['layer'],r['path_mm'],r['width_mm']);push(r,v)
connections=[];deferred=[]
pad=lambda r,p:next(o for o in c['objects'] if o.get('ref')==r and o.get('pin')==p)
baselegal=legal
def legal(net,layer,points,width):
 if not baselegal(net,layer,points,width):return False
 if net=='PWR_AGND':
  line=LineString(points)
  for r in connections:
   if r['net']==net and r['owner']!=owner and r['layer']==layer and line.distance(LineString(r['path_mm']))<width/2+r['width_mm']/2+.21:return False
 return True

def grid(net,layer,start,end,limit):
 for step in [.2,.1]:
  bounds=box(min(start[0],end[0])-8,min(start[1],end[1])-8,max(start[0],end[0])+8,max(start[1],end[1])+8)
  obs=[]
  for o,g in rows[layer]:
   if (o['net']!=net or (net=='PWR_AGND' and o['uuid'] not in allowed[owner])) and g.intersects(bounds.buffer(.31)):obs.append(g.buffer(.310001))
  for n,l,w,g in added:
   if n!=net and l==layer and g.intersects(bounds.buffer(.7)):obs.append(g.buffer(w/2+.310001))
  if net=='PWR_AGND':
   for r,v in zip(routes,vias):
    if r['net']==net and r['owner']!=owner:
     obs.append(Point(v['position_mm']).buffer(.610001))
     if r['layer']==layer:obs.append(LineString(r['path_mm']).buffer(r['width_mm']/2+.310001))
   for r in connections:
    if r['net']==net and r['owner']!=owner and r['layer']==layer:obs.append(LineString(r['path_mm']).buffer(r['width_mm']/2+.310001))
  if layer=='In6.Cu' and net=='/E_rail_disconnect/ANA_PG0':obs.append(protected_back.buffer(.310001))
  free=bounds.intersection(screen.via_outline.buffer(.2)).difference(unary_union(obs));pr=prep(free)
  # Each node is relative to the exact source pad; endpoint connection is checked separately.
  xy=lambda k:[round(start[0]+k[0]*step,6),round(start[1]+k[1]*step,6)]
  queue=[(math.dist(start,end),0.,(0,0))];cost={(0,0):0.};parent={};cached={};goal=None;visits=0
  while queue and visits<22000:
   _,dist,k=heapq.heappop(queue)
   if dist>cost[k]+1e-8:continue
   visits+=1;p=xy(k)
   if math.dist(p,end)<step*2 and legal(net,layer,[p,end],.2):goal=k;break
   for dx,dy in itertools.product([-1,0,1],repeat=2):
    if not(dx or dy):continue
    j=(k[0]+dx,k[1]+dy);new=dist+step*math.hypot(dx,dy)
    if new>=cost.get(j,math.inf)-1e-8 or new+math.dist(xy(j),end)>limit:continue
    key=tuple(sorted([k,j]))
    if key not in cached:cached[key]=pr.covers(LineString([p,xy(j)]))
    if not cached[key]:continue
    cost[j]=new;parent[j]=k;heapq.heappush(queue,(new+math.dist(xy(j),end),new,j))
  if goal is None:continue
  chain=[goal]
  while chain[-1]!=(0,0):chain.append(parent[chain[-1]])
  points=[xy(k) for k in reversed(chain)]+[end];points=[p for i,p in enumerate(points) if not i or math.dist(p,points[i-1])>1e-8]
  simple=[points[0]];i=0
  while i<len(points)-1:
   j=len(points)-1
   while j>i+1 and not legal(net,layer,[points[i],points[j]],.2):j-=1
   simple.append(points[j]);i=j
  assert legal(net,layer,simple,.2)
  return simple

def connect(label,net,layer,start,end,quiet=False,limit=18):
 opts=[]
 for ps in routing.candidate_paths(start,end):
  ps=[list(p) for i,p in enumerate(ps) if not i or list(p)!=list(ps[i-1])]
  if len(ps)<2:continue
  length=LineString(ps).length
  if length<=limit and legal(net,layer,ps,.2):opts.append((length,ps))
 if not opts:
  ps=grid(net,layer,start,end,limit)
  if ps:opts=[(LineString(ps).length,ps)]
 if not opts:deferred.append(dict(owner=owner,label=label,net=net,layer=layer,start=start,end=end));print('DEFER',label,flush=True);return False
 length,ps=min(opts,key=lambda a:a[0]);r=dict(owner=owner,chip=owner,label=label,net=net,layer=layer,width_mm=.2,path_mm=ps,length_mm=length,quiet_return=quiet);connections.append(r);added.append((net,layer,.2,LineString(ps)));print('ROUTE',label,round(length,3),flush=True);return True



fixed=json.loads((STAGING/'two-board-analog-cell-plan-06/fixed.json').read_text())
for r in fixed['connections']:
 owner=r['owner'];assert legal(r['net'],r['layer'],r['path_mm'],r['width_mm']),(r['label'],'fixed route')
 connections.append(r);added.append((r['net'],r['layer'],r['width_mm'],LineString(r['path_mm'])))
# Account for the retained quiet stitch, which has no surface escape.
extra_quiet_vias=fixed['extra_quiet_vias']
for v in extra_quiet_vias:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:added.append((v['net'],l,.6,Point(v['position_mm'])))
# Recheck the new resistor position using native footprint geometry from the
# last pose fixture; only its position/orientation changes within the same face.
from hardware.fabrication.route_two_board_buck_cell import mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.electronics.common.sexpr import first
posed=read_sexpr((STAGING/'two-board-analog-cell-native-poses-04/native-poses.kicad_pcb').read_text());pf={prop(f,'Reference')[2]:f for f in children(posed,'footprint')}
pf['E_R100']=rotate_footprint(pf['E_R100'],[51.75,114.5],180)
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text());accepted={r['ref']:r for r in pl['reconciled_existing_passive_sides']}
for rec in placement['parts']:
 if rec['id'] in pf and rec['id'] not in moving and rec['side']!=first(pf[rec['id']],'layer')[1][0]:
  a=accepted[rec['id']];assert a['old_side']==rec['side'] and a['current_side']==first(pf[rec['id']],'layer')[1][0];rec['side']=a['current_side']
mechanical_check(pf,moving,placement);print('MECHANICAL PASS',flush=True)
# Shortened enable path now stays below PG0 and AUX on the reference layer.
owner='E_U14';o=pad('E_R100','1');assert connect('E_R100.1 restored enable',o['net'],'B.Cu',o['position_mm'],[50.,116.5])
opts=candidates('E_R100','2',32);assert opts
length,rr,v=min(opts,key=lambda a:(a[0]+.08*math.dist(a[2]['position_mm'],[53.86,118.425]),a[0]))
rr.update(label='E_R100.2 local quiet return',quiet_return=True);v.update(owner=owner,ref='E_R100',pin='2');push(rr,v)
print('R100 GROUND',length,v['position_mm'],flush=True)
# Preserve every previously complete B.Cu reference underneath the replacement
# PG0 path, plus the newly accepted local ILM/DVDT and enable surface routes.
review=json.loads((STAGING/'two-board-power-analog-cells-native-02/analog-reference-review.json').read_text());objects={o['uuid']:o for o in c['objects']};shadow=[]
for rec in review['retained_reference_cases']:
 u=rec['track_uuid']
 if rec['reference_layer']!='In6.Cu' or u in retire:continue
 o=objects[u]
 if list(o['layers'])!=['B.Cu']:continue
 g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
 for v0 in c['objects']:
  if v0['kind']=='PCB_VIA' and v0['net']==o['net']:g=g.difference(Point(v0['position_mm']).buffer(v0['width_mm']/2+.215))
 shadow.append(g)
for r in routes+connections:
 if r['layer']!='B.Cu' or r['net']=='PWR_AGND':continue
 g=LineString(r['path_mm']).buffer(r['width_mm']/2)
 for vv in [*vias,*[o for o in c['objects'] if o['kind']=='PCB_VIA']]:
  if vv['net']==r['net']:g=g.difference(Point(vv['position_mm']).buffer(.515))
 shadow.append(g)
# Every new quiet bridge/star is also a ground contact that PG0 must avoid.
for r,v in zip(routes,vias):
 if v['net']=='PWR_AGND':shadow.append(Point(v['position_mm']).buffer(.3))
for v in extra_quiet_vias:shadow.append(Point(v['position_mm']).buffer(.3))
protected_back=unary_union(shadow)
previous_legal=legal
def legal(net,layer,points,width):
 if not previous_legal(net,layer,points,width):return False
 if layer=='In6.Cu' and net=='/E_rail_disconnect/ANA_PG0' and LineString(points).distance(protected_back)<width/2+.21:return False
 return True
owner='E_U13';pgvia=next(v['position_mm'] for r,v in zip(routes,vias) if r['ref']==owner and r['pin']=='3')
for label,start,end in [('pullup',pgvia,[44.,109.5]),('monitor',[44.,109.5],[50.,114.])]:
 connect('E_U13 power-good restoration '+label,'/E_rail_disconnect/ANA_PG0','In6.Cu',start,end,limit=22)
result=dict(routes=routes,vias=vias,connections=connections,extra_quiet_vias=extra_quiet_vias,deferred=deferred,moves=pl['moves'],retired_objects=sorted(retire),preserved_shared_enable_objects=fixed['preserved_shared_enable_objects'],removed_redundant_vias=fixed['removed_redundant_vias'],scope='Reference-aware PG0 reconstruction and R100 local reposition; new planes and native verification pending.',fabrication_released=False)
(STAGING/'two-board-analog-cell-plan-06/routes.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(routes=len(routes)+len(connections),deferred=deferred)),flush=True)
