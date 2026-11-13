"""Retarget only three complete isolated driver/bypass supply branches."""
import ast,json,sys,hashlib,shutil,subprocess,uuid
from pathlib import Path
import pcbnew
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'bypass_local/native-03'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Reuse the reviewed native inspectors without executing their entry points.
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));before,opens=groups(b);state=object_state(b);fills=fill_state(b);pads={f.GetReference()+'.'+p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()};objects={p.m_Uuid.AsString():p for f in b.GetFootprints() for p in f.Pads()};objects.update({t.m_Uuid.AsString():t for t in b.GetTracks()});ident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()}
plan=json.loads((H/'shared_cutover/plan.json').read_text());moves={};removed=plan['removed_track_uuids'];branches=plan['pin_moves']
for r in branches:
 p=pads[r['ref']+'.'+r['pin']];assert p.m_Uuid.AsString()==r['uuid'] and p.GetNetname()==r['old_net'];p.SetNet(b.GetNetsByName()[r['new_net']]);moves[r['uuid']]=r['new_net']
for u in removed:assert objects[u].GetClass() in ['PCB_TRACK','PCB_VIA'];b.Remove(objects[u])
routeplan=json.loads((H/'shared_cutover/routes.json').read_text());assert routeplan['cut_plan_sha256']==sha(H/'shared_cutover/plan.json');added=[];routegroups=[]
for i,r in enumerate(routeplan['routes']):
 ids=[]
 for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  t=pcbnew.PCB_TRACK(b);t.SetUuid(pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:SHARED-CUTOVER-01:'+str(i)+':'+str(j)))));t.SetStart(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in start]));t.SetEnd(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in end]));t.SetWidth(pcbnew.FromMM(r['width_mm']));t.SetLayer(b.GetLayerID(r['layer']));t.SetNet(b.GetNetsByName()[r['net']]);b.Add(t);ids.append(t.m_Uuid.AsString());added.append(t.m_Uuid.AsString())
 routegroups.append({'net':r['net'],'old_members':[r['source_uuid'],r['target_uuid']],'new_members':ids})
OUT.mkdir(parents=True,exist_ok=True)
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
shutil.copytree(BASE/'libraries',OUT/'libraries',dirs_exist_ok=True)
pcbnew.SaveBoard(str(OUT/'power_protection.kicad_pcb'),b);b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));after,afteropens=groups(b);now=object_state(b)
assert set(now)==(set(state)-set(removed))|set(added)
for u,old in state.items():
 if u in removed:continue
 expected=list(old)
 if u in moves:expected[1]=moves[u]
 assert now[u]==expected,(u,'Unexpected physical or net change')
assert fills==fill_state(b)
expected=[]
for r in before:
 retained=set(r['members'])-set(removed)-set(moves)
 if retained:expected.append({'net':r['net'],'members':sorted(retained)})
for u,net in moves.items():expected.append({'net':net,'members':[u]})
for rg in routegroups:
 selected=[r for r in expected if set(r['members'])&set(rg['old_members'])];assert len(selected)==2
 expected=[r for r in expected if r not in selected]+[{'net':rg['net'],'members':sorted(set(rg['new_members']).union(*(set(r['members']) for r in selected)))}]
if sorted(expected,key=lambda r:r['members'])!=sorted(after,key=lambda r:r['members']):
 old={json.dumps(r,sort_keys=True) for r in expected};new={json.dumps(r,sort_keys=True) for r in after};(OUT/'rejected-group-delta.json').write_text(json.dumps({'missing':sorted(old-new),'unexpected':sorted(new-old)},indent=2)+'\n');raise AssertionError('Isolation changed undeclared original group membership; inspect rejected delta')
newident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert set(ident)==set(newident)
for u,old in ident.items():
 expected=dict(old)
 if u in moves:expected['net']=moves[u]
 assert expected==newident[u]
mapping=json.loads((H/'routed/anonymous-pad-mapping.json').read_text());keys=[]
for row in mapping['mappings']:
 u=row['candidate_uuid'];assert ident[u]==newident[u]==row['full_physical_identity'];keys.append(json.dumps(newident[u],sort_keys=True))
assert len(keys)==55 and len(set(keys))==55
subprocess.run(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],check=True)
report={'source_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_sha256':sha(OUT/'power_protection.kicad_pcb'),'script_sha256':sha(Path(__file__)),'plan_sha256':sha(H/'shared_cutover/plan.json'),'routes_sha256':sha(H/'shared_cutover/routes.json'),'added_track_uuids':added,'local_route_group_merges':routegroups,'removed_copper_uuids':removed,'changed_pin_nets':moves,'native_groups_before':len(before),'native_groups_after':len(after),'exact_declared_pin_isolations_and_local_joins_only':True,'all_original_fills_unchanged':True,'all_other_original_copper_unchanged':True,'anonymous_identity_bijection_preserved':55,'opens_before':opens,'opens_after':afteropens,'qualified':False,'scope':'Isolate and retarget eight shared supply/reset pads; replacement distribution still pending'}
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
