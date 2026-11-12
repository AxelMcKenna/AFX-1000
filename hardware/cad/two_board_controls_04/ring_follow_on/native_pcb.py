"""Run under the pinned Linux KiCad image; read-only board, explicit output directory."""
import json,hashlib,subprocess,sys
from pathlib import Path
import pcbnew
R=Path(__file__).resolve().parent;O=Path(sys.argv[1]);p=R/'ring.kicad_pcb';b=pcbnew.LoadBoard(str(p));b.BuildConnectivity();nets={}
for f in b.GetFootprints():
 for pad in f.Pads():
  if pad.GetNetname():nets.setdefault(pad.GetNetname(),[]).append(f.GetReference()+'.'+pad.GetNumber())
assert sorted(nets['ANODE_5V'])==sorted([f'D{i}.1' for i in range(1,9)]+['W1.1'])
for j,n in enumerate(['RING_RED_93','RING_GREEN_94','RING_BLUE_95']):
 assert sorted(nets[n])==sorted([f'R{i*3+j+1}.'+('2' if j==0 else '1') for i in range(8)]+[f'W{j+2}.1'])
 for i in range(8):assert sorted(nets[f'BRANCH_{i}_{j}'])==sorted([f'D{i+1}.{j+2}',f'R{i*3+j+1}.'+('1' if j==0 else '2')])
x=subprocess.run(['kicad-cli','pcb','drc','--format','json','--severity-all','-o',str(O/'drc.json'),str(p)],capture_output=True,text=True,timeout=60);(O/'native.log').write_text(x.stdout+x.stderr);assert x.returncode==0
v=json.loads((O/'drc.json').read_text());files=[p,R/'pcb.py',Path(__file__),R/'fp-lib-table',*sorted((R/'TBH06.pretty').glob('*'))]
report=dict(image='kicad/kicad@sha256:c8f05703e865a1caa7266851cf4986dd01d5fb1148e4f63382b6a73466ba7e71',source_sha256={str(q.relative_to(R)):hashlib.sha256(q.read_bytes()).hexdigest() for q in files},violations=v['violations'],unconnected=v['unconnected_items'],net_pin_groups=nets,scope='Populated RGB ring connectivity and native design rules; optical/electrical qualification pending')
(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('violations',len(v['violations']),'opens',len(v['unconnected_items']),flush=True);assert not v['violations'] and not v['unconnected_items']
subprocess.run(['kicad-cli','pcb','export','svg','--layers','F.Cu,Edge.Cuts','-o',str(O/'front.svg'),str(p)],check=True,capture_output=True,timeout=60)
