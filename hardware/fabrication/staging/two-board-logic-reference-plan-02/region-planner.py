import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString,box,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import STAGING
from hardware.fabrication.route_nf_surface import shape
S=STAGING;c=json.loads((S/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json').read_text());r=json.loads((S/'two-board-power-startup-logic-native-02/startup-logic-routing.json').read_text());prior=json.loads((S/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())
pgplan=json.loads(Path('/private/tmp/logic-reference-pg1-route.json').read_text());follow=json.loads(Path('/private/tmp/logic-reference-follow1-route.json').read_text())
labels={x['label'] for x in [pgplan['retired_route'],*follow['retired_routes']]}
r['routes']=[x for x in r['routes'] if x.get('label') not in labels]+pgplan['routes']+follow['routes']
r['vias']=[v for v in r['vias'] if v['uuid']!=follow['retired_via']['uuid']]+pgplan['vias']+follow['vias']
main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
quiet={v['uuid'] for q in prior['quiet_ground_islands'] for v in q['control_vias']+q['extra_quiet_vias']}
qids={u for q in prior['quiet_ground_islands'] for u in q['zone_uuids']}
regions={};targets={};oldzone={'In1.Cu':None,'In4.Cu':'787e0385-5c4c-5b8f-9a2a-017054f7da0e','In5.Cu':'2fff880c-5da4-5609-a6d1-dfc1d5b3e287','In6.Cu':'4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'}
refs={'F.Cu':'In1.Cu','B.Cu':'In6.Cu','In2.Cu':'In1.Cu','In3.Cu':'In4.Cu','In6.Cu':'In5.Cu'}
for l in oldzone:
 paths=[LineString(x['path_mm']).buffer(x['width_mm']/2+1.0) for x in r['routes'] if refs[x['layer']]==l]
 anchors=[Point(v['position_mm']).buffer(1.0) for v in r['vias'] if v['net']=='PWR_AGND']
 targets[l]=unary_union(paths)
 # The broad local fields also cover pad exits and provide lateral return
 # space; reference coverage is independently checked against native fills.
 g=unary_union(paths+anchors).convex_hull
 for o in c['objects']:
  if o['net']=='PWR_AGND' and (o.get('group')!=main or o['uuid'] in quiet) and o['layers'].get(l):g=g.difference(shape(o['layers'][l]).buffer(.215,quad_segs=64))
  if o.get('npth'):g=g.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
 for z in c['zones']:
  if z['layer']==l and z['uuid']!=oldzone[l]:g=g.difference(shape(z['authored_outline']).buffer(.3 if z['net']!='PWR_AGND' else .215))
 if oldzone[l]:g=unary_union([g,shape(next(z['authored_outline'] for z in c['zones'] if z['uuid']==oldzone[l]))])
 regions[l]=g
 print(l,g.geom_type,round(g.area,3),g.bounds)
 # Print authored connected parts and their same-net physical contacts.
 for pg in (list(g.geoms) if hasattr(g,'geoms') else [g]):
  contacts=[o for o in c['objects'] if o['net']=='PWR_AGND' and o['layers'].get(l) and pg.intersects(shape(o['layers'][l]))]
  print('part',round(pg.area,3),'contacts',len(contacts),'groups',len({o['group'] for o in contacts}),'quiet_contacts',len({o['uuid'] for o in contacts}&quiet))
record=dict(main_group=main,quiet_vias_excluded=sorted(quiet),regions={l:dict(existing_zone_uuid=oldzone[l],polygons=[dict(outer=list(pg.exterior.coords),holes=[list(h.coords) for h in pg.interiors]) for pg in (list(g.geoms) if hasattr(g,'geoms') else [g])]) for l,g in regions.items()},reroutes=[pgplan,follow],combined_routes=r['routes'],combined_vias=r['vias'],native_validation_pending=True)
Path('/private/tmp/startup-logic-reference-plan-v2.json').write_text(json.dumps(record,indent=2))
