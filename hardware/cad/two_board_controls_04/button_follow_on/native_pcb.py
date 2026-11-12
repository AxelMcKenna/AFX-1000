import json,hashlib,subprocess,sys
from pathlib import Path
import pcbnew
R=Path(__file__).resolve().parent;O=Path(sys.argv[1]);results=[]
for name in ['vertical','horizontal','scene','pad','pad1','vertical_top']:
 p=R/(name+'.kicad_pcb');b=pcbnew.LoadBoard(str(p));b.BuildConnectivity();nets={}
 for f in b.GetFootprints():
  for pad in f.Pads():
   if pad.GetNetname():nets.setdefault(pad.GetNetname(),[]).append(f.GetReference()+'.'+pad.GetNumber())
 assert sorted(nets['LED_K'])==['D1.1','W1.1'] and sorted(nets['LED_A'])==['D1.2','W2.1']
 x=subprocess.run(['kicad-cli','pcb','drc','--format','json','--severity-all','-o',str(O/(name+'.json')),str(p)],capture_output=True,text=True,timeout=60);(O/(name+'.log')).write_text(x.stdout+x.stderr);assert x.returncode==0
 v=json.loads((O/(name+'.json')).read_text());results.append(dict(board=name,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),nets=nets,violations=v['violations'],unconnected=v['unconnected_items']));print(name,len(v['violations']),len(v['unconnected_items']),flush=True)
(O/'review.json').write_text(json.dumps(dict(results=results,scope='Button emitter board connectivity/native DRC; no optical/physical acceptance'),indent=2)+'\n');assert all(not r['violations'] and not r['unconnected'] for r in results)
