from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;R=H.parents[3];A=H.parent/'workflow_adapter';sources={}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bind(p):
 p=p.resolve();key=str(p.relative_to(R))
 if key in sources:return
 sources[key]=sha(p)
 if p.suffix=='.scad':
  for q in re.findall(r'(?:use|include)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
c=json.loads((H/'contract.json').read_text());v=json.loads((H/'verification.json').read_text())
for data in [c,v]:
 for key,s in data['source_sha256'].items():assert sha(R/key)==s;bind(R/key)
for check in v['native'].values():p=R/check['evidence'];assert sha(p)==check['sha256'];bind(p)
source=A/'fan-mates.scad';source.write_text('use <../r24_fan_mates/harness.scad>\nuse <../r24_fan_mates/mates.scad>\nmodule cooling_internal_harness_r24(){reconciled_fan_harness();}\nmodule cooling_fan_mates_r24(){conditional_fan_connectors();}\nmodule cooling_fan_entries_r24(){fan_entry_masks();}\n')
for p in [source,H/'contract.json',H/'verification.json',H/'README.md',Path(__file__)]:bind(p)
sources[c['native_pcb']['path']]=c['native_pcb']['sha256']
components=[dict(id=n,source=str(source.relative_to(R)),module=n,role='receiving',category=category,description=d,uncertainty='Conditional body projection<=10.5mm; actual assembled maximum and wire-entry registration unqualified. Formation, termination and service acceptance remain open.') for n,category,d in [('cooling_internal_harness_r24','wire_envelope','Original bundle cells through exact fanout ownership start, unchanged six individual wire paths'),('cooling_fan_mates_r24','fan_mating_connectors','Only F_J202/F_J203 conditional receiving bodies; preserve full captured XY and bottomZ')]]
out=dict(schema_version=1,components=components,source_sha256=sources,supersedes_components=['cooling_internal_harness'],replaces_captured_component_references=['F_J202','F_J203'],tail_allocations_unchanged=True,intentional_contacts=[],contact_proposals=[dict(components=['cooling_internal_harness_r24','cooling_fan_mates_r24'],mask_source=str(source.relative_to(R)),mask_module='cooling_fan_entries_r24',reason='Conditional six own-wire straight entries only; actual cavity registration must be established',evidence=str((H/'verification.json').relative_to(R)),status='CONDITIONAL_NOT_QUALIFIED')],physical_wire_routes_unchanged=True,full_current_assembly_checked=False,fabrication_released=False)
(A/'fan-mates-registry.json').write_text(json.dumps(out,indent=2)+'\n')
