"""Author isolated new-part/new-track candidate and audit original native groups."""
import sys,json,hashlib,uuid,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew
H=Path(sys.argv[1]);BASE=Path(sys.argv[2]);OUT=Path(sys.argv[3]);PLACE=H/'placement'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
uid=lambda s:pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:AUX-ROUTED-01:'+s)))
plan=json.loads((H/'routed/plan.json').read_text());assert sha(BASE/'power_protection.kicad_pcb')==plan['source_sha256']['baseline_pcb']
assert sha(H/'routed/placement.json')==plan['source_sha256']['placement']
assert sha(H/'held_rail/native-03/candidate-netlist.xml')==plan['source_sha256']['netlist']
board=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));board.BuildConnectivity();conn=board.GetConnectivity();conn.RecalculateRatsnest()
def groups(b):
 b.BuildConnectivity();c=b.GetConnectivity();c.RecalculateRatsnest();items=[p for f in b.GetFootprints() for p in f.Pads()]+list(b.GetTracks());by={i.m_Uuid.AsString():i for i in items};seen=set();rows=[]
 for u,p in sorted(by.items()):
  if p.GetClass()!='PAD' or not p.GetNetname() or not p.GetNumber() or u in seen:continue
  members={u}|{i.m_Uuid.AsString() for i in c.GetConnectedItems(p)};members={i for i in members if i in by and by[i].GetNetname()==p.GetNetname()};seen|=members;rows.append({'net':p.GetNetname(),'members':sorted(members)})
 return rows,c.GetUnconnectedCount(False)
def object_state(b):
 rows={}
 for f in b.GetFootprints():
  for p in f.Pads():rows[p.m_Uuid.AsString()]=[p.GetClass(),p.GetNetname(),p.GetNumber(),p.GetPosition().x,p.GetPosition().y,p.GetSize().x,p.GetSize().y,p.GetOrientation().AsDegrees(),p.GetLayerSet().FmtHex()]
 for t in b.GetTracks():
  rows[t.m_Uuid.AsString()]=[t.GetClass(),t.GetNetname(),t.GetPosition().x,t.GetPosition().y,t.GetEnd().x,t.GetEnd().y,t.GetWidth(pcbnew.F_Cu) if t.GetClass()=='PCB_VIA' else t.GetWidth(),t.GetLayer()]
 return rows
def fill_state(b):
 out={}
 for z in b.Zones():
  if z.GetIsRuleArea():continue
  for layer in b.GetEnabledLayers().CuStack():
   if z.IsOnLayer(layer):
    p=z.GetFilledPolysList(layer);loops=[]
    for i in range(p.OutlineCount()):
     chain=p.COutline(i);loops.append([[chain.CPoint(k).x,chain.CPoint(k).y] for k in range(chain.PointCount())])
    out[z.m_Uuid.AsString()+':'+str(layer)]=loops
 return out
before,opens_before=groups(board);oldstate=object_state(board);oldfills=fill_state(board)
xml=ET.parse(H/'held_rail/native-03/candidate-netlist.xml');nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')};comps={c.attrib['ref']:c for c in xml.findall('./components/comp')}
netmap={str(k):v for k,v in board.GetNetsByName().items()};code=max(n.GetNetCode() for n in netmap.values())+1
proposal=json.loads((H/'routed/placement.json').read_text());poses=[p for g in proposal['groups'].values() for p in g['chosen']['parts']]
for name in sorted({nets.get((p['ref'],pin),'') for p in poses for pin in proposal['footprints'][p['ref']]['pads']} - {''}):
 if name not in netmap:n=pcbnew.NETINFO_ITEM(board,name,code);code+=1;board.Add(n);netmap[name]=n
