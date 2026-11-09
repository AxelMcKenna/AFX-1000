import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import first,children,read_sexpr
from hardware.fabrication.integrate_two_board_signal import STAGING,prop
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
S=STAGING;c=json.loads((S/'two-board-power-routing-inputs-2294-logic-references-02/capture.json').read_text());p=json.loads(Path('/private/tmp/startup-completion-routes-v5.json').read_text());prior=json.loads((S/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())
unused={('E_U30','3'),('E_U13','1'),('E_R99','1'),('E_R96','1')}
p['unused_fanout_not_emitted']=[list(k) for k in sorted(unused)]
for cell in p['cells']:
 cell['routes']=[r for r in cell['routes'] if (r.get('ref'),r.get('pin')) not in unused]
 cell['vias']=[v for v in cell['vias'] if (v['ref'],v['pin']) not in unused]
p['routes']=[r for r in p['routes'] if r.get('label') not in {f'{ref}.{pin} escape' for ref,pin in unused}]
p['extra_vias']=[v for v in p['extra_vias'] if (v['ref'],v['pin']) not in unused]
b=read_sexpr((S/'two-board-power-logic-references-native-02/power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(b,'footprint')}
objects=[]
for o in c['objects']:
 if o['uuid'] in p['retired_objects']:continue
 if o.get('ref') in p['moves']:
  xy,rot,_=p['moves'][o['ref']];o=transform_object(o,position(fps[o['ref']]),xy,rot)
 objects.append(o)
routes=[r for cell in p['cells'] for r in cell['routes']]+p['routes'];vias=[v for cell in p['cells'] for v in cell['vias']]+p['extra_vias']
main=next(o['group'] for o in objects if o.get('ref')=='P_C103' and o.get('pin')=='2')
quiet={v['uuid'] for q in prior['quiet_ground_islands'] for v in q['control_vias']+q['extra_quiet_vias']}
oldzone={'In1.Cu':'13cfea4d-d36e-5757-b531-ed680e4c4562','In4.Cu':'cfbe2e9d-6fef-5185-a803-f1564fa418df','In5.Cu':'2fff880c-5da4-5609-a6d1-dfc1d5b3e287','In6.Cu':'4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'}
refs={'F.Cu':'In1.Cu','B.Cu':'In6.Cu','In2.Cu':'In1.Cu','In3.Cu':'In4.Cu','In6.Cu':'In5.Cu'};regions={}
for layer,u in oldzone.items():
 paths=[LineString(r['path_mm']).buffer(r['width_mm']/2+1.0) for r in routes if refs[r['layer']]==layer]
 anchors=[Point(v['position_mm']).buffer(1.0) for v in vias if v['net']=='PWR_AGND']
 g=unary_union(paths+anchors).convex_hull
 for o in objects:
  if o['net']=='PWR_AGND' and (o.get('group')!=main or o['uuid'] in quiet) and o['layers'].get(layer):g=g.difference(shape(o['layers'][layer]).buffer(.215,quad_segs=64))
  if o.get('npth'):g=g.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
 for z in c['zones']:
  if z['layer']==layer and z['uuid']!=u:g=g.difference(shape(z['authored_outline']).buffer(.3 if z['net']!='PWR_AGND' else .215))
 original=shape(next(z['authored_outline'] for z in c['zones'] if z['uuid']==u));g=unary_union([g,original]).simplify(.00001,preserve_topology=True)
 assert original.difference(g.buffer(.000002)).area<1e-7
 parts=list(g.geoms) if hasattr(g,'geoms') else [g]
 for pg in parts:
  contacts=[o for o in objects if o['net']=='PWR_AGND' and o['layers'].get(layer) and pg.intersection(shape(o['layers'][layer])).area>1e-9]
  assert not {o['uuid'] for o in contacts}&quiet
  assert {o['group'] for o in contacts}<={main},(layer,'Foreign ground contact')
  print(layer,round(pg.area,3),'old main contacts',len(contacts),'new ground vias',[v['ref'] for v in vias if v['net']=='PWR_AGND' and pg.covers(Point(v['position_mm']))])
 regions[layer]=dict(existing_zone_uuid=u,polygons=[dict(outer=list(pg.exterior.coords),holes=[list(h.coords) for h in pg.interiors]) for pg in parts])
p['reference_regions']=regions;p['main_ground_group']=main;p['quiet_vias_excluded']=sorted(quiet)
Path('/private/tmp/startup-completion-plan-v1.json').write_text(json.dumps(p,indent=2)+'\n')
