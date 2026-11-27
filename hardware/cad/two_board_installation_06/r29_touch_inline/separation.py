"""Conservative mutual swept-wire clearance including arc chord error."""
import json,math,hashlib
from pathlib import Path
import numpy as np
from hardware.cad.two_board_installation_06.r12_ground.verify import distance
H=Path(__file__).resolve().parent
c=json.loads((H/'route-draft.json').read_text());segments=[]
for e in c['edges']:
 segments.append([(np.array(a),np.array(b)) for s in e['segments'] for a,b in zip(s['points_mm'],s['points_mm'][1:])])
minimum=1e9;witness=None
for i,aa in enumerate(segments):
 for j in range(i+1,len(segments)):
  for ai,(a,b) in enumerate(aa):
   for bi,(x,y) in enumerate(segments[j]):
    alo,ahi=np.minimum(a,b),np.maximum(a,b);blo,bhi=np.minimum(x,y),np.maximum(x,y)
    if np.linalg.norm(np.maximum(np.maximum(alo-bhi,blo-ahi),0))>=minimum:continue
    d=distance(a,b,x,y)
    if d<minimum:minimum=d;witness=[i+1,j+1,ai,bi]
sag=13*(1-math.cos(math.radians(1.5)))
r={'minimum_centerline_segment_distance_mm':minimum,'surface_gap_lower_bound_mm':minimum-1.3-2*sag,'witness':witness,'chord_sag_per_wire_mm':sag,'minimum_required_gap_mm':.25,'source_sha256':{str(p.relative_to(H.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),H/'route-draft.json']},'passes':minimum-1.3-2*sag>=.25}
(H/'separation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
