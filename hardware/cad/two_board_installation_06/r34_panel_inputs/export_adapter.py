"""Publish only verified additive S04 sources; never select the root assembly."""
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
for part in ['positive','receiving','wires','structure','controls_clearance','future_touch']:
 folder=H/'native'/(part+'-r6');p=folder/'result.json';v=json.loads(p.read_text())
 assert not v['runtime_failure'] and v['empty']==(part!='positive')
 if part=='positive':assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for path,digest in v['source_sha256'].items():assert sha(R/path)==digest;bind(R/path)
 for artifact in folder.iterdir():
  if artifact.is_file():bind(artifact)
 checks[part]=str(p.relative_to(R))
for p in [Path(__file__),H/'README.md',A/'panel-input-r34.scad']:bind(p)
registry={'schema_version':1,'components':[{'id':'panel_signal_r34_scene4','source':str((A/'panel-input-r34.scad').relative_to(R)),'module':'panel_signal_r34_scene4','role':'receiving','category':'formed_panel_input_wire','description':'D_J2002:6 CONTROL_23 to scene4 B3F terminal1; conditional R12 formed wire.','uncertainty':'Requires r22 and preserves S01-S03. Full root assembly screening, terminal/support/tolerance and lid-opening qualification remain open.'}],'source_sha256':sources,'local_verification':checks,'requires_roles':['panel_ground_r22_scene_links','panel_signal_r20_scene2','panel_signal_r21_scene1','panel_signal_r21_scene3','panel_ground_r16_support','panel_ground_r18_guide','panel_ground_r17_selectors'],'candidate_inventory_edges':[{'source':'D_J2002:6','target':'button_scene_4:1','net':'/D_CONTROLS/CONTROL_23'}],'intentional_contacts':[],'selected':False,'fabrication_released':False,'complete_harness':False,'opening_slack_qualified':False}
(A/'panel-input-r34-registry.json').write_text(json.dumps(registry,indent=2)+'\n');print('Verified S04 adapter; no assembly selection changed')
