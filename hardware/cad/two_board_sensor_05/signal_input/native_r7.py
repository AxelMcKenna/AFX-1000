"""Isolated native refill, parity, connectivity and old-object preservation audit."""
import sys,json,subprocess,shutil,hashlib
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent;REPO=R.parents[3];B=R.parent/'i2c_routing/native-r4';O=R/sys.argv[1]
assert O.is_dir() and not list(O.iterdir())
for p in B.iterdir():
 if p.is_file() and(p.suffix in ['.kicad_sch','.kicad_pro','.kicad_dru']or p.name in ['sym-lib-table','fp-lib-table']):shutil.copy2(p,O/p.name)
for name in ['symbols','libraries']:
 if(B/name).is_dir():shutil.copytree(B/name,O/name)
shutil.copy2(R/'candidate-r7/signal_main.kicad_pcb',O/'signal_main.kicad_pcb')
p=O/'signal_main.kicad_pcb';board=pcbnew.LoadBoard(str(p));board.BuildConnectivity();pcbnew.ZONE_FILLER(board).Fill(board.Zones());pcbnew.SaveBoard(str(p),board)
def run(label,args):
 r=subprocess.run(['kicad-cli',*args],capture_output=True,text=True,timeout=90);(O/(label+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(label,r.stdout,r.stderr)
run('netlist',['sch','export','netlist','--format','kicadxml','-o',str(O/'netlist.xml'),str(O/'signal_main.kicad_sch')])
run('erc',['sch','erc','--severity-all','--format','json','-o',str(O/'erc.json'),str(O/'signal_main.kicad_sch')])
run('drc',['pcb','drc','--severity-all','--schematic-parity','--format','json','-o',str(O/'drc.json'),str(p)])
d=json.loads((O/'drc.json').read_text());e=json.loads((O/'erc.json').read_text());old=json.loads((B/'drc.json').read_text())
assert not d['ignored_checks'] and not e['ignored_checks'];assert not any(s['violations']for s in e['sheets'])
assert d['schematic_parity']==old['schematic_parity']
print(json.dumps({'violations':d['violations'],'opens':len(d['unconnected_items']),'bus_opens':[v for v in d['unconnected_items']if any(n in json.dumps(v)for n in ['/A_INPUT/'])]}),flush=True)
# Netlist electrical equivalence is exact across every node; metadata timestamps irrelevant.
import xml.etree.ElementTree as ET
def nets(path):
 t=ET.parse(path);return {n.attrib['name']:sorted((v.attrib['ref'],v.attrib['pin'])for v in n.findall('node'))for n in t.findall('./nets/net')}
assert nets(O/'netlist.xml')==nets(B/'netlist.xml')
# Require every pre-existing geometry object to retain exact authored parameters, ignoring refill polygons only.
def objects(path):
 t=read_sexpr(path.read_text());r={}
 for tag in ['footprint','segment','via','zone','gr_line','gr_rect','gr_arc','gr_circle','gr_poly']:
  for row in children(t,tag):
   uid=children(row,'uuid')
   if not uid:continue
   if tag=='zone':row=[v for v in row if not(isinstance(v,list)and v and v[0]=='filled_polygon')]
   r[uid[0][1]]=sexpr(row)
 return r
b0,b1=objects(B/'signal_main.kicad_pcb'),objects(p)
changed=[u for u,v in b0.items()if b1.get(u)!=v]
(O/'object-delta.json').write_text(json.dumps({'changed_old_objects':changed,'added':sorted(set(b1)-set(b0))},indent=2)+'\n')
# Native save may serialize board attributes differently; unexpected changes require inspection.
assert not changed,changed[:10]
paths=[Path(__file__),R/'plan_multilayer.py',R/'reference.py',R/'separate_channels.py',R/'candidate-r7/signal_main.kicad_pcb',R/'candidate-r7/routing.json',B/'signal_main.kicad_pcb',B/'drc.json',B/'netlist.xml']
report={'source_sha256':{str(v.relative_to(REPO)):hashlib.sha256(v.read_bytes()).hexdigest()for v in paths},'output_pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'exact_all_netlist_partitions':True,'old_objects_unchanged':True,'native_geometry':d['violations'],'native_opens':len(d['unconnected_items']),'scope':'Sixteen internal input-stage opens only; remaining230 opens and missing ESS footprint retained; analog/reference audit separate'}
(O/'review.json').write_text(json.dumps(report,indent=2)+'\n')
assert not d['violations'] and len(d['unconnected_items'])==230
assert not any(any(n in json.dumps(v)for n in ['/A_INPUT/'])for v in d['unconnected_items'])
