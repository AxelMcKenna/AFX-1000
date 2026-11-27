from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
verification=json.loads((HERE/'verification.json').read_text())
contract=json.loads((HERE/'exit-contract.json').read_text())
sources={**verification['source_sha256'],**contract['source_sha256']}
for p in [Path(__file__),HERE/'verification.json',HERE/'README.md']:
 sources[str(p.relative_to(REPO))]=hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in sources.items():assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
out={'schema_version':1,'components':[{'id':'panel_ground_r13_exits','source':str((HERE/'exits.scad').relative_to(REPO)),'module':'panel_ground_selected_exits','role':'receiving','category':'partial_formed_wire_routes','description':'Two source escape quarter circles with12mm centerline radius; selected D_J2002 pins15/16 at250/270degrees. Replaces initial r12 root transitions only; not a complete harness.','uncertainty':'Remaining wires, supports and service slack not implemented. Conditional female stack and wire exit datum; full current assembly intersection checks pending.'}],'source_sha256':sources,'intentional_contacts':[],'complete_harness':False,'fabrication_released':False,'replaces_only':'Initial D_J2002 root transitions in r12; do not overlay both representations as one harness.'}
(HERE.parent/'workflow_adapter/formed-ground-registry.json').write_text(json.dumps(out,indent=2)+'\n')
