from pathlib import Path
import json,hashlib,re
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];ADAPTER=HERE.parent/'workflow_adapter'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def bind(p):
 p=p.resolve();key=str(p.relative_to(REPO))
 if key in sources:return
 sources[key]=sha(p)
 if p.suffix=='.scad':
  for q in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
bind(ADAPTER/'left-ground.scad')
for p in [Path(__file__),HERE/'README.md',HERE/'left-routes.json',HERE/'verification.json']:bind(p)
for name in ('left-routes.json','verification.json'):
 for p,h in json.loads((HERE/name).read_text())['source_sha256'].items():assert sha(REPO/p)==h;bind(REPO/p)
checks={}
for group in ('feed','links'):
 for part in ('structure','allocations','positive'):
  p=HERE/'native'/(part+'-'+group+'-r3')/'result.json';v=json.loads(p.read_text())
  assert not v['runtime_failure'] and v['empty']==(part!='positive')
  assert all(sha(REPO/k)==h for k,h in v['source_sha256'].items())
  bind(p);checks[group+'_'+part]=str(p.relative_to(REPO))
components=[]
for suffix,desc in [('left_feed','Complete formed D_J2002:15 to quantize ground feed'),('left_links','18 formed inter-button wires serving all19 non-scene buttons'),('right_exit','Unchanged radius12 D_J2002:16 source exit only; downstream scene/selector route pending')]:
 components.append({'id':'panel_ground_r14_'+suffix,'source':str((ADAPTER/'left-ground.scad').relative_to(REPO)),'module':'panel_ground_r14_'+suffix,'role':'receiving','category':'formed_ground_wire_candidate','description':desc,'uncertainty':'Supports, strain relief, service slack and exact terminal preparation unqualified. Left wire surface gap0.4mm; root full assembly verification pending. Links must use original SCAD for Booleans.'})
out={'schema_version':1,'components':components,'source_sha256':sources,'intentional_contacts':[],'local_verification':checks,'supersedes_roles':['panel_ground_r13_exits','panel_ground_r12_wires'],'electrical_contract':str((HERE/'left-routes.json').relative_to(REPO)),'partial_branch_receivers':19,'complete_harness':False,'fabrication_released':False,'native_mesh_policy':{'left_feed':'Closed oriented positive witness','left_links':'16 bad edges in positive STL; original source required for Boolean use'}}
(ADAPTER/'left-ground-registry.json').write_text(json.dumps(out,indent=2)+'\n')
