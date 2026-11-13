"""Source-bound no-refill parity/DRC plus complete native state evidence."""
import ast,json,sys,hashlib
from pathlib import Path
import pcbnew
from hardware.qualification.two_board_aux_current_08.ldo_local.immutable_inputs import check_tree,check_recorded,sha
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);Q=H.parent;m=json.loads((H/'review-manifest-02.json').read_text());src=H/m['bundle_name'];check_tree(src,m)
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((Q/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
evidence={}
for label,path in [('source',Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb'),('candidate',src/'power_protection.kicad_pcb')]:
 b=pcbnew.LoadBoard(str(path));assert b is not None;gs,n=groups(b);evidence[label]={'board_sha256':sha(path),'groups':gs,'opens':n,'native_fill_state_sha256':hashlib.sha256(json.dumps(fill_state(b),sort_keys=True).encode()).hexdigest(),'objects':object_state(b),'pad_identities':{p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()}}
(OUT/'native-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
inputs=[src/'power_protection.kicad_pcb',*sorted(src.glob('*.kicad_sch'))];r=run_recorded(['kicad-cli','pcb','drc','--schematic-parity','--format','json','--output',str(OUT/'parity.json'),str(src/'power_protection.kicad_pcb')],OUT/'parity-process',120,inputs);check_recorded(r,{str(p):m['files'][str(p.relative_to(src))] for p in inputs});check_tree(src,m)
d=json.loads((OUT/'parity.json').read_text());result={'source_sha256':evidence['source']['board_sha256'],'candidate_sha256':evidence['candidate']['board_sha256'],'manifest_sha256':sha(H/'review-manifest-02.json'),'script_sha256':sha(Path(__file__)),'opens':evidence['candidate']['opens'],'violations':len(d['violations']),'schematic_parity':len(d['schematic_parity']),'violation_types':[v['type'] for v in d['violations']],'qualified':False};(OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
