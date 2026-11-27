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
checks={}
for part,group in [(p,'all') for p in ['selectors','wires','receiving','structure','positive']]+[('rotation_stop','cw'),('rotation_stop','ccw')]:
 p=HERE/'native'/(part+'-'+group+'-r3')/'result.json';v=json.loads(p.read_text());positive=part in ['positive','rotation_stop'];assert not v['runtime_failure'] and v['empty']!=positive
 if positive:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 for key,h in v['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
 bind(p);checks[part+'_'+group]=str(p.relative_to(REPO))
for p in [ADAPTER/'selector-key.scad',ADAPTER/'selector-support.scad',Path(__file__),HERE/'README.md',HERE/'SELF-REVIEW.md']:bind(p)
prior=json.loads((ADAPTER/'selector-support-registry.json').read_text())
for key,h in prior['source_sha256'].items():assert sha(REPO/key)==h;bind(REPO/key)
bind(ADAPTER/'selector-support-registry.json')
source=str((ADAPTER/'selector-key.scad').relative_to(REPO))
out=dict(schema_version=1,components=[dict(id='panel_ground_r18_guide',source=source,module='panel_ground_r18_guide',role='receiving',category='selector_wire_support_candidate',description='R17 curved wire guide with positive rear/east PCB-edge rotation stops',uncertainty='Nominal positive rotation constraint verified; PCB/print strength, tolerance, abrasion and axial strain relief unqualified.')],source_sha256=sources,local_verification=checks,supersedes_roles=['panel_ground_r17_guide'],requires_roles=['panel_ground_r17_selectors','panel_ground_r16_support'],intentional_contacts=[dict(components=['panel_ground_r18_guide','panel_ground_r17_selectors'],reason='Unchanged release rear PCB underside and washer seating planes; edge stops have nominal clearance.',evidence=str((HERE/'README.md').relative_to(REPO)),blanket_pair_exclusion=False,contact_mask_contract=dict(kind='scad_module',source='hardware/cad/two_board_installation_06/workflow_adapter/selector-support.scad',module='panel_ground_r17_seat_mask'))],fabrication_released=False,supports_qualified=False,axial_strain_relief_qualified=False,opening_slack_qualified=False,complete_harness=False)
(ADAPTER/'selector-key-registry.json').write_text(json.dumps(out,indent=2)+'\n')
