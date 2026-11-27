import sys,json,subprocess
from pathlib import Path
from contracts import *
sys.path.insert(0,str(REPO/'hardware/electronics'))
from common.netlists import netlist
out=Path(sys.argv[1]);sch=R/'assembly/panel.kicad_sch'
for args,log in [(['erc','--severity-all','--format','json','--exit-code-violations','-o',str(out/'erc.json'),str(sch)],'erc'),(['export','netlist','--format','kicadxml','-o',str(out/'netlist.xml'),str(sch)],'netlist')]:
 p=subprocess.run(['kicad-cli','sch']+args,capture_output=True,text=True,timeout=120);(out/(log+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(log,p.stdout,p.stderr)
parts,pins=netlist(out/'netlist.xml');m=json.loads((R/'assembly-manifest.json').read_text());cs=m['components']
assert set(parts)=={c['ref'] for c in cs}
for c in cs:
 assert parts[c['ref']].findtext('value')==c['part']
 assert (parts[c['ref']].findtext('footprint') or '')==c['footprint']
 assert pins.get(c['ref'],{})=={p['number']:p['net'] for p in c['pins']},(c['ref'],pins.get(c['ref']),c['pins'])
review=dict(erc_violations=0,components=len(cs),passive_board_instances=len(m['passive_board_instances']),channels=len(m['channels']),whole_panel_netlist_parity=True)
(out/'review.json').write_text(json.dumps(review,indent=2)+'\n');print(review)
