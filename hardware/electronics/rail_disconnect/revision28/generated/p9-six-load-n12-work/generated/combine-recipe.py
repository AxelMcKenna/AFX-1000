import hashlib,json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
root=Path('hardware/electronics/rail_disconnect/revision28').resolve();base=root/'generated/p9-six-load-work';route=root/'generated/p9-n12-positive-guard-reverse-work';original=root/'generated/p9-analog-outlet-work';work=root/'generated/p9-six-load-n12-work';assert not work.exists()
recipe=json.loads((route/'generated/search.json').read_text());assert recipe['success'];assert recipe['source_sha256']==hashlib.sha256((original/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest()
oldtree=read_sexpr((original/'rail_disconnect.kicad_pcb').read_text());routetree=read_sexpr((route/'rail_disconnect.kicad_pcb').read_text());assert routetree[:len(oldtree)]==oldtree
added=[read_sexpr(s) for s in recipe['added_objects']];assert routetree[len(oldtree):]==added
for workspace,label,opens in ((base,'six-load1',44),(route,'n12-positive-guard1',43)):
 raw=json.loads((workspace/f'generated/drc-{label}.json').read_text());assert len(raw['unconnected_items'])==opens and not raw['schematic_parity'] and not any(v['severity']=='error' for v in raw['violations'])
tree=read_sexpr((base/'rail_disconnect.kicad_pcb').read_text());identities={str(first(s,'uuid')[1]) for s in tree if isinstance(s,list) and s and children(s,'uuid')};assert not any(str(first(s,'uuid')[1]) in identities for s in added)
work.mkdir();(work/'generated').mkdir()
for p in base.iterdir():
 if p.is_file() and (p.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym') or p.name in ('components.json','fp-lib-table','sym-lib-table')):shutil.copy2(p,work/p.name)
 elif p.suffix=='.pretty':shutil.copytree(p,work/p.name)
(work/'rail_disconnect.kicad_pcb').write_text(sexpr(tree+added)+'\n');shutil.copy2(__file__,work/'generated/combine-recipe.py')
r=dict(source_pcb_sha256=hashlib.sha256((base/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),route_pcb_sha256=hashlib.sha256((route/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),route_recipe_sha256=hashlib.sha256((route/'generated/search.json').read_bytes()).hexdigest(),candidate_pcb_sha256=hashlib.sha256((work/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),actual_append_only_objects=recipe['added_objects'],combined_native_and_copper_checks_required=True,physical_qualified=False)
(work/'generated/combine.json').write_text(json.dumps(r,indent=2)+'\n');print(r['candidate_pcb_sha256'])
