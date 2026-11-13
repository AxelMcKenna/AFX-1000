"""Publish only verified additive S05/S06 sources; never select the root assembly."""
import hashlib,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3];A=H.parent/'workflow_adapter'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def bind(p):
 p=p.resolve();name=str(p.relative_to(R))
 if name in sources:return
 sources[name]=sha(p)
 if p.suffix=='.scad':
  for q in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
for name in ['routes.json','verification.json','mutation-tests.json','native-verification.json']:
 p=H/name;v=json.loads(p.read_text())
 for path,digest in v['source_sha256'].items():assert sha(R/path)==digest;bind(R/path)
 bind(p)
checks={}
for part in ['positive','positive_S05','positive_S06','receiving','wires','structure','controls_clearance','future_touch']:
 folder=H/'native'/(part+'-r1');p=folder/'result.json';v=json.loads(p.read_text())
 assert not v['runtime_failure'] and v['empty']==(not part.startswith('positive'))
 if part.startswith('positive'):assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for path,digest in v['source_sha256'].items():assert sha(R/path)==digest;bind(R/path)
 for artifact in folder.iterdir():
  if artifact.is_file():bind(artifact)
 checks[part]=str(p.relative_to(R))
for p in [Path(__file__),H/'README.md',A/'panel-input-r37.scad']:bind(p)
components=[]
for name,description in [('tap','D_J2001:9 CONTROL_02 to TAP terminal 1'),('auto','D_J2001:11 CONTROL_01 to AUTO terminal 1')]:
 components.append({'id':'panel_signal_r37_'+name,'source':str((A/'panel-input-r37.scad').relative_to(R)),'module':'panel_signal_r37_'+name,'role':'receiving','category':'formed_panel_input_wire','description':description,'uncertainty':'Requires r36 scene-zero holder relief and r34 S04 reservation. Full root screening, termination/support/tolerance and opening qualification pending.'})
for kind,old,scene in [('holders','base_button_holders',False),('mechanisms','controls_button_mechanisms',True)]:
 components.append({'id':'panel_'+kind+'_r37','source':str((A/'panel-input-r37.scad').relative_to(R)),'module':'panel_'+kind+'_r37','role':'receiving','category':'button_holder_relief_candidate','description':'Frozen '+kind+' with only verified r36 scene-zero source channels subtracted.','scene':scene,'replaces_component':old,'uncertainty':'Printed strength, creep, retention and manufacturing tolerance unqualified. Exact protected regions verified in r36; other poses and actual button bodies unchanged.'})
registry={'schema_version':1,'components':components,'source_sha256':sources,'local_verification':checks,'requires_roles':['panel_ground_r22_scene_links','panel_signal_r20_scene2','panel_signal_r21_scene1','panel_signal_r21_scene3','panel_signal_r34_scene4','panel_ground_r16_support','panel_ground_r18_guide','panel_ground_r17_selectors'],'replacement_contract':{'remove':['base_button_holders','controls_button_mechanisms'],'add':['panel_holders_r37','panel_mechanisms_r37'],'atomic_scene_false':'panel_holders_r37','composite_scene_true':'panel_mechanisms_r37','reason':'Both original roles contain scene-zero plastic obstruction. No mask or broad exclusion.'},'candidate_inventory_edges':[{'source':'D_J2001:9','target':'button_tap:1','net':'/D_CONTROLS/CONTROL_02'},{'source':'D_J2001:11','target':'button_auto:1','net':'/D_CONTROLS/CONTROL_01'}],'intentional_contacts':[],'selected':False,'fabrication_released':False,'complete_harness':False,'opening_slack_qualified':False}
(A/'panel-input-r37-registry.json').write_text(json.dumps(registry,indent=2)+'\n');print('Verified paired-input adapter; no assembly selection changed')
