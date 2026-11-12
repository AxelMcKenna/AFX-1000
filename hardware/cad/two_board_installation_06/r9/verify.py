"""Fresh native cooling-bay checks and analytic circular-route envelope bound."""
import hashlib,json,math
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
empty=['external_pod','external_parts','external_fans','external_ties','ties_pod','ties_parts','head_pod','head_parts','head_leads','lead_components','lead_controls','lead_fans','fan_pod_clearance','bushing_pod','bushing_shell','pod_components'];positive=['tie_positive'];solids=['pod','lead_cap','external_harness'];rows=[]
for name in empty+positive+solids:
 p=R/'native'/name/'result.json';d=json.loads(p.read_text());assert not d['runtime_failure']
 for f,h in d['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
 if name in empty:assert d['empty'] and d['mesh'] is None,name
 else:assert not d['empty'] and d['mesh']['closed_oriented_boundary'] and d['mesh']['volume_mm3']>0,name
 rows.append(dict(part=name,result_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
d=json.loads((R/'external-path.json').read_text());required=(d['nominal_bundle_radius_mm']+d['sagitta_upper_mm'])/math.cos(math.pi/32)**2;assert required<d['native_sphere_radius_mm'];assert d['turn_radius_mm']==10
out=dict(scope='External fan bay routing candidate, internal supports and terminal paths; actual factory exit transition and physical qualification remain',empty_checks=len(empty),positive_checks=1,closed_exports=3,overall_envelope_mm=[363.6,192.4,45.6],external_curve_length_mm=d['length_mm'],required_native_sphere_radius_mm=required,checks=rows,physical_tests_performed=False,thermal_qualified=False)
(R/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='checks'}))
