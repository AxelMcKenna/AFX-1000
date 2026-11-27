"""Isolated C13 relocation, fixed source identities, unchanged pad connectivity."""
import ast,json,sys,uuid,hashlib
from pathlib import Path
import pcbnew
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);Q=H.parent;src=Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src)=='2a09f31abdcca36908a37008a5d8a493a13e41d8e4913c590131b7afd86dc860'
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((Q/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(src));assert b is not None
before,opens=groups(b);state=object_state(b);fills=fill_state(b);ids={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()}
p=json.loads((H/'plan.json').read_text());r=p['rows'][0]['chosen'];assert r['capacitor']=='E_C13' and r['driver']=='E_U4' and not r['new_ground_via'];fp={f.GetReference():f for f in b.GetFootprints()};pads={f.GetReference()+'.'+p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()}
assert pads['E_C13.1'].GetNetname()==pads['E_U4.1'].GetNetname()=='PWR_AUX_HELD3V3';assert pads['E_C13.2'].GetNetname()==pads['E_U4.4'].GetNetname()=='PWR_AGND';assert pads['E_U4.2'].GetNetname().endswith('_TT')
removed=set(r['removed_obsolete_ground_track_uuids']);assert removed=={'be10ecd4-fadc-5c64-aaeb-bd4b51ed6179','5ef08684-f016-59a4-b87e-49d4da43c3b3'}
objects={t.m_Uuid.AsString():t for t in b.GetTracks()}
for u in removed:
 assert objects[u].GetClass()=='PCB_TRACK';b.Remove(objects[u])
f=fp['E_C13'];assert [f.GetPosition().x/1e6,f.GetPosition().y/1e6]==[108.275,129.095];assert f.GetOrientationDegrees()==90;oldref=f.Reference().GetPosition();f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(v) for v in r['position_mm']]));f.Reference().SetPosition(oldref)
added=[]
for kind,net,path in [('supply','PWR_AUX_HELD3V3',r['supply_path_mm']),('ground','PWR_AGND',r['ground_path_mm'])]:
 for j,(a,z) in enumerate(zip(path,path[1:])):
  t=pcbnew.PCB_TRACK(b);t.SetUuid(pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:C13-RECEIVING-01:'+kind+str(j)))));t.SetStart(pcbnew.VECTOR2I(*[pcbnew.FromMM(v) for v in a]));t.SetEnd(pcbnew.VECTOR2I(*[pcbnew.FromMM(v) for v in z]));t.SetWidth(pcbnew.FromMM(.3));t.SetLayer(pcbnew.F_Cu);t.SetNet(b.GetNetsByName()[net]);b.Add(t);added.append(t.m_Uuid.AsString())
after,nopens=groups(b);now=object_state(b);assert set(now)==(set(state)-removed)|set(added)
moved={p.m_Uuid.AsString() for p in f.Pads()}
for u,v in state.items():
 if u not in removed|moved:assert now[u]==v,u
normalize=lambda gs: sorted((g['net'],tuple(sorted(set(g['members'])-removed-set(added)))) for g in gs)
assert normalize(before)==normalize(after);assert nopens==opens;assert fill_state(b)==fills
nids={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()}
for u,v in ids.items():
 if u not in moved:assert nids[u]==v,u
for row in json.loads((Q/'routed/anonymous-pad-mapping.json').read_text())['mappings']:
 assert ids[row['candidate_uuid']]==nids[row['candidate_uuid']]
OUT.mkdir(exist_ok=True,parents=True);target=OUT/'power_protection.kicad_pcb';pcbnew.SaveBoard(str(target),b)
report={'source_sha256':sha(src),'plan_sha256':sha(H/'plan.json'),'script_sha256':sha(Path(__file__)),'candidate_sha256':sha(target),'moved_pad_UUIDs':sorted(moved),'removed_track_UUIDs':sorted(removed),'added_track_UUIDs':added,'before_opens':opens,'after_opens':nopens,'all_original_pad_groups_preserved':True,'all_fills_unchanged':True,'all_other_pad_identities_unchanged':True,'new_position_mm':r['position_mm'],'qualified':False};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
