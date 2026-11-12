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
for name in ['route.json','verification.json']:
 p=HERE/name;v=json.loads(p.read_text())
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p)
checks={}
for part in ['ground','structure','receiving','positive']:
 p=HERE/'native'/(part+'-r6')/'result.json';v=json.loads(p.read_text());assert not v['runtime_failure'] and v['empty']==(part!='positive')
 if part=='positive':assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p);checks[part]=str(p.relative_to(REPO))
for p in [ADAPTER/'scene-signal.scad',Path(__file__),HERE/'README.md',HERE/'SELF-REVIEW.md']:bind(p)
source=str((ADAPTER/'scene-signal.scad').relative_to(REPO))
out=dict(schema_version=1,components=[dict(id='panel_signal_r20_scene2',source=source,module='panel_signal_r20_scene2',role='receiving',category='formed_panel_input_wire',description='D_J2002:2 CONTROL_21 to scene2 terminal1 formed wire receiving path',uncertainty='Actual connector and solder transition, supports and fixed/lid service allowance unqualified; root full scene screen pending.')],source_sha256=sources,local_verification=checks,intentional_contacts=[],completed_inventory_edges=[dict(source='D_J2002:2',target='button_scene_2:1')],fabrication_released=False,complete_harness=False,opening_slack_qualified=False)
(ADAPTER/'scene-signal-registry.json').write_text(json.dumps(out,indent=2)+'\n')
