import json
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
st=Path('hardware/fabrication/staging');c=json.loads((st/'two-board-power-routing-inputs-2268-startup-completion-04/capture.json').read_text());r=json.loads((st/'two-board-power-startup-completion-native-04/startup-completion-routing.json').read_text());a=json.loads((st/'two-board-power-startup-completion-native-04/startup-completion-review.json').read_text())
for row in a['new_logic_reference']:
 if min(row['adjacent_uncovered_mm2'].values())<1e-6:continue
 route=next(t for t in r['routes'] if t.get('label',t.get('ref','')+'.'+t.get('pin',''))==row['label']);layer=min(row['adjacent_uncovered_mm2'],key=row['adjacent_uncovered_mm2'].get)
 g=LineString(route['path_mm']).buffer(route['width_mm']/2)
 holes=unary_union([Point(o['position_mm']).buffer(o['width_mm']/2+.215) for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==route['net']]);g=g.difference(holes)
 ground=unary_union([shape(z['polygons']) for z in c['zones'] if z['layer']==layer and z['net']=='PWR_AGND']);miss=g.difference(ground.buffer(.0015));parts=list(miss.geoms) if hasattr(miss,'geoms') else [miss]
 print('\nROUTE',row['label'],layer,'PATH',route['path_mm'])
 for part in parts:
  if part.area<1e-7:continue
  print('GAP',part.area,part.bounds)
  near=sorted([(part.distance(shape(o['layers'][layer])),o) for o in c['objects'] if o['layers'].get(layer) and o['net']!='PWR_AGND'],key=lambda x:x[0])[:3]
  print('COPPER',[(d,o['kind'],o.get('ref'),o.get('pin'),o['position_mm'],o['net'],o['uuid']) for d,o in near])
  zs=sorted([(part.distance(shape(z['polygons'])),z) for z in c['zones'] if z['layer']==layer],key=lambda x:x[0])[:3]
  print('ZONES',[(d,z['uuid'],z['net']) for d,z in zs])
