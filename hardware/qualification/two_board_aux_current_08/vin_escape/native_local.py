"""Native paired transition with declared AGND antipads and exact group delta."""
import ast,copy,json,sys,hashlib,uuid,shutil
from pathlib import Path
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from hardware.qualification.two_board_aux_current_08.held_cell.process_adapter import run_recorded
H=Path(sys.argv[1]);OUT=Path(sys.argv[2]);BASE=H/'precision/native-01';P=H/'vin_escape';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();plan=json.loads((P/'plan.json').read_text());assert not plan['failures'] and sha(BASE/'power_protection.kicad_pcb')==plan['source_board_sha256'];assert plan['planner_sha256']==sha(P/'plan.py')
for name,names in [('routed/native.py',{'groups','object_state','fill_state'}),('routed/identity_native.py',{'identity','polygons'})]:
 tree=ast.parse((H/name).read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),name,'exec'))
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));assert b is not None;before,opens=groups(b);state=object_state(b);fills=fill_state(b);ident={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};pads={f.GetReference()+'.'+p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()};netmap=b.GetNetsByName();added=[];parent={};nets={}
def find(u):
 parent.setdefault(u,u)
 if parent[u]!=u:parent[u]=find(parent[u])
 return parent[u]
def union(a,b):parent[find(a)]=find(b)
for r in before:
 for u in r['members']:union(u,r['members'][0]);nets[u]=r['net']
uid=lambda label:pcbnew.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:VIN-PAIRED-ESCAPE-01:'+label)))
for v in plan['new_vias']:
 t=pcbnew.PCB_VIA(b);t.SetUuid(uid('via:'+v['name']));t.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in v['position_mm']]));t.SetWidth(pcbnew.FromMM(v['size_mm']));t.SetDrill(pcbnew.FromMM(v['drill_mm']));t.SetViaType(pcbnew.VIATYPE_THROUGH);t.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);t.SetNet(netmap[v['net']]);b.Add(t);u=t.m_Uuid.AsString();added.append(u);pads['via:'+v['name']]=t;nets[u]=v['net'];find(u)
 if v['net']=='PWR_AGND':union(u,'00b41082-e346-59e4-aee2-f34d9b87e697')
for i,r in enumerate(plan['routes']):
 a,z=pads[r['source']],pads[r['target']];assert a.GetNetname()==z.GetNetname()==r['net'];su=a.m_Uuid.AsString();union(su,z.m_Uuid.AsString())
 for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  t=pcbnew.PCB_TRACK(b);t.SetUuid(uid('track:'+str(i)+':'+str(j)));t.SetStart(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in start]));t.SetEnd(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in end]));t.SetWidth(pcbnew.FromMM(r['width_mm']));t.SetLayer(b.GetLayerID(r['layer']));t.SetNet(netmap[r['net']]);b.Add(t);u=t.m_Uuid.AsString();added.append(u);nets[u]=r['net'];union(u,su)
OUT.mkdir(exist_ok=True);resume='--resume' in sys.argv
if resume:
 ab=pcbnew.LoadBoard(str(OUT/'authored.kicad_pcb'));assert ab is not None and object_state(ab)==object_state(b) and fill_state(ab)==fill_state(b)
else:pcbnew.SaveBoard(str(OUT/'authored.kicad_pcb'),b)
auth=read_sexpr((OUT/'authored.kicad_pcb').read_text());cut=set(plan['declared_cutback_zone_uuids']);legacy_zone='78fadc71-5bdb-5968-8ca8-0e3b4b40722f';bridge='38c31b6e-bfc4-5702-b059-ff9efeabba60';assert legacy_zone in cut and bridge in cut;filled={};context_reports={}
# Reuse recorded native refills only to extract the exact new antipad contour.
prior=P/'native-01';local=pcbnew.LoadBoard(str(OUT/'authored.kicad_pcb'));assert local is not None
for tag in ['default','legacy-in6']:
 source=prior/(tag+'-full-refill.kicad_pcb');rb=pcbnew.LoadBoard(str(source));assert rb is not None
 context_reports[tag]={'full_refill_sha256':sha(source),'omitted_zone_uuids':[bridge] if tag=='legacy-in6' else []}
 for z in rb.Zones():
  u=z.m_Uuid.AsString()
  if u not in cut or (u==legacy_zone)!=(tag=='legacy-in6'):continue
  pg=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()));pg.Unfracture();holes=[]
  at=pcbnew.VECTOR2I(pcbnew.FromMM(198),pcbnew.FromMM(118.6))
  for oi in range(pg.OutlineCount()):
   for hi in range(pg.HoleCount(oi)):
    h=pg.Hole(oi,hi)
    if h.PointInside(at):holes.append(h)
  assert len(holes)==1
  hole=pcbnew.SHAPE_POLY_SET();hole.AddOutline(holes[0]);target=next(x for x in local.Zones() if x.m_Uuid.AsString()==u)
  original=pcbnew.SHAPE_POLY_SET(target.GetFilledPolysList(target.GetLayer()));original.Unfracture();original.BooleanSubtract(hole);original.Fracture();target.SetFilledPolysList(target.GetLayer(),original)
