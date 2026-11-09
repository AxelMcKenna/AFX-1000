"""Verify startup reference fields and reroutes without changing native connectivity."""
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
BASE=STAGING/'two-board-power-startup-logic-native-02'
OUT=STAGING/'two-board-power-logic-references-native-02'
FILLED=STAGING/'two-board-power-logic-references-filled-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2294-logic-references-02/capture.json'


def run():
 sources=[Path(__file__),BEFORE,AFTER,OUT/'logic-reference-routing.json',FILLED/'local-plane-fill.json',BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',OUT/'review.json',OUT/'erc.json',BASE/'startup-logic-review.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','repack_two_board_buck_input.py','route_two_board_buck_cell.py','verify_native_zone_unfracture.py']]]
 before,after,r,fill=[json.loads(p.read_text()) for p in sources[1:5]]
 for p in [BEFORE,AFTER,OUT/'logic-reference-routing.json',FILLED/'local-plane-fill.json',OUT/'review.json',BASE/'startup-logic-review.json']:
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
  return [n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired|added or n[0]=='footprint' and prop(n,'Reference')[2] in r.get('moves',{})))]
 assert strip(b0)==strip(b1),'Unexpected board edit outside declared objects'
 for ref,(xy,rot,flip) in r.get('moves',{}).items():assert not flip and read_sexpr(sexpr(rotate_footprint(fps0[ref],xy,rot)))==fps1[ref]
 moved=[]
 for u in old.keys()-retired:
  o=old[u];n=new[u]
  if o.get('ref') not in r.get('moves',{}):assert physical(o)==physical(n),u;continue
  xy,rot,_=r.get('moves',{})[o['ref']];expected=transform_object(o,position(fps0[o['ref']]),xy,rot)
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
 actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
 assert expected==actual,'Native connection partition changed'
 assert before['native_uncapped_opens']==after['native_uncapped_opens']==2294
 assert all(new[u].get('group') for u in added),'Orphan new copper'
 parts0,pins0=read_netlist(BASE/'netlist.xml');parts1,pins1=read_netlist(OUT/'netlist.xml')
 assert parts0.keys()==parts1.keys() and pins0==pins1
 assert all(parts0[ref].findtext(k)==parts1[ref].findtext(k) for ref in parts0 for k in ['value','footprint','datasheet'])
 z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]];assert z0.keys()<=z1.keys() and len(z1)==39
 addedzones={z['uuid']:z for z in r['added_zones']};assert z1.keys()-z0.keys()==addedzones.keys()
 def hits(g,layer,net,cap):return [o for o in cap['objects'] if o['net']==net and o['layers'].get(layer) and g.buffer(.0015).intersection(shape(o['layers'][layer])).area>1e-9]
 edited={z['uuid']:z for z in r['edited_zone_outlines']};refilled=set(r['refilled_existing_zones'])
 priorities=r['zone_priority_changes'];assert len(priorities)==1 and priorities[0]['uuid']=='de233285-cc07-5d51-9dbd-88a46856bbca' and priorities[0]['before']==0 and priorities[0]['after']==2
 priority_uuid=priorities[0]['uuid']
 t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
 without=lambda z,keys:[n for n in z if not(isinstance(n,list) and n and n[0] in keys)]
 components={}
 for key in {(z['layer'],z['net']) for z in z1.values()}:
  g=unary_union([shape(z['polygons']) for z in z1.values() if (z['layer'],z['net'])==key]);components[key]=list(g.geoms) if hasattr(g,'geoms') else [g]
 for u in z0:
  assert z0[u]['net']==z1[u]['net'] and z0[u]['layer']==z1[u]['layer']
  if u not in refilled:assert t0[u]==t1[u] and z0[u]==z1[u],u
  else:
   exclusions=['filled_polygon']+(['polygon'] if u in edited else [])+(['priority'] if u==priority_uuid else [])
   assert without(t0[u],exclusions)==without(t1[u],exclusions),u
   if u==priority_uuid:
    assert first(t0[u],'priority') is None or int(first(t0[u],'priority')[1])==0
    assert int(first(t1[u],'priority')[1])==2
  if u in edited:assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(edited[u]['outer_mm'],edited[u]['holes_mm']))<2e-6
  for part in z1[u]['polygons']:
   pg=Polygon(part['outer'],part['holes']);cs=[g for g in components[z1[u]['layer'],z1[u]['net']] if pg.difference(g.buffer(.000002)).area<1e-6]
   assert len(cs)==1 and len({o['group'] for o in hits(cs[0],z1[u]['layer'],z1[u]['net'],after)})==1,(u,'Orphan or ambiguous fill')
 assert set(fill['unchanged_existing_zone_canonical_polygon_match'])==z0.keys()-refilled
 main=new[pad(old,'P_C103','2')['uuid']]['group']
 for u,z in addedzones.items():
  assert z1[u]['net']=='PWR_AGND' and z1[u]['layer']==z['layer']
  assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(z['outer_mm'],z['holes_mm']))<2e-6
  for pg in z1[u]['polygons']:
   contacts=hits(Polygon(pg['outer'],pg['holes']),z['layer'],'PWR_AGND',after)
   assert {o['group'] for o in contacts}=={main},(u,'New reference is orphaned or has wrong ground owner')
 priorpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json';sources.append(priorpath);prior=json.loads(priorpath.read_text());quiet=[]
 for q in prior['quiet_ground_islands']:
  ownzones=set(q['zone_uuids']);own={v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]};contacts={}
  for u in ownzones:
   z=z1[u];g=shape(z['polygons']);contact={o['uuid'] for o in hits(g,z['layer'],'PWR_AGND',after)}
   beforecontact={o['uuid'] for o in hits(shape(z0[u]['polygons']),z0[u]['layer'],'PWR_AGND',before)}
   assert contact==beforecontact and q['star_via']['uuid'] in contact and contact<=own and len(z['polygons'])==1,(q['ref'],u,'Quiet contacts changed')
   assert all(g.distance(shape(other['polygons']))>=.1985 for uid,other in z1.items() if uid!=u and other['layer']==z['layer'] and other['net']=='PWR_AGND')
   contacts[u]=sorted(contact)
  for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]:
   o=new[v['uuid']];other={u for u,z in z1.items() if u not in ownzones and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
   if v['uuid']==q['star_via']['uuid']:assert any(z1[u]['layer']=='In5.Cu' for u in other)
   else:assert not other,(q['ref'],v['uuid'],'Quiet bypass')
  quiet.append(dict(ref=q['ref'],contacts=contacts,star_only_main_return=True))
 minimum_smd=1000.;minimum_hole=1000.
 for v in r['vias']:
  pt=Point(v['position_mm'])
  for o in new.values():
   if o['uuid']==v['uuid']:continue
   d=o.get('drill_mm',0);radius=(max(d) if isinstance(d,list) else d)/2
   if radius:
    gap=pt.distance(Point(o['position_mm']))-.15-radius;minimum_hole=min(minimum_hole,gap);assert gap>=.24999,(v['uuid'],'Hole spacing',o['uuid'],gap)
   elif o['kind']=='PAD':
    for l in ['F.Cu','B.Cu']:
     if not o['layers'].get(l):continue
     gap=pt.distance(shape(o['layers'][l]))-.15;minimum_smd=min(minimum_smd,gap);assert gap>=.149,(v['uuid'],'Drill to SMD',o['uuid'],gap)
 source=next(u for u,z in z0.items() if z['net']=='PWR_5V_DIG_SRC' and z['layer']=='In4.Cu')
 hs=lambda c,z:{o['uuid'] for o in hits(shape(z['polygons']),z['layer'],z['net'],c)}
 assert hs(before,z0[source])==hs(after,z1[source]) and len(z1[source]['polygons'])==1
 # Compare against a separately refilled control containing ONLY the declared
 # track/via replacements on the original board and original zone definitions.
 # This also captures native polygon remeshing caused by the replaced vias;
 # a guessed circular exclusion alone cannot distinguish that from zone trim.
 controlpath=STAGING/'two-board-logic-reference-refill-diagnostic-01/reroutes_only.json'
 control=json.loads(controlpath.read_text());sources.append(controlpath)
 for field in ['source_sha256','artifact_sha256']:
  for name,h in control.get(field,{}).items():
   path=REPO/name if name.startswith('hardware/') else controlpath.parent/name
   assert sha(path)==h,(controlpath,name)
 assert control['case']['repeat_refill_identical']
 cb=read_sexpr((controlpath.parent/'reroutes-only-control/power_protection.kicad_pcb').read_text())
 def without_copper(board):
  return [n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired|added)]
 assert without_copper(cb)==without_copper(b0),'Control differs outside declared rerouting'
 ct={str(first(n,'uuid')[1]):n for n in cb if isinstance(n,list) and n and n[0] in ['segment','via']}
 nt={str(first(n,'uuid')[1]):n for n in b1 if isinstance(n,list) and n and n[0] in ['segment','via']}
 assert all(ct[u]==nt[u] for u in added) and not retired&ct.keys()
 assert set(control['case']['before'])==z0.keys()==set(control['case']['after'])
 for u,z in z0.items():
  assert shape(control['case']['before'][u]['polygons']).symmetric_difference(shape(z['polygons'])).area<1e-7
 expected_source=shape(control['case']['after'][source]['polygons'])
 actual_source=shape(z1[source]['polygons'])
 unexplained_source_delta=actual_source.symmetric_difference(expected_source).area
 assert unexplained_source_delta<1e-7 and actual_source.hausdorff_distance(expected_source)<2e-6,('Source differs from reroute-only control',unexplained_source_delta)
 source_delta=shape(z0[source]['polygons']).symmetric_difference(actual_source)
 changed_via_regions=[Point(old[u]['position_mm']).buffer(.8) for u in retired if old[u]['kind']=='PCB_VIA']+[Point(v['position_mm']).buffer(.8) for v in r['vias']]
 native_remeshing_outside_vias=source_delta.difference(unary_union(changed_via_regions).buffer(.000005)).area

 # Preserve complete adjacent-ground coverage and the electrical identity of
 # its return group for every retained trace, not just selected named routes.
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
 viaholes={}
 for o in old.values():
  if o['kind']=='PCB_VIA':viaholes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
 viaholes={net:unary_union(xs) for net,xs in viaholes.items()}
 for u,o in old.items():
  if u in retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)};g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  if o['net'] in viaholes:g=g.difference(viaholes[o['net']])
  if g.is_empty:continue
  for (layer,gid),reference in refs0.items():
   if layer not in adj or g.difference(reference.buffer(.0015)).area>=1e-6:continue
   anchors=[x for x in before['all_groups'][gid] if x in new];assert anchors
   target=refs1[(layer,new[anchors[0]]['group'])];area=g.difference(target.buffer(.0015)).area
   assert area<1e-6,(u,'Lost prior adjacent reference',area)
   coverage.append(dict(track_uuid=u,reference_layer=layer,uncovered_mm2=area))
 # Preserve quiet ILM/DVDT return ownership including existing small gaps.
 localpath=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json'
 trackpath=STAGING/'two-board-power-digital-reference-native-02/digital-reference-track-routing.json';sources.extend([localpath,trackpath])
 local=json.loads(localpath.read_text());replacement=json.loads(trackpath.read_text())
 ownerparts={ref:chip for chip,refs in {'E_U15':['E_U15','E_R105','E_R106','E_C43'],'E_U16':['E_U16','E_R109','E_R110','E_C45'],'E_U17':['E_U17','E_R113','E_R114','E_C47'],'E_U33':['E_U33','E_R121','E_R122','E_C51']}.items() for ref in refs}
 own={q['ref']:set(q['zone_uuids']) for q in prior['quiet_ground_islands']};ownreference=[]
 for route in local['routes']:
  if route.get('label')==replacement['retired_route']['label']:route=replacement['replacement_route']
  if route['net'] in ['PWR_AGND','PWR_5V_DIG_SRC']:continue
  chip=route.get('chip',ownerparts.get(route.get('ref')));assert chip in own
  layer='In1.Cu' if route['layer']=='F.Cu' else 'In6.Cu';g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  if route['net'] in viaholes:g=g.difference(viaholes[route['net']])
  missing=[g.difference(unary_union([shape(z[u]['polygons']) for u in own[chip] if z[u]['layer']==layer]).buffer(.0015)) for z in [z0,z1]]
  assert missing[1].difference(missing[0].buffer(.000002)).area<1e-6,(route.get('label'),'Lost own quiet reference',missing[0].area,missing[1].area)
  ownreference.append(dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),owner=chip,layer=layer,before_uncovered_mm2=missing[0].area,after_uncovered_mm2=missing[1].area))
 # Quantify, rather than imply, reference coverage for new routing.
 ground={l:unary_union([shape(z['polygons']) for z in after['zones'] if z['layer']==l and z['net']=='PWR_AGND']) for l in layers}
 newholes={}
 for o in new.values():
  if o['kind']=='PCB_VIA':newholes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
 newholes={n:unary_union(xs) for n,xs in newholes.items()};newrefs=[]
 for route in r['effective_logic_routes']:
  if route['net']=='PWR_AGND':continue
  g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  if route['net'] in newholes:g=g.difference(newholes[route['net']])
  i=layers.index(route['layer']);adj=[layers[j] for j in [i-1,i+1] if 0<=j<len(layers)]
  newrefs.append(dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),net=route['net'],layer=route['layer'],screen_area_mm2=g.area,adjacent_uncovered_mm2={l:g.difference(ground[l].buffer(.0015)).area for l in adj}))
 native=json.loads((OUT/'review.json').read_text());assert native['geometry_findings']==native['schematic_parity_findings']==0
 warnings=[v for s in json.loads((OUT/'erc.json').read_text())['sheets'] for v in s.get('violations',[])];assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,generated_pad_identity_aliases=aliases,closed_connections=0,new_opens=2294,moved_pad_count=len(moved),retained_part_count=len(parts0),retained_pin_entries=len(pins0),native_connection_partition_unchanged=True,all_other_native_groups_preserved=True,quiet_returns=quiet,source_plane_contacts_preserved=len(hs(before,z0[source])),source_plane_area_mm2=shape(z1[source]['polygons']).area,source_plane_clearance_change_mm2=source_delta.area,unexplained_source_plane_change_mm2=unexplained_source_delta,source_matches_isolated_reroute_control=True,source_native_remeshing_outside_via_neighborhoods_mm2=native_remeshing_outside_vias,source_zone_priority_before=0,source_zone_priority_after=2,added_reference_zones=len(addedzones),edited_existing_zone_outlines=len(edited),unchanged_existing_fills=len(z0)-len(refilled),prior_reference_coverage=coverage,own_quiet_reference_preservation=ownreference,new_logic_reference=newrefs,new_logic_fully_referenced_sections=sum(min(x['adjacent_uncovered_mm2'].values())<1e-6 for x in newrefs),minimum_new_via_to_SMD_drill_gap_mm=minimum_smd,minimum_new_hole_gap_mm=minimum_hole,geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,complete_startup_routing=False,complete_current_thermal_parasitic_qualification=False,fabrication_released=False)
 with (OUT/'logic-reference-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(opens=2294,closed_connections=0,prior_reference_cases_preserved=len(coverage),new_fully_referenced_sections=result['new_logic_fully_referenced_sections'],new_screened_sections=len(newrefs))))
if __name__=='__main__':run()
