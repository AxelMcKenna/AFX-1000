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
contract=json.loads((HERE/'curve-source.json').read_text());assert sha(REPO/contract['source'])==contract['sha256'];bind(REPO/contract['source'])
checks={}
for part in ['selectors','wires','receiving','structure','positive']:
 p=HERE/'native'/(part+'-r1')/'result.json';v=json.loads(p.read_text());assert not v['runtime_failure'] and v['empty']==(part!='positive')
 if part=='positive':assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p);checks[part]=str(p.relative_to(REPO))
for p in [ADAPTER/'selector-support.scad',Path(__file__),HERE/'build.py',HERE/'curve-source.json',HERE/'README.md',HERE/'SELF-REVIEW.md']:bind(p)
source=str((ADAPTER/'selector-support.scad').relative_to(REPO))
components=[dict(id='panel_ground_r17_'+suffix,source=source,module='panel_ground_r17_'+suffix,role='receiving',category='selector_wire_support_candidate',description=desc,uncertainty='Single screw rotation, PCB/print strength, bore abrasion and actual routing unqualified; positional guide only, no axial pull rating.') for suffix,desc in [('guide','Lid-carried curved R13 positional guide'),('selectors','r16 selectors with release rear M2x12 replacement; all original PCB/body datums retained')]]
out=dict(schema_version=1,components=components,source_sha256=sources,local_verification=checks,supersedes_roles=['panel_ground_r16_selectors'],requires_roles=['panel_ground_r16_support'],intentional_contacts=[dict(components=['panel_ground_r17_guide','panel_ground_r17_selectors'],reason='Only release rear PCB underside and washer seating planes.',evidence=str((HERE/'README.md').relative_to(REPO)),blanket_pair_exclusion=False,contact_mask_contract=dict(kind='scad_module',source=source,module='panel_ground_r17_seat_mask'))],fabrication_released=False,supports_qualified=False,axial_strain_relief_qualified=False,opening_slack_qualified=False,complete_harness=False)
out['intentional_contacts'].append(dict(components=['panel_ground_r16_support','panel_ground_r17_selectors'],reason='Inherited r16 settings PCB and washer seat planes, unchanged by rear release screw replacement.',evidence='hardware/cad/two_board_installation_06/r16_ground_support/README.md',blanket_pair_exclusion=False,contact_mask_contract=dict(kind='scad_module',source='hardware/cad/two_board_installation_06/workflow_adapter/ground-support.scad',module='panel_ground_r16_selector_contact_mask')))
bind(ADAPTER/'ground-support.scad')
(ADAPTER/'selector-support-registry.json').write_text(json.dumps(out,indent=2)+'\n')
