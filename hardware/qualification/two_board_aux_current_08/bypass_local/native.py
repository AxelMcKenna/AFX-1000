"""Retarget only three complete isolated driver/bypass supply branches."""
import ast,json,sys,hashlib,shutil,subprocess,uuid
from pathlib import Path
import pcbnew
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'held_loops/native-02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Reuse the reviewed native inspectors without executing their entry points.
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));before,opens=groups(b);state=object_state(b);fills=fill_state(b);pads={f.GetReference()+'.'+p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()};objects={p.m_Uuid.AsString():p for f in b.GetFootprints() for p in f.Pads()};objects.update({t.m_Uuid.AsString():t for t in b.GetTracks()});ident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()}
plan=json.loads((H/'bypass_local/plan.json').read_text());choices=[r['chosen'] for r in plan['rows'] if r['chosen']];assert choices;added=[];removed=[];changedpads={};movedrefs={r['capacitor'] for r in choices};fp={f.GetReference():f for f in b.GetFootprints()};net=b.GetNetsByName()['PWR_AGND'];held=b.GetNetsByName()['PWR_AUX_HELD3V3'];moves={};branches=[]
for r in choices:
 cap=r['capacitor'];f=fp[cap];f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in r['position_mm']]));f.SetOrientationDegrees(r['orientation_degrees'])
 for p in f.Pads():
  expected=r['pad_centers_mm'][p.GetNumber()];assert abs(p.GetPosition().x/1e6-expected[0])<1e-6 and abs(p.GetPosition().y/1e6-expected[1])<1e-6;changedpads[p.m_Uuid.AsString()]=cap
 for u in r['removed_positive_track_uuids']+r['removed_obsolete_ground_track_uuids']:assert objects[u].GetClass()=='PCB_TRACK';b.Remove(objects[u]);removed.append(u)
 for key in [cap+'.1',r['driver']+'.1']:
  p=pads[key]
  if p.GetNetname()!=held.GetNetname():p.SetNet(held);moves[p.m_Uuid.AsString()]=held.GetNetname()
 for kind,n in [('supply',held),('ground',net)]:
  for j,(start,end) in enumerate(zip(r[kind+'_path_mm'],r[kind+'_path_mm'][1:])):
   t=pcbnew.PCB_TRACK(b);t.SetUuid(pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:BYPASS-LOCAL-01:'+cap+':'+kind+':'+str(j)))));t.SetStart(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in start]));t.SetEnd(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in end]));t.SetWidth(pcbnew.FromMM(.3));t.SetLayer(pcbnew.F_Cu);t.SetNet(n);b.Add(t);added.append(t.m_Uuid.AsString())
 if r['new_ground_via']:
  v=r['new_ground_via'];t=pcbnew.PCB_VIA(b);t.SetUuid(pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:BYPASS-LOCAL-01:via:'+cap))));t.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in v['position_mm']]));t.SetWidth(pcbnew.FromMM(.6));t.SetDrill(pcbnew.FromMM(.3));t.SetViaType(pcbnew.VIATYPE_THROUGH);t.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);t.SetNet(net);b.Add(t);added.append(t.m_Uuid.AsString())
OUT.mkdir(parents=True,exist_ok=True)
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
shutil.copytree(BASE/'libraries',OUT/'libraries',dirs_exist_ok=True)
pcbnew.SaveBoard(str(OUT/'power_protection.kicad_pcb'),b);b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));after,afteropens=groups(b);now=object_state(b)
assert set(now)==(set(state)-set(removed))|set(added)
for u,old in state.items():
 if u in removed or u in changedpads:continue
 expected=list(old)
 if u in moves:expected[1]=moves[u]
 assert now[u]==expected,(u,'Unexpected physical or net change')
assert fills==fill_state(b)
# Compare complete original memberships after only one declared join and removal.
oldids=set(state)-set(removed); projected=[{'net':r['net'],'members':sorted(set(r['members'])&oldids)} for r in after if set(r['members'])&oldids]
expected=[{'net':r['net'],'members':sorted(set(r['members'])-set(removed))} for r in before if set(r['members'])-set(removed)]
for nets,keys in ([('PWR_AGND',['E_C36.2'])] if 'E_C36' in movedrefs else [])+([('PWR_AUX_HELD3V3',['E_C13.1','E_U4.1'])] if 'E_C13' in movedrefs else []):
 ids={pads[k].m_Uuid.AsString() for k in keys};selected=[r for r in expected if set(r['members'])&ids or (nets=='PWR_AGND' and '00b41082-e346-59e4-aee2-f34d9b87e697' in r['members'])];joined=set().union(*(set(r['members']) for r in selected));expected=[r for r in expected if r not in selected]+[{'net':nets,'members':sorted(joined)}]
assert sorted(projected,key=lambda r:r['members'])==sorted(expected,key=lambda r:r['members'])
newident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert set(ident)==set(newident)
for u,old in ident.items():
 if u in changedpads:
  for k in ['ref','pin','side','shape','size_nm','drill_nm','drill_shape','attribute','layers_hex','offset_nm','roundrect_radius_ratio','chamfer_ratio']:assert old[k]==newident[u][k]
  assert newident[u]['net']==moves.get(u,old['net'])
 else:
  expected=dict(old)
  if u in moves:expected['net']=moves[u]
  assert expected==newident[u]
mapping=json.loads((H/'routed/anonymous-pad-mapping.json').read_text());keys=[]
for row in mapping['mappings']:
 u=row['candidate_uuid'];assert ident[u]==newident[u]==row['full_physical_identity'];keys.append(json.dumps(newident[u],sort_keys=True))
assert len(keys)==55 and len(set(keys))==55
subprocess.run(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],check=True)
report={'source_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_sha256':sha(OUT/'power_protection.kicad_pcb'),'script_sha256':sha(Path(__file__)),'plan_sha256':sha(H/'bypass_local/plan.json'),'added_copper_uuids':added,'removed_track_uuids':removed,'moved_capacitor_pad_uuids':changedpads,'changed_pin_nets':moves,'native_groups_before':len(before),'native_groups_after':len(after),'exact_declared_group_changes_only':True,'all_other_original_pad_identities_unchanged':True,'all_original_fills_unchanged':True,'all_other_original_copper_unchanged':True,'anonymous_identity_bijection_preserved':55,'opens_before':opens,'opens_after':afteropens,'qualified':False}
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
