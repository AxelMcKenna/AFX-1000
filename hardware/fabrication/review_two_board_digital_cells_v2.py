"""Audit native digital-cell placement, routing, quiet returns and retained copper."""
import json,math
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,read_netlist,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
BASE=STAGING/'two-board-power-digital-distribution-native-02'
OUT=STAGING/'two-board-power-digital-cells-native-03'
FILLED=STAGING/'two-board-power-digital-cells-filled-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2320-digital-cells-03/capture.json'


def run():
 sources=[Path(__file__),BEFORE,AFTER,OUT/'digital-cell-routing.json',FILLED/'local-plane-fill.json',BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',OUT/'review.json',OUT/'erc.json',BASE/'digital-distribution-routing.json',STAGING/'two-board-digital-cell-native-poses-02/native-poses.kicad_pcb',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_buck_cell.py','verify_native_zone_unfracture.py']]]
 before,after,report,fill=[json.loads(p.read_text()) for p in sources[1:5]]
 for p in [BEFORE,AFTER,OUT/'digital-cell-routing.json',FILLED/'local-plane-fill.json',OUT/'review.json']:
  d=json.loads(p.read_text())
  for field in ['source_sha256','artifact_sha256']:
   for name,h in d.get(field,{}).items():
    q=Path(name)
    if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
    assert sha(q)==h,(p,name)
 fidelity=verify_capture(after)
 b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
 fps0,fps1=[{prop(f,'Reference')[2]:f for f in children(b,'footprint')} for b in [b0,b1]]
 moved=set(report['moves']);retired=set(report['retired_objects']);old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
 added={u for r in report['routes'] for u in r['segment_uuids']}|{v['uuid'] for v in report['vias']}
 assert retired<=old.keys() and not retired&new.keys()
 aliases={}
 def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group']}
 for u in old.keys()-retired-new.keys():
  assert old[u]['kind']=='PAD'
  matches=[v for v,o in new.items() if o.get('ref')==old[u].get('ref') and o.get('pin')==old[u].get('pin') and v not in old]
  if old[u].get('ref') not in moved:matches=[v for v in matches if physical(old[u])==physical(new[v])]
  assert len(matches)==1,(u,matches);aliases[u]=matches[0]
 mapped={aliases.get(u,u) for u in old if u not in retired}
 assert len(mapped)==len(old)-len(retired) and new.keys()-mapped==added
 for u,o in old.items():
  if u in retired:continue
  n=new[aliases.get(u,u)]
  if o.get('ref') not in moved:assert physical(o)==physical(n),(u,'retained geometry')
  else:
   xy,rot,flip=report['moves'][o['ref']];expected=transform_object(o,position(fps0[o['ref']]),xy,rot)
   if flip:expected['layers']={('B.Cu' if l=='F.Cu' else 'F.Cu' if l=='B.Cu' else l):p for l,p in expected['layers'].items()}
   assert n['net']==expected['net'] and n['ref']==expected['ref'] and n['pin']==expected['pin']
   assert math.dist(n['position_mm'],expected['position_mm'])<1e-6 and n['layers'].keys()==expected['layers'].keys()
   assert abs((n['orientation_degrees']-expected['orientation_degrees']+180)%360-180)<1e-6
   for l in n['layers']:
    a,b=shape(n['layers'][l]),shape(expected['layers'][l]);assert a.hausdorff_distance(b)<2e-6 and a.symmetric_difference(b).area<1e-5,(u,l)
 def strip(b,remove):
  return [n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or(n[0]=='footprint' and prop(n,'Reference')[2] in moved) or(n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in remove)))]
 assert strip(b0,retired)==strip(b1,added),'Unexpected retained board edit'
 posed=read_sexpr(sources[12].read_text());posefps={prop(f,'Reference')[2]:f for f in children(posed,'footprint')}
 def native_pose_key(f):
  def normalize(n):
   if not isinstance(n,list):return n
   if n and n[0]=='net':return [n[0],n[-1]]
   return [normalize(v) for v in n]
  # Native preparation writes named pad nets; the integration wrapper restores
  # numeric codes and appends the unchanged schematic path at the end.
  return f[:2]+sorted((json.dumps(normalize(n)) for n in f[2:]))
 assert all(native_pose_key(fps1[r])==native_pose_key(posefps[r]) for r in moved)
 parts0,pins0=read_netlist(BASE/'netlist.xml');parts1,pins1=read_netlist(OUT/'netlist.xml')
 assert parts0.keys()==parts1.keys() and pins0==pins1
 assert all(parts0[r].findtext(k)==parts1[r].findtext(k) for r in parts0 for k in ['value','footprint','datasheet'])
 members={u:set(g) for g in after['all_groups'].values() for u in g}
 for g in before['all_groups'].values():
  translated={aliases.get(u,u) for u in g if u not in retired};assert translated and translated<=members[next(iter(translated))]
 pad=lambda ref,pin:next(o for o in new.values() if o.get('ref')==ref and o.get('pin')==pin)
 oldpad=lambda ref,pin:next(o for o in old.values() if o.get('ref')==ref and o.get('pin')==pin)
 target_nets={r['net'] for r in report['routes']};joins=[];merged=0
 for net in sorted(target_nets):
  if net=='PWR_AGND':anchors=[('P_C103','2'),*[(r,'2') for r in ['E_R105','E_R109','E_R113','E_R121','E_C43','E_C45','E_C47','E_C51']]];groups={oldpad(*a)['group'] for a in anchors}
  elif net=='PWR_5V_DIG_SRC':anchors=[('P_L20','2')];groups={oldpad(*anchors[0])['group']}
  else:
   anchors=[(o['ref'],o['pin']) for o in old.values() if o['kind']=='PAD' and o['net']==net];groups={oldpad(*a)['group'] for a in anchors};assert len(groups)==2
  expected={aliases.get(u,u) for gid in groups for u in before['all_groups'][gid] if u not in retired}|{u for u in added if new[u]['net']==net}
  assert all(members[pad(*a)['uuid']]==expected for a in anchors),(net,'unintended connectivity')
  merged+=len(groups)-1;joins.append(dict(net=net,previous_groups=len(groups),final_objects=len(expected)))
 assert merged==20 and before['native_uncapped_opens']==2340 and after['native_uncapped_opens']==2320
 for ref in ['E_U15','E_U16','E_U17','E_U33']:
  for p in ['6','11']:assert pad(ref,p)['group']!=pad(ref,'5')['group']
 aux=oldpad('P_U102','4');assert members[pad('P_U102','4')['uuid']]=={aliases.get(u,u) for u in before['all_groups'][aux['group']]}
 for p in ['1','2']:assert members[pad('G_NT1',p)['uuid']]=={pad('G_NT1',p)['uuid']}
 for r in report['routes']:
  for u,p,q in zip(r['segment_uuids'],r['path_mm'],r['path_mm'][1:]):
   o=new[u];assert o['kind']=='PCB_TRACK' and o['net']==r['net'] and list(o['layers'])==[r['layer']]
   assert math.dist(o['position_mm'],p)<1e-6 and math.dist(o['end_mm'],q)<1e-6 and abs(o['width_mm']-r['width_mm'])<1e-8
 for v in report['vias']:
  o=new[v['uuid']];assert o['kind']=='PCB_VIA' and o['position_mm']==v['position_mm'] and o['net']==v['net'] and o['drill_mm']==.3 and o['width_mm']==.6
 z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]];t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
 assert z0.keys()==z1.keys() and len(z1)==30
 edited={z['uuid']:z for z in report['edited_zone_outlines']};changed=set(report['refilled_existing_zones']);deltas=[]
 without=lambda z,k:[n for n in z if not(isinstance(n,list) and n and n[0] in k)]
 for u in z0:
  assert without(t0[u],['polygon','filled_polygon'])==without(t1[u],['polygon','filled_polygon'])
  if u in edited:
   r=edited[u];assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(r['outer_mm'],r['holes_mm']))<1e-6
  else:assert without(t0[u],['filled_polygon'])==without(t1[u],['filled_polygon'])
  if u not in changed:assert t0[u]==t1[u] and z0[u]==z1[u]
  else:
   a,b=shape(z0[u]['polygons']),shape(z1[u]['polygons']);deltas.append(dict(uuid=u,layer=z0[u]['layer'],removed_mm2=a.difference(b).area,added_mm2=b.difference(a).area))
 assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==20 and all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
 def contacts(g,layer,net,cap):
  regions=[shape(z['polygons']) for z in cap['zones'] if z['layer']==layer and z['net']==net];region=g.buffer(.0015)
  while True:
   extended=unary_union([region,*[h.buffer(.0015) for h in regions if region.intersects(h)]])
   if extended.equals(region):break
   region=extended
  hits=[o for o in cap['objects'] if o['net']==net and o['layers'].get(layer) and region.intersection(shape(o['layers'][layer])).area>1e-9];assert hits;return hits
 for u in changed:
  z=z1[u];g=shape(z['polygons']);assert shape(z['authored_outline']).buffer(2e-6).covers(g)
  for p in z['polygons']:assert len({o['group'] for o in contacts(Polygon(p['outer'],p['holes']),z['layer'],z['net'],after)})==1
 prior=json.loads((BASE/'digital-distribution-routing.json').read_text());quiet=[]
 for cell in report['quiet_ground_islands']:
  ref=cell['ref'];u=cell['zone_uuid'];g=shape(z1[u]['polygons']);own={v['uuid'] for v in cell['control_vias']}|{cell['star_via']['uuid']}
  hit={o['uuid'] for o in new.values() if o['net']=='PWR_AGND' and o['layers'].get('In1.Cu') and g.intersects(shape(o['layers']['In1.Cu']))}
  assert hit==own and len(z1[u]['polygons'])==1,(ref,'island contacts/fill')
  assert all(g.distance(shape(z['polygons']))>=.1985 for uid,z in z1.items() if uid!=u and z['layer']=='In1.Cu' and z['net']=='PWR_AGND')
  for v in [*cell['control_vias'],cell['star_via']]:
   o=new[v['uuid']];other={z['layer'] for uid,z in z1.items() if uid!=u and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
   if v['uuid']==cell['star_via']['uuid']:assert 'In5.Cu' in other
   else:assert not other,(ref,v['uuid'],other)
  refs={'E_U15':['E_R105','E_C43'],'E_U16':['E_R109','E_C45'],'E_U17':['E_R113','E_C47'],'E_U33':['E_R121','E_C51']}[ref]
  allowed={pad(r,p)['uuid'] for r,p in [(ref,'2'),(ref,'4'),(ref,'8'),*[(r,'2') for r in refs]]}|own
  for r,v in zip(prior['routes'],prior['vias']):
   if r['ref']==ref and r['pin'] in ['2','4']:allowed.update(aliases.get(x,x) for x in r['segment_uuids'])
  chosen=[r for r in report['routes'] if (r.get('ref')==ref and r.get('pin')=='8') or (r.get('chip')==ref and r.get('quiet_return'))]
  allowed.update(u for r in chosen for u in r['segment_uuids'])
  for r in chosen:
   geom=LineString(r['path_mm']).buffer(r['width_mm']/2)
   for o in new.values():
    if o['net']=='PWR_AGND' and o['uuid'] not in allowed and o['layers'].get(r['layer']):assert geom.distance(shape(o['layers'][r['layer']]))>=.1985,(ref,r.get('label'),o['uuid'],'extra surface return contact')
  quiet.append(dict(ref=ref,zone_uuid=u,star_via=cell['star_via']['uuid'],all_quiet_surface_returns_checked=True))
 smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm']) for l,ps in o['layers'].items() if l in ['F.Cu','B.Cu'] and ps];tree=STRtree(smd);minimum=100
 for o in new.values():
  if o['kind']=='PCB_VIA':
   p=Point(o['position_mm']);gap=p.distance(smd[int(tree.nearest(p))])-o['drill_mm']/2;assert gap>=.15-1e-8,(o['uuid'],gap);minimum=min(minimum,gap)
 def references(cap):
  refs={}
  for z in cap['zones']:
   if z['net']!='PWR_AGND':continue
   g=shape(z['polygons']);ids={o['group'] for o in contacts(g,z['layer'],z['net'],cap)};assert len(ids)==1
   refs.setdefault((z['layer'],next(iter(ids))),[]).append(g)
  return {k:unary_union(v) for k,v in refs.items()}
 refs0,refs1=references(before),references(after);coverage=[];layers=after['copper_layers']
 for u,o in old.items():
  if u in retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers'];i=layers.index(layer);adjacent={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)};g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  for v in old.values():
   if v['kind']=='PCB_VIA' and v['net']==o['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  if g.is_empty:continue
  for (rlayer,gid),reference in refs0.items():
   if rlayer not in adjacent or g.difference(reference.buffer(.0015)).area>=1e-6:continue
   anchor=next(v for v in before['all_groups'][gid] if v not in retired);target=refs1[(rlayer,new[aliases.get(anchor,anchor)]['group'])]
   area=g.difference(target.buffer(.0015)).area;assert area<1e-6,(u,'lost old reference',area)
   coverage.append(dict(track_uuid=u,reference_layer=rlayer,uncovered_mm2=area))
 new_reference=[]
 for r in report['routes']:
  if r['net']=='PWR_AGND':continue
  g=LineString(r['path_mm']).buffer(r['width_mm']/2)
  for v in new.values():
   if v['kind']=='PCB_VIA' and v['net']==r['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
  i=layers.index(r['layer']);adjacent=[layers[j] for j in [i-1,i+1] if 0<=j<len(layers)]
  areas={l:g.difference(unary_union([shape(z['polygons']) for z in z1.values() if z['net']=='PWR_AGND' and z['layer']==l]).buffer(.0015)).area for l in adjacent}
  new_reference.append(dict(label=r.get('label',r.get('ref','')+'.'+r.get('pin','')),adjacent_uncovered_mm2=areas))
 source_id=next(z['uuid'] for z in prior['new_zones'] if z['label']=='source-distribution')
 source_region=shape(z1[source_id]['polygons'])
 for o in new.values():
  if o['net']=='PWR_5V_DIG_SRC' and o['layers'].get('In5.Cu'):source_region=source_region.difference(shape(o['layers']['In5.Cu']).buffer(.215))
 source_uncovered=source_region.difference(refs1[('In5.Cu',pad('P_C103','2')['group'])].buffer(.0015))
 native=json.loads((OUT/'review.json').read_text());assert native['geometry_findings']==native['schematic_parity_findings']==0
 warnings=[v for s in json.loads((OUT/'erc.json').read_text())['sheets'] for v in s.get('violations',[])];assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,old_opens=2340,new_opens=2320,closed_connections=20,all_prior_connection_groups_preserved=len(before['all_groups']),retained_objects_verified=len(old)-len(retired),moved_footprints=len(moved),unchanged_complete_footprints=len(fps0)-len(moved),unchanged_pin_net_entries=len(pins0),retired_tracks=sum(old[u]['kind']=='PCB_TRACK' for u in retired),retired_vias=sum(old[u]['kind']=='PCB_VIA' for u in retired),added_tracks=report['added_tracks'],added_vias=report['added_vias'],native_group_merges=joins,unchanged_zone_fills=20,edited_zone_outlines=len(edited),refilled_zone_deltas=deltas,quiet_returns=quiet,all_vias_screened=sum(o['kind']=='PCB_VIA' for o in new.values()),minimum_all_via_drill_to_SMD_mm=minimum,previous_full_width_reference_cases_preserved=len(coverage),prior_reference_coverage=coverage,source_In5_reference_screen_area_mm2=source_region.area,source_In5_reference_uncovered_mm2=source_uncovered.area,new_route_reference_screen=new_reference,full_new_route_reference_complete=all(min(r['adjacent_uncovered_mm2'].values())<1e-6 for r in new_reference),AUX_group_preserved=True,G_NT1_isolated=True,geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,complete_current_thermal_transient_qualification=False,fabrication_released=False)
 with (OUT/'digital-cell-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['new_opens','closed_connections','all_prior_connection_groups_preserved','all_vias_screened','minimum_all_via_drill_to_SMD_mm','previous_full_width_reference_cases_preserved','full_new_route_reference_complete']}))
if __name__=='__main__':run()
