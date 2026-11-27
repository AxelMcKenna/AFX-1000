"""Apply four source-supported resistor MPNs without changing values or geometry."""
import json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,sexpr
from ..schematic_candidate.build import field
from ..metadata.build import props,sha
H=Path(__file__).resolve().parent;ROOT=H.parent;SRC=ROOT/'metadata/authored';BASE=ROOT/'reference_bridge/native-01';OUT=H/'authored'
def run():
 sel=json.loads((H/'selection.json').read_text());shutil.copytree(SRC,OUT,symlinks=True);s=read_sexpr((OUT/'E_rail_disconnect.kicad_sch').read_text());board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());parts={x['ref']:x for x in sel['parts']};syms={props(x)['Reference'][2]:x for x in children(s,'symbol')};fps={props(x)['Reference'][2]:x for x in children(board,'footprint')};delta=[]
 for ref,p in parts.items():
  for key,value in [('MPN',p['MPN']),('Datasheet',p['datasheet'])]:
   field(syms[ref],key,value);prop=props(fps[ref])[key];delta.append({'ref':ref,'field':key,'before':prop[2],'after':value});prop[2]=value
 (OUT/'E_rail_disconnect.kicad_sch').write_text(sexpr(s)+'\n');(OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
 result={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'source_netlist_sha256':sha(ROOT/'metadata/native-01/candidate-netlist.xml'),'source_schematic_sha256':{p.name:sha(p) for p in SRC.iterdir() if p.is_file()},'library_sha256':{n:{str(p.relative_to(SRC/n)):sha(p) for p in (SRC/n).rglob('*') if p.is_file()} for n in ['libraries','symbols']},'builder_sha256':sha(Path(__file__)),'selection_sha256':sha(H/'selection.json'),'native_script_sha256':sha(H/'native.py'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'changes':delta,'qualified':False};(H/'changes.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':run()
