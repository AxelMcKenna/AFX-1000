"""Independently verify relocated startup logic, connectivity and references."""
import copy,json,math
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,prop,read_netlist
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
BASE=STAGING/'two-board-power-permission-native-04'
OUT=STAGING/'two-board-power-analog-cells-native-03'
FILLED=STAGING/'two-board-power-analog-cells-filled-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json'


def run():
 sources=[Path(__file__),BEFORE,AFTER,OUT/'analog-cell-routing.json',FILLED/'local-plane-fill.json',BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',OUT/'review.json',OUT/'erc.json',BASE/'permission-review.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','repack_two_board_buck_input.py','route_two_board_buck_cell.py','verify_native_zone_unfracture.py']]]
 before,after,r,fill=[json.loads(p.read_text()) for p in sources[1:5]]
 for p in [BEFORE,AFTER,OUT/'analog-cell-routing.json',FILLED/'local-plane-fill.json',OUT/'review.json',BASE/'permission-review.json']:
  d=json.loads(p.read_text())
  for field in ['source_sha256','artifact_sha256']:
   for name,h in d.get(field,{}).items():
    q=Path(name)
    if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
    assert sha(q)==h,(p,name)
 fidelity=verify_capture(after)
 retired=set(r['retired_objects']);added={u for route in r['routes'] for u in route['segment_uuids']}|{v['uuid'] for v in r['vias']}
 old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
 physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
 aliases={}
 for u in old.keys()-new.keys()-retired:
  assert old[u]['kind']=='PAD'
  matches=[v for v in new.keys()-old.keys()-added if physical(old[u])==physical(new[v])]
  assert len(matches)==1,(u,'unmatched pad');aliases[matches[0]]=u
 assert set(aliases)==new.keys()-old.keys()-added
 for o in after['objects']:o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
 after['all_groups']={aliases.get(g,g):[aliases.get(u,u) for u in members] for g,members in after['all_groups'].items()}
 new={o['uuid']:o for o in after['objects']}
 assert old.keys()-retired==new.keys()-added and not retired&new.keys() and not added&old.keys()
 b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
 fps0,fps1=[{prop(f,'Reference')[2]:f for f in children(b,'footprint')} for b in [b0,b1]]
 def strip(b):
  return [n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired|added or n[0]=='footprint' and prop(n,'Reference')[2] in r['moves']))]
 assert strip(b0)==strip(b1),'Unexpected board edit outside declared objects'
 posepath=STAGING/'two-board-analog-cell-native-poses-05/native-poses.kicad_pcb';sources.append(posepath)
 posefps={prop(f,'Reference')[2]:f for f in children(read_sexpr(posepath.read_text()),'footprint')}
 codes={str(n[2]):int(n[1]) for n in children(b1,'net')}
 for ref in r['moves']:
  f=copy.deepcopy(posefps[ref])
  for pp in children(f,'pad'):
   nn=first(pp,'net');name=str(nn[-1]);nn[:]=[a('net'),codes[name],name]
  paths=children(f,'path');assert len(paths)==1 and paths==children(fps1[ref],'path')
  f[:]=[n for n in f if not(isinstance(n,list) and n and n[0]=='path')];f.extend(paths)
  # The native validator moves the unchanged canonical path to the final field.
  # Atom/string normalization is done through the same native file grammar.
  assert read_sexpr(sexpr(f))==fps1[ref],(ref,'native pose footprint differs')
 moved=[]
 for u in old.keys()-retired:
  o=old[u];n=new[u]
  if o.get('ref') not in r['moves']:assert physical(o)==physical(n),u;continue
  xy,rot,flip=r['moves'][o['ref']];expected=transform_object(o,position(fps0[o['ref']]),xy,rot)
  if flip:expected['layers']={('B.Cu' if l=='F.Cu' else 'F.Cu' if l=='B.Cu' else l):ps for l,ps in expected['layers'].items()}
  for key in ['kind','ref','pin','net','drill_mm','npth']:assert o[key]==n[key],(u,key)
  assert math.dist(expected['position_mm'],n['position_mm'])<1e-6
  assert expected['layers'].keys()==n['layers'].keys()
  for layer in expected['layers']:assert shape(expected['layers'][layer]).hausdorff_distance(shape(n['layers'][layer]))<2e-6
  moved.append(u)
 for route in r['routes']:
  assert len(route['segment_uuids'])==len(route['path_mm'])-1
  for u,p,q in zip(route['segment_uuids'],route['path_mm'],route['path_mm'][1:]):
   o=new[u];assert o['kind']=='PCB_TRACK' and o['net']==route['net'] and list(o['layers'])==[route['layer']] and o['width_mm']==route['width_mm']
   assert math.dist(o['position_mm'],p)<1e-6 and math.dist(o['end_mm'],q)<1e-6
 for v in r['vias']:
  o=new[v['uuid']];assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['width_mm']==.6 and o['drill_mm']==.3 and o['span']==['F.Cu','B.Cu']
  assert math.dist(o['position_mm'],v['position_mm'])<1e-6
 def pad(objects,ref,pin):return next(o for o in objects.values() if o.get('ref')==ref and o.get('pin')==pin)
 expected={frozenset(set(g)-retired) for g in before['all_groups'].values()}-{frozenset()};merges=[]
 def merge(a,b,label):
  left=next(g for g in expected if a in g);right=next(g for g in expected if b in g)
  if left==right:return
  expected.remove(left);expected.remove(right);expected.add(left|right);merges.append(dict(left=a,right=b,label=label))
 cells=[('E_U13','E_R97','E_R98','E_C39','E_R96'),('E_U14','E_R101','E_R102','E_C41','E_R100'),('E_U32','E_R117','E_R118','E_C49','E_R116')]
 for chip,ilm,dvdt,cap,pulldown in cells:
  for left,pin,right,rpin,label in [(chip,'9',ilm,'1','ILM'),(chip,'7',dvdt,'1','DVDT'),(dvdt,'2',cap,'1','DVDT capacitor')]:
   x,y=pad(old,left,pin),pad(old,right,rpin);assert x['net']==y['net'];merge(x['uuid'],y['uuid'],chip+' '+label)
  for ref,pin in [(chip,'2'),(chip,'4'),(chip,'8'),(ilm,'2'),(cap,'2'),(pulldown,'2')]:merge(pad(old,ref,pin)['uuid'],pad(old,'P_C103','2')['uuid'],ref+'.'+pin+' owned ground')
 actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
 assert expected==actual,'Unexpected native connectivity change'
 assert len(merges)==26 and before['native_uncapped_opens']-after['native_uncapped_opens']==26 and after['native_uncapped_opens']==2211
 assert all(new[u].get('group') for u in added),'Orphan new track or via'
 parts0,pins0=read_netlist(BASE/'netlist.xml');parts1,pins1=read_netlist(OUT/'netlist.xml')
 assert parts0.keys()==parts1.keys() and pins0==pins1
 assert all(parts0[ref].findtext(k)==parts1[ref].findtext(k) for ref in parts0 for k in ['value','footprint','datasheet'])
 z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]];nz={z['uuid']:z for z in r['new_zones']}
 assert z1.keys()==z0.keys()|nz.keys() and len(z1)==47
 def hits(g,layer,net,cap):return [o for o in cap['objects'] if o['net']==net and o['layers'].get(layer) and g.buffer(.0015).intersection(shape(o['layers'][layer])).area>1e-9]
 edited={z['uuid']:z for z in r['edited_zone_outlines']};refilled=set(r['refilled_existing_zones'])
 t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
 without=lambda z,keys:[n for n in z if not(isinstance(n,list) and n and n[0] in keys)]
 for u in z0:
  assert z0[u]['net']==z1[u]['net'] and z0[u]['layer']==z1[u]['layer']
  if u not in refilled:assert t0[u]==t1[u] and z0[u]==z1[u],u
  else:assert without(t0[u],['filled_polygon']+(['polygon'] if u in edited else []))==without(t1[u],['filled_polygon']+(['polygon'] if u in edited else [])),u
  if u in edited:assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(edited[u]['outer_mm'],edited[u]['holes_mm']))<2e-6
 assert set(fill['unchanged_existing_zone_canonical_polygon_match'])==z0.keys()-refilled
 quiet=[]
 for q in r['quiet_ground_islands']:
  ownzones=set(q['zone_uuids']);own={v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]};contacts={}
  for u in ownzones:
   z=z1[u];g=shape(z['polygons']);contact={o['uuid'] for o in hits(g,z['layer'],'PWR_AGND',after)}
   assert contact==set(nz[u]['expected_contact_vias']) and contact<=own and len(z['polygons'])==1,(q['ref'],u,'Quiet contacts or field changed',contact)
   assert all(g.distance(shape(other['polygons']))>=.1985 for uid,other in z1.items() if uid!=u and other['layer']==z['layer'] and other['net']=='PWR_AGND'),(u,'Quiet field bypass')
   contacts[u]=sorted(contact)
  reached={q['star_via']['uuid']};pending=set(ownzones)
  while True:
   previous=set(reached)
   for u in list(pending):
    if reached.intersection(contacts[u]):reached.update(contacts[u]);pending.remove(u)
   if reached==previous:break
  assert not pending and own<=reached,(q['ref'],'Disconnected owned return graph')
  for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]:
   o=new[v['uuid']];other={u for u,z in z1.items() if u not in ownzones and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
   assert other==(set(q['allowed_main_star_zones']) if v['uuid']==q['star_via']['uuid'] else set()),(q['ref'],v['uuid'],'Unexpected main/quiet return',other)
  quiet.append(dict(ref=q['ref'],contacts=contacts,owned_graph_connected=True,star_only_main_return=True))
 priorpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json';sources.append(priorpath);prior=json.loads(priorpath.read_text());retainedquiet=[]
 for q in prior['quiet_ground_islands']:
  ownzones=set(q['zone_uuids']);own={v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]}
  for u in ownzones:
   beforecontact={o['uuid'] for o in hits(shape(z0[u]['polygons']),z0[u]['layer'],'PWR_AGND',before)}
   contact={o['uuid'] for o in hits(shape(z1[u]['polygons']),z1[u]['layer'],'PWR_AGND',after)}
   assert contact==beforecontact and q['star_via']['uuid'] in contact and contact<=own
  for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]:
   o=new[v['uuid']];other={u for u,z in z1.items() if u not in ownzones and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
   if v['uuid']==q['star_via']['uuid']:assert any(z1[u]['layer']=='In5.Cu' for u in other)
   else:assert not other,(q['ref'],v['uuid'],'Retained quiet bypass')
  retainedquiet.append(dict(ref=q['ref'],contacts_preserved=True,star_only_main_return=True))
 ownerparts={ref:cell[0] for cell in cells for ref in cell}
 owned={q['ref']:{v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]} for q in r['quiet_ground_islands']}
 for q in r['quiet_ground_islands']:
  owned[q['ref']].update(o['uuid'] for o in new.values() if o['net']=='PWR_AGND' and ownerparts.get(o.get('ref'))==q['ref'])
  owned[q['ref']].update(u for route in r['routes'] if route['net']=='PWR_AGND' and route['owner']==q['ref'] for u in route['segment_uuids'])
 for route in r['routes']:
  if route['net']!='PWR_AGND':continue
  for u in route['segment_uuids']:
   o=new[u];layer=route['layer'];g=shape(o['layers'][layer])
   for other in new.values():
    if other['net']=='PWR_AGND' and other['uuid'] not in owned[route['owner']] and other['layers'].get(layer):assert g.distance(shape(other['layers'][layer]))>=.1985,(u,'Surface return bypass',other['uuid'])
 # Report actual adjacent coverage separately from connectivity. A candidate
 # with reference gaps cannot become the selected revision just because DRC passes.
 ownreference=[]
 for route in r['routes']:
  if not any(s in route['net'] for s in ['_ILM','_DVDT']):continue
  layer={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[route['layer']];g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  for o in new.values():
   if o['kind']=='PCB_VIA' and o['net']==route['net']:g=g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
  fields=unary_union([shape(z1[u]['polygons']) for q in r['quiet_ground_islands'] if q['ref']==route['owner'] for u in q['zone_uuids'] if z1[u]['layer']==layer])
  area=g.difference(fields.buffer(.0015)).area
  ownreference.append(dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),owner=route['owner'],reference_layer=layer,uncovered_mm2=area))
 native=json.loads((OUT/'review.json').read_text());erc=json.loads((OUT/'erc.json').read_text());ef=[v for s in erc['sheets'] for v in s.get('violations',[])]
 assert native['geometry_findings']==native['schematic_parity_findings']==0 and all(v['severity']=='warning' for v in ef) and len(ef)==2
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,generated_pad_identity_aliases=aliases,closed_connections=26,new_opens=2211,moved_pad_count=len(moved),retained_part_count=len(parts0),retained_pin_entries=len(pins0),declared_native_joins=merges,all_other_native_groups_preserved=True,new_quiet_returns=quiet,retained_digital_quiet_returns=retainedquiet,own_quiet_reference=ownreference,own_quiet_reference_complete=all(x['uncovered_mm2']<1e-6 for x in ownreference),geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,retained_reference_audit_pending=True,new_control_reference_audit_pending=True,complete_current_thermal_parasitic_qualification=False,fabrication_released=False)
 with (OUT/'analog-connectivity-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['closed_connections','new_opens','moved_pad_count','all_other_native_groups_preserved','own_quiet_reference_complete']}))
if __name__=='__main__':run()
