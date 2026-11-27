"""Add only declared local cell copper and audit exact original-group joins."""
import ast,json,sys,hashlib,uuid,shutil,os
from pathlib import Path
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
import copy,xml.etree.ElementTree as ET
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'main_ldo/native-03';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();plan=json.loads((H/'ldo_local/local-routes.json').read_text());capture=json.loads((H/'ldo_local/capture-01/capture.json').read_text());assert plan['capture_sha256']==sha(H/'ldo_local/capture-01/capture.json');assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in capture['source_sha256'].items())
plan.update(new_vias=[],failures=[]);assert all(r['path_mm'] for r in plan['routes'])
OUT.mkdir(parents=True,exist_ok=True)
for label,args in [('netlist',['sch','export','netlist','--format','kicadxml','--output',str(OUT/'candidate-netlist.xml')]),('erc',['sch','erc','--format','json','--output',str(OUT/'candidate-erc.json')])]:
 result=run_recorded(['kicad-cli',*args,str(H/'ldo_local/authored/power_protection.kicad_sch')],OUT/(label+'-process'),180,[H/'ldo_local/authored/P_power_p03.kicad_sch']);assert result['status']=='passed'
xml=ET.parse(OUT/'candidate-netlist.xml');pin_nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')};assert {pin:net for (ref,pin),net in pin_nets.items() if ref=='P_C907'}=={'1':'/P_power_supply/AUX_PREREG5','2':'PWR_AGND'}
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
uid=lambda label:pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:LDO-LOCAL-01:'+label)))
f=pcbnew.FootprintLoad(str(H/'shared_cutover/native-04/libraries/TB05_P_Capacitor_SMD.pretty'),'C_0603_1608Metric');assert f is not None;b.Add(f);f.SetUuid(uid('P_C907'));f.SetReference('P_C907');f.SetValue('1uF 25V X7R 10%');f.SetFPID(pcbnew.LIB_ID('TB05_P_Capacitor_SMD','C_0603_1608Metric'));f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(187.5),pcbnew.FromMM(126.6)));f.SetOrientationDegrees(180);f.Reference().SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(183.5),pcbnew.FromMM(126.6)));f.Reference().SetTextAngle(pcbnew.EDA_ANGLE(0,pcbnew.DEGREES_T))
newpads=[]
for pad in f.Pads():
 pin=pad.GetNumber();pad.SetUuid(uid('P_C907.'+pin));pad.SetNet(netmap[pin_nets['P_C907',pin]]);u=pad.m_Uuid.AsString();newpads.append(u);pads['P_C907.'+pin]=pad;netnames[u]=pad.GetNetname();find(u)
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
(OUT/'libraries').symlink_to((BASE/'libraries').resolve(),target_is_directory=True);pcbnew.SaveBoard(str(OUT/'authored-native.kicad_pcb'),b)
d=OUT/'refill';d.mkdir();shutil.copy2(OUT/'authored-native.kicad_pcb',d/'power_protection.kicad_pcb')
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,d/n)
(d/'libraries').symlink_to((BASE/'libraries').resolve(),target_is_directory=True)
proc=run_recorded(['kicad-cli','pcb','drc','--refill-zones','--save-board','--format','json','--output',str(d/'drc.json'),str(d/'power_protection.kicad_pcb')],OUT/'refill-process',180,[OUT/'authored-native.kicad_pcb',H/'ldo_local/local-routes.json']);assert proc['status']=='passed';shutil.copy2(d/'power_protection.kicad_pcb',OUT/'full-refill.kicad_pcb');rt=read_sexpr((OUT/'full-refill.kicad_pcb').read_text());rz={first(z,'uuid')[1]:z for z in children(rt,'zone')};cut='d0572a8e-b95d-5c59-9a7c-1d3514a507b4'
tree=read_sexpr((OUT/'authored-native.kicad_pcb').read_text());source=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());original={first(z,'uuid')[1]:z for z in children(source,'zone')};tree[:]=[copy.deepcopy(original[first(x,'uuid')[1]]) if isinstance(x,list) and x[0]=='zone' else x for x in tree]
for z in children(tree,'zone'):
 if first(z,'uuid')[1]==cut:
  assert first(z,'net')[1]=='PWR_AGND';z[:]=[v for v in z if not isinstance(v,list) or v[0]!='filled_polygon'];z.extend(copy.deepcopy(children(rz[cut],'filled_polygon')))
fp=next(f for f in children(tree,'footprint') if any(p[1:3]==['Reference','P_C907'] for p in children(f,'property')))
for key,val in [('MPN','C0603C105K3RACTU'),('Datasheet','https://search.kemet.com/component-documentation/download/specsheet/C0603C105K3RAC7867')]:
 existing=next((x for x in children(fp,'property') if x[1]==key),None)
 if existing:existing[2]=val
 else:fp.append([Atom('property'),key,val,[Atom('at'),Atom('187.5'),Atom('126.6'),Atom('0')],[Atom('layer'),'F.Fab'],[Atom('hide'),Atom('yes')],[Atom('effects'),[Atom('font'),[Atom('size'),Atom('1'),Atom('1')]]]])
(OUT/'power_protection.kicad_pcb').write_text(sexpr(tree)+'\n');b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));assert b is not None;after,afteropens=groups(b);now=object_state(b);assert set(now)==set(state)|set(added)|set(newpads) and all(now[u]==s for u,s in state.items());nf=fill_state(b);assert all(nf[u]==v for u,v in fills.items() if u.rsplit(':',1)[0]!=cut);newident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert set(newident)==set(ident)|set(newpads) and all(newident[u]==v for u,v in ident.items())
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
report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'planner_sha256':sha(H/'ldo_local/local_routes.py'),'plan_sha256':sha(H/'ldo_local/local-routes.json'),'script_sha256':sha(Path(__file__)),'helper_sha256':{n:sha(H/n) for n in ['routed/native.py','routed/identity_native.py','held_cell/process_adapter.py']},'added_geometry_sha256':sha(OUT/'added-copper-geometry.json'),'added_copper_uuids':added,'added_pad_uuids':newpads,'added_footprint':'P_C907','opens_before':opens,'opens_after':afteropens,'exact_declared_group_joins_only':True,'all_original_objects_and_pad_identities_unchanged':True,'all_48_other_fills_unchanged':True,'cutback_zone_uuid':cut,'full_refill_sha256':sha(OUT/'full-refill.kicad_pcb'),'anonymous_identity_bijection_preserved':55,'routes':len(plan['routes']),'new_vias':len(plan['new_vias']),'remaining_plan_failures':plan['failures'],'qualified':False};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
