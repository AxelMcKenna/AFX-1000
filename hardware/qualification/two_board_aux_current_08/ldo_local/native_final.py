"""Read-only native parity on an immutable host-hashed bundle; no fill or save."""
import json,sys
from pathlib import Path
import pcbnew
from hardware.qualification.two_board_aux_current_08.ldo_local.immutable_inputs import check_tree,check_recorded,sha
from hardware.qualification.two_board_aux_current_08.ldo_local.associations import expected_paths
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);mp=H/'inputs-local-return-08.json';m=json.loads(mp.read_text());src=H/m['bundle_name'];check_tree(src,m);inputs=[src/'power_protection.kicad_pcb',*sorted(src.glob('*.kicad_sch'))];expected={str(p):m['files'][str(p.relative_to(src))] for p in inputs};p=run_recorded(['kicad-cli','pcb','drc','--schematic-parity','--format','json','--output',str(OUT/'parity.json'),str(src/'power_protection.kicad_pcb')],OUT/'parity-process',180,inputs);check_recorded(p,expected);check_tree(src,m)
b=pcbnew.LoadBoard(str(src/'power_protection.kicad_pcb'));assert b is not None;paths=expected_paths(src/'power_protection.kicad_sch',H/'native-07/candidate-netlist.xml');assert {f.GetReference():f.GetPath().AsString() for f in b.GetFootprints() if f.GetReference() in paths}==paths
pr=json.loads((OUT/'parity.json').read_text());assert not pr['schematic_parity'];assert len(pr['violations'])==4 and all(v['type']=='clearance' for v in pr['violations']),pr['violations']
r={'manifest_sha256':sha(mp),'script_sha256':sha(Path(__file__)),'helper_sha256':sha(H/'immutable_inputs.py'),'candidate_board_sha256':sha(src/'power_protection.kicad_pcb'),'parity_sha256':sha(OUT/'parity.json'),'host_native_all_input_hashes_equal':True,'uuid_associations':len(paths),'schematic_parity_issues':0,'unwaived_DSE_errors':4};(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
