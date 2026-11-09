"""Independently audit native digital startup fanout and connection changes."""
import copy,json,math
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,prop,read_netlist
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
BASE=STAGING/'two-board-power-digital-reference-native-02'
OUT=STAGING/'two-board-power-digital-startup-native-01'
FILLED=STAGING/'two-board-power-digital-startup-filled-02'
BEFORE=STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2310-digital-startup-01/capture.json'


def run():
 sources=[Path(__file__),BEFORE,AFTER,OUT/'digital-startup-routing.json',FILLED/'local-plane-fill.json',BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',OUT/'review.json',OUT/'erc.json',BASE/'digital-reference-review.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','repack_two_board_buck_input.py','route_two_board_buck_cell.py','verify_native_zone_unfracture.py']]]
 before,after,r,fill=[json.loads(p.read_text()) for p in sources[1:5]]
 for p in [BEFORE,AFTER,OUT/'digital-startup-routing.json',FILLED/'local-plane-fill.json',OUT/'review.json',BASE/'digital-reference-review.json']:
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
 for ref,(xy,rot,flip) in r['moves'].items():assert not flip and read_sexpr(sexpr(rotate_footprint(fps0[ref],xy,rot)))==fps1[ref]
 moved=[]
 for u in old.keys()-retired:
  o=old[u];n=new[u]
  if o.get('ref') not in r['moves']:assert physical(o)==physical(n),u;continue
  xy,rot,_=r['moves'][o['ref']];expected=transform_object(o,position(fps0[o['ref']]),xy,rot)
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
 expected={frozenset(set(g)-retired) for g in before['all_groups'].values()}-{frozenset()}
 merges=[]
 for resistor,chip,pin in [('E_R103','E_U15','3'),('E_R107','E_U16','3'),('E_R111','E_U17','3'),('E_R119','E_U33','3'),('E_R108','E_U16','1'),('E_R112','E_U17','1'),('E_R120','E_U33','1')]:
  merges.append((pad(old,resistor,'1')['uuid'],pad(old,chip,pin)['uuid']))
  if pin=='1':merges.append((pad(old,resistor,'2')['uuid'],pad(old,chip,'8')['uuid']))
 for a,b in merges:
  left=next(g for g in expected if a in g);right=next(g for g in expected if b in g);assert left!=right
  expected.remove(left);expected.remove(right);expected.add(left|right)
 actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
 assert expected==actual,'Native connection changes differ from the ten declared joins'
 assert before['native_uncapped_opens']-after['native_uncapped_opens']==10 and after['native_uncapped_opens']==2310
 parts0,pins0=read_netlist(BASE/'netlist.xml');parts1,pins1=read_netlist(OUT/'netlist.xml')
 assert parts0.keys()==parts1.keys() and pins0==pins1
 assert all(parts0[ref].findtext(k)==parts1[ref].findtext(k) for ref in parts0 for k in ['value','footprint','datasheet'])
 z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]];assert z0.keys()==z1.keys() and len(z1)==36
 def hits(g,layer,net,cap):return [o for o in cap['objects'] if o['net']==net and o['layers'].get(layer) and g.buffer(.0015).intersection(shape(o['layers'][layer])).area>1e-9]
 edited={z['uuid']:z for z in r['edited_zone_outlines']};refilled=set(r['refilled_existing_zones'])
 t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
 without=lambda z,keys:[n for n in z if not(isinstance(n,list) and n and n[0] in keys)]
 # Several retained ground bridges contact another same-layer zone rather
 # than a pad or via directly. Audit the actual merged copper component.
 copper_components={}
 for key in {(z['layer'],z['net']) for z in z1.values()}:
  g=unary_union([shape(z['polygons']) for z in z1.values() if (z['layer'],z['net'])==key])
  copper_components[key]=list(g.geoms) if hasattr(g,'geoms') else [g]
 for u in z0:
  assert z0[u]['net']==z1[u]['net'] and z0[u]['layer']==z1[u]['layer']
  if u not in refilled:assert t0[u]==t1[u] and z0[u]==z1[u]
  else:assert without(t0[u],['filled_polygon']+(['polygon'] if u in edited else []))==without(t1[u],['filled_polygon']+(['polygon'] if u in edited else []))
  if u in edited:assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(edited[u]['outer_mm'],edited[u]['holes_mm']))<2e-6
  for p in z1[u]['polygons']:
   part=Polygon(p['outer'],p['holes']);components=[g for g in copper_components[z1[u]['layer'],z1[u]['net']] if part.difference(g.buffer(.000002)).area<1e-6]
   assert len(components)==1,(u,'ambiguous copper component')
   assert len({o['group'] for o in hits(components[0],z1[u]['layer'],z1[u]['net'],after)})==1,(u,'orphaned copper')
 assert set(fill['unchanged_existing_zone_canonical_polygon_match'])==z0.keys()-refilled
 quiet=[]
 for q in r['quiet_ground_islands']:
  own={v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]};ownzones=set(q['zone_uuids']);contacts={}
  for u in ownzones:
   z=z1[u];g=shape(z['polygons']);contact={o['uuid'] for o in hits(g,z['layer'],'PWR_AGND',after)}
   assert q['star_via']['uuid'] in contact and contact<=own and len(z['polygons'])==1,(q['ref'],u,contact)
   if z['layer']=='In1.Cu':assert {v['uuid'] for v in q['control_vias']}<=contact
   if z['layer']=='In6.Cu':assert {v['uuid'] for v in q['extra_quiet_vias']}<=contact
   assert all(g.distance(shape(other['polygons']))>=.1985 for uid,other in z1.items() if uid!=u and other['layer']==z['layer'] and other['net']=='PWR_AGND')
   contacts[u]=sorted(contact)
  for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]:
   o=new[v['uuid']];other={u for u,z in z1.items() if u not in ownzones and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
   if v['uuid']==q['star_via']['uuid']:assert any(z1[u]['layer']=='In5.Cu' for u in other)
   else:assert not other,(q['ref'],v['uuid'],other)
  quiet.append(dict(ref=q['ref'],contacts=contacts,star_only_main_return=True))
 # Same-net ground copper is deliberately screened by local owner; ordinary
 # DRC and net-specific connected groups cannot detect a quiet-return bypass.
 localpath=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json'
 oldlocal=json.loads(localpath.read_text());sources.append(localpath)
 ownerrefs={'E_U15':['E_U15','E_R105','E_C43','E_R103'],'E_U16':['E_U16','E_R109','E_C45','E_R107','E_R108'],'E_U17':['E_U17','E_R113','E_C47','E_R111','E_R112'],'E_U33':['E_U33','E_R121','E_C51','E_R119','E_R120']}
 allowed={chip:{o['uuid'] for o in new.values() if o.get('ref') in refs and o['net']=='PWR_AGND'} for chip,refs in ownerrefs.items()}
 for route in oldlocal['routes']+r['routes']:
  chip=route.get('owner',route.get('chip',route.get('ref')))
  if chip in allowed and route['net']=='PWR_AGND':allowed[chip].update(set(route['segment_uuids'])&new.keys())
 for q in r['quiet_ground_islands']:allowed[q['ref']].update(v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']])
 minimum_quiet_gap=1000.
 for route in r['routes']:
  if route['net']!='PWR_AGND':continue
  chip=route.get('owner',route.get('chip',route.get('ref')));assert chip in allowed
  for u in route['segment_uuids']:
   o=new[u];layer=route['layer'];g=shape(o['layers'][layer])
   for other in new.values():
    if other['uuid'] in allowed[chip] or other['net']!='PWR_AGND' or not other['layers'].get(layer):continue
    gap=g.distance(shape(other['layers'][layer]));minimum_quiet_gap=min(minimum_quiet_gap,gap)
    assert gap>=.1985,(u,'surface quiet return bypass',other['uuid'],gap)
 minimum_via_smd_drill_gap=1000.;minimum_hole_gap=1000.
 for via in r['vias']:
  pt=Point(via['position_mm'])
  for o in new.values():
   if o['uuid']==via['uuid']:continue
   drill=o.get('drill_mm',0);radius=max(drill)/2 if isinstance(drill,list) else drill/2
   if radius:
    gap=pt.distance(Point(o['position_mm']))-.15-radius;minimum_hole_gap=min(minimum_hole_gap,gap);assert gap>=.24999,(via['uuid'],'hole separation',o['uuid'],gap)
   elif o['kind']=='PAD':
    for layer in ['F.Cu','B.Cu']:
     if not o['layers'].get(layer):continue
     gap=pt.distance(shape(o['layers'][layer]))-.15;minimum_via_smd_drill_gap=min(minimum_via_smd_drill_gap,gap);assert gap>=.149,(via['uuid'],'drill-to-SMD copper',o['uuid'],gap)
 source=next(u for u,z in z0.items() if z['net']=='PWR_5V_DIG_SRC' and z['layer']=='In4.Cu')
 hs=lambda c,z:{o['uuid'] for o in hits(shape(z['polygons']),z['layer'],z['net'],c)}
 assert hs(before,z0[source])==hs(after,z1[source]) and len(z1[source]['polygons'])==1
 # Preserve complete adjacent-ground coverage of every retained old signal trace.
 def references(c):
  regions={}
  for z in c['zones']:
   if z['net']!='PWR_AGND':continue
   for p in z['polygons']:
    g=Polygon(p['outer'],p['holes']);contact=hits(g,z['layer'],z['net'],c)
    if not contact:continue
    groups={o['group'] for o in contact};assert len(groups)==1
    regions.setdefault((z['layer'],next(iter(groups))),[]).append(g)
  return {key:unary_union(ps) for key,ps in regions.items()}
 refs0,refs1=references(before),references(after);coverage=[];layers=after['copper_layers']
 for u,o in old.items():
  if u in retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)};g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  for v in old.values():
   if v['kind']=='PCB_VIA' and v['net']==o['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  if g.is_empty:continue
  for (layer,gid),reference in refs0.items():
   if layer not in adj or g.difference(reference.buffer(.0015)).area>=1e-6:continue
   anchors=[x for x in before['all_groups'][gid] if x in new];assert anchors
   target=refs1[(layer,new[anchors[0]]['group'])];area=g.difference(target.buffer(.0015)).area
   assert area<1e-6,(u,'lost prior adjacent reference',area)
   coverage.append(dict(track_uuid=u,reference_layer=layer,uncovered_mm2=area))
 # Preserve each ILM/DVDT support route's own quiet reference, including
 # the explicitly retained tiny via-edge gaps from TBP39.
 oldreferencepath=BASE/'digital-reference-routing.json';trackpath=BASE/'digital-reference-track-routing.json'
 sources.extend([oldreferencepath,trackpath]);oldreference=json.loads(oldreferencepath.read_text());replacement=json.loads(trackpath.read_text())
 ownbefore={q['ref']:{q['zone_uuid'],next(z['uuid'] for z in oldreference['new_zones'] if z['ref']==q['ref'] and z['layer']=='In6.Cu')} for q in oldreference['quiet_ground_islands']}
 ownafter={q['ref']:set(q['zone_uuids']) for q in r['quiet_ground_islands']}
 ownerparts={ref:chip for chip,refs in {'E_U15':['E_U15','E_R105','E_R106','E_C43'],'E_U16':['E_U16','E_R109','E_R110','E_C45'],'E_U17':['E_U17','E_R113','E_R114','E_C47'],'E_U33':['E_U33','E_R121','E_R122','E_C51']}.items() for ref in refs}
 ownreference=[]
 for route in oldlocal['routes']:
  if route.get('label')==replacement['retired_route']['label']:route=replacement['replacement_route']
  if route['net'] in ['PWR_AGND','PWR_5V_DIG_SRC']:continue
  chip=route.get('chip',ownerparts.get(route.get('ref')));assert chip in ownbefore
  layer='In1.Cu' if route['layer']=='F.Cu' else 'In6.Cu';g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  for v in old.values():
   if v['kind']=='PCB_VIA' and v['net']==route['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  missing=[]
  for z,owned in [(z0,ownbefore),(z1,ownafter)]:missing.append(g.difference(unary_union([shape(z[u]['polygons']) for u in owned[chip] if z[u]['layer']==layer]).buffer(.0015)))
  assert missing[1].difference(missing[0].buffer(.000002)).area<1e-6,(route.get('label'),'lost own quiet reference',missing[0].area,missing[1].area)
  ownreference.append(dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),owner=chip,layer=layer,before_uncovered_mm2=missing[0].area,after_uncovered_mm2=missing[1].area))
 native=json.loads((OUT/'review.json').read_text());assert native['geometry_findings']==native['schematic_parity_findings']==0
 warnings=[v for s in json.loads((OUT/'erc.json').read_text())['sheets'] for v in s.get('violations',[])];assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,generated_pad_identity_aliases=aliases,closed_connections=10,new_opens=2310,moved_pad_count=len(moved),retained_part_count=len(parts0),retained_pin_entries=len(pins0),declared_native_joins=merges,all_other_native_groups_preserved=True,quiet_returns=quiet,source_plane_contacts_preserved=len(hs(before,z0[source])),prior_reference_coverage=coverage,own_quiet_reference_preservation=ownreference,minimum_quiet_surface_gap_mm=minimum_quiet_gap,minimum_new_via_to_SMD_drill_gap_mm=minimum_via_smd_drill_gap,minimum_new_hole_gap_mm=minimum_hole_gap,geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,complete_startup_routing=False,complete_current_thermal_parasitic_qualification=False,fabrication_released=False)
 with (OUT/'digital-startup-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(opens=2310,closed_connections=10,prior_reference_cases_preserved=len(coverage))))
if __name__=='__main__':run()
