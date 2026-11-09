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
OUT=STAGING/'two-board-nf-pin-escape-rework-plan-02'
assert not OUT.exists()
CAP=STAGING/'two-board-power-routing-inputs-nf-logic-detours-02/capture.json'
c=json.loads(CAP.read_text());objects={o['uuid']:o for o in c['objects']}
removed=['27e2e0c1-6013-5296-ab6b-122407631d95','893644e2-02de-50fb-814a-5e5e6fa4eb1a','4506ea96-7fce-564c-9e60-c70766db4c20','ad080640-4aeb-5003-8582-be2a27a33f12','fbc727e7-be66-5419-a176-87e869099dad','99c64ba9-580c-5379-8d42-6c1fbc4bccdc','77630fb7-a1c7-528f-bbae-39edfa872e0c','3b96f72e-136d-524c-9756-826637c38b7e','438a5313-4c87-5b5f-a60b-23aba7017b50','0b3100fe-5ce5-51d1-b79c-3a0c828f958b','fcdd8611-df84-5684-b978-4af7d225a148','c41b3128-8e5f-54c9-b0ed-a795a5c39546','224c4f54-631c-5af1-ae9e-e281b30145a7']
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
  if not cache[net].covers(line) or supply_lines[layer].intersects(line) or quiet.intersects(line):return False
  if any(n!=net and line.distance(Point(xy))<=.625 for n,xy in self.vias):return False
  return super().legal(net,layer,points)
 def via_legal(self,net,xy):
  point=Point(xy)
  if any(n!=net and point.distance(band)<=.64 for n,band in newreferences):return False
  return not (all_supply.intersects(point) or quiet.intersects(point) or protected_vias.intersects(point)) and super().via_legal(net,xy)
 def escapes(self,net,layer,point):
  sites=sorted((math.dist(point,(ix/4,iy/4)),(ix/4,iy/4)) for ix in range(math.floor((point[0]-4)*4),math.ceil((point[0]+4)*4)+1) for iy in range(math.floor((point[1]-4)*4),math.ceil((point[1]+4)*4)+1))
  candidates=[];legal_sites=[]
  for distance,xy in sites:
   if distance>4 or not self.via_legal(net,xy):continue
   legal_sites.append((distance,xy))
   path=self.simple(net,layer,point,xy,7)
   if path:candidates.append((path[0],xy,path[1]))
   if len(candidates)>=12:break
  if not candidates:
   for distance,xy in legal_sites[:24]:
    path=self.grid_path(net,layer,point,xy,budget=8000)
    if path and LineString(path).length<=10:candidates.append((LineString(path).length,xy,path))
    if len(candidates)>=8:break
  return sorted(candidates)
screen=Screen(dict(c,zones=[],objects=[o for o in c['objects'] if o['uuid'] not in removed]))
routes=[];vias=[];repairs=[];deferred=[]
def addpath(net,layer,path,purpose):
 line=LineString(path);screen.added.append((net,layer,line));newreferences.append((net,line.buffer(.1)))
 routes.append(dict(net=net,layer=layer,path_mm=path,width_mm=.2,reference_layer='In1.Cu',ground_group=main,purpose=purpose))
def addvia(net,xy):
 screen.vias.append((net,xy))
 for l in routing.SIGNAL_LAYERS:screen.added.append((net,l,Point(xy).buffer(.2)))
 vias.append(dict(net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
for ref,pin in [('N_U35','11'),('N_U48','12'),('N_U51','13')]:
 o=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin)
 es=screen.escapes(o['net'],'F.Cu',o['position_mm'])
 if not es:deferred.append(dict(ref=ref,reason='No escape after declared removal'));continue
 length,xy,path=es[0];addpath(o['net'],'F.Cu',path,'Trapped pad escape');addvia(o['net'],xy)
 repairs.append(dict(ref=ref,pin=pin,pad_uuid=o['uuid'],net=o['net'],via_mm=xy,path_mm=path))
 print('Escape',ref,xy,flush=True)
cages=[('N19_ARM_CONDITIONED',[[239.8625,158.3],[241.5,155.5]],{1}),('NF_NOT_OUTPUT_VALID',[[251,164.5],[254.8,161.1375]],set()),('N12_STAGE_ENABLED',[[264.7,179.2],[263.1,175.5],[270.4,168.9]],set())]
for suffix,ends,existing in cages:
 net=next(o['net'] for o in c['objects'] if o['net'].rsplit('/',1)[-1]==suffix)
 options=[]
 for i,pt in enumerate(ends):
  options.append([(0,pt,None)] if i in existing else screen.escapes(net,'F.Cu',pt))
 print('Replacement options',suffix,[len(x) for x in options],flush=True)
 if any(not x for x in options):deferred.append(dict(net=net,reason='No replacement terminal escape',counts=[len(x) for x in options]));continue
 best=None
 import itertools
 for choice in itertools.product(*[x[:8] for x in options]):
  paths=[];total=sum(x[0] for x in choice)
  if any(math.dist(a[1],b[1])<=.81 for a,b in itertools.combinations(choice,2)):continue
  for ea,eb in zip(choice,choice[1:]):
   mid=screen.simple(net,'In2.Cu',ea[1],eb[1],60)
   if not mid:break
   paths.append(mid[1]);total+=mid[0]
  else:
   if best is None or total<best[0]:best=(total,choice,paths)
 if best is None:
  for choice in itertools.islice(itertools.product(*[x[:4] for x in options]),12):
   paths=[];total=sum(x[0] for x in choice)
   if any(math.dist(a[1],b[1])<=.81 for a,b in itertools.combinations(choice,2)):continue
   for ea,eb in zip(choice,choice[1:]):
    path=screen.grid_path(net,'In2.Cu',ea[1],eb[1],budget=12000)
    if not path:break
    paths.append(path);total+=LineString(path).length
   else:best=(total,choice,paths);break
 if best is None:deferred.append(dict(net=net,reason='No replacement inner corridor'));continue
 length,choice,paths=best
 for i,e in enumerate(choice):
  if i not in existing:addpath(net,'F.Cu',e[2],'Cage replacement');addvia(net,e[1])
 for path in paths:addpath(net,'In2.Cu',path,'Cage replacement')
 print('Replaced',suffix,length,flush=True)
sources=[Path(__file__),CAP,STAGING/'two-board-power-nf-logic-detours-native-02/final-review.json',*quietpaths,*[REPO/'hardware/fabrication'/n for n in ['plan_two_board_startup_controls.py','route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_nf_surface.py']]]
for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(dict(source_sha256={str(s.relative_to(REPO)):sha(s) for s in sources},removed_track_uuids=removed,routes=routes,vias=vias,pad_escapes=repairs,deferred=deferred,all_replacements_found=not deferred,native_validation_pending=True,fabrication_released=False),indent=2)+'\n')
print('Finished',len(routes),'paths',len(vias),'vias',len(deferred),'deferred',flush=True)
