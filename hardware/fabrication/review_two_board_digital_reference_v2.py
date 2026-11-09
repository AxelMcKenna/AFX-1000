"""Independent native audit of the digital-source layer and quiet reference fields."""
import json
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,read_netlist
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
BASE=STAGING/'two-board-power-digital-cells-native-03'
OUT=STAGING/'two-board-power-digital-reference-native-02'
FILLED=STAGING/'two-board-power-digital-reference-filled-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2320-digital-cells-03/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json'


def run():
 sources=[Path(__file__),BEFORE,AFTER,OUT/'digital-reference-routing.json',FILLED/'local-plane-fill.json',BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',OUT/'review.json',OUT/'erc.json',BASE/'digital-cell-routing.json',BASE/'digital-cell-review.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','verify_native_zone_unfracture.py']]]
 sources.extend([OUT/'digital-reference-track-routing.json',STAGING/'two-board-power-digital-reference-filled-02/local-plane-fill.json',STAGING/'two-board-power-digital-reference-native-01/digital-reference-review.json'])
 before,after,report,fill=[json.loads(p.read_text()) for p in sources[1:5]]
 track=json.loads((OUT/'digital-reference-track-routing.json').read_text());retired=set(track['retired_route']['segment_uuids']);added_tracks=set(track['replacement_route']['segment_uuids'])
 for p in [BEFORE,AFTER,OUT/'digital-reference-routing.json',FILLED/'local-plane-fill.json',OUT/'review.json',BASE/'digital-cell-review.json',OUT/'digital-reference-track-routing.json',STAGING/'two-board-power-digital-reference-filled-02/local-plane-fill.json',STAGING/'two-board-power-digital-reference-native-01/digital-reference-review.json']:
  d=json.loads(p.read_text())
  for field in ['source_sha256','artifact_sha256']:
   for name,h in d.get(field,{}).items():
    q=Path(name)
    if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
    assert sha(q)==h,(p,name)
 fidelity=verify_capture(after)
 b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
 strip=lambda b:[n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or (n[0]=='segment' and str(first(n,'uuid')[1]) in retired|added_tracks)))]
 assert strip(b0)==strip(b1),'Unexpected non-zone edit'
 old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
 # KiCad generates identities for older embedded G_* pads without saved UUIDs.
 # Match only these pad identities by their complete physical/net capture.
 physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
 aliases={}
 for u in old.keys()-new.keys()-retired:
  assert old[u]['kind']=='PAD'
  matches=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
  assert len(matches)==1,(u,'ambiguous generated pad identity');aliases[matches[0]]=u
 assert set(aliases)==new.keys()-old.keys()-added_tracks
 for o in after['objects']:
  o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
 after['all_groups']={aliases.get(g,g):[aliases.get(u,u) for u in members] for g,members in after['all_groups'].items()}
 new={o['uuid']:o for o in after['objects']}
 assert old.keys()-retired==new.keys()-added_tracks and retired.isdisjoint(new) and added_tracks.isdisjoint(old)
 for u in old.keys()-retired:assert {k:v for k,v in old[u].items() if k!='group'}=={k:v for k,v in new[u].items() if k!='group'},u
 for r,objects in [(track['retired_route'],old),(track['replacement_route'],new)]:
  for u,p,q in zip(r['segment_uuids'],r['path_mm'],r['path_mm'][1:]):
   o=objects[u];assert o['net']==r['net'] and list(o['layers'])==['F.Cu'] and o['width_mm']==.2
   assert sum((a-b)**2 for a,b in zip(o['position_mm'],p))<1e-12 and sum((a-b)**2 for a,b in zip(o['end_mm'],q))<1e-12
 assert track['retired_route']['net']==track['replacement_route']['net']
 assert track['retired_route']['path_mm'][0]==track['replacement_route']['path_mm'][0] and track['retired_route']['path_mm'][-1]==track['replacement_route']['path_mm'][-1]
 groups=lambda c:{frozenset(set(g)-retired-added_tracks) for g in c['all_groups'].values()}
 assert groups(before)==groups(after),'Native connection partition changed'
 assert before['native_uncapped_opens']==after['native_uncapped_opens']==2320
 parts0,pins0=read_netlist(BASE/'netlist.xml');parts1,pins1=read_netlist(OUT/'netlist.xml')
 assert parts0.keys()==parts1.keys() and pins0==pins1
 assert all(parts0[r].findtext(k)==parts1[r].findtext(k) for r in parts0 for k in ['value','footprint','datasheet'])
 z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]];t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
 edits={z['uuid']:z for z in report['edited_zones']};added={z['uuid']:z for z in report['new_zones']}
 assert z1.keys()-z0.keys()==added.keys() and z0.keys()<=z1.keys() and len(z1)==36
 without=lambda z,keys:[n for n in z if not(isinstance(n,list) and n and n[0] in keys)]
 for u in z0:
  if u not in edits:assert t0[u]==t1[u] and z0[u]==z1[u],u
  else:
   e=edits[u];ignore=['polygon','filled_polygon']+(['layer'] if 'old_layer' in e else [])
   assert without(t0[u],ignore)==without(t1[u],ignore),u
 for u,r in {**edits,**added}.items():
  assert z1[u]['layer']==r['layer'] and shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(r['outer_mm'],r['holes_mm']))<1e-6
  assert shape(z1[u]['authored_outline']).buffer(2e-6).covers(shape(z1[u]['polygons'])),u
 assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==36 and all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
 def hits(g,layer,net,cap):return [o for o in cap['objects'] if o['net']==net and o['layers'].get(layer) and g.buffer(.0015).intersection(shape(o['layers'][layer])).area>1e-9]
 for u in {*edits,*added}:
  z=z1[u]
  for p in z['polygons']:assert len({o['group'] for o in hits(Polygon(p['outer'],p['holes']),z['layer'],z['net'],after)})==1,(u,'disconnected piece')
 quiet=[]
 for q in report['quiet_ground_islands']:
  ref=q['ref'];own={v['uuid'] for v in [*q['control_vias'],q['star_via']]}
  ownzones={q['zone_uuid'],next(u for u,z in added.items() if z['ref']==ref)}
  for u in ownzones:
   z=z1[u];g=shape(z['polygons']);contact={o['uuid'] for o in hits(g,z['layer'],'PWR_AGND',after)}
   assert q['star_via']['uuid'] in contact and contact<=own and len(z['polygons'])==1,(ref,u,contact)
   if z['layer']=='In1.Cu':assert contact==own
   assert all(g.distance(shape(other['polygons']))>=.1985 for uid,other in z1.items() if uid!=u and other['layer']==z['layer'] and other['net']=='PWR_AGND'),(ref,'quiet island separation')
  for v in [*q['control_vias'],q['star_via']]:
   o=new[v['uuid']];other={z['layer'] for u,z in z1.items() if u not in ownzones and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
   if v['uuid']==q['star_via']['uuid']:assert 'In5.Cu' in other
   else:assert not other,(ref,v['uuid'],other)
  quiet.append(dict(ref=ref,zones=sorted(ownzones),star_via=q['star_via']['uuid'],only_star_contacts_main_ground=True))
 source_id=next(u for u,z in edits.items() if z.get('old_layer')=='In6.Cu');s0,s1=z0[source_id],z1[source_id]
 assert s0['net']==s1['net']=='PWR_5V_DIG_SRC' and s1['layer']=='In4.Cu' and len(s1['polygons'])==1
 c0={o['uuid'] for o in hits(shape(s0['polygons']),'In6.Cu',s0['net'],before)}
 c1={o['uuid'] for o in hits(shape(s1['polygons']),'In4.Cu',s1['net'],after)}
 assert c0==c1,'Source-plane physical contacts changed'
 def references(c):
  result={}
  for z in c['zones']:
   if z['net']!='PWR_AGND':continue
   for p in z['polygons']:
    g=Polygon(p['outer'],p['holes']);hs=hits(g,z['layer'],z['net'],c)
    if not hs:continue
    gids={o['group'] for o in hs};assert len(gids)==1
    result.setdefault((z['layer'],next(iter(gids))),[]).append(g)
  return {k:unary_union(v) for k,v in result.items()}
 refs0,refs1=references(before),references(after);layers=after['copper_layers'];coverage=[]
 for u,o in old.items():
  if u in retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers'];i=layers.index(layer);adjacent={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
  g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  for v in old.values():
   if v['kind']=='PCB_VIA' and v['net']==o['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  if g.is_empty:continue
  for (rlayer,gid),reference in refs0.items():
   if rlayer not in adjacent or g.difference(reference.buffer(.0015)).area>=1e-6:continue
   anchor=before['all_groups'][gid][0];target=refs1[(rlayer,new[anchor]['group'])];area=g.difference(target.buffer(.0015)).area
   assert area<1e-6,(u,'lost old reference',area)
   coverage.append(dict(track_uuid=u,reference_layer=rlayer,uncovered_mm2=area))
 routes=json.loads((BASE/'digital-cell-routing.json').read_text())['routes'];new_reference=[]
 routes=[track['replacement_route'] if r.get('label')==track['retired_route']['label'] else r for r in routes]
 replacement=LineString(track['replacement_route']['path_mm']).buffer(.1)
 replacement_gap=replacement.difference(shape(z1[track['reference_zone']]['polygons']).buffer(.001)).area
 assert replacement_gap<1e-6,'Replacement DVDT route leaves its own quiet reference'
 for r in routes:
  if r['net']=='PWR_AGND':continue
  g=LineString(r['path_mm']).buffer(r['width_mm']/2)
  for v in new.values():
   if v['kind']=='PCB_VIA' and v['net']==r['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  i=layers.index(r['layer']);adjacent=[layers[j] for j in [i-1,i+1] if 0<=j<len(layers)]
  areas={l:g.difference(unary_union([shape(z['polygons']) for z in z1.values() if z['net']=='PWR_AGND' and z['layer']==l]).buffer(.0015)).area for l in adjacent}
  new_reference.append(dict(label=r.get('label',r.get('ref','')+'.'+r.get('pin','')),adjacent_uncovered_mm2=areas))
 # Check each critical support route against its own quiet field, not merely
 # any region carrying the same ground net. Retain residuals as open evidence.
 ownzones={q['ref']:{q['zone_uuid'],next(u for u,z in added.items() if z['ref']==q['ref'])} for q in report['quiet_ground_islands']}
 refowner={ref:chip for chip,refs in {'E_U15':['E_U15','E_R105','E_R106','E_C43'],'E_U16':['E_U16','E_R109','E_R110','E_C45'],'E_U17':['E_U17','E_R113','E_R114','E_C47'],'E_U33':['E_U33','E_R121','E_R122','E_C51']}.items() for ref in refs}
 own_reference=[];residuals=[]
 for r in routes:
  if r['net']=='PWR_AGND':continue
  layer='In1.Cu' if r['layer']=='F.Cu' else 'In6.Cu';g=LineString(r['path_mm']).buffer(r['width_mm']/2)
  signalvias=[o for o in new.values() if o['kind']=='PCB_VIA' and o['net']==r['net']]
  for v in signalvias:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  label=r.get('label',r.get('ref','')+'.'+r.get('pin',''))
  ground=unary_union([shape(z['polygons']) for z in z1.values() if z['net']=='PWR_AGND' and z['layer']==layer])
  missing=g.difference(ground.buffer(.0015))
  if missing.area>1e-6:
   envelope=unary_union([Point(v['position_mm']).buffer(v['width_mm']/2+.25) for v in signalvias])
   assert envelope.buffer(1e-6).covers(missing),(label,'reference gap away from same-signal via')
   residuals.append(dict(label=label,uncovered_mm2=missing.area,confined_to_same_net_via_edge_margin_mm=.25,bounds_mm=list(missing.bounds)))
  if r['net']=='PWR_5V_DIG_SRC':continue
  owner=r.get('chip',refowner.get(r.get('ref')));assert owner in ownzones
  ground=unary_union([shape(z1[u]['polygons']) for u in ownzones[owner] if z1[u]['layer']==layer]);missing=g.difference(ground.buffer(.0015))
  if missing.area>1e-6:assert unary_union([Point(v['position_mm']).buffer(v['width_mm']/2+.25) for v in signalvias]).buffer(1e-6).covers(missing)
  own_reference.append(dict(label=label,owner=owner,layer=layer,own_reference_uncovered_mm2=missing.area))
 region=shape(s1['polygons'])
 for o in new.values():
  if o['net']=='PWR_5V_DIG_SRC' and o['layers'].get('In5.Cu'):region=region.difference(shape(o['layers']['In5.Cu']).buffer(.215))
 main=next(o['group'] for o in new.values() if o.get('ref')=='P_C103' and o.get('pin')=='2');uncovered=region.difference(refs1[('In5.Cu',main)].buffer(.0015))
 native=json.loads((OUT/'review.json').read_text());assert native['geometry_findings']==native['schematic_parity_findings']==0
 warnings=[v for s in json.loads((OUT/'erc.json').read_text())['sheets'] for v in s.get('violations',[])];assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,generated_pad_identity_aliases=aliases,new_opens=2320,closed_connections=0,unchanged_native_connection_groups=len(before['all_groups']),unchanged_physical_objects=len(old)-len(retired),retired_tracks=len(retired),added_tracks=len(added_tracks),replacement_route_length_mm=track['replacement_route']['length_mm'],replacement_own_quiet_reference_uncovered_mm2=replacement_gap,unchanged_complete_footprints=len(children(b0,'footprint')),unchanged_pin_net_entries=len(pins0),unchanged_zone_fills=24,edited_zone_count=len(edits),added_zone_count=len(added),quiet_returns=quiet,source_plane_contacts_preserved=len(c0),source_plane_area_mm2=shape(s1['polygons']).area,source_In5_reference_screen_area_mm2=region.area,source_In5_reference_uncovered_mm2=uncovered.area,previous_full_width_reference_cases_preserved=len(coverage),prior_reference_coverage=coverage,new_route_reference_screen=new_reference,own_quiet_reference_screen=own_reference,remaining_via_edge_reference_gaps=residuals,full_new_route_reference_complete=all(min(r['adjacent_uncovered_mm2'].values())<1e-6 for r in new_reference),geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,complete_current_thermal_parasitic_qualification=False,fabrication_released=False)
 with (OUT/'digital-reference-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['new_opens','unchanged_native_connection_groups','source_plane_contacts_preserved','previous_full_width_reference_cases_preserved','full_new_route_reference_complete']}))
if __name__=='__main__':run()
