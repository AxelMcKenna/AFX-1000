"""Check deterministic regeneration and bind complete circuit-source dependencies."""
import hashlib,json,subprocess,sys
from contracts import *
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generated():
 files=list((R/'assembly').rglob('*'))+list((R/'layouts').rglob('*'))+[R/'assembly-manifest.json',R/'layout-contract-review.json']
 return {str(p.relative_to(R)):sha(p) for p in files if p.is_file()}
before=generated()
for script in ['generate.py','panel.py']:subprocess.run([sys.executable,str(R/script)],check=True)
after=generated();assert before==after,'Regeneration changed committed outputs'
inputs=list(R.glob('*.py'))+list((R/'reference').glob('*'))+[CONTROLS/p for p,l in DESIGNS.values()]
inputs += [CONTROLS/p for p in ['display-wiring.csv','led_follow_on/wiring.csv','ring_follow_on/wiring.csv','button_follow_on/wiring.csv']]
inputs += [REPO/p for p in ['hardware/electronics/common/__init__.py','hardware/electronics/common/flat_schematic.py','hardware/electronics/common/symbols.py','hardware/electronics/common/sexpr.py','hardware/electronics/common/netlists.py','hardware/electronics/led_driver/generated/channel-map.csv','hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb']]
for path,lib in DESIGNS.values():inputs+=list(((CONTROLS/path).parent/(lib+'.pretty')).glob('*'))
report=dict(deterministic_regeneration=True,inputs={str(p.relative_to(REPO)):sha(p) for p in sorted(set(inputs))},outputs=after)
(R/'source-closure.json').write_text(json.dumps(report,indent=2)+'\n');print('Deterministic regeneration:',len(after),'outputs;',len(set(inputs)),'source bindings')
