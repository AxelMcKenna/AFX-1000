"""Export only the locally verified candidate, without revising frozen adapters."""
from pathlib import Path
import json,hashlib,re
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
ADAPTER=HERE.parent/'workflow_adapter'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def bind(p):
 p=p.resolve();key=str(p.relative_to(REPO))
 if key in sources:return
 sources[key]=sha(p)
 if p.suffix=='.scad':
  for q in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
bind(ADAPTER/'ground.scad')
for name in ['ground-routes.json','verification.json','README.md','build.py','verify.py','probe.scad','run.py','build_adapter.py']:bind(HERE/name)
g=json.loads((HERE/'ground-routes.json').read_text())
for p,h in g['source_sha256'].items():assert sha(REPO/p)==h;bind(REPO/p)
checks={}
for part in ('structure','allocations','mates','positive'):
 p=HERE/'native'/(part+'-r2')/'result.json';result=json.loads(p.read_text())
 assert not result['runtime_failure']
 assert result['empty']==(part!='positive')
 assert all(sha(REPO/k)==h for k,h in result['source_sha256'].items())
 bind(p);checks[part]=str(p.relative_to(REPO))
components=[]
for kind in ('wires','splice'):
 components.append({'id':'panel_ground_r12_'+kind,'source':str((ADAPTER/'ground.scad').relative_to(REPO)), 'module':'panel_ground_r12_'+kind,'role':'receiving','category':'conditional_ground_harness','description': '32 routed ground wire receiving paths' if kind=='wires' else 'One TE34130/TE505872P034 project receiving reservation','uncertainty':'Sharp polyline path candidate. Bend formation, strain supports, lid-opening slack, exact terminal exits and D_J2003 mating are unresolved. Minimum wire surface gap 0.11186 mm; full current assembly intersections pending.'})
out={'schema_version':1,'owner':'installation','components':components,'source_sha256':sources,'intentional_contacts':[], 'local_verification':checks,'electrical_topology':{'ground':str((HERE/'ground-routes.json').relative_to(REPO)), 'ground_splices':1,'ground_wires':32,'buttons':29,'selector_commons':2,'daisychain_uses_internal_pair':[3,4], 'supersedes_only':'r11 ground tree and intermediate r10 terminal-4 no-wire assignment','panel_schematic_update_required':True}, 'fabrication_released':False,'full_assembly_fit_verified':False,'positive_mesh_closed_oriented_boundary':False,'native_boolean_input_policy':'Use original SCAD; combined positive STL has 10 bad edges and is visual evidence only.'}
(ADAPTER/'ground-registry.json').write_text(json.dumps(out,indent=2)+'\n')
print('2 conditional roles;',len(sources),'bound files')
