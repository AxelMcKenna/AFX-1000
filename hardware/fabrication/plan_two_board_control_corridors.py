"""Plan a broader additive control pass using exact polygon corridors."""
import json,math,itertools,xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
OUT=STAGING/'two-board-control-corridor-plan-01'
assert not OUT.exists()
CAP=STAGING/'two-board-power-routing-inputs-nf-pin-escape-rework-01/capture.json'
c=json.loads(CAP.read_text());objects={o['uuid']:o for o in c['objects']}
removed=[]
fields,excluded=anchored_fields(c);main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
holes={}
for o in c['objects']:
 if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
holes={n:unary_union(v) for n,v in holes.items()}
protected={l:[] for l in c['copper_layers']}
buffered_fields={k:f.buffer(.0015) for k,f in fields.items()}
for o in c['objects']:
 if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND' or o['uuid'] in removed:continue
 layer,=o['layers'];i=c['copper_layers'].index(layer);adjacent={c['copper_layers'][j] for j in [i-1,i+1] if 0<=j<len(c['copper_layers'])}
 band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
 if band.is_empty:continue
 for (l,gid),f in buffered_fields.items():
  if l in adjacent and band.difference(f).area<1e-6:protected[l].append(band)
protected_lines={l:prep(unary_union(v).buffer(.435)) for l,v in protected.items()}
protected_vias=prep(unary_union([x for v in protected.values() for x in v]).buffer(.64))
quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
quietids={u for f in quietpaths for q in json.loads(f.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
quiet=prep(unary_union([routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in quietids]))
supply={l:unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['layer']==l and z['net']!='PWR_AGND']) for l in c['copper_layers']}
all_supply=prep(unary_union(list(supply.values())).buffer(.55))
supply_lines={l:prep(supply[l].buffer(.315)) for l in ['F.Cu','In2.Cu']}
newreferences=[]
cache={};routing.SIGNAL_LAYERS=('F.Cu','In2.Cu');routing.WIDTH=.2
class Screen(ViaScreen):
 def legal(self,net,layer,points):
  line=LineString(points)
  if net not in cache:cache[net]=prep(fields['In1.Cu',main].buffer(.0015).union(holes.get(net,Polygon())).buffer(-.100001))
  if not cache[net].covers(line) or supply_lines[layer].intersects(line) or quiet.intersects(line) or protected_lines[layer].intersects(line):return False
  if any(n!=net and line.distance(Point(xy))<=.625 for n,xy in self.vias):return False
  return super().legal(net,layer,points)
 def via_legal(self,net,xy):
  point=Point(xy)
  if any(n!=net and point.distance(band)<=.64 for n,band in newreferences):return False
  return not (all_supply.intersects(point) or quiet.intersects(point) or protected_vias.intersects(point)) and super().via_legal(net,xy)
 def corridor(self,net,layer,start,end):
  from shapely.geometry import box
  from hardware.fabrication.route_polygon_corridor import corridor_path
  bounds=box(min(start[0],end[0])-10,min(start[1],end[1])-10,max(start[0],end[0])+10,max(start[1],end[1])+10)
  obs=[g.buffer(d+.002,quad_segs=32) for n,g,d in self.geometry[layer] if n!=net and g.intersects(bounds)]
  obs.extend(g.buffer(.412,quad_segs=32) for n,l,g in self.added if n!=net and l==layer)
  obs.extend(Point(xy).buffer(.627,quad_segs=32) for n,xy in self.vias if n!=net)
  obs.extend(p.buffer(r+.112,quad_segs=32) for ref,p,r in self.mounts)
  field=fields['In1.Cu',main].buffer(.0015).union(holes.get(net,Polygon())).buffer(-.100001)
  free=bounds.intersection(field).intersection(self.outline).difference(unary_union(obs)).difference(quiet.context).difference(supply_lines[layer].context).difference(protected_lines[layer].context)
  return corridor_path(free,start,end,lambda ps:self.legal(net,layer,ps))
 def escapes(self,net,layer,point):
  sites=sorted((math.dist(point,(ix/4,iy/4)),(ix/4,iy/4)) for ix in range(math.floor((point[0]-4)*4),math.ceil((point[0]+4)*4)+1) for iy in range(math.floor((point[1]-4)*4),math.ceil((point[1]+4)*4)+1))
  candidates=[];legal_sites=[]
  for distance,xy in sites:
   if distance>4 or not self.via_legal(net,xy):continue
   legal_sites.append((distance,xy))
   path=self.simple(net,layer,point,xy,7)
   if path:candidates.append((path[0],xy,path[1]))
   if len(candidates)>=48:break
  if not candidates and legal_sites:
   from shapely.geometry import box
   from hardware.fabrication.route_polygon_corridor import corridor_path
   pt=Point(point);bounds=box(pt.x-7,pt.y-7,pt.x+7,pt.y+7)
   obs=[g.buffer(d+.002,quad_segs=32) for n,g,d in self.geometry[layer] if n!=net and g.intersects(bounds)]
   obs.extend(g.buffer(.412,quad_segs=32) for n,l,g in self.added if n!=net and l==layer)
   obs.extend(Point(xy).buffer(.627,quad_segs=32) for n,xy in self.vias if n!=net)
   obs.extend(p.buffer(r+.112,quad_segs=32) for ref,p,r in self.mounts)
   field=fields['In1.Cu',main].buffer(.0015).union(holes.get(net,Polygon())).buffer(-.100001)
   free=bounds.intersection(field).intersection(self.outline).difference(unary_union(obs)).difference(quiet.context).difference(supply_lines[layer].context).difference(protected_lines[layer].context)
   for distance,xy in legal_sites[:48]:
    path=corridor_path(free,point,xy,lambda ps:self.legal(net,layer,ps))
    if path and LineString(path).length<=18:candidates.append((LineString(path).length,xy,path))
    if len(candidates)>=8:break
  return sorted(candidates)
