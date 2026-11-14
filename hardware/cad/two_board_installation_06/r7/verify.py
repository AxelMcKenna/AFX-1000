"""Source-fresh independent audit of the r7 mechanical installation evidence."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
empty=['bushing_pod','bushing_shell','tie_bridge_clearance','exhaust_components','exhaust_controls','exhaust_lever','exhaust_mesh_frame','lead_components','lead_controls','lead_fans','pod_components','shell_components','fan_pod_clearance','mesh_fan_clearance','mesh_hardware_clearance','hardware_components','hardware_controls']
positive=['bushing_retention_positive','tie_retention_positive','exhaust_positive','exhaust_escape_out','exhaust_escape_in','bushing_escape_out']
solids=['lead_cap','lead_bushing','exhaust_frame','pod','guard','shell_variant']
rows=[]
for name in empty+positive+solids:
 p=R/'native'/name/'result.json';d=json.loads(p.read_text())
 assert not d['runtime_failure']
 for f,h in d['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
 if name in empty:assert d['empty'] and d['mesh'] is None,name
 else:assert not d['empty'] and d['mesh']['closed_oriented_boundary'] and d['mesh']['volume_mm3']>0,name
 rows.append(dict(part=name,result_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
r=dict(scope='r7 external cooling mechanical candidate; full harness/thermal acceptance pending',empty_checks=len(empty),positive_controls=len(positive),closed_export_solids=len(solids),checks=rows,overall_width_mm=363.6,depth_mm=192.4,body_height_mm=45.6,physical_tests_performed=False,thermal_qualified=False,source_sha256={str(Path(__file__).relative_to(REPO)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
(R/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['checks','source_sha256']},indent=2))
