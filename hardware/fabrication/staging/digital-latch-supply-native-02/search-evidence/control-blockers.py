import json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.fabrication.route_nf_surface import shape
c=json.loads(Path('hardware/fabrication/staging/digital-blank-pullup-inputs-43/capture.json').read_text());objects=[(o,{f:shape(ps) for f,ps in o['layers'].items() if ps}) for o in c['objects']]
for ref,pin,lo,hi in [('U2002','6',(67.8,29.2),(68.8,30.5)),('U2003','22',(99.2,34.1),(100.2,35.2))]:
 source=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin);net=source['net'];start=source['position_mm'];choices=[]
 for x in [lo[0]+i*.1 for i in range(round((hi[0]-lo[0])*10)+1)]:
  for y in [lo[1]+i*.1 for i in range(round((hi[1]-lo[1])*10)+1)]:
   p=Point(x,y);line=LineString([start,(x,y)]);blocks={}
   for o,gs in objects:
    if o['net']!=net and (any(p.distance(g)<.513-1e-8 for g in gs.values()) or ('B.Cu' in gs and line.distance(gs['B.Cu'])<.3105-1e-8)):blocks[o['uuid']]=o
    if o['kind']=='PAD' and not any(o['drill_mm']) and any(p.distance(gs[f])<.313-1e-8 for f in ('F.Cu','B.Cu') if f in gs):blocks[o['uuid']]=o
   if any(o['kind']=='PAD' for o in blocks.values()):continue
   choices.append((len(blocks),math.dist(start,(x,y)),(x,y),list(blocks.values())))
 print('ENDPOINT',ref,pin,net)
 for n,d,p,obs in sorted(choices,key=lambda x:x[:2])[:4]:
  print('SITE',p,'blockers',n)
  for o in obs:print(o['uuid'],o['net'],o['kind'],o['position_mm'],o.get('end_mm'),list(o['layers']))
