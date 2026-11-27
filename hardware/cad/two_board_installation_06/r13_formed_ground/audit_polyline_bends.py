"""Fail-closed test of whether the r12 vertices can accept radius12 fillets."""
from pathlib import Path
import json,math,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
gpath=HERE.parent/'r12_ground/ground-routes.json'
g=json.loads(gpath.read_text());contract=json.loads((HERE/'exit-contract.json').read_text())
R=contract['selected_centerline_radius_mm'];bad=[]
for e in g['edges']:
 p=np.array(e['points_mm']);cuts=[0.0]
 for a,b,c in zip(p,p[1:],p[2:]):
  u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
  theta=math.acos(float(np.clip(u@v,-1,1)))
  cuts.append(R*math.tan(theta/2))
 cuts.append(0.0)
 failures=[]
 for i,(a,b) in enumerate(zip(p,p[1:])):
  available=float(np.linalg.norm(b-a));required=cuts[i]+cuts[i+1]
  if required>available+1e-8:failures.append({'segment':i,'length_mm':available,'required_tangent_length_mm':required})
 if failures:bad.append({'wire':e['id'],'segments':failures})
report={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),gpath,HERE/'exit-contract.json']},'radius_mm':R,'wires_audited':len(g['edges']),'wires_requiring_reroute':len(bad),'failures':bad,'existing_polylines_accept_selected_radius':not bad,'fabrication_released':False}
(HERE/'polyline-bend-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(len(bad),'of',len(g['edges']),'routes cannot be filleted in place at radius',R)
