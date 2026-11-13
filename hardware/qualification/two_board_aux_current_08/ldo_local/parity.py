"""Separate native schematic-parity and UUID readback gate; no board update/save."""
import json,sys,shutil,hashlib
from pathlib import Path
import pcbnew
from .associations import expected_paths
from ..held_cell.process_adapter import run_recorded
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'native-07';SRC=H/'authored-v2';OUT.mkdir(exist_ok=True)
for p in SRC.glob('*.kicad_sch'):shutil.copy2(p,OUT/p.name)
for n in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
for n in ['symbols','libraries']:(OUT/n).symlink_to((SRC/n).resolve(),target_is_directory=True)
shutil.copy2(SRC/'sym-lib-table',OUT/'sym-lib-table');before=sha(OUT/'power_protection.kicad_pcb');b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));assert b is not None;expected=expected_paths(SRC/'power_protection.kicad_sch',BASE/'candidate-netlist.xml');actual={f.GetReference():f.GetPath().AsString() for f in b.GetFootprints() if f.GetReference() in expected};assert actual==expected
import xml.etree.ElementTree as ET
fps={f.GetReference():f for f in b.GetFootprints()}
for c in ET.parse(BASE/'candidate-netlist.xml').findall('./components/comp'):assert fps[c.attrib['ref']].GetFPIDAsString()==c.findtext('footprint')
inputs=[OUT/'power_protection.kicad_pcb',*sorted(OUT.glob('*.kicad_sch'))];process=run_recorded(['kicad-cli','pcb','drc','--schematic-parity','--format','json','--output',str(OUT/'parity.json'),str(OUT/'power_protection.kicad_pcb')],OUT/'parity-process',180,inputs);assert process['status']=='passed' and sha(OUT/'power_protection.kicad_pcb')==before
for n,target in [('libraries','../../shared_cutover/native-04/libraries'),('symbols','../../held_cutover/authored/symbols')]:(OUT/n).unlink();(OUT/n).symlink_to(target,target_is_directory=True)
pr=json.loads((OUT/'parity.json').read_text());assert not pr['schematic_parity'] and len(pr['violations'])==4 and all(v['type']=='clearance' for v in pr['violations'])
report={'native_footprint_ids_match':True,'schematic_parity_issues':0,'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'source_schematic_sha256':{p.name:sha(p) for p in SRC.glob('*.kicad_sch')},'script_sha256':sha(Path(__file__)),'native_loaded_UUID_paths_equal_schematic':True,'electrical_associations':len(actual),'board_unchanged':True,'parity_report_sha256':sha(OUT/'parity.json')};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
