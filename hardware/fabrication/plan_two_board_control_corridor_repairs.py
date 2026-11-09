"""Plan local track replacement to unlock three trapped NF logic pads."""
import json,math
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
OUT=STAGING/'two-board-control-corridor-repair-plan-01'
assert not OUT.exists()
CAP=STAGING/'two-board-power-routing-inputs-control-corridors-01/capture.json'
c=json.loads(CAP.read_text());objects={o['uuid']:o for o in c['objects']}
MANIFEST=STAGING/'two-board-power-control-corridors-native-01/control-corridor-routing.json'
m=json.loads(MANIFEST.read_text());indices=[7,38]
removed=[u for i in indices for u in m['routes'][i]['segment_uuids']]
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

repairs=[];deferred=[]
for i in indices:
 r=m['routes'][i];start,end=r['path_mm'][0],r['path_mm'][-1]
 path=screen.simple(r['net'],r['layer'],start,end,25)
 if path:path=path[1]
 if not path:path=screen.corridor(r['net'],r['layer'],start,end)
 if path:
  repairs.append(dict(route_index=i,net=r['net'],layer=r['layer'],original_path_mm=r['path_mm'],path_mm=path))
  line=LineString(path);screen.added.append((r['net'],r['layer'],line));newreferences.append((r['net'],line.buffer(.1)))
  print('Repaired',i,LineString(path).length,path,flush=True)
 else:
  deferred.append(i);print('Deferred',i,'endpoint coverage',cache.get(r['net']).covers(Point(start)) if r['net'] in cache else None,flush=True)
sources=[Path(__file__),CAP,MANIFEST,*quietpaths,*[REPO/'hardware/fabrication'/n for n in ['plan_two_board_startup_controls.py','route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_nf_surface.py','route_polygon_corridor.py']]]
for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(dict(source_sha256={str(s.relative_to(REPO)):sha(s) for s in sources},repairs=repairs,deferred=deferred,native_validation_pending=True,fabrication_released=False),indent=2)+'\n')
