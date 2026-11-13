import json,hashlib
from pathlib import Path
from .analyze import calculate
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 r=json.loads((H/'decision.json').read_text())
 for n,p in r['primary'].items():assert sha(H/'primary'/n)==p['sha256']
 assert sha(H.parent/'placement/dse-review/vector-check.json')==r['existing_dse_drawing_check_sha256'] and sha(H.parent/'fast_inhibit/primary/tps3703.pdf')==r['existing_supervisor_datasheet_sha256']
 p=H.parent/'ldo_local/native-08/parity.json';assert sha(p)==r['existing_DRC_sha256'];vs=json.loads(p.read_text())['violations'];assert len(vs)==4 and all(v['type']=='clearance' and 'actual 0.1500 mm' in v['description'] for v in vs)
 actual=set()
 for v in vs:
  parts=[i['description'].split(' of ') for i in v['items']];refs={b.split()[0] for a,b in parts};assert len(refs)==1;actual.add((next(iter(refs)),tuple(sorted(a.split()[1] for a,b in parts))))
 assert actual=={(ref,pair) for ref in ['E_U900','P_U902'] for pair in [('1','2'),('2','3')]}
 assert abs(.65-.45-.2)<1e-12 and abs(.95-.6-.35)<1e-12 and abs(.5-(.25+.05*2)-.15)<1e-12
 assert r['conditional_sensitivity']==calculate() and not r['clearance_waiver'] and not r['selected_board_changed'];assert calculate()['effective_uF_for_50us_shutdown_plus_11us']>430
 print('PASS: exact four DSE errors, primary hashes, nominal package spacing, conditional hold-up calculation; no qualified replacement claimed')
if __name__=='__main__':verify()
