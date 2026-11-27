"""Publish only verified additive S08/S09 sources; never select the root assembly."""
import hashlib,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3];A=H.parent/'workflow_adapter'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def bind(p):
 p=p.resolve();name=str(p.relative_to(R))
 if name in sources:return
 sources[name]=sha(p)
 # Rejected SCAD snapshots are evidence bytes; native verifier resolves original compile scope.
 if p.suffix=='.scad' and not any(x.startswith('rejected-r') for x in p.parts):
  for q in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
for name in ['routes.json','verification.json','mutation-tests.json','native-verification.json']:
 p=H/name;v=json.loads(p.read_text())
 for path,digest in v['source_sha256'].items():assert sha(R/path)==digest;bind(R/path)
 bind(p)
checks={}
for part in ['positive','positive_S10','positive_S11','positive_clearance','receiving','wires','structure','controls_clearance','future_touch','original_controls','lid_guide']:
 folder=H/'native'/(part+'-r7');p=folder/'result.json';v=json.loads(p.read_text())
 assert not v['runtime_failure'] and v['empty']==(not part.startswith('positive'))
 if part.startswith('positive'):assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for path,digest in v['source_sha256'].items():assert sha(R/path)==digest;bind(R/path)
 for artifact in folder.iterdir():
  if artifact.is_file():bind(artifact)
 checks[part]=str(p.relative_to(R))
for p in [Path(__file__),H/'README.md',A/'panel-input-r40.scad']:bind(p)
components=[]
for index in [2,3]:
 components.append({'id':'panel_signal_r40_isolate'+str(index),'source':str((A/'panel-input-r40.scad').relative_to(R)),'module':'panel_signal_r40_isolate'+str(index),'role':'receiving','category':'formed_panel_input_wire','description':'D_J2001:'+str(2+2*index)+' CONTROL_'+str(7+index).zfill(2)+' to isolate '+str(index)+' terminal 1; conditional R12 wire.','uncertainty':'Reserves S01–S09 and r22 ground. Original unrelieved controls independently audited. Full root screening including current nominal main-board fastener stacks and their receiving role, physical terminations/support/tolerance and opening qualification pending.'})
registry={'schema_version':1,'components':components,'source_sha256':sources,'local_verification':checks,'requires_roles':['panel_ground_r22_scene_links','panel_signal_r20_scene2','panel_signal_r21_scene1','panel_signal_r21_scene3','panel_signal_r34_scene4','panel_signal_r37_tap','panel_signal_r37_auto','panel_signal_r38_nudge_up','panel_ground_r16_support','panel_ground_r18_guide','panel_ground_r17_selectors','panel_signal_r39_isolate0','panel_signal_r39_isolate1','main_fastener_receiving_r1','base_board_heads'],'candidate_inventory_edges':[{'source':'D_J2001:'+str(2+2*i),'target':'button_isolate_'+str(i)+':1','net':'/D_CONTROLS/CONTROL_'+str(7+i).zfill(2)} for i in [2,3]],'intentional_contacts':[],'selected':False,'fabrication_released':False,'complete_harness':False,'opening_slack_qualified':False}
(A/'panel-input-r40-registry.json').write_text(json.dumps(registry,indent=2)+'\n');print('Verified pair adapter; no root selection changed')
