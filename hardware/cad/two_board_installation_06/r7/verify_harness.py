"""Reject stale, colliding or insufficiently conservative fan routing evidence."""
import hashlib,json,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent;REPO=R.parents[3]
empty=['route_0_obstacles','route_1_obstacles','mutual','shell','boards'];positive=['positive','harness'];checks=[]
for part in empty+positive:
 p=R/'native-harness'/part/'result.json';d=json.loads(p.read_text());assert not d['runtime_failure']
 for name,h in d['source_sha256'].items():assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==h,name
 if part in empty:assert d['empty'] and d['mesh'] is None,part
 else:assert not d['empty'] and d['mesh']['closed_oriented_boundary'] and d['mesh']['volume_mm3']>0,part
 checks.append(dict(part=part,result_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
proof=json.loads((R/'route-continuous-proof.json').read_text());assert proof['accepted_continuous_screen']
for name,h in proof['source_sha256'].items():
 p=REPO/'hardware/cad/two_board_print_01/capture.json' if name=='capture.json' else R/name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
limits={}
for ref,p in json.loads((R/'route-pair-search.json').read_text())['control_points'].items():
 a=20*np.diff(np.array(p),n=2,axis=0);deviation=np.linalg.norm(a,axis=1).max()/(8*160**2)
 required=(2.5+deviation)/math.cos(math.pi/24)**2;assert required<=2.56
 limits[ref]=dict(chord_deviation_bound_mm=float(deviation),required_native_sphere_radius_mm=float(required),used_native_sphere_radius_mm=2.56)
out=dict(scope='Geometric fan bundle candidate; final supports, physical bends, latest assembly cross-fit and operating harness remain open',empty_checks=len(empty),positive_controls=1,closed_export_solids=1,checks=checks,continuous_bounds=proof,mesh_inflation=limits,physical_tests_performed=False)
(R/'harness-verification.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS: 5 empty native checks, positive control, closed harness export and continuous route bounds')
