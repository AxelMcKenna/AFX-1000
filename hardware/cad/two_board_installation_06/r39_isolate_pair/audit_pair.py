"""Retain rejected source fanout and accepted pair-separation calculations."""
import hashlib,json,math,importlib.util
from pathlib import Path
import numpy as np
from hardware.cad.two_board_installation_06.r39_isolate_pair.search_corridor import route
from hardware.cad.two_board_installation_06.r12_ground.verify import distance
H=Path(__file__).resolve().parent;R=H.parents[3]
import types
old=types.ModuleType('rejected');old.__file__=str(H/'search_corridor.py');exec(compile((H/'rejected-r1/search_corridor.py').read_text(),str(H/'rejected-r1/search_corridor.py'),'exec'),old.__dict__)
# The frozen helper uses its own parent for relative data; restore original base.
old.B=H.parent
rows=[]
for label,angles,low,fn in [('rejected-spacing',[210,210],[27,28.6],old.route),('rejected-native-r1',[220,220],[27,28.6],old.route),('current',[150,170],[25.2,27],lambda i,a,z:route(i,a,z,[0,-.5][i]))]:
 a,b=fn(0,angles[0],low[0]),fn(1,angles[1],low[1]);minimum=999;witness=None
 for p,q in zip(a.points,a.points[1:]):
  for u,v in zip(b.points,b.points[1:]):
   if np.linalg.norm(np.maximum(0,np.maximum(np.minimum(p,q),np.minimum(u,v))-np.minimum(np.maximum(p,q),np.maximum(u,v))))>=minimum:continue
   d=distance(p,q,u,v)
   if d<minimum:minimum=d;witness=[[p.tolist(),q.tolist()],[u.tolist(),v.tolist()]]
 gap=minimum-1.2-24*(1-math.cos(math.radians(1.5)))
 rows.append(dict(label=label,angles_degrees=angles,minimum_centerline_gap_mm=minimum,surface_gap_lower_bound_mm=gap,passes_quarter_mm_gap=gap>=.25,nearest_segments=witness,native_verified=False))
assert not rows[0]['passes_quarter_mm_gap'] and all(r['passes_quarter_mm_gap'] for r in rows[1:])
report={'cases':rows,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),H/'search_corridor.py',H/'build.py',H/'rejected-r1/search_corridor.py',H.parent/'r15_right_ground/curves.py',H.parent/'r12_ground/verify.py']}}
(H/'pair-planning.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows))
