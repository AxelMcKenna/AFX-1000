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
bind(ADAPTER/'right-ground.scad')
for p in [Path(__file__),HERE/'README.md',HERE/'SELF-REVIEW.md',HERE/'right-routes.json',HERE/'verification.json',HERE/'ground-contract.json']:bind(p)
for name in ('right-routes.json','verification.json','ground-contract.json'):
 for p,h in json.loads((HERE/name).read_text())['source_sha256'].items():assert sha(REPO/p)==h;bind(REPO/p)
checks={}
for part in ('structure','allocations','mates','outside','contact_positive'):
 p=HERE/'native'/(part+'-r2')/'result.json';v=json.loads(p.read_text());assert not v['runtime_failure'] and v['empty']==(part!='contact_positive')
 for k,h in v['source_sha256'].items():assert sha(REPO/k)==h;bind(REPO/k)
 bind(p);checks[part]=str(p.relative_to(REPO))
components=[]
for suffix,desc in [('right_feed','Complete formed D_J2002:16 to scene2:4 receiving path'),('scene_links','Nine formed inter-scene wire receiving paths'),('selector_wires','Scene3 to splice plus two selector return wire receiving paths'),('splice','TE34130/TE505872P034 project receiving envelope25xdiameter6.2 at[293,32,29.5]')]:
 components.append({'id':'panel_ground_r15_'+suffix,'source':str((ADAPTER/'right-ground.scad').relative_to(REPO)),'module':'panel_ground_r15_'+suffix,'role':'receiving','category':'formed_ground_wire_candidate','description':desc,'uncertainty':'Supports, strain relief, lid opening, exact terminal preparation and actual crimp envelope unqualified. Full root assembly validation pending. Use original SCAD.'})
contacts=[{'components':['panel_ground_r15_selector_wires','panel_ground_r15_splice'],'reason':'Only three explicit wire entry/exit receiving ports terminate into the splice sleeve. No blanket pair exclusion.','evidence':str((HERE/'right-routes.json').relative_to(REPO)),'blanket_pair_exclusion':False,'contact_mask_contract':{'kind':'union_of_spheres','centers_mm':[[280.5,32,29.5],[305.5,31,29.5],[305.5,33,29.5]],'radius_mm':.62}}]
out={'schema_version':1,'components':components,'source_sha256':sources,'intentional_contacts':contacts,'local_verification':checks,'supersedes_roles':['panel_ground_r14_right_exit','panel_ground_r12_splice'],'electrical_contract':str((HERE/'ground-contract.json').relative_to(REPO)),'ground_endpoint_graph_complete':True,'complete_harness':False,'supports_qualified':False,'opening_slack_qualified':False,'fabrication_released':False,'native_mesh_policy':'Use original SCAD; root integration must validate current positive operands.'}
(ADAPTER/'right-ground-registry.json').write_text(json.dumps(out,indent=2)+'\n')
