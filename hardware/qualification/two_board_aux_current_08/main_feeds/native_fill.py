"""Evaluate only declared B.Cu fill cutbacks; preserve every other source zone."""
import ast,copy,hashlib,json,shutil,sys
from pathlib import Path
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'main_feeds/native-01';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();plan=json.loads((H/'main_feeds/fill-plan.json').read_text());assert plan['routed_board_sha256']==sha(BASE/'power_protection.kicad_pcb')
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));assert b is not None;before,opens=groups(b);state=object_state(b);ident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};OUT.mkdir(exist_ok=True);scratch=OUT/'refill';scratch.mkdir()
for n in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,scratch/n)
(scratch/'libraries').symlink_to((BASE/'libraries').resolve(),target_is_directory=True);proc=run_recorded(['kicad-cli','pcb','drc','--refill-zones','--save-board','--format','json','--output',str(scratch/'drc.json'),str(scratch/'power_protection.kicad_pcb')],OUT/'refill-process',180,[BASE/'power_protection.kicad_pcb',H/'main_feeds/fill-plan.json']);assert proc['status']=='passed';shutil.copy2(scratch/'power_protection.kicad_pcb',OUT/'full-refill.kicad_pcb')
old=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());filled=read_sexpr((OUT/'full-refill.kicad_pcb').read_text());fullzones={first(z,'uuid')[1]:z for z in children(filled,'zone')}
for z in children(old,'zone'):
 uid=first(z,'uuid')[1]
 if uid in plan['cutback_zone_uuids']:
  assert first(z,'layer')[1]=='B.Cu';z[:]=[x for x in z if not isinstance(x,list) or x[0]!='filled_polygon'];z.extend(copy.deepcopy(children(fullzones[uid],'filled_polygon')))
(OUT/'power_protection.kicad_pcb').write_text(sexpr(old)+'\n')
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
(OUT/'libraries').symlink_to((BASE/'libraries').resolve(),target_is_directory=True);b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));assert b is not None;after,afteropens=groups(b);now={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert state==object_state(b) and ident==now
geo=[]
for z in b.Zones():
 if z.m_Uuid.AsString() in plan['cutback_zone_uuids']:
  pg=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(pcbnew.B_Cu));pg.Unfracture();geo.append({'uuid':z.m_Uuid.AsString(),'net':z.GetNetname(),'layer':'B.Cu','polygons_nm':polygons(pg)})
(OUT/'changed-zone-geometry.json').write_text(json.dumps({'source_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'zones':geo},indent=2)+'\n');proc=run_recorded(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],OUT/'drc-process',180,[OUT/'power_protection.kicad_pcb']);assert proc['status']=='passed';(OUT/'libraries').unlink();(OUT/'libraries').symlink_to('../../shared_cutover/native-04/libraries',target_is_directory=True)
result={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'fill_plan_sha256':sha(H/'main_feeds/fill-plan.json'),'script_sha256':sha(Path(__file__)),'full_refill_sha256':sha(OUT/'full-refill.kicad_pcb'),'changed_geometry_sha256':sha(OUT/'changed-zone-geometry.json'),'opens_before':opens,'opens_after':afteropens,'all_groups_unchanged_from_routed_candidate':before==after,'all_copper_objects_and_pad_identities_unchanged':True,'cutback_zone_uuids':plan['cutback_zone_uuids'],'qualified':False};(OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert before==after and opens==afteropens,'Fill cutback changed existing native connectivity'
