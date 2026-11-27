"""Fill extension natively, retain original zones exactly, and prove original group identity."""
import ast,json,sys,hashlib,shutil,subprocess,copy
from pathlib import Path
import pcbnew
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'shared_cutover/native-04';AUTH=H/'held_cell/authored-02';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();plan=json.loads((H/'held_cell/plane-plan-02.json').read_text());assert sha(BASE/'power_protection.kicad_pcb')==plan['source_board_sha256'] and sha(AUTH/'power_protection.kicad_pcb')==plan['authored_board_sha256']
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
original=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));assert original is not None,'Source board failed to load';before,opens=groups(original);state=object_state(original);fills=fill_state(original);ident={p.m_Uuid.AsString():identity(p,original) for f in original.GetFootprints() for p in f.Pads()}
OUT.mkdir(parents=True,exist_ok=True);refill=OUT/'refill';refill.mkdir();shutil.copy2(AUTH/'power_protection.kicad_pcb',refill/'power_protection.kicad_pcb')
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,refill/n)
shutil.copytree(BASE/'libraries',refill/'libraries')
result=run_recorded(['kicad-cli','pcb','drc','--refill-zones','--save-board','--format','json','--output',str(refill/'drc.json'),str(refill/'power_protection.kicad_pcb')],OUT/'refill-process',timeout=180,input_paths=[BASE/'power_protection.kicad_pcb',AUTH/'power_protection.kicad_pcb',H/'held_cell/plane-plan-02.json'])
assert result['status']=='passed' and all(result['inputs_unchanged'].values()),'Native refill did not complete; inspect recorded process'
shutil.copy2(refill/'power_protection.kicad_pcb',OUT/'full-refill.kicad_pcb')
auth=read_sexpr((AUTH/'power_protection.kicad_pcb').read_text());filled=read_sexpr((OUT/'full-refill.kicad_pcb').read_text());new=next(z for z in children(filled,'zone') if first(z,'uuid')[1]==plan['new_zone_uuid']);target=next(z for z in children(auth,'zone') if first(z,'uuid')[1]==plan['new_zone_uuid']);polys=children(new,'filled_polygon');assert polys;target.extend(copy.deepcopy(polys));(OUT/'power_protection.kicad_pcb').write_text(sexpr(auth)+'\n')
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
shutil.copytree(BASE/'libraries',OUT/'libraries',dirs_exist_ok=True)
b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));assert b is not None,'Retained-fill candidate failed to load';after,afteropens=groups(b);assert before==after and opens==afteropens;assert state==object_state(b);newfills=fill_state(b);assert all(newfills[u]==v for u,v in fills.items());now={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert ident==now
mapping=json.loads((H/'routed/anonymous-pad-mapping.json').read_text());keys=[]
for row in mapping['mappings']:assert now[row['candidate_uuid']]==row['full_physical_identity'];keys.append(json.dumps(now[row['candidate_uuid']],sort_keys=True))
assert len(set(keys))==len(keys)==55
z=next(z for z in b.Zones() if z.m_Uuid.AsString()==plan['new_zone_uuid']);pg=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(b.GetLayerID('In6.Cu')));pg.Unfracture();(OUT/'new-zone-geometry.json').write_text(json.dumps({'source_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'zone_uuid':plan['new_zone_uuid'],'layer':'In6.Cu','polygons_nm':polygons(pg)},indent=2)+'\n')
check=run_recorded(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],OUT/'final-drc-process',timeout=180,input_paths=[OUT/'power_protection.kicad_pcb']);assert check['status']=='passed'
report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'plan_sha256':sha(H/'held_cell/plane-plan-02.json'),'script_sha256':sha(Path(__file__)),'adapter_sha256':sha(H/'held_cell/process_adapter.py'),'full_refill_sha256':sha(OUT/'full-refill.kicad_pcb'),'geometry_sha256':sha(OUT/'new-zone-geometry.json'),'opens_before':opens,'opens_after':afteropens,'original_group_count':len(before),'all_original_groups_unchanged':True,'all_original_objects_unchanged':True,'all_original_fills_unchanged':True,'anonymous_identity_bijection_preserved':55,'new_zone_uuid':plan['new_zone_uuid'],'new_filled_polygons':len(polys),'qualified':False};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
