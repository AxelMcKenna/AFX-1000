import json, math
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
import hardware.fabrication.route_nf_surface as routing
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
from hardware.fabrication.integrate_two_board_signal import STAGING
c=json.loads((STAGING/'two-board-power-routing-inputs-2369-regulator-distribution-04/capture.json').read_text())
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
for ref,pins,width,nvia in [(r,['5','12'],.4,1) for r in ['E_U15','E_U16','E_U17','E_U33']]+[(r,['1','2'],.6,2) for r in ['E_C44','E_C46','E_C48','E_C52']]+[(r,['2','4','8'],.2,1) for r in ['E_U15','E_U16','E_U17','E_U33']]+[('E_J11',['1'],.8,2)]:
 for pin in pins:
  o=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin);net=o['net'];layer=next(iter(o['layers']));x,y=o['position_mm']
  for vi in range(nvia):
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
    if paths:candidates.append((min(paths,key=lambda a:a[0]),xy))
    if len(candidates)>=6:break
   if not candidates:
    print('NO ROUTE',ref,pin,flush=True);continue
   (length,ps),xy=min(candidates,key=lambda a:a[0][0])
   routes.append(dict(ref=ref,pin=pin,net=net,layer=layer,width_mm=width,path_mm=ps))
   vias.append(dict(net=net,position_mm=xy))
   added.append((net,layer,width,LineString(ps)))
   screen.vias.append((net,xy))
   for l in c['copper_layers']:added.append((net,l,.6,Point(xy)))
   print(ref,pin,vi,xy,round(length,3),flush=True)
Path('/private/tmp/digital-distribution-plan.json').write_text(json.dumps(dict(routes=routes,vias=vias),indent=2))
