"""Check exact delegation, immutable source closure and current selected PCB hashes."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
d=json.loads((R/'components.json').read_text());scad=(R/'sensor.scad').read_text()
expected={'sensor_fixture':'carrier_complete();sensor_cap();sensor_screws();cap_screws();','sensor_substrate':'sensor_board();','sensor_population':'actual_population();','sensor_harness':'tbh05_harness_complete();','sensor_lever_bracket':'spring_bracket_world();','sensor_lever_guard':'guard();','sensor_lever_motion':'spring_arm_sweep(.5);','sensor_spring_motion':'spring_installed_envelope();'}
actual=dict(re.findall(r'module\s+(\w+)\(\)\{([^{}]*)\}',scad));assert actual==expected
assert {x['id']for x in d['components']}==set(expected)
all_modules=set()
for name,h in d['sources_sha256'].items():
 p=REPO/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
 all_modules.update(re.findall(r'module\s+(\w+)\(',p.read_text()))
for calls in expected.values():
 for name in re.findall(r'(\w+)\(',calls):assert name in all_modules,name
for key,path in d['selected_pcb'].items():assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==d['selected_pcb_sha256'][key]
assert [x['ref']for x in d['replacement_hardware']]==['D_H2','D_H5']
assert all(c['mode']in ['seating_boundary_only','electronic_attachment','termination_region_only','attachment_only']for c in d['intentional_contacts'])
report=dict(adapter_delegation_exact=True,all_called_modules_in_frozen_closure=True,source_bindings=len(d['sources_sha256']),selected_pcb_hashes_match=True,geometry_changed=False,scope='Structural adapter and source-freshness validation; existing native geometry evidence stays authoritative, root unified runner owns combined rendering/checks',source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/'components.json',R/'sensor.scad',Path(__file__)]})
(R/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS8 exactdelegation roles,14SCAD source bindings,2selected PCB hashes')
