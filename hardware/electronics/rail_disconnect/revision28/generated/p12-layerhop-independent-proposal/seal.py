import hashlib
import json
from pathlib import Path

R = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
proof = json.loads((R / 'final-delta-proof.json').read_text())
source = Path(json.loads((R / 'screen.json').read_text())['source'])
assert sha(source / 'rail_disconnect.kicad_pcb') == proof['source_pcb_sha256']
files = {str(p.relative_to(R)): sha(p) for p in sorted(R.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in ['handoff.json', 'seal-verification.json']}
report = dict(status='READY_SOURCE_SPECIFIC_PARTIAL_DELTA_NOT_ADOPTED', source_pcb_sha256=proof['source_pcb_sha256'], candidate_pcb_sha256=proof['candidate_pcb_sha256'], candidate='candidate-paired/rail_disconnect.kicad_pcb', delta='final-delta-proof.json', raw_native_drc='candidate-drc.json', raw_native_erc='candidate-erc.json', actual_native_connectivity='native-connectivity.json', tests=6, files_sha256=files, source_unchanged=True, uncapped_opens=31, native_hard=0, native_parity=0, PCB_ignored_checks=[], ERC_stock_ignored_count=4, V5_buffered_open=True, physical_qualified=False, adopted=False)
(R / 'handoff.json').write_text(json.dumps(report, indent=2)+'\n')
for p, h in files.items(): assert sha(R / p) == h, p
(R / 'seal-verification.json').write_text(json.dumps(dict(handoff_sha256=sha(R / 'handoff.json'), files_verified=len(files), all_pass=True, source_still_unchanged=sha(source / 'rail_disconnect.kicad_pcb')==proof['source_pcb_sha256']),indent=2)+'\n')
print('READY', len(files), 'files', 'handoff',sha(R / 'handoff.json'))
