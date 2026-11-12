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
for name in ['routes.json','verification.json']:
 p=HERE/name;v=json.loads(p.read_text())
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p)
checks={}
for part in ['wires','structure','receiving','controls_clearance','positive','positive-S02','positive-S03']:
 p=HERE/'native'/(part+'-r13')/'result.json';v=json.loads(p.read_text());assert not v['runtime_failure'] and v['empty']==(not part.startswith('positive'))
 if part.startswith('positive'):assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p);checks[part]=str(p.relative_to(REPO))
for p in [ADAPTER/'adjacent-signals.scad',Path(__file__),HERE/'README.md',HERE/'SELF-REVIEW.md',HERE/'correction-history.json']:bind(p)
source=str((ADAPTER/'adjacent-signals.scad').relative_to(REPO))
components=[dict(id='panel_signal_r21_'+name,source=source,module='panel_signal_r21_'+name,role='receiving',category='formed_panel_input_wire',description=description,uncertainty='Requires r22 ground variant; physical terminal approach, supports, tolerance and fixed/lid opening allowance unqualified. Root full screen pending.') for name,description in [('scene1','D_J2002:1 CONTROL20 to scene1 terminal1'),('scene3','D_J2002:4 CONTROL22 to scene3 terminal1')]]
out=dict(schema_version=1,components=components,source_sha256=sources,local_verification=checks,requires_roles=['panel_ground_r22_scene_links','panel_signal_r20_scene2','panel_ground_r16_support','panel_ground_r18_guide','panel_ground_r17_selectors'],intentional_contacts=[],completed_inventory_edges=[dict(source='D_J2002:1',target='button_scene_1:1'),dict(source='D_J2002:4',target='button_scene_3:1')],fabrication_released=False,complete_harness=False,opening_slack_qualified=False)
(ADAPTER/'adjacent-signals-registry.json').write_text(json.dumps(out,indent=2)+'\n')
