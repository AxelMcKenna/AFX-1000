from pathlib import Path
import json,hashlib,shutil,uuid
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
from hardware.electronics.rail_disconnect.revision26 import router as aid
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.force_guard import ForceGuard
from hardware.electronics.rail_disconnect.revision28.search import diagonal_connect
root=Path('hardware/electronics/rail_disconnect/revision28').resolve();source=root/'generated/p9-u14-input-escape-work';out=root/'generated/p9-ready-guarded-3d-work';assert not out.exists();path=source/'rail_disconnect.kicad_pcb';before=path.read_bytes();digest=hashlib.sha256(before).hexdigest();assert digest=='28c86cea474e46e9b857c11c059f304b8e61f46444d87b8aabcfc50f2b81c945';tree=read_sexpr(before.decode());original=len(tree)
oldfile=root/'generated/p9-pruned-leaf-reviewed-work/generated/pruned-pad-only-vias.json';old=json.loads(oldfile.read_text());oldvia=next(r for r in old['actual_unlocked_leaf_vias'] if r['net']=='/P03_SOURCES_READY');uid=oldvia['uuid'];via=next(s for s in old['removed_actual_objects'] if str(first(read_sexpr(s),'uuid')[1])==uid);tree.append(read_sexpr(via))
aid.STEP=.1;aid.CLEARANCE=.205;r=Router(tree);guard=ForceGuard(read_sexpr((source/'generated/filled-u14-input-escape1.kicad_pcb').read_text()),r,.1)
net='P03_SOURCES_READY';start=next(p for p in r.by_ref['J9'] if p['pin']=='2');end=next(p for p in r.by_ref['R142'] if p['pin']=='1');assert start['net']==end['net']==net
start=dict(start,layers=tuple(range(6)));end=dict(end,layers=(1,2,3,4,5));blocked,drills=aid.Router.masks(r,net,.2);blocked,drills=guard.apply(net,blocked,drills,.2)
for ep in (start,end):
 ix,iy=[round(v/.1) for v in ep['xy']]
 for z in ep['layers']:blocked[z,ix,iy]=False
 drills[ix,iy]=False
r.masks=lambda name,width:(blocked,drills);r.max_search_nodes=900000;r.search_bias=1.7;ok=diagonal_connect(r,start,end,.2)
out.mkdir();(out/'generated').mkdir();report=dict(source_pcb_sha256=digest,source_old_via_record_sha256=hashlib.sha256(oldfile.read_bytes()).hexdigest(),restored_existing_via=oldvia,search=r.last_search,success=ok,routes=r.routes,all_actual_filled_force_regions_and_new_drills_guarded=True,target_requires_a_real_nonF_layer_connection=True,native_all_open_force_and_return_checks_required=True,physical_qualified=False)
shutil.copy2(__file__,out/'generated/recipe.py')
if ok:
 for i,node in enumerate(tree[original:]):
  if not children(node,'uuid'):node.append([a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'rmx:E28:READYguard:{digest}:{i}'))])
 for p in source.iterdir():
  if p.is_file() and (p.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym') or p.name in ('components.json','fp-lib-table','sym-lib-table')):shutil.copy2(p,out/p.name)
  elif p.suffix=='.pretty':shutil.copytree(p,out/p.name)
 (out/path.name).write_text(sexpr(tree)+'\n');report['candidate_pcb_sha256']=hashlib.sha256((out/path.name).read_bytes()).hexdigest();report['added_actual_objects']=[sexpr(n) for n in tree[original:]]
(out/'generated/READY-route.json').write_text(json.dumps(report,indent=2)+'\n');print(ok,r.last_search,flush=True)
