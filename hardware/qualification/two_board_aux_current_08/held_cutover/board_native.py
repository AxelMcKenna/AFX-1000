"""Retarget only three complete isolated driver/bypass supply branches."""
import ast,json,sys,hashlib,shutil,subprocess
from pathlib import Path
import pcbnew
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'routed/native-04'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Reuse the reviewed native inspectors without executing their entry points.
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));before,opens=groups(b);state=object_state(b);fills=fill_state(b);pads={f.GetReference()+'.'+p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()};objects={p.m_Uuid.AsString():p for f in b.GetFootprints() for p in f.Pads()};objects.update({t.m_Uuid.AsString():t for t in b.GetTracks()});ident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()}
net=b.GetNetsByName()['PWR_AUX_HELD3V3'];moves={};branches=[]
for driver,cap in [('E_U1','E_C29'),('E_U2','E_C36'),('E_U3','E_C9')]:
 ids={pads[driver+'.1'].m_Uuid.AsString(),pads[cap+'.1'].m_Uuid.AsString()};rows=[r for r in before if ids<=set(r['members'])];assert len(rows)==1
 row=rows[0];assert row['net']=='PWR_V2V5_AUX' and len(row['members'])==3
 assert {u for u in row['members'] if objects[u].GetClass()=='PAD'}==ids
 for u in row['members']:objects[u].SetNet(net);moves[u]=net.GetNetname()
 branches.append({'driver':driver,'capacitor':cap,'members':row['members'],'old_net':row['net'],'new_net':net.GetNetname()})
for f in b.GetFootprints():
 if f.GetReference() in ['E_C29','E_C36','E_C9','E_C13']:f.SetValue('100nF 50V X7R 10%')
OUT.mkdir(parents=True,exist_ok=True)
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)
shutil.copytree(BASE/'libraries',OUT/'libraries',dirs_exist_ok=True)
pcbnew.SaveBoard(str(OUT/'power_protection.kicad_pcb'),b);b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));after,afteropens=groups(b);now=object_state(b)
assert set(now)==set(state)
for u,old in state.items():
 expected=list(old)
 if u in moves:expected[1]=moves[u]
 assert now[u]==expected,(u,'Unexpected physical or net change')
assert fills==fill_state(b)
expected=[{'net':moves.get(r['members'][0],r['net']),'members':r['members']} for r in before]
assert sorted(expected,key=lambda r:r['members'])==sorted(after,key=lambda r:r['members'])
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
report={'source_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_sha256':sha(OUT/'power_protection.kicad_pcb'),'script_sha256':sha(Path(__file__)),'schematic_sha256':sha(H/'held_cutover/native-03/candidate-netlist.xml'),'anonymous_mapping_sha256':sha(H/'routed/anonymous-pad-mapping.json'),'branches':branches,'changed_objects':moves,'native_groups_checked':len(before),'all_group_memberships_unchanged':True,'all_original_fills_unchanged':True,'full_pad_identities_checked':len(ident),'anonymous_identity_bijection_preserved':55,'opens_before':opens,'opens_after':afteropens,'qualified':False,'limitations':['C29/C36 ground pads remain disconnected','E_U4/C13 and AUP shared branch cutovers pending','Held distribution, return and actual current/timing qualification pending','DSE process clearance conflict remains unwaived']}
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
