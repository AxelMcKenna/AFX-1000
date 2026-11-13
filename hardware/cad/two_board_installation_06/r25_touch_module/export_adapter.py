from pathlib import Path
import json,hashlib,re
from .verify import verify
H=Path(__file__).resolve().parent;R=H.parents[3];A=H.parent/'workflow_adapter';sources={}
def bind(p):
 p=p.resolve();n=str(p.relative_to(R))
 if n in sources:return
 sources[n]=hashlib.sha256(p.read_bytes()).hexdigest()
 if p.suffix=='.scad':
  for q in re.findall(r'(?:use|include)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
v=verify();c=json.loads((H/'contract.json').read_text())
s=A/'touch-module.scad';s.write_text('use <../r25_touch_module/module.scad>\nmodule panel_touch_c3_r25(){touch_c3_receiving();}\n')
for n in c['source_sha256']:bind(R/n)
for row in v['native'].values():bind(R/row['evidence'])
for p in [s,H/'contract.json',H/'verification.json',H/'README.md',H/'verify.py',Path(__file__)]:bind(p)
out=dict(schema_version=1,components=[dict(id='panel_touch_c3_r25',source=str(s.relative_to(R)),module='panel_touch_c3_r25',role='receiving',category='touch_module',description='Nominal C3 board with two actual holes; 13 component and36 solder-tail allocations at TC02 pose',uncertainty='Project height/tail allocations; current fastener selection, wiring and physical tolerances unqualified')],source_sha256=sources,supersedes_components=['controls_touch_module_receiving'],replaces_captured_context_ids=['touch_module_body_and_tail_reserve'],intentional_contacts=[],contact_proposals=[dict(components=['panel_touch_c3_r25','housing_shell'],reason='Only exact two Ø7.2 post annular seats at Z20; raw zero-volume witness retained; root must bind actual housing component ID and narrow numerical face mask if needed',evidence=v['native']['posts_board']['evidence'],status='SEAT_PLANE_ONLY_NO_BLANKET_EXCLUSION')],full_current_assembly_checked=False,fastener_selected=False,fabrication_released=False)
(A/'touch-module-registry.json').write_text(json.dumps(out,indent=2)+'\n')
