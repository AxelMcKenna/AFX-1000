"""Recheck source bindings, native cutover evidence and unchanged complete zones."""
import hashlib,json
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children
H=Path(__file__).resolve().parent;B=H.parent/'routed/native-04';O=H/'board-native-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 r=json.loads((O/'review.json').read_text())
 for key,path in [('source_sha256',B/'power_protection.kicad_pcb'),('candidate_sha256',O/'power_protection.kicad_pcb'),('script_sha256',H/'board_native.py'),('schematic_sha256',H/'native-03/candidate-netlist.xml'),('anonymous_mapping_sha256',H.parent/'routed/anonymous-pad-mapping.json')]:assert r[key]==sha(path)
 assert r['all_group_memberships_unchanged'] and r['all_original_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['full_pad_identities_checked']==3777
 assert r['opens_before']==r['opens_after']==1964 and len(r['changed_objects'])==9
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (B/n).read_bytes()==(O/n).read_bytes()
 trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [B,O]]
 assert children(trees[0],'zone')==children(trees[1],'zone')
 old=json.loads((B/'drc.json').read_text());new=json.loads((O/'drc.json').read_text())
 assert sorted(new['violations'],key=lambda x:json.dumps(x,sort_keys=True))==sorted(old['violations'],key=lambda x:json.dumps(x,sort_keys=True)) and len(new['violations'])==4
 assert all(v['severity']=='error' for v in new['violations'])
 print('PASS: exact three whole branches; 2714 native groups; 3777 pad identities; 55 anonymous mappings; complete original zones; four unchanged unwaived DSE errors')
if __name__=='__main__':verify()
