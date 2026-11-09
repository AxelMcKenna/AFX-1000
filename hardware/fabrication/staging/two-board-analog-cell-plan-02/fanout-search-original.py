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
pl=json.loads((STAGING/'two-board-analog-cell-plan-01/placement.json').read_text());moving=set(pl['moves']);retire=set(pl['retired_objects'])
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


seed=json.loads((STAGING/'two-board-analog-cell-plan-01/seed.json').read_text())
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
attempts=0;deadline=time.monotonic()+150
# Bounded recursive allocation preserves the best completed cell set on failure.
def allocate(ref,pins):
 global attempts
 attempts+=1
 if attempts>500 or time.monotonic()>deadline:return False
 if not pins:return True
 for length,r,v in candidates(ref,pins[0],16):
  push(r,v)
  if allocate(ref,pins[1:]):return True
  pop()
 return False
deferred=[]
for owner,*_ in seed['cells']:
 attempts=0
 print('SEARCH',owner,flush=True)
 if allocate(owner,(['2','4','3','9','7','8'] if owner!='E_U32' else ['2','4','9','7','8'])):print('DONE',owner,[(r['pin'],v['position_mm']) for r,v in zip(routes,vias) if r['ref']==owner],flush=True)
 else:deferred.append(owner);print('DEFER',owner,attempts,flush=True)
Path('/private/tmp/analog-cell-fanout-03.json').write_text(json.dumps(dict(routes=routes,vias=vias,retired_objects=sorted(retire),deferred=deferred,scope='Candidate local fanout; zones deliberately excluded from this routing screen and require explicit ownership/refill/native validation.',fabrication_released=False),indent=2)+'\n')
