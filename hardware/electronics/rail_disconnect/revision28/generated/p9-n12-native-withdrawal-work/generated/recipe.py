import hashlib,json,uuid,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr,a
from hardware.electronics.rail_disconnect.revision26 import router as aid
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.force_guard import ForceGuard
from hardware.electronics.rail_disconnect.revision28.search import diagonal_connect
root=Path('hardware/electronics/rail_disconnect/revision28').resolve();source=root/'generated/p9-analog-outlet-work';out=root/'generated/p9-n12-native-withdrawal-work';assert not out.exists()
aid.STEP=.1;aid.CLEARANCE=.205
tree=read_sexpr((source/'rail_disconnect.kicad_pcb').read_text());r=Router(tree)
guard=ForceGuard(read_sexpr((source/'generated/filled-analog-outlet1.kicad_pcb').read_text()),r,aid.STEP)
start=dict(net='N12_SRC',xy=(48.2875,29.7),layers=tuple(range(6)));end=dict(net='N12_SRC',xy=(70,14.3),layers=tuple(range(6)))
blocked,via=aid.Router.masks(r,'N12_SRC',.2)
for ep in (start,end):
 ix,iy=[round(v/aid.STEP) for v in ep['xy']]
 for z in ep['layers']:blocked[z,ix,iy]=False
 via[ix,iy]=False
r.masks=lambda net,width:(blocked,via)
r.max_search_nodes=300000;r.search_bias=1.15
before=len(tree);ok=diagonal_connect(r,start,end,.2)
out.mkdir();(out/'generated').mkdir()
for p in source.iterdir():
 if p.is_file() and (p.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym') or p.name in ('components.json','fp-lib-table','sym-lib-table')):shutil.copy2(p,out/p.name)
 elif p.suffix=='.pretty':shutil.copytree(p,out/p.name)
digest=hashlib.sha256((source/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest()
for i,n in enumerate(tree[before:]):
 if children(n,'uuid'):continue
 n.append([a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'rmx:E28:N12drilltradeoff3d:{digest}:{i}'))])
if ok:(out/'rail_disconnect.kicad_pcb').write_text(sexpr(tree)+'\n')
recipe=Path(__file__);shutil.copy2(recipe,out/'generated/recipe.py')
(out/'generated/search.json').write_text(json.dumps(dict(success=ok,search=r.last_search,routes=r.routes,source_sha256=digest,recipe_sha256=hashlib.sha256(recipe.read_bytes()).hexdigest(),added_objects=[sexpr(n) for n in tree[before:]],local_native_foreign_pour_withdrawal_is_a_deliberate_unaccepted_tradeoff=True,native_and_all_conductor_checks_required=True,physical_qualified=False),indent=2)+'\n');print(ok,r.last_search,flush=True)
