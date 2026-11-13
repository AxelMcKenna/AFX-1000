"""Add only declared local cell copper and audit exact original-group joins."""
import ast,json,sys,hashlib,uuid,shutil,os
from pathlib import Path
import pcbnew
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'held_cell/native-plane-04';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();plan=json.loads((H/'held_cell/local-routes.json').read_text());capture=json.loads((H/'held_cell/capture-04/capture.json').read_text());assert plan['capture_sha256']==sha(H/'held_cell/capture-04/capture.json');assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in capture['source_sha256'].items())
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));assert b is not None;before,opens=groups(b);state=object_state(b);fills=fill_state(b);ident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};pads={f.GetReference()+'.'+p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()};netmap=b.GetNetsByName();added=[];parent={};netnames={}
def find(u):
 parent.setdefault(u,u)
 if parent[u]!=u:parent[u]=find(parent[u])
 return parent[u]
def union(a,b):parent[find(a)]=find(b)
for row in before:
 for u in row['members']:union(u,row['members'][0]);netnames[u]=row['net']
uid=lambda label:pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:HELD-CELL-LOCAL-01:'+label)))
viamap={}
for v in plan['new_vias']:
 t=pcbnew.PCB_VIA(b);t.SetUuid(uid('via:'+v['name']));t.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in v['position_mm']]));t.SetWidth(pcbnew.FromMM(v['size_mm']));t.SetDrill(pcbnew.FromMM(v['drill_mm']));t.SetViaType(pcbnew.VIATYPE_THROUGH);t.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);t.SetNet(netmap[v['net']]);b.Add(t);u=t.m_Uuid.AsString();added.append(u);viamap['via:'+v['name']]=u;netnames[u]=v['net'];union(u,'00b41082-e346-59e4-aee2-f34d9b87e697')
for i,r in enumerate(plan['routes']):
 source=pads[r['source']];assert source.GetNetname()==r['net'];su=source.m_Uuid.AsString();tu=viamap.get(r['target'])
 if tu is None:target=pads[r['target']];assert target.GetNetname()==r['net'];tu=target.m_Uuid.AsString()
 union(su,tu)
 for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  t=pcbnew.PCB_TRACK(b);t.SetUuid(uid('track:'+str(i)+':'+str(j)));t.SetStart(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in start]));t.SetEnd(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in end]));t.SetWidth(pcbnew.FromMM(r['width_mm']));t.SetLayer(b.GetLayerID(r['layer']));t.SetNet(netmap[r['net']]);b.Add(t);u=t.m_Uuid.AsString();added.append(u);netnames[u]=r['net'];union(u,su)
OUT.mkdir(parents=True,exist_ok=True)
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
(OUT/'libraries').symlink_to((BASE/'libraries').resolve(),target_is_directory=True);pcbnew.SaveBoard(str(OUT/'power_protection.kicad_pcb'),b);b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));assert b is not None;after,afteropens=groups(b);now=object_state(b);assert set(now)==set(state)|set(added) and all(now[u]==s for u,s in state.items());assert fills==fill_state(b);newident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert ident==newident
expected={}
for u in parent:expected.setdefault(find(u),[]).append(u)
rows=[{'net':netnames[us[0]],'members':sorted(us)} for us in expected.values()];assert sorted(rows,key=lambda r:r['members'])==sorted(after,key=lambda r:r['members']),'Unexpected native group change'
mapping=json.loads((H/'routed/anonymous-pad-mapping.json').read_text());keys=[]
for row in mapping['mappings']:assert newident[row['candidate_uuid']]==row['full_physical_identity'];keys.append(json.dumps(newident[row['candidate_uuid']],sort_keys=True))
assert len(keys)==len(set(keys))==55
geometry=[]
for t in b.GetTracks():
 if t.m_Uuid.AsString() not in added:continue
 layers={}
 for l in b.GetEnabledLayers().CuStack():
  if t.IsOnLayer(l):pg=pcbnew.SHAPE_POLY_SET();t.TransformShapeToPolygon(pg,l,0,pcbnew.FromMM(.001),pcbnew.ERROR_OUTSIDE);pg.Simplify();layers[b.GetLayerName(l)]=polygons(pg)
 geometry.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'kind':t.GetClass(),'layers_nm':layers})
(OUT/'added-copper-geometry.json').write_text(json.dumps({'source_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'objects':geometry},indent=2)+'\n');drc=run_recorded(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],OUT/'drc-process',timeout=180,input_paths=[OUT/'power_protection.kicad_pcb']);assert drc['status']=='passed'
(OUT/'libraries').unlink();(OUT/'libraries').symlink_to('../../shared_cutover/native-04/libraries',target_is_directory=True)
report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'planner_sha256':sha(H/'held_cell/local_routes.py'),'plan_sha256':sha(H/'held_cell/local-routes.json'),'script_sha256':sha(Path(__file__)),'helper_sha256':{n:sha(H/n) for n in ['routed/native.py','routed/identity_native.py','held_cell/process_adapter.py']},'added_geometry_sha256':sha(OUT/'added-copper-geometry.json'),'added_copper_uuids':added,'opens_before':opens,'opens_after':afteropens,'exact_declared_group_joins_only':True,'all_original_objects_and_pad_identities_unchanged':True,'all_original_fills_unchanged':True,'anonymous_identity_bijection_preserved':55,'routes':len(plan['routes']),'new_vias':len(plan['new_vias']),'remaining_plan_failures':plan['failures'],'qualified':False};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
