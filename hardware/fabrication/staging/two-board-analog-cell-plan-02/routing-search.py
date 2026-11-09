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
pl=json.loads((STAGING/'two-board-analog-cell-plan-02/placement.json').read_text());moving=set(pl['moves']);retire=set(pl['retired_objects'])
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
full=json.loads((STAGING/'two-board-analog-cell-plan-02/fanout.json').read_text())
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
  bounds=box(min(start[0],end[0])-4,min(start[1],end[1])-4,max(start[0],end[0])+4,max(start[1],end[1])+4)
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

# Restore both removed power-good escapes before any support tracks can consume their corridors.
for owner,endpoint in [('E_U13',[50.,114.]),('E_U14',[50.,117.5])]:
 v=next(v for r,v in zip(routes,vias) if r['ref']==owner and r['pin']=='3')
 # Existing connected copper offers multiple equivalent physical contacts.
 contacts=[endpoint]
 for o,g in rows['In6.Cu']:
  if o['net']!=v['net']:continue
  if o.get('end_mm'):
   line=LineString([o['position_mm'],o['end_mm']]);point=line.interpolate(line.project(Point(v['position_mm'])))
   contacts.extend([list(point.coords[0]),o['position_mm'],o['end_mm']])
 contacts=sorted(contacts,key=lambda xy:math.dist(xy,v['position_mm']))
 for contact in contacts:
  if math.dist(contact,v['position_mm'])>22:continue
  if connect(owner+' power-good restoration',v['net'],'In6.Cu',v['position_mm'],contact,limit=22):break
  deferred.pop()
 else:deferred.append(dict(owner=owner,label='power-good restoration exhausted contacts'))
for owner,ilm,dvdt,cap,pulldown in seed['cells']:
 pv={r['pin']:v['position_mm'] for r,v in zip(routes,vias) if r['ref']==owner}
 for pin,ref in [('9',ilm),('7',dvdt)]:
  o=pad(ref,'1');connect(ref+'.1',o['net'],next(iter(o['layers'])),pv[pin],o['position_mm'])
 a,b=pad(dvdt,'2'),pad(cap,'1');la,lb=next(iter(a['layers'])),next(iter(b['layers']))
 if la==lb:connect(dvdt+'-'+cap,a['net'],la,a['position_mm'],b['position_mm'])
 else:
  opts=candidates(cap,'1',16)
  if opts:
   length,r,v=opts[0];push(r,v);connect(dvdt+'-'+cap,a['net'],la,a['position_mm'],v['position_mm'])
  else:deferred.append(dict(owner=owner,label=cap+' signal via'));print('DEFER cap via',cap,flush=True)
 for ref in [ilm,cap,pulldown]:
  o=pad(ref,'2');connect(ref+'.2 quiet',o['net'],next(iter(o['layers'])),o['position_mm'],pv['8'],quiet=True)
 o=pad(pulldown,'1');target={'E_U13':[50.5,113.],'E_U14':[50.,116.5],'E_U32':[46.5,120.]}[owner]
 connect(pulldown+'.1 restored enable',o['net'],next(iter(o['layers'])),o['position_mm'],target)
(STAGING/'two-board-analog-cell-plan-02/routes.json').write_text(json.dumps(dict(routes=routes,vias=vias,connections=connections,deferred=deferred,moves=pl['moves'],retired_objects=sorted(retire),scope='Candidate geometry, pending quiet-zone construction, native DRC and preservation/reference review.',fabrication_released=False),indent=2)+'\n')
print(json.dumps(dict(escapes=len(routes),connections=len(connections),deferred=len(deferred))),flush=True)
