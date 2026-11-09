"""Verify the single R104 return join and preserve all other board state."""
import copy,json,math
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha,read_netlist
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
BASE=STAGING/'two-board-power-analog-cells-native-03'
OUT=STAGING/'two-board-power-digital-return-native-02'
BEFORE=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2210-digital-return-02/capture.json'
FILL=STAGING/'two-board-power-digital-return-filled-02/local-plane-fill.json'

def run():
 paths=[BEFORE,AFTER,OUT/'digital-return-routing.json',FILL,OUT/'review.json']
 before,after,r,fill,native=[json.loads(p.read_text()) for p in paths]
 for p,d in zip(paths,[before,after,r,fill,native]):
  for key in ['source_sha256','artifact_sha256']:
   for name,h in d.get(key,{}).items():
    f=Path(name)
    if not f.is_absolute():f=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/f
    assert sha(f)==h,(p,name)
 fidelity=verify_capture(after);old,new=[{o['uuid']:o for o in cap['objects']} for cap in [before,after]]
 retired=set(r['retired_objects']);added={u for route in r['routes'] for u in route['segment_uuids']}
 physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
 aliases={}
 for u in old.keys()-new.keys()-retired:
  assert old[u]['kind']=='PAD' and old[u].get('ref')!='E_R104'
  matches=[v for v in new.keys()-old.keys()-added if physical(old[u])==physical(new[v])]
  assert len(matches)==1,(u,'unmatched unchanged generated pad');aliases[matches[0]]=u
 assert set(aliases)==new.keys()-old.keys()-added
 for o in after['objects']:o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
 after['all_groups']={aliases.get(g,g):[aliases.get(u,u) for u in members] for g,members in after['all_groups'].items()}
 new={o['uuid']:o for o in after['objects']}
 assert len(retired)==3 and len(added)==2 and old.keys()-retired==new.keys()-added
 b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
 f0,f1=[{prop(f,'Reference')[2]:f for f in children(b,'footprint')} for b in [b0,b1]]
 def strip(b):return [n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired|added or n[0]=='footprint' and prop(n,'Reference')[2]=='E_R104'))]
 assert strip(b0)==strip(b1),'Undeclared board change'
 xy,rotation,flip=r['moves']['E_R104'];assert not rotation and not flip
 assert read_sexpr(sexpr(rotate_footprint(f0['E_R104'],xy,0)))==f1['E_R104']
 for u,o in old.items():
  if u in retired:continue
  n=new[u]
  if o.get('ref')!='E_R104':assert physical(o)==physical(n),u;continue
  expected=transform_object(o,position(f0['E_R104']),xy,0)
  for key in ['ref','pin','net','drill_mm','npth','orientation_degrees']:assert expected[key]==n[key]
  assert math.dist(expected['position_mm'],n['position_mm'])<1e-6 and expected['layers'].keys()==n['layers'].keys()
  for l in n['layers']:assert shape(expected['layers'][l]).hausdorff_distance(shape(n['layers'][l]))<2e-6
 for route in r['routes']:
  o=new[route['segment_uuids'][0]];assert o['kind']=='PCB_TRACK' and list(o['layers'])==[route['layer']] and o['width_mm']==route['width_mm'] and o['net']==route['net']
  assert math.dist(o['position_mm'],route['path_mm'][0])<1e-6 and math.dist(o['end_mm'],route['path_mm'][1])<1e-6
 pad=lambda objs,ref,pin:next(o for o in objs.values() if o.get('ref')==ref and o.get('pin')==pin)
 expected={frozenset(set(g)-retired) for g in before['all_groups'].values()}-{frozenset()}
 x,y=[pad(old,*args)['uuid'] for args in [('E_R104','2'),('E_U15','8')]]
 left,right=[next(g for g in expected if u in g) for u in [x,y]];assert left!=right and left=={x}
 expected.remove(left);expected.remove(right);expected.add(left|right)
 actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
 assert expected==actual and before['native_uncapped_opens']-after['native_uncapped_opens']==1 and after['native_uncapped_opens']==2210
 assert all(new[u].get('group') for u in added)
 a0,p0=read_netlist(BASE/'netlist.xml');a1,p1=read_netlist(OUT/'netlist.xml')
 assert a0.keys()==a1.keys() and p0==p1
 assert all(a0[k].findtext(f)==a1[k].findtext(f) for k in a0 for f in ['value','footprint','datasheet'])
 z0,z1=[{z['uuid']:z for z in cap['zones']} for cap in [before,after]];assert z0.keys()==z1.keys() and len(z1)==47
 t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
 edited={z['uuid']:z for z in r['edited_zone_outlines']};refilled=set(r['refilled_existing_zones'])
 assert set(edited)=={'11f818e8-37ae-523f-9c0d-b52c7cace6d6','4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'}
 stripzone=lambda z,keys:[n for n in z if not(isinstance(n,list) and n and n[0] in keys)]
 for u,z in z0.items():
  if u not in refilled:assert t0[u]==t1[u] and z==z1[u],u
  else:assert stripzone(t0[u],['filled_polygon']+(['polygon'] if u in edited else []))==stripzone(t1[u],['filled_polygon']+(['polygon'] if u in edited else []))
  if u in edited:assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(edited[u]['outer_mm'],edited[u]['holes_mm']))<2e-6
  if z['net']!='PWR_AGND':assert z==z1[u],('Supply plane changed',u)
 assert set(fill['unchanged_existing_zone_canonical_polygon_match'])==z0.keys()-refilled
 priorpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json';analogpath=BASE/'analog-cell-routing.json'
 qs=json.loads(priorpath.read_text())['quiet_ground_islands']+json.loads(analogpath.read_text())['quiet_ground_islands'];quiet=[]
 def hits(cap,z):
  g=shape(z['polygons']);return {o['uuid'] for o in cap['objects'] if o['net']=='PWR_AGND' and o['layers'].get(z['layer']) and g.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9}
 for q in qs:
  zs=set(q['zone_uuids']);vs=[q['star_via'],*q['control_vias'],*q['extra_quiet_vias']];own={v['uuid'] for v in vs};contacts={}
  for u in zs:
   contacts[u]=hits(after,z1[u]);assert contacts[u]==hits(before,z0[u]) and contacts[u]<=own
   assert len(z0[u]['polygons'])==len(z1[u]['polygons'])
   g=shape(z1[u]['polygons']);assert all(g.distance(shape(z['polygons']))>=.1985 for uid,z in z1.items() if uid!=u and z['net']=='PWR_AGND' and z['layer']==z1[u]['layer'])
  reached={q['star_via']['uuid']};pending=set(zs)
  while True:
   prev=set(reached)
   for u in list(pending):
    if reached&contacts[u]:reached.update(contacts[u]);pending.remove(u)
   if reached==prev:break
  assert not pending and own<=reached
  for v in vs:
   hitsets=[]
   for cap,zmap in [(before,z0),(after,z1)]:
    o=next(o for o in cap['objects'] if o['uuid']==v['uuid'])
    hitsets.append({u for u,z in zmap.items() if u not in zs and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))})
   assert hitsets[0]==hitsets[1]
   if v['uuid']!=q['star_via']['uuid']:assert not hitsets[1]
   else:assert hitsets[1] and all(z1[u]['layer']=='In5.Cu' for u in hitsets[1])
  quiet.append(dict(ref=q['ref'],contacts_preserved=True,owned_graph_connected=True,star_only_main_return=True))
 owned=set(r['existing_surface_quiet_objects'])|added
 for route in r['routes']:
  if route['net']!='PWR_AGND':continue
  g=LineString(route['path_mm']).buffer(.1)
  for o in after['objects']:
   if o['net']=='PWR_AGND' and o['uuid'] not in owned and o['layers'].get('B.Cu'):assert g.distance(shape(o['layers']['B.Cu']))>=.1985,(o['uuid'],'surface quiet bypass')
 erc=json.loads((OUT/'erc.json').read_text());ef=[v for s in erc['sheets'] for v in s.get('violations',[])];assert all(v['severity']=='warning' for v in ef) and len(ef)==2
 assert native['geometry_findings']==native['schematic_parity_findings']==0
 sources=[Path(__file__),*paths,priorpath,analogpath,*[d/n for d in [BASE,OUT] for n in ['power_protection.kicad_pcb','netlist.xml']],OUT/'erc.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_buck_cell.py','repack_two_board_buck_input.py','verify_native_zone_unfracture.py']]]
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,generated_pad_identity_aliases=aliases,closed_connections=1,new_opens=2210,declared_native_join=[x,y],all_other_native_groups_preserved=True,moved_pad_count=2,retained_part_count=len(a0),retained_pin_entries=len(p0),quiet_returns=quiet,all_supply_planes_unchanged=True,geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,reference_audit_pending=True,fabrication_released=False)
 with (OUT/'digital-return-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['closed_connections','new_opens','all_other_native_groups_preserved','all_supply_planes_unchanged']}))
if __name__=='__main__':run()
