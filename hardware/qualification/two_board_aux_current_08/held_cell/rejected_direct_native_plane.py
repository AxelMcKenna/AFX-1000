"""Fill extension natively, retain original zones exactly, and prove original group identity."""
import ast,json,sys,hashlib,shutil,subprocess,copy
from pathlib import Path
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'shared_cutover/native-04';AUTH=H/'held_cell/authored';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();plan=json.loads((H/'held_cell/plane-plan.json').read_text());assert sha(BASE/'power_protection.kicad_pcb')==plan['source_board_sha256'] and sha(AUTH/'power_protection.kicad_pcb')==plan['authored_board_sha256']
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
original=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));before,opens=groups(original);state=object_state(original);fills=fill_state(original);ident={p.m_Uuid.AsString():identity(p,original) for f in original.GetFootprints() for p in f.Pads()}
b=pcbnew.LoadBoard(str(AUTH/'power_protection.kicad_pcb'));filler=pcbnew.ZONE_FILLER(b);assert filler.Fill(b.Zones());OUT.mkdir(parents=True,exist_ok=True);pcbnew.SaveBoard(str(OUT/'full-refill.kicad_pcb'),b)
auth=read_sexpr((AUTH/'power_protection.kicad_pcb').read_text());filled=read_sexpr((OUT/'full-refill.kicad_pcb').read_text());new=next(z for z in children(filled,'zone') if first(z,'uuid')[1]==plan['new_zone_uuid']);target=next(z for z in children(auth,'zone') if first(z,'uuid')[1]==plan['new_zone_uuid']);polys=children(new,'filled_polygon');assert polys;target.extend(copy.deepcopy(polys));(OUT/'power_protection.kicad_pcb').write_text(sexpr(auth)+'\n')
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
shutil.copytree(BASE/'libraries',OUT/'libraries',dirs_exist_ok=True)
b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));after,afteropens=groups(b);assert before==after and opens==afteropens;assert state==object_state(b);newfills=fill_state(b);assert all(newfills[u]==v for u,v in fills.items());now={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert ident==now
mapping=json.loads((H/'routed/anonymous-pad-mapping.json').read_text());keys=[]
for row in mapping['mappings']:assert now[row['candidate_uuid']]==row['full_physical_identity'];keys.append(json.dumps(now[row['candidate_uuid']],sort_keys=True))
assert len(set(keys))==len(keys)==55
z=next(z for z in b.Zones() if z.m_Uuid.AsString()==plan['new_zone_uuid']);pg=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(b.GetLayerID('In6.Cu')));pg.Unfracture();(OUT/'new-zone-geometry.json').write_text(json.dumps({'source_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'zone_uuid':plan['new_zone_uuid'],'layer':'In6.Cu','polygons_nm':polygons(pg)},indent=2)+'\n')
subprocess.run(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],check=True)
report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'plan_sha256':sha(H/'held_cell/plane-plan.json'),'script_sha256':sha(Path(__file__)),'full_refill_sha256':sha(OUT/'full-refill.kicad_pcb'),'geometry_sha256':sha(OUT/'new-zone-geometry.json'),'opens_before':opens,'opens_after':afteropens,'original_group_count':len(before),'all_original_groups_unchanged':True,'all_original_objects_unchanged':True,'all_original_fills_unchanged':True,'anonymous_identity_bijection_preserved':55,'new_zone_uuid':plan['new_zone_uuid'],'new_filled_polygons':len(polys),'qualified':False};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
