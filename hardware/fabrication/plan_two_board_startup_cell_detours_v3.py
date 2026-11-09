"""Move obstructing In6 signal spans around retained and proposed B.Cu returns."""
import copy,json,math
from collections import defaultdict
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,children
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,prop
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
BASE=STAGING/'two-board-power-startup-cells-native-03'
CAP=STAGING/'two-board-power-routing-inputs-2199-startup-cells-03/capture.json'
PLAN=STAGING/'two-board-startup-remaining-plan-04/plan.json'
OUT=STAGING/'two-board-startup-remaining-plan-05'


def polys(g):
 return [dict(outer=list(g.exterior.coords),holes=[list(r.coords) for r in g.interiors])]


def run():
 assert not OUT.exists()
 c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
 for d in [c,p]:
  for n,h in d['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 old={o['uuid']:o for o in c['objects']};z={z['uuid']:z for z in c['zones']}
 p['routes']=[r for r in p['routes'] if r not in p['reference_detours']]
 surface_retired={u for u in p['retired_objects'] if list(old[u]['layers'])==['B.Cu']}
 main5=routing.shape(z['2fff880c-5da4-5609-a6d1-dfc1d5b3e287']['polygons'])
 main6=routing.shape(z['4b63f119-2e71-5d61-96f6-8b78a1f5c6cb']['polygons'])
 holes={}
 for o in old.values():
  if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
 holes={n:unary_union(gs) for n,gs in holes.items()}
 reserved=[]
 for o in old.values():
  if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND' or list(o['layers']) not in [['B.Cu'],['In5.Cu']]:continue
  g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
  if g.difference(main6.buffer(.0015)).area<1e-6:reserved.append(g)
 reserved.extend(LineString(r['path_mm']).buffer(r['width_mm']/2) for r in p['routes'] if r['net']!='PWR_AGND')
 reserved=unary_union(reserved)
 inner=[o for o in old.values() if o['kind']=='PCB_TRACK' and list(o['layers'])==['In6.Cu'] and o['net']!='PWR_AGND']
 # Retire complete authored segments intersecting the reserved reference band.
 retired={o['uuid'] for o in inner if LineString([o['position_mm'],o['end_mm']]).distance(reserved)<o['width_mm']/2+.216}
 retired.update(o['uuid'] for o in inner if o['net']=='/E_rail_disconnect/E28_TIMEOUT_RAW')
 bynet=defaultdict(list)
 for u in retired:bynet[old[u]['net']].append(old[u])
 tasks=[]
 for net,rows in bynet.items():
  graph=defaultdict(set)
  for o in rows:
   a,b=tuple(o['position_mm']),tuple(o['end_mm']);graph[a].add(b);graph[b].add(a)
  pending=set(graph)
  while pending:
   component={next(iter(pending))};todo=list(component)
   while todo:
    v=todo.pop()
    for w in graph[v]-component:component.add(w);todo.append(w)
   pending-=component;ends=[v for v in component if len(graph[v])==1]
   assert len(ends)==2 and all(len(graph[v])<=2 for v in component),(net,ends)
   # Internal native via/branch contacts require a separately split plan.
   external=[o for o in c['objects'] if o['net']==net and o['uuid'] not in retired and o['layers'].get('In6.Cu')]
   for v in component-set(ends):
    for o in external:
     g=routing.shape(o['layers']['In6.Cu'])
     # Several fine terminal segments lie within the same endpoint via land.
     # That is still one preserved endpoint, not an intermediate branch.
     if Point(v).distance(g)<1e-6:
      assert o['kind']=='PCB_VIA' and any(Point(end).distance(g)<1e-6 for end in ends),(net,v,'internal contact')
   tasks.append((math.dist(*ends),net,[list(x) for x in sorted(ends)]))
 fps={prop(f,'Reference')[2]:f for f in children(read_sexpr((BASE/'power_protection.kicad_pcb').read_text()),'footprint')}
 objects=[]
 for o in c['objects']:
  if o['uuid'] in retired|surface_retired:continue
  if o.get('ref') in p['moves']:
   xy,rot,_=p['moves'][o['ref']];o=transform_object(o,position(fps[o['ref']]),xy,rot)
  objects.append(o)
 for i,v in enumerate(p['vias']):
  objects.append(dict(uuid='planned-via-'+str(i),kind='PCB_VIA',net=v['net'],position_mm=v['position_mm'],width_mm=.6,drill_mm=.3,layers={l:polys(Point(v['position_mm']).buffer(.3,quad_segs=64)) for l in c['copper_layers']}))
 routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
 main1=routing.shape(z['13cfea4d-d36e-5757-b531-ed680e4c4562']['polygons'])
 band=prep(reserved.buffer(.215+.1))
 fields={}
 for net in bynet:
  for layer,field in [('In6.Cu',main5),('In2.Cu',main1)]:
   fields[net,layer]=prep(unary_union([field.buffer(.0015),holes.get(net,Polygon())]).buffer(-.1))
 class RefScreen(ViaScreen):
  def legal(self,net,layer,points):
   if not super().legal(net,layer,points):return False
   if layer not in ['In6.Cu','In2.Cu']:return True
   g=LineString(points)
   if layer=='In6.Cu' and band.intersects(g):return False
   return fields[net,layer].covers(g)
 s=RefScreen(dict(c,objects=objects,zones=[]))
 for r in p['routes']:s.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
 added=[];failed=[]
 for distance,net,(start,end) in sorted(tasks):
  layers=['In2.Cu','In6.Cu'] if net=='/E_rail_disconnect/E28_TIMEOUT_RAW' else ['In6.Cu']
  best=None;layer=None
  for candidate in layers:
   best=s.simple(net,candidate,start,end,distance*1.8+8)
   if best:layer=candidate;break
  if not best:
   for candidate in layers:
    route=s.grid_path(net,candidate,start,end,budget=18000)
    if route:best=(LineString(route).length,route);layer=candidate;break
  if not best:
   failed.append(dict(net=net,start=start,end=end));print('NO DETOUR',net,start,end,flush=True);continue
  length,path=best;r=dict(label=net.split('/')[-1]+' reference detour',net=net,layer=layer,width_mm=.2,path_mm=path)
  added.append(r);s.added.append((net,layer,LineString(path)));print('DETOUR',net,layer,round(distance,3),round(length,3),flush=True)
 sources=[Path(__file__),CAP,PLAN,BASE/'power_protection.kicad_pcb',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_layer_detours.py','route_two_board_power_local.py','route_two_board_power_local_v2.py','route_two_board_buck_cell.py']]]
 result=dict(p,source_sha256={str(f.relative_to(REPO)):sha(f) for f in sources},retired_objects=sorted(retired|surface_retired),routes=p['routes']+added,reference_detours=added,unresolved_detours=failed,reference_repair_pending=True,native_validation_pending=True,fabrication_released=False)
 OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(retired=len(retired),detours=len(added),failed=failed)))


if __name__=='__main__':run()
