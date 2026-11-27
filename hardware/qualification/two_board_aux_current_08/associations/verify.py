"""Recheck exact source binding and metadata-only change independently of native run."""
import json,hashlib
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children
from .paths import expected_paths,bind,NEW_REFS
from .build import stripped
H=Path(__file__).resolve().parents[1];D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 r=json.loads((D/'changes.json').read_text());src=H/'main_ldo/native-03/power_protection.kicad_pcb';dst=D/'authored/power_protection.kicad_pcb'
 assert sha(src)==r['source_board_sha256'] and sha(dst)==r['candidate_board_sha256']
 assert sha(D/'build.py')==r['script_sha256'] and sha(D/'paths.py')==r['helper_sha256']
 assert sha(H/'precision/native-01/candidate-netlist.xml')==r['source_netlist_sha256']
 for n,h in r['source_schematic_sha256'].items():assert sha(H/'precision/authored'/n)==sha(D/'authored'/n)==h
 a=read_sexpr(src.read_text());b=read_sexpr(dst.read_text());assert stripped(a)==stripped(b)
 actual=bind(a,expected_paths(D/'authored/power_protection.kicad_sch',H/'precision/native-01/candidate-netlist.xml'));assert a==b and actual['changes']==r['changes']
 for n in ['symbols','libraries']:
  p=D/'authored'/n;assert str(p.readlink())==r['library_targets'][n];assert {str(f.relative_to(p.resolve())):sha(f) for f in sorted(p.resolve().rglob('*')) if f.is_file()}==r['library_sha256'][n];assert p.is_symlink() and p.resolve().is_dir() and p.resolve().is_relative_to(H.resolve())
 nr=json.loads((D/'native-02/review.json').read_text());assert nr['source_sha256']==sha(src) and nr['candidate_sha256']==sha(dst) and nr['script_sha256']==sha(D/'native.py');assert nr['native_uuid_associations']==1104 and nr['all_native_groups_objects_fills_unchanged'] and nr['opens']==1943
 assert sha(D/'native-02/parity.json')==nr['parity_sha256']
 process=json.loads((D/'native-02/parity-process/process.json').read_text());assert process['status']=='passed' and all(process['inputs_unchanged'].values())
 for n in ['stdout.log','stderr.log']:assert sha(D/'native-02/parity-process'/n)==process[n+'_sha256']
 parity=json.loads((D/'native-02/parity.json').read_text());assert len(parity['schematic_parity'])==18 and all(x['type']=='footprint_symbol_mismatch' for x in parity['schematic_parity']);assert {x['items'][0]['description'].removeprefix('Footprint ') for x in parity['schematic_parity']}==NEW_REFS
 assert len(parity['violations'])==4 and all(x['type']=='clearance' for x in parity['violations'])
 result={'metadata_association_gate':'passed','changed_paths':18,'native_electrical_associations':1104,'opens':1943,'geometry_nets_poses_fills_unchanged':True,'schematic_parity_release_gate':'failed: 18 existing footprint-symbol identifier mismatches remain; four DSE clearances unwaived','qualified':False}
 (D/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':verify()