screen=Screen(dict(c,zones=[],objects=[o for o in c['objects'] if o['uuid'] not in removed]))

BASE=STAGING/'two-board-power-nf-pin-escape-rework-native-01'
SELECTION=STAGING/'two-board-nf-logic-route-plan-03/plan.json'
selected=json.loads(SELECTION.read_text())['selected_nets'];selected=set(selected)
netnodes={}
for n in ET.parse(BASE/'netlist.xml').findall('./nets/net'):
 name=n.attrib['name'];nodes=[p.attrib for p in n.findall('node')];types={p.get('pintype') for p in nodes}
 if name not in c['open_nets']:continue
 if name in selected or routing.is_logic_net(name) and types&{'output','open_collector'} and not types&{'power_in','power_out'}:
  assert types&{'output','open_collector'} and not types&{'power_in','power_out'},name
  netnodes[name]=nodes
contacts={};groups={}
for gid,us in c['groups'].items():
 net=objects[us[0]]['net']
 if net not in netnodes:continue
 groups.setdefault(net,[]).append(gid);pts=set()
 for u in us:
  o=objects[u]
  for l in set(o['layers'])&set(routing.SIGNAL_LAYERS):
   for pt in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):pts.add((l,tuple(pt)))
 contacts[gid]=pts
parent={g:g for g in contacts}
def root(g):
 while parent[g]!=g:parent[g]=parent[parent[g]];g=parent[g]
 return g
routes=[];vias=[];joins=[];deferred=[]
def addpath(net,layer,path):
 path=[x for i,x in enumerate(path) if not i or math.dist(x,path[i-1])>1e-7]
 if len(path)<2:return
 line=LineString(path);screen.added.append((net,layer,line));newreferences.append((net,line.buffer(.1)))
 routes.append(dict(net=net,layer=layer,path_mm=path,width_mm=.2,reference_layer='In1.Cu',ground_group=main))
