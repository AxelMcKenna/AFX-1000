import json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3];A=H.parent/'workflow_adapter';c=json.loads((H/'direct-exits.json').read_text());v=json.loads((H/'direct-exits-verification.json').read_text());o=json.loads((H/'obstacle-sources.json').read_text());sources=dict(c['source_sha256'])
def bind(p):sources[str(p.relative_to(R))]=hashlib.sha256(p.read_bytes()).hexdigest()
s=A/'touch-source-exits.scad';s.write_text('use <../r27_touch_host/direct-exits.scad>\nmodule panel_touch_source_exits_r27(){touch_direct_exits();}\n')
for p in [s,H/'direct-exits.scad',H/'direct-exits.json',H/'direct-exits-verification.json',H/'verify_direct_exits.py',H/'obstacle-sources.json',H/'README.md',Path(__file__)]:bind(p)
for row in v['native'].values():
 bind(R/row['evidence'])
 for n,h in row['artifact_sha256'].items():bind(R/n)
sources[o['root_sensor_source']]=o['root_sensor_sha256']
out=dict(schema_version=1,components=[dict(id='panel_touch_source_exits_r27',source=str(s.relative_to(R)),module='panel_touch_source_exits_r27',role='receiving',category='wire_source_study',description='Four direct-solder candidate free-wire source corridors, D_J1009 only; endsX175 not connected toTrill',uncertainty='Source-only; solder preparation/strain/inline disconnect/downstream route unfinished')],source_sha256=sources,intentional_contacts=[],conditional_replacement_of_captured_component='D_J1009',replacement_not_adopted=True,completed_touch_wires=0,completed_panel_edges=0,full_current_assembly_checked=False,fabrication_released=False)
(A/'touch-source-exits-registry.json').write_text(json.dumps(out,indent=2)+'\n')