pcbnew.SaveBoard(str(OUT/'local-fill.kicad_pcb'),local)
lf=read_sexpr((OUT/'local-fill.kicad_pcb').read_text());lz={first(z,'uuid')[1]:z for z in children(lf,'zone')}
for z in children(auth,'zone'):
 u=first(z,'uuid')[1]
 if u in cut:
  z[:]=[x for x in z if not isinstance(x,list) or x[0]!='filled_polygon'];z.extend(copy.deepcopy(children(lz[u],'filled_polygon')))
(OUT/'power_protection.kicad_pcb').write_text(sexpr(auth)+'\n')
for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(BASE/n,OUT/n)

if not (OUT/'libraries').is_symlink():(OUT/'libraries').symlink_to((BASE/'libraries').resolve(),target_is_directory=True)
b=pcbnew.LoadBoard(str(OUT/'power_protection.kicad_pcb'));assert b is not None;after,afteropens=groups(b);now=object_state(b);assert set(now)==set(state)|set(added) and all(now[u]==v for u,v in state.items());nf=fill_state(b);assert all(nf[u]==v for u,v in fills.items() if u.rsplit(':',1)[0] not in cut);ni={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};assert ni==ident;expected={}
for u in parent:expected.setdefault(find(u),[]).append(u)
rows=[{'net':nets[us[0]],'members':sorted(us)} for us in expected.values()];group_pass=sorted(rows,key=lambda r:r['members'])==sorted(after,key=lambda r:r['members']);mapping=json.loads((H/'routed/anonymous-pad-mapping.json').read_text());keys=[]
for r in mapping['mappings']:assert ni[r['candidate_uuid']]==r['full_physical_identity'];keys.append(json.dumps(ni[r['candidate_uuid']],sort_keys=True))
assert len(keys)==len(set(keys))==55;geo=[];zones=[]
for t in b.GetTracks():
 if t.m_Uuid.AsString() in added:
  layers={}
  for l in b.GetEnabledLayers().CuStack():
   if t.IsOnLayer(l):pg=pcbnew.SHAPE_POLY_SET();t.TransformShapeToPolygon(pg,l,0,pcbnew.FromMM(.001),pcbnew.ERROR_OUTSIDE);pg.Simplify();layers[b.GetLayerName(l)]=polygons(pg)
  geo.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'kind':t.GetClass(),'layers_nm':layers})
for z in b.Zones():
 if z.m_Uuid.AsString() in cut:
  layer=z.GetLayer();pg=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(layer));pg.Unfracture();zones.append({'uuid':z.m_Uuid.AsString(),'net':z.GetNetname(),'layer':b.GetLayerName(layer),'polygons_nm':polygons(pg)})
(OUT/'geometry.json').write_text(json.dumps({'source_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'objects':geo,'zones':zones},indent=2)+'\n');proc=run_recorded(['kicad-cli','pcb','drc','--format','json','--output',str(OUT/'drc.json'),str(OUT/'power_protection.kicad_pcb')],OUT/'drc-process',180,[OUT/'power_protection.kicad_pcb']);assert proc['status']=='passed';(OUT/'libraries').unlink();(OUT/'libraries').symlink_to('../../shared_cutover/native-04/libraries',target_is_directory=True)
report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'authored_board_sha256':sha(OUT/'authored.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'plan_sha256':sha(P/'plan.json'),'script_sha256':sha(Path(__file__)),'helper_sha256':{n:sha(H/n) for n in ['routed/native.py','routed/identity_native.py','held_cell/process_adapter.py']},'geometry_sha256':sha(OUT/'geometry.json'),'contexts':context_reports,'added_copper_uuids':added,'cutback_zone_uuids':sorted(cut),'opens_before':opens,'opens_after':afteropens,'exact_declared_group_joins_only':group_pass,'all_original_objects_and_pad_identities_unchanged':True,'all_other_fills_unchanged':True,'anonymous_identity_bijection_preserved':55,'local_antipad_only_from_recorded_native_refill':True,'resumed_after_zone_key_guard_correction':resume,'initial_script_sha256':sha(P/'native_initial.py') if resume else None,'qualified':False};(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert group_pass