OUT.mkdir(parents=True,exist_ok=True);derived=OUT/'libraries/AUX_ROUTE.pretty';derived.mkdir(parents=True,exist_ok=True);derived_records={}
for pose in poses:
 lib,name=pose['footprint'].split(':');lp=PLACE/'AUX_READY.pretty' if lib=='AUX_READY' else H/'held_rail/authored/libraries'/f'{lib}.pretty'
 assert sha(lp/(name+'.kicad_mod'))==proposal['footprints'][pose['ref']]['source_sha256']
 qualified=lib+'__'+name
 if qualified not in derived_records:
  template=pcbnew.FootprintLoad(str(lp),name);template.SetFPID(pcbnew.LIB_ID('AUX_ROUTE',qualified))
  for text in [template.Reference(),template.Value()]:text.SetLayer(pcbnew.F_Fab);text.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(.8),pcbnew.FromMM(.8)))
  for item in template.GraphicalItems():
   if item.GetLayer()==pcbnew.F_SilkS:item.SetLayer(pcbnew.F_Fab)
  pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(derived),template)
  assert (derived/(qualified+'.kicad_mod')).exists()
  derived_records[qualified]={'source_sha256':sha(lp/(name+'.kicad_mod')),'derived_sha256':sha(derived/(qualified+'.kicad_mod')),'change':'assembly-layer reference/value/artwork only; copper unchanged'}
 f=pcbnew.FootprintLoad(str(derived),qualified);board.Add(f);f.SetUuid(uid(pose['ref']));f.SetReference(pose['ref']);f.SetValue(comps[pose['ref']].findtext('value'));f.SetFPID(pcbnew.LIB_ID('AUX_ROUTE',qualified))
 if pose['layer']=='B.Cu':f.Flip(pcbnew.VECTOR2I(0,0),True)
 f.SetOrientationDegrees(pose['kicad_orientation_degrees_after_left_right_flip']);f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in pose['at_mm']]))
 # Dense candidate: references and pin-one artwork remain visible on the assembly layer.
 for text in [f.Reference(),f.Value()]:text.SetLayer(pcbnew.B_Fab);text.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(.8),pcbnew.FromMM(.8)))
 for item in f.GraphicalItems():
  if item.GetLayer()==pcbnew.B_SilkS:item.SetLayer(pcbnew.B_Fab)
 for p in f.Pads():
  expected=plan['pad_centers_mm'][pose['ref']+'.'+p.GetNumber()];assert abs(p.GetPosition().x/1e6-expected[0])<1e-6 and abs(p.GetPosition().y/1e6-expected[1])<1e-6
  pin=p.GetNumber();p.SetUuid(uid(pose['ref']+'.'+pin));net=nets.get((pose['ref'],pin));p.SetNet(netmap[net]) if net else None
for i,r in enumerate(plan['routes']):
 for j,(a,b) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  t=pcbnew.PCB_TRACK(board);t.SetUuid(uid('track:'+str(i)+':'+str(j)));t.SetStart(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in a]));t.SetEnd(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in b]));t.SetWidth(pcbnew.FromMM(r['width_mm']));t.SetLayer(board.GetLayerID(r['layer']));t.SetNet(netmap[r['net']]);board.Add(t)
for i,v in enumerate(plan['new_vias']):
 t=pcbnew.PCB_VIA(board);t.SetUuid(uid('via:'+v['name']));t.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in v['position_mm']]));t.SetWidth(pcbnew.FromMM(v['size_mm']));t.SetDrill(pcbnew.FromMM(v['drill_mm']));t.SetViaType(pcbnew.VIATYPE_THROUGH);t.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);t.SetNet(netmap[v['net']]);board.Add(t)
current_state=object_state(board);assert all(current_state[u]==s for u,s in oldstate.items());assert fill_state(board)==oldfills
OUT.mkdir(parents=True,exist_ok=True)
for n in ['power_protection.kicad_pro','power_protection.kicad_dru']:shutil.copy2(BASE/n,OUT/n)
shutil.copytree(H/'held_rail/authored/libraries',OUT/'libraries',dirs_exist_ok=True);shutil.copytree(PLACE/'AUX_READY.pretty',OUT/'libraries/AUX_READY.pretty',dirs_exist_ok=True)
table=(H/'held_rail/authored/fp-lib-table').read_text();table=table.rstrip()[:-1]+'(lib (name "AUX_READY") (type "KiCad") (uri "${KIPRJMOD}/libraries/AUX_READY.pretty") (options "") (descr "Isolated AUX land candidates"))(lib (name "AUX_ROUTE") (type "KiCad") (uri "${KIPRJMOD}/libraries/AUX_ROUTE.pretty") (options "") (descr "Assembly-layer variants")))\n';(OUT/'fp-lib-table').write_text(table)
pcbnew.SaveBoard(str(OUT/'power_protection.kicad_pcb'),board);loaded=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));after,opens_after=groups(loaded);state=object_state(loaded);assert all(state[u]==s for u,s in oldstate.items());assert fill_state(loaded)==oldfills
oldids=set(oldstate);after_old=[(r['net'],tuple(sorted(set(r['members'])&oldids))) for r in after if set(r['members'])&oldids];before_old=[(r['net'],tuple(r['members'])) for r in before];assert sorted(after_old)==sorted(before_old),'Original connectivity changed'
subprocess.run(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],check=True)
report={'source_sha256':plan['source_sha256'],'plan_sha256':sha(H/'routed/plan.json'),'native_version':pcbnew.Version(),'opens_before':opens_before,'opens_after':opens_after,'added_vias':len(plan['new_vias']),'added_parts':len(poses),'added_tracks':sum(len(r['path_mm'])-1 for r in plan['routes']),'all_original_pad_and_track_states_preserved':True,'all_original_fills_preserved':True,'all_original_native_connectivity_groups_preserved':True,'all_original_groups_checked':len(before),'derived_footprints':derived_records,'before_groups':before,'after_groups':after,'fabrication_qualified':False,'schematic_parity_checked':False,'scope':'Local new buck routes only; original supply topology retained'}
report['artifact_sha256']={n:sha(OUT/n) for n in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','drc.json','fp-lib-table']}
report['native_script_sha256']=sha(H/'routed/native.py')
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['opens_before','opens_after','added_parts','added_tracks','all_original_groups_checked']}))
