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
for name in ['bows.json','verification.json']:
 p=HERE/name;v=json.loads(p.read_text())
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p)
checks={}
for part in ['terminal_clearance','original_terminal_conflict','wires','receiving','structure','positive']:
 p=HERE/'native'/(part+'-r3')/'result.json';v=json.loads(p.read_text());positive=part in ['positive','original_terminal_conflict'];assert not v['runtime_failure'] and v['empty']!=positive
 if positive:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['degenerate_triangles_excluded']==0 and v['mesh']['volume_mm3']>0
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p);checks[part]=str(p.relative_to(REPO))
for p in [ADAPTER/'ground-signal-clearance.scad',Path(__file__),HERE/'README.md',HERE/'SELF-REVIEW.md']:bind(p)
source=str((ADAPTER/'ground-signal-clearance.scad').relative_to(REPO))
out=dict(schema_version=1,components=[dict(id='panel_ground_r22_scene_links',source=source,module='panel_ground_r22_scene_links',role='receiving',category='formed_ground_wire_candidate',description='Nine scene ground links: four radius18 downward bows free signal terminals; other five unchanged',uncertainty='Physical joint approach/preparation, supports and opening allowance unqualified; root full screen pending.')],source_sha256=sources,local_verification=checks,supersedes_roles=['panel_ground_r15_scene_links'],intentional_contacts=[],electrical_adjacency_unchanged=True,fabrication_released=False,complete_harness=False,opening_slack_qualified=False)
(ADAPTER/'ground-signal-clearance-registry.json').write_text(json.dumps(out,indent=2)+'\n')
