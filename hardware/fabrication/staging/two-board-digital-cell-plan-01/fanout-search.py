import json, math
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
import hardware.fabrication.route_nf_surface as routing
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
from hardware.fabrication.integrate_two_board_signal import STAGING
c=json.loads((STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json').read_text())
from hardware.electronics.common.sexpr import children,read_sexpr
from hardware.fabrication.integrate_two_board_signal import prop
from hardware.fabrication.route_two_board_buck_cell import transform_object,position
pl=json.loads(Path('/private/tmp/digital-cell-placement.json').read_text());moving=set(pl['moves']);retire=set(pl['retired_objects'])
fps={prop(f,'Reference')[2]:f for f in children(read_sexpr((STAGING/'two-board-power-digital-distribution-native-02/power_protection.kicad_pcb').read_text()),'footprint')}
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
  if o['net']!=net and line.distance(g)<width/2+.21-1e-8:return False
 if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-8 for n,l,w,g in added):return False
 return True

def candidates(ref,pin,limit=16):
 o=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin);net=o['net'];layer=next(iter(o['layers']));x,y=o['position_mm'];width=.2
 sites=sorted((math.hypot(i*.2,j*.2),[round(x+i*.2,4),round(y+j*.2,4)]) for i in range(-20,21) for j in range(-20,21))
 candidates=[]
 for d,xy in sites:
  if d<.5 or d>4:continue
  if not screen.via_legal(net,xy):continue
  if any(n!=net and Point(xy).distance(g)<.3+w/2+.21 for n,l,w,g in added):continue
  paths=[]
  for ps in routing.candidate_paths([x,y],xy):
   ps=[p for i,p in enumerate(ps) if not i or list(p)!=list(ps[i-1])]
   if len(ps)<2:continue
   ln=LineString(ps).length
   if ln<=5 and legal(net,layer,ps,width):paths.append((ln,ps))
  if paths:
   length,ps=min(paths,key=lambda a:a[0]);candidates.append((length,dict(ref=ref,pin=pin,net=net,layer=layer,width_mm=width,path_mm=ps),dict(net=net,position_mm=xy)))
  if len(candidates)>=limit:break
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
for ref in ['E_U15','E_U16','E_U17','E_U33']:
 assert cell(ref,['9','7','8']),ref
 print(ref,[(r['pin'],v['position_mm'],r['path_mm']) for r,v in zip(routes[-3:],vias[-3:])],flush=True)
Path('/private/tmp/digital-repacked-fanout-plan.json').write_text(json.dumps(dict(routes=routes,vias=vias,retired_objects=sorted(retire),moving_components=sorted(moving)),indent=2))
