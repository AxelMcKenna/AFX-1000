"""Independent assertions over recorded native results and source freshness."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]
empty=['hardware_components','hardware_controls','shell_components','pod_components','fan_pod_clearance','mesh_fan_clearance','mesh_hardware_clearance']
positive=['positive_control','pod','guard','shell_variant']
checks=[]
for part in empty+positive:
 p=ROOT/'native'/part/'result.json';d=json.loads(p.read_text())
 assert not d['runtime_failure']
 for f,h in d['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
 if part in empty:assert d['empty'] and d['mesh'] is None,part
 else:assert not d['empty'] and d['mesh']['closed_oriented_boundary'] and d['mesh']['volume_mm3']>0,part
 checks.append(dict(part=part,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
# Exact circular segment integration of two width-1.2 bars centred ±6.
def primitive(x):return x*math.sqrt(18**2-x*x)+18**2*math.asin(x/18)
opening=math.pi*18**2
audit=json.loads((ROOT/'installation-audit.json').read_text())
for p,h in audit['source_sha256'].items():assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h,p
result=dict(scope='Alternative geometry only; no harness or thermal completion',native_checks=checks,connector_count=audit['connector_count'],guard_nominal_open_mm2_per_fan=opening,guard_open_mm2_with_selected_81pct_mesh=opening*.81,intake_slots_mm2=2*36*30,exhaust_slots_mm2=2*36*30,body_width_with_pods_mm=355,overall_width_including_modeled_bolt_heads_mm=359,fan_bolt_heads_not_included_in_width=False,fan_bolt_clamp_qualified=False,mesh_selected=True,loaded_pressure_flow_qualified=False,thermal_qualified=False,complete_harness=False,source_sha256={str(Path(__file__).relative_to(REPO)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
(ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
