"""Check native schematic/footprint parity without changing any placed board object."""
import hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew
from hardware.qualification.two_board_aux_current_08.associations.paths import expected_paths
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);D=H/'footprint_identity';A=D/'authored';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();board=A/'power_protection.kicad_pcb';before=sha(board)
for name,args in [('netlist',['sch','export','netlist','--format','kicadxml','--output',str(OUT/'candidate-netlist.xml'),str(A/'power_protection.kicad_sch')]),('erc',['sch','erc','--format','json','--output',str(OUT/'erc.json'),str(A/'power_protection.kicad_sch')]),('parity',['pcb','drc','--schematic-parity','--format','json','--output',str(OUT/'parity.json'),str(board)])]:
 if '--resume-readback' in sys.argv:
  p=json.loads((OUT/(name+'-process/process.json')).read_text());assert all(sha(Path(path))==h for path,h in p['input_sha256'].items())
 else:p=run_recorded(['kicad-cli',*args],OUT/(name+'-process'),180,[board,*sorted(A.glob('*.kicad_sch'))])
 assert p['status']=='passed'
b=pcbnew.LoadBoard(str(board));assert b is not None;paths=expected_paths(A/'power_protection.kicad_sch',OUT/'candidate-netlist.xml');fps={f.GetReference():f for f in b.GetFootprints()};xml=ET.parse(OUT/'candidate-netlist.xml')
for c in xml.findall('./components/comp'):
 ref=c.attrib['ref'];assert fps[ref].GetPath().AsString()==paths[ref] and fps[ref].GetFPIDAsString()==c.findtext('footprint'),ref
assert sha(board)==before
p=json.loads((OUT/'parity.json').read_text());assert not p['schematic_parity'];assert len(p['violations'])==4 and all(v['type']=='clearance' for v in p['violations'])
r={'candidate_board_sha256':before,'native_electrical_associations_and_footprint_ids':len(paths),'schematic_parity_issues':0,'board_unchanged':True,'script_sha256':sha(Path(__file__)),'result_sha256':{n:sha(OUT/n) for n in ['candidate-netlist.xml','erc.json','parity.json']},'qualified':False};(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
