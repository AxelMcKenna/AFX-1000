import json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.fabrication.route_nf_surface import shape
c=json.loads(Path('hardware/fabrication/staging/digital-blank-pullup-inputs-43/capture.json').read_text());net='/LED/LATCH_5V_SRC';start=(68.8625,21.175)
objects=[(o,{f:shape(ps) for f,ps in o['layers'].items() if ps}) for o in c['objects']]
choices=[]
for x in [69.75+i*.25 for i in range(10)]:
 for y in [20.75+i*.25 for i in range(5)]:
  p=Point(x,y);line=LineString([start,(x,y)]);blocks={}
  for o,gs in objects:
   if o['net']!=net and (any(p.distance(g)<.51-1e-8 for g in gs.values()) or ('F.Cu' in gs and line.distance(gs['F.Cu'])<.31-1e-8)):blocks[o['uuid']]=o
   if o['kind']=='PAD' and not any(o['drill_mm']) and any(p.distance(gs[f])<.31-1e-8 for f in ('F.Cu','B.Cu') if f in gs):blocks[o['uuid']]=o
  if any(o['kind']=='PAD' for o in blocks.values()):continue
  choices.append((len(blocks),math.dist(start,(x,y)),(x,y),list(blocks.values())))
for n,d,p,obs in sorted(choices,key=lambda x:x[:2])[:8]:
 print('SITE',p,'blockers',n)
 for o in obs:print(o['uuid'],o['net'],o['kind'],o['position_mm'],o.get('end_mm'),list(o['layers']))
