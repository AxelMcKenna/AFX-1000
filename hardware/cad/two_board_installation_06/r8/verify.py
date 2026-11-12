"""Source-fresh checks for internal supports and separated terminal-wire routes."""
import hashlib,json
from pathlib import Path
import trimesh
R=Path(__file__).resolve().parent;REPO=R.parents[3]
sets={'native':(['components','shell','hardware','harness'],['retention_positive','positive','supports']),'native-terminal':(['supports','components','shell','mutual_wires'],['positive','harness'])};rows=[]
for folder,(empty,solid) in sets.items():
 for name in empty+solid:
  p=R/folder/name/'result.json';d=json.loads(p.read_text());assert not d['runtime_failure']
  for f,h in d['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
  if name in empty:assert d['empty'] and d['mesh'] is None,name
  else:assert not d['empty'] and d['mesh']['closed_oriented_boundary'] and d['mesh']['volume_mm3']>0,name
  rows.append(dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
parts=trimesh.load_mesh(R/'native/supports/supports.stl').split();assert len(parts)==2 and all(p.is_watertight and p.volume>0 for p in parts)
d=json.loads((R/'terminal-routes.json').read_text());assert d['accepted']
for f,h in d['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
out=dict(scope='Internal routing eyes and individual terminal transitions; external bay route and physical receiving still open',empty_checks=8,positive_checks=3,closed_exports=2,support_connected_parts=len(parts),terminal_wire_clearance_lower_bound_mm=d['minimum_pairwise_wire_clearance_lower_bound_mm'],minimum_terminal_bend_radius_mm=min(r['curvature_radius_lower_bound_mm'] for r in d['rows']),checks=rows,physical_tests_performed=False)
(R/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='checks'}))