def addvia(net,xy):
 screen.vias.append((net,xy))
 for l in routing.SIGNAL_LAYERS:screen.added.append((net,l,Point(xy).buffer(.2)))
 vias.append(dict(net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
tasks=[]
for net,gs in groups.items():
 for a,b in itertools.combinations(gs,2):
  opts=sorted((math.dist(x,y),l,x,m,y) for l,x in contacts[a] for m,y in contacts[b] if math.dist(x,y)>1e-6)
  if opts:tasks.append((opts[0][0],net,a,b,opts))
print('Selected',len(netnodes),'open control nets',sum(len(g)-1 for g in groups.values()),'missing joins',flush=True)
for distance,net,a,b,allopts in sorted(tasks):
 if root(a)==root(b):continue
 opts=allopts[:8]
 # Retain existing inner contacts even when nearby front pads sort first.
 opts+=[o for o in allopts if o[1]==o[3]=='In2.Cu'][:4]
 opts=list(dict.fromkeys(opts));best=None
 limit=min(250,1.8*distance+14)
 for d,l,x,m,y in opts:
  if l!=m:continue
  path=screen.simple(net,l,x,y,limit)
  if path and (best is None or path[0]<best[0]):best=(path[0],[(l,path[1])],[])
 if best is None:
  for d,l,x,m,y in opts[:4]:
   if l!=m:continue
   path=screen.corridor(net,l,x,y)
   if path and LineString(path).length<=limit:
    length=LineString(path).length
    if best is None or length<best[0]:best=(length,[(l,path)],[])
 # Reuse existing In2 contacts without inserting duplicate vias.
 escape_cache={};pairs=[]
 for d,l,x,m,y in opts[:6]:
  if d>180:continue
  ee=[]
  for layer,pt in [(l,x),(m,y)]:
   key=(layer,pt)
   if key not in escape_cache:
    escape_cache[key]=[(0,pt,None)] if layer=='In2.Cu' else screen.escapes(net,layer,pt)
   ee.append(escape_cache[key])
  for ea,eb in itertools.product(*ee):
   lower=ea[0]+math.dist(ea[1],eb[1])+eb[0]
   if lower>limit or best and lower>=best[0] or math.dist(ea[1],eb[1])<=.81:continue
   pairs.append((lower,l,m,ea,eb))
 seen=set()
 for lower,l,m,ea,eb in sorted(pairs)[:96]:
  key=(tuple(ea[1]),tuple(eb[1]))
  if key in seen:continue
  seen.add(key)
  mid=screen.simple(net,'In2.Cu',ea[1],eb[1],limit-ea[0]-eb[0])
  if mid:
   length=ea[0]+mid[0]+eb[0]
   if best is None or length<best[0]:best=(length,[(l,ea[2]),('In2.Cu',mid[1]),(m,list(reversed(eb[2])) if eb[2] else None)],[e[1] for e in [ea,eb] if e[2]])
 if best is None:
  seen=set()
  for lower,l,m,ea,eb in sorted(pairs)[:24]:
   key=(tuple(ea[1]),tuple(eb[1]))
   if key in seen:continue
   seen.add(key)
   path=screen.corridor(net,'In2.Cu',ea[1],eb[1])
   if path and ea[0]+eb[0]+LineString(path).length<=limit:
    best=(ea[0]+eb[0]+LineString(path).length,[(l,ea[2]),('In2.Cu',path),(m,list(reversed(eb[2])) if eb[2] else None)],[e[1] for e in [ea,eb] if e[2]]);break
 if best is None:
  deferred.append(dict(net=net,source_groups=[a,b],nearest_mm=distance,escape_counts=[len(x) for x in escape_cache.values()]))
  print('Deferred',net.rsplit('/',1)[-1],round(distance,2),flush=True);continue
 length,paths,positions=best
 for l,path in paths:
  if path:addpath(net,l,path)
 for xy in positions:addvia(net,xy)
 parent[root(b)]=root(a);joins.append(dict(net=net,source_groups=[a,b],length_mm=length))
 print('Joined',net.rsplit('/',1)[-1],round(length,3),'vias',len(positions),flush=True)
sources=[Path(__file__),CAP,SELECTION,BASE/'final-review.json',BASE/'netlist.xml',*quietpaths,*[REPO/'hardware/fabrication'/n for n in ['plan_two_board_startup_controls.py','route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_nf_surface.py','route_polygon_corridor.py']]]
for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(dict(source_sha256={str(s.relative_to(REPO)):sha(s) for s in sources},routes=routes,vias=vias,joins=joins,expected_closed_connections=len(joins),deferred_pairs=deferred,selected_nets=netnodes,excluded_unanchored_fragments=excluded,reference_transitions=[dict(net=v['net'],position_mm=v['position_mm'],reference_layers=['In1.Cu'],same_reference_plane=True) for v in vias],native_validation_pending=True,fabrication_released=False),indent=2)+'\n')
print('Finished',len(joins),'joins',len(routes),'paths',len(vias),'vias',len(deferred),'deferred pairs',flush=True)
