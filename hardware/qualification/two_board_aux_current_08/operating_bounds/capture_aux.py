"""Reproduce the AUX-only TBP72 snapshot from its frozen full native capture."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4]);ap.add_argument('--check',action='store_true');args=ap.parse_args()
root=args.repo
p=root/'hardware/fabrication/staging/two-board-power-routing-inputs-aux-ground-reuse-01/capture.json'
q=root/'hardware/fabrication/staging/two-board-aux-distribution-survey-06/inventory.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
x=json.loads(p.read_text());d=json.loads(q.read_text())
assert d['source_sha256'][str(p.relative_to(root))]==sha(p)
assert x['native_uncapped_opens']==d['native_board_opens']==1937
s={'source_path':str(p.relative_to(root)),'source_sha256':sha(p),'native_version':x['native_version'],'native_uncapped_opens':x['native_uncapped_opens'],'objects':[o for o in x['objects'] if o['net']=='PWR_V2V5_AUX'],'copper_layers':x['copper_layers']}
if args.check:
    assert json.loads((HERE/'TBP72-AUX-copper.json').read_text())==s
    assert (HERE/'TBP72-distribution.json').read_bytes()==q.read_bytes()
else:
    (HERE/'TBP72-AUX-copper.json').write_text(json.dumps(s,indent=2)+'\n')
    (HERE/'TBP72-distribution.json').write_bytes(q.read_bytes())
    (HERE/'capture-provenance.json').write_text(json.dumps({'generator_sha256':sha(Path(__file__)),'source_sha256':{str(p.relative_to(root)):sha(p),str(q.relative_to(root)):sha(q)},'snapshots_sha256':{n:sha(HERE/n) for n in ['TBP72-AUX-copper.json','TBP72-distribution.json']}},indent=2)+'\n')
print('TBP72 AUX-only extraction matches frozen native capture and distribution evidence')
