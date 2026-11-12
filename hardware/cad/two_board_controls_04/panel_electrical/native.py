import sys,json,subprocess,hashlib
from pathlib import Path
from contracts import *
sys.path.insert(0,str(REPO/'hardware/electronics'))
from common.netlists import netlist
out=Path(sys.argv[1]);results={}
for name in DESIGNS:
 d=out/name;d.mkdir(parents=True,exist_ok=True);sch=R/'layouts'/name/(name+'.kicad_sch')
 for args,log in [(['erc','--severity-all','--format','json','--exit-code-violations','-o',str(d/'erc.json'),str(sch)],'erc'),(['export','netlist','--format','kicadxml','-o',str(d/'netlist.xml'),str(sch)],'netlist')]:
  p=subprocess.run(['kicad-cli','sch']+args,capture_output=True,text=True,timeout=60);(d/(log+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,log,p.stdout,p.stderr)
 erc=json.loads((d/'erc.json').read_text());assert not any(s['violations'] for s in erc['sheets'])
 parts,pins=netlist(d/'netlist.xml');cs=contract(name)['components']
 assert set(parts)=={c['ref'] for c in cs},(name,set(parts))
 for c in cs:
  assert parts[c['ref']].findtext('value')==c['part']
  assert parts[c['ref']].findtext('footprint')==c['footprint']
  assert pins.get(c['ref'],{})=={p['number']:p['net'] for p in c['pins']},(name,c['ref'],pins.get(c['ref']))
 results[name]=dict(erc_violations=0,netlist_contract_parity=True,schematic_sha256=hashlib.sha256(sch.read_bytes()).hexdigest())
 (out/'review.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
