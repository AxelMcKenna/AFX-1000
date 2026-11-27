from pathlib import Path
import json,math,hashlib,importlib.util
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3]
helper=BASE/'r12_ground/verify.py';spec=importlib.util.spec_from_file_location('distance',helper);distance=importlib.util.module_from_spec(spec);spec.loader.exec_module(distance)
g=json.loads((HERE/'bows.json').read_text());old=json.loads((BASE/'r15_right_ground/right-routes.json').read_text())['edges'];left=json.loads((BASE/'r14_left_ground/left-routes.json').read_text())['edges'];signal=json.loads((BASE/'r20_scene_signal/route.json').read_text())['edges'];ids=set(g['replaces_wires']);unchanged=[e for e in old if e['id'] not in ids]
datums=json.loads((BASE/'r12_ground/ground-routes.json').read_text())['endpoints_mm'];terminals={k:np.array(v) for k,v in datums.items() if k.startswith('button_') and k.endswith(':1')};assert len(terminals)==29
minimum_wire=999;minimum_terminal=999;curves=[]
for e in g['edges']:
 original=next(x for x in old if x['id']==e['id']);assert (e['from'],e['to'])==(original['from'],original['to'])
 p=np.array(e['points_mm']);assert np.linalg.norm(p[0]-original['points_mm'][0])<1e-7 and np.linalg.norm(p[-1]-original['points_mm'][-1])<1e-7
 assert len(e['primitives'])==1;arc=e['primitives'][0];R=arc['radius_mm'];assert arc['kind']=='arc' and R>=12
 T,N=np.array(arc['tangent']),np.array(arc['normal']);assert abs(T@N)<1e-8 and abs(np.linalg.norm(T)-1)<1e-8 and abs(np.linalg.norm(N)-1)<1e-8
 angles=np.linspace(0,math.radians(arc['angle_degrees']),len(p));analytic=p[0]+R*np.sin(angles)[:,None]*T+R*(1-np.cos(angles))[:,None]*N
 assert np.max(np.linalg.norm(p-analytic,axis=1))<1e-7
 end_tangent=math.cos(angles[-1])*T+math.sin(angles[-1])*N
 curves.append(dict(wire=e['id'],radius_mm=R,one_analytic_arc_no_internal_tangent_discontinuity=True,start_tangent=T.tolist(),end_tangent=end_tangent.tolist(),terminal_approach_changed=True))
 for other in unchanged+left+signal+[x for x in g['edges'] if x['id']>e['id']]:
  q=np.array(other['points_mm'])
  for a,b in zip(p,p[1:]):
   for c,d in zip(q,q[1:]):
    lower=np.linalg.norm(np.maximum(0,np.maximum(np.minimum(a,b),np.minimum(c,d))-np.minimum(np.maximum(a,b),np.maximum(c,d))))
    if lower>=minimum_wire:continue
    minimum_wire=min(minimum_wire,distance.distance(a,b,c,d))
assert minimum_wire>=1.2,(minimum_wire,'wire collision')
terminal_rows=[]
for name,point in terminals.items():
 best=999;nearest=None
 for e in g['edges']+unchanged+left:
  for a,b in zip(e['points_mm'],e['points_mm'][1:]):
   a,b=np.array(a),np.array(b);v=b-a;gap=float(np.linalg.norm(point-a-np.clip((point-a)@v/(v@v),0,1)*v))
   if gap<best:best=gap;nearest=e['id']
 assert best>=1.2,(name,best,nearest);minimum_terminal=min(minimum_terminal,best);terminal_rows.append(dict(terminal=name,nearest_wire=nearest,centerline_distance_mm=best,surface_gap_mm=best-1.2))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(REPO/p)==h for p,h in g['source_sha256'].items())
sources=[Path(__file__),helper,HERE/'bows.json',HERE/'bows.scad',HERE/'terminals.scad',BASE/'r15_right_ground/right-routes.json',BASE/'r14_left_ground/left-routes.json',BASE/'r20_scene_signal/route.json',BASE/'r12_ground/ground-routes.json']
out=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},replaced_wires=sorted(ids),graph_and_endpoints_unchanged=True,curves=curves,minimum_wire_surface_gap_mm=minimum_wire-1.2,minimum_all29_terminal_surface_gap_mm=minimum_terminal-1.2,terminal_rows=terminal_rows,fabrication_released=False)
(HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['source_sha256','terminal_rows','curves']}))
