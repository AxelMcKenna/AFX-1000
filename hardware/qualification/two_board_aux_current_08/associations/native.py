"""Native UUID readback and unchanged connectivity, with separate schematic parity."""
import ast,hashlib,json,sys
from pathlib import Path
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children
from hardware.qualification.two_board_aux_current_08.associations.paths import expected_paths
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);D=H/'associations';BASE=H/'main_ldo/native-03/power_protection.kicad_pcb';C=D/'authored/power_protection.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
a=pcbnew.LoadBoard(str(BASE));b=pcbnew.LoadBoard(str(C));assert a is not None and b is not None
assert groups(a)==groups(b) and object_state(a)==object_state(b) and fill_state(a)==fill_state(b)
paths=expected_paths(D/'authored/power_protection.kicad_sch',H/'precision/native-01/candidate-netlist.xml');assert {f.GetReference():f.GetPath().AsString() for f in b.GetFootprints() if f.GetReference() in paths}==paths
p=run_recorded(['kicad-cli','pcb','drc','--schematic-parity','--format','json','--output',str(OUT/'parity.json'),str(C)],OUT/'parity-process',180,[C,*sorted((D/'authored').glob('*.kicad_sch'))]);assert p['status']=='passed'
report={'source_sha256':sha(BASE),'candidate_sha256':sha(C),'script_sha256':sha(Path(__file__)),'parity_sha256':sha(OUT/'parity.json'),'all_native_groups_objects_fills_unchanged':True,'native_uuid_associations':len(paths),'opens':groups(b)[1]};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
