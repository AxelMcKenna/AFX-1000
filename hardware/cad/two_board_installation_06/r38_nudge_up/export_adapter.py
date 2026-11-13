"""Publish only verified additive S07 sources; never select the root assembly."""
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
for part in ['positive','receiving','wires','structure','controls_clearance','future_touch','original_controls']:
 folder=H/'native'/(part+'-r1');p=folder/'result.json';v=json.loads(p.read_text())
 assert not v['runtime_failure'] and v['empty']==(part!='positive')
 if part=='positive':assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for path,digest in v['source_sha256'].items():assert sha(R/path)==digest;bind(R/path)
 for artifact in folder.iterdir():
  if artifact.is_file():bind(artifact)
 checks[part]=str(p.relative_to(R))
for p in [Path(__file__),H/'README.md',A/'panel-input-r38.scad']:bind(p)
registry={'schema_version':1,'components':[{'id':'panel_signal_r38_nudge_up','source':str((A/'panel-input-r38.scad').relative_to(R)),'module':'panel_signal_r38_nudge_up','role':'receiving','category':'formed_panel_input_wire','description':'D_J2001:5 CONTROL_04 to NUDGE UP B3F terminal1; conditional R12 formed wire.','uncertainty':'Requires r22 and reserves S01-S04 and unselected r37 TAP/AUTO. Original unrelieved controls independently clear. Full root assembly screening, terminal/support/tolerance and lid-opening qualification remain open.'}],'source_sha256':sources,'local_verification':checks,'requires_roles':['panel_ground_r22_scene_links','panel_signal_r20_scene2','panel_signal_r21_scene1','panel_signal_r21_scene3','panel_ground_r16_support','panel_ground_r18_guide','panel_ground_r17_selectors','panel_signal_r34_scene4','panel_signal_r37_tap','panel_signal_r37_auto'],'candidate_inventory_edges':[{'source':'D_J2001:5','target':'button_nudge_up:1','net':'/D_CONTROLS/CONTROL_04'}],'intentional_contacts':[],'selected':False,'fabrication_released':False,'complete_harness':False,'opening_slack_qualified':False}
(A/'panel-input-r38-registry.json').write_text(json.dumps(registry,indent=2)+'\n');print('Verified S07 adapter; no assembly selection changed')
