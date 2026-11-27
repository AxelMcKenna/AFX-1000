"""Source-bound conditional support registry; fail closed on stale native checks."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];ADAPTER=HERE.parent/'workflow_adapter'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def bind(p):
 p=p.resolve();key=str(p.relative_to(REPO))
 if key in sources:return
 sources[key]=sha(p)
 if p.suffix=='.scad':
  for q in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
checks={}
for part in ['selectors','ground_wires','splice_body','allocations','structure','cap_hardware','halves','saddle_positive','cap_positive','positive']+['retention-'+d for d in ['up','down','left','right']]:
 name=part+'-r4';p=HERE/'native'/name/'result.json';v=json.loads(p.read_text())
 positive='positive' in part or part.startswith('retention')
 assert not v['runtime_failure'] and v['empty']!=positive
 if positive:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p);checks[part]=str(p.relative_to(REPO))
for p in [ADAPTER/'ground-support.scad',Path(__file__),HERE/'README.md',HERE/'SELF-REVIEW.md']:bind(p)
source=str((ADAPTER/'ground-support.scad').relative_to(REPO))
components=[dict(id='panel_ground_r16_'+suffix,source=source,module='panel_ground_r16_'+suffix,role='receiving',category='lid_splice_support_candidate',description=desc,uncertainty='Actual sleeve, PCB/print strength, tolerances, tool access and retention unqualified; installed geometry only.') for suffix,desc in [('support','Two-piece splice cage with two M2x8 cap screws'),('selectors','Original selectors with settings M2x12 replacement hardware; release hardware unchanged')]]
out=dict(schema_version=1,components=components,source_sha256=sources,local_verification=checks,supersedes_roles=['controls_selectors'],intentional_contacts=[dict(components=['panel_ground_r16_support','panel_ground_r16_selectors'],reason='Only selector PCB underside feet and washer seating planes; no blanket pair exclusion.',evidence=str((HERE/'README.md').relative_to(REPO)),blanket_pair_exclusion=False,contact_mask_contract=dict(kind='scad_module',source=source,module='panel_ground_r16_selector_contact_mask'))],fabrication_released=False,supports_qualified=False,opening_slack_qualified=False,complete_harness=False)
(ADAPTER/'ground-support-registry.json').write_text(json.dumps(out,indent=2)+'\n')
