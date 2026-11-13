"""Isolate schematic association metadata; assert every other board AST node exact."""
import copy,hashlib,json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,sexpr
from .paths import expected_paths,bind
H=Path(__file__).resolve().parents[1];D=Path(__file__).resolve().parent;OUT=D/'authored';BASE=H/'main_ldo/native-03';SRC=H/'precision/authored'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def stripped(tree):
 tree=copy.deepcopy(tree)
 for f in children(tree,'footprint'):f[:]=[n for n in f if not isinstance(n,list) or n[0]!='path']
 return tree

def main():
 OUT.mkdir(exist_ok=False)
 source=BASE/'power_protection.kicad_pcb';board=read_sexpr(source.read_text());before=copy.deepcopy(board)
 result=bind(board,expected_paths(SRC/'power_protection.kicad_sch',H/'precision/native-01/candidate-netlist.xml'))
 assert stripped(board)==stripped(before)
 (OUT/source.name).write_text(sexpr(board)+'\n')
 for p in SRC.glob('*.kicad_sch'):shutil.copy2(p,OUT/p.name)
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
 shutil.copy2(SRC/'sym-lib-table',OUT/'sym-lib-table')
 for n,target in [('symbols','../../held_cutover/authored/symbols'),('libraries','../../shared_cutover/native-04/libraries')]:(OUT/n).symlink_to(target,target_is_directory=True)
 result.update(source_board_sha256=sha(source),candidate_board_sha256=sha(OUT/source.name),source_netlist_sha256=sha(H/'precision/native-01/candidate-netlist.xml'),source_schematic_sha256={p.name:sha(p) for p in SRC.glob('*.kicad_sch')},script_sha256=sha(Path(__file__)),helper_sha256=sha(D/'paths.py'),all_non_path_board_AST_unchanged=True)
 result['library_targets']={n:str((OUT/n).readlink()) for n in ['symbols','libraries']}
 result['library_sha256']={n:{str(p.relative_to((OUT/n).resolve())):sha(p) for p in sorted((OUT/n).resolve().rglob('*')) if p.is_file()} for n in ['symbols','libraries']}
 (D/'changes.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
