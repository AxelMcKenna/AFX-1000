"""Run only in pinned Linux KiCad. Retain all categories and source-bound logs."""
import json,subprocess,hashlib,sys
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
R=Path(__file__).resolve().parent;O=R/'pcb-native-r2';O.mkdir(exist_ok=False)
results=[]
for name in ['settings','release']:
 p=R/(name+'.kicad_pcb');board=pcbnew.LoadBoard(str(p));board.BuildConnectivity()
 padgroups={}
 for fp in board.GetFootprints():
  for pad in fp.Pads():
   if pad.GetNetname():padgroups.setdefault(pad.GetNetname(),[]).append(fp.GetReference()+'.'+pad.GetNumber())
 assert all(sorted(v)==sorted(['SW1.'+k.split('_')[-1],'W'+k.split('_')[-1]+'.1']) for k,v in padgroups.items()),padgroups
 cmd=['kicad-cli','pcb','drc','--format','json','--severity-all','-o',str(O/(name+'-drc.json')),str(p)]
 run=subprocess.run(cmd,capture_output=True,text=True,timeout=60);(O/(name+'.log')).write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
 d=json.loads((O/(name+'-drc.json')).read_text());assert not d['unconnected_items'],d['unconnected_items']
 subprocess.run(['kicad-cli','pcb','export','svg','--layers','F.Cu,F.SilkS,Edge.Cuts','-o',str(O/(name+'.svg')),str(p)],check=True,capture_output=True,timeout=60)
 results.append(dict(board=name,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),net_pin_groups=padgroups,unconnected=len(d['unconnected_items']),violations=d['violations']))
(O/'review.json').write_text(json.dumps(dict(scope='Selector breakouts only; no full-unit release or physical acceptance',results=results),indent=2)+'\n');print(json.dumps(results))
