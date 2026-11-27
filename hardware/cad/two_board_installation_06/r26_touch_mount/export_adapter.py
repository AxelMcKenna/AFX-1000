import json,hashlib,re
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3];A=H.parent/'workflow_adapter'
c=json.loads((H/'contract.json').read_text());v=json.loads((H/'verification.json').read_text());sources=dict(c['source_sha256'])
def bind(p):
 n=str(p.relative_to(R));sources[n]=hashlib.sha256(p.read_bytes()).hexdigest()
s=A/'touch-mount.scad';s.write_text('use <../r26_touch_mount/mount.scad>\nmodule panel_touch_hardware_r26(){touch_fastener_nominal();}\nmodule panel_touch_upper_receiving_r26(){touch_upper_fastener_receiving();}\nmodule panel_touch_nut_cuts_r26(){touch_nut_pocket_extension();}\n')
for p in [s,H/'mount.scad',H/'contract.json',H/'verification.json',H/'README.md',H/'verify.py',Path(__file__)]:bind(p)
for row in v['native'].values():
 bind(R/row['evidence'])
 for n,h in row['artifact_sha256'].items():
  assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h
  bind(R/n)
components=[dict(id='panel_touch_hardware_r26',source=str(s.relative_to(R)),module='panel_touch_hardware_r26',role='receiving',category='touch_mount_hardware',description='Candidate exact sourced nominal screw/washer/nut stack at two C3 mounts; requires two pocket extensions',uncertainty='Conditional length/print/board/tip/registration acceptance requirements; strength, torque, retention, assembly access unqualified')]
out=dict(schema_version=1,components=components,source_sha256=sources,intentional_contacts=[],required_shell_revision=dict(operation='difference',source=str(s.relative_to(R)),module='panel_touch_nut_cuts_r26',scope='Only two existing AF4.2 pocket ceilings1.8→4.8'),required_hardware_replacement='Only two touch heads in board_heads(); retain all main PCB heads',additional_clearance_probe=dict(module='panel_touch_upper_receiving_r26',source=str(s.relative_to(R))),nominal_hardware_not_full_tolerance_envelope=True,root_selection_changed=False,full_assembly_checked=False,fabrication_released=False)
(A/'touch-mount-registry.json').write_text(json.dumps(out,indent=2)+'\n')
