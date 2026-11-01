from pathlib import Path
import hashlib,shutil,json,uuid
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.electronics.rail_disconnect.revision28.repair import Router
root=Path('hardware/electronics/rail_disconnect/revision28').resolve();src=root/'generated/p9-targeted-timing-leaf-work';dst=root/'generated/p9-u14-barrel-probe-work';assert not dst.exists()
p=src/'rail_disconnect.kicad_pcb';before=p.read_bytes();digest=hashlib.sha256(before).hexdigest();assert digest=='bdac7c169ad48284d7f9eb267a66c7081a43ac2724d890058f0594ecc244d3ac';t=read_sexpr(before.decode());r=Router(t);codes={str(n[2]).lstrip('/'):str(n[1]) for n in children(t,'net')};added=[]
for pin,net,xy in [('5','V5_REG_SRC',(41.124,10.95)),('11','V5_REG',(41.876,10.05))]:
 pad=next(p for p in r.by_ref['U14'] if p['pin']==pin);assert pad['net']==net
 uid=uuid.uuid5(uuid.NAMESPACE_URL,f'rmx:E28:U14-pin{pin}-realbarrel:{digest}')
 n=read_sexpr(f'(via (at {100+xy[0]} {100+xy[1]}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {codes[net]}) (uuid {uid}))');t.append(n);added.append(dict(pin=pin,net=net,pad_xy=pad['xy'],via_xy=xy,actual_object=sexpr(n)))
dst.mkdir();(dst/'generated').mkdir()
for f in src.iterdir():
 if f.is_file() and (f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym') or f.name in ('components.json','fp-lib-table','sym-lib-table')):shutil.copy2(f,dst/f.name)
 elif f.suffix=='.pretty':shutil.copytree(f,dst/f.name)
(dst/'rail_disconnect.kicad_pcb').write_text(sexpr(t)+'\n');shutil.copy2(__file__,dst/'generated/recipe.py');(dst/'generated/barrel-probe.json').write_text(json.dumps(dict(source_pcb_sha256=digest,candidate_pcb_sha256=hashlib.sha256((dst/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),added_real_barrels=added,all_original_pads_and_routes_and_holes_retained=True,physical_process_and_native_acceptance=False),indent=2)+'\n')
print('Added two real U14 holes; raw native probe is not an accepted design')
