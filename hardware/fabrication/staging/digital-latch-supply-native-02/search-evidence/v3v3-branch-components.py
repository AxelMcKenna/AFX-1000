import json
from pathlib import Path
from hardware.fabrication.route_nf_surface import shape
from shapely.strtree import STRtree
c=json.loads(Path('hardware/fabrication/staging/digital-blank-pullup-inputs-43/capture.json').read_text());objs=[o for o in c['objects'] if o['net']=='V3V3_IO'];cut={'96e3c929-704e-5f6b-81f3-654dd7b06838'}
for removed in [set(),cut]:
 rows=[o for o in objs if o['uuid'] not in removed];parent=list(range(len(rows)))
 def root(i):
  while parent[i]!=i:i=parent[i]
  return i
 for face in c['copper_layers']:
  shapes=[(i,shape(o['layers'][face])) for i,o in enumerate(rows) if o['layers'].get(face)];tree=STRtree([g for _,g in shapes])
  for i,g in shapes:
   for k in tree.query(g.buffer(.000001)):
    j,h=shapes[int(k)]
    if g.distance(h)<.000001:parent[root(i)]=root(j)
 groups={}
 for i,o in enumerate(rows):groups.setdefault(root(i),[]).append((o.get('ref'),o.get('pin'),o['uuid'],o['position_mm']))
 print('REMOVED',removed,'components',len(groups))
 for g in groups.values():print('PADS',[(r,p) for r,p,_,_ in g if r],'OBJECTS',len(g))
