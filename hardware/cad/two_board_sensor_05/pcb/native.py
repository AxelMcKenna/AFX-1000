"""Isolated Linux-only native connectivity, ERC, DRC/parity and plot audit."""
import sys,json,subprocess,shutil,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,a
R=Path(__file__).resolve().parent;O=R/sys.argv[1]
assert O.is_dir() and not list(O.iterdir())
for p in R.iterdir():
 if p.suffix in ['.kicad_sch','.kicad_pro','.kicad_pcb','.kicad_sym']or p.name in ['fp-lib-table','sym-lib-table']:shutil.copy2(p,O/p.name)
shutil.copytree(R/'RMX_TBH05.pretty',O/'RMX_TBH05.pretty')
def run(label,args):
 p=subprocess.run(['kicad-cli',*args],capture_output=True,text=True,timeout=60);(O/(label+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(label,p.stdout,p.stderr)
run('netlist',['sch','export','netlist','--format','kicadxml','-o',str(O/'netlist.xml'),str(O/'sensor.kicad_sch')])
netlist=ET.parse(O/'netlist.xml');pins={};names={}
for n in netlist.findall('./nets/net'):
 name=n.attrib['name'];names[name]=len(names)+1
 for p in n.findall('node'):pins[(p.attrib['ref'],p.attrib['pin'])]=name
expected={('U1','1'):'V3V3_IO',('U1','2'):'V3V3_IO',('U1','4'):'AGND',('U1','6'):'SDA',('U1','7'):'SCL',('U1','8'):'AGND',('C1','1'):'AGND',('C1','2'):'V3V3_IO',('W1','1'):'AGND',('W2','1'):'V3V3_IO',('W3','1'):'SCL',('W4','1'):'SDA'}
assert all(pins[k].lstrip('/')==v for k,v in expected.items()),pins
assert all('unconnected' in pins[k] for k in [('U1','3'),('U1','5')]),pins
# Rebind codes to exact native exported net names, including deliberate NC pads.
p=O/'sensor.kicad_pcb';tree=read_sexpr(p.read_text());old={int(v[1]):v[2]for v in children(tree,'net')}
for row in children(tree,'segment')+children(tree,'via')+children(tree,'zone'):
 n=first(row,'net');n[1]=a(names[old[int(n[1])]])
tree[:]=[v for v in tree if not(isinstance(v,list)and v and v[0]=='net')]
idx=next(i for i,v in enumerate(tree)if isinstance(v,list)and v and v[0]=='footprint')
tree[idx:idx]=[[a('net'),a(0),'']]+[[a('net'),a(i),n]for n,i in names.items()]
for fp in children(tree,'footprint'):
 ref=next(v[2]for v in children(fp,'property')if v[1]=='Reference')
 for pad in children(fp,'pad'):
  n=pins[(ref,pad[1])];pad[:]=[v for v in pad if not(isinstance(v,list)and v and v[0]=='net')];pad.append([a('net'),a(names[n]),n])
p.write_text(sexpr(tree)+'\n')
board=pcbnew.LoadBoard(str(p));board.BuildConnectivity();pcbnew.ZONE_FILLER(board).Fill(board.Zones());pcbnew.SaveBoard(str(p),board)
run('erc',['sch','erc','--severity-all','--format','json','-o',str(O/'erc.json'),str(O/'sensor.kicad_sch')])
run('drc',['pcb','drc','--severity-all','--schematic-parity','--format','json','-o',str(O/'drc.json'),str(p)])
erc=json.loads((O/'erc.json').read_text());drc=json.loads((O/'drc.json').read_text())
run('plot',['pcb','export','svg','--layers','F.Cu,F.SilkS,Edge.Cuts','-o',str(O/'front.svg'),str(p)])
r={'scope':'AS5600 local sensor PCB candidate, whole bus and physical qualification pending','source_sha256':{str(v.relative_to(R.parent)):hashlib.sha256(v.read_bytes()).hexdigest()for v in [R/'generate.py',R/'native.py',R/'sensor.kicad_sch',R/'sensor.kicad_pcb',R/'sensor.kicad_pro',R/'RMX_TBH05.kicad_sym',R/'fp-lib-table',R/'sym-lib-table',*(R/'RMX_TBH05.pretty').glob('*.kicad_mod')]},'output_pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'native_pin_contract':{f'{k[0]}.{k[1]}':v for k,v in pins.items()},'erc':erc,'drc':drc}
(O/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'erc_violations':sum(len(x['violations'])for x in erc['sheets']),'drc_violations':drc['violations'],'opens':drc['unconnected_items'],'parity':drc['schematic_parity']}))
assert not erc['ignored_checks'] and not drc['ignored_checks']
assert not any(x['violations']for x in erc['sheets'])
assert not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
