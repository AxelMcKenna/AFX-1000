import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.integrate_two_board_signal import STAGING
p=STAGING/'two-board-analog-cell-plan-03';r=json.loads((p/'routes.json').read_text());c=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text())
req={};details=[]
for owner in ['E_U13','E_U14','E_U32']:
 for layer in ['In1.Cu','In6.Cu']:
  geoms=[];labels=[]
  for route in r['routes']+r['connections']:
   if route['owner']!=owner or not any(s in route['net'] for s in ['_ILM','_DVDT']):continue
   target={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[route['layer']]
   if target!=layer:continue
   g=LineString(route['path_mm']).buffer(route['width_mm']/2)
   for via in r['vias']:
    if via['net']==route['net']:g=g.difference(Point(via['position_mm']).buffer(.515))
   geoms.append(g);labels.append(route.get('label',route.get('ref','')+'.'+route.get('pin','')))
  contacts=[]
  for route,via in zip(r['routes'],r['vias']):
   if route['ref']==owner and (route['pin']=='8' or (layer=='In1.Cu' and route['pin'] in ['2','4'])):
    geoms.append(Point(via['position_mm']).buffer(.301));contacts.append(dict(pin=route['pin'],position_mm=via['position_mm']))
  req[owner,layer]=unary_union(geoms);details.append(dict(owner=owner,layer=layer,required_routes=labels,required_ground_contacts=contacts,required_area_mm2=req[owner,layer].area))
conflicts=[]
for (owner,layer),g in req.items():
 for (other,l),h in req.items():
  if l==layer and owner<other and g.distance(h)<.21:conflicts.append(dict(kind='required-quiet-region-pair',owner=owner,other=other,layer=layer,gap_mm=g.distance(h),overlap_area_mm2=g.intersection(h).area))
 for o in c['objects']:
  if o['uuid'] in r['retired_objects'] or o['net']!='PWR_AGND' or not o['layers'].get(layer):continue
  h=shape(o['layers'][layer])
  if g.distance(h)<.21:conflicts.append(dict(kind='retained-ground-object',owner=owner,layer=layer,uuid=o['uuid'],gap_mm=g.distance(h),overlap_area_mm2=g.intersection(h).area))
 for rr,v in zip(r['routes'],r['vias']):
  if v['net']!='PWR_AGND' or rr['owner']==owner:continue
  h=Point(v['position_mm']).buffer(.3)
  if g.distance(h)<.21:conflicts.append(dict(kind='other-quiet-via',owner=owner,other=rr['owner'],pin=rr['pin'],layer=layer,gap_mm=g.distance(h),overlap_area_mm2=g.intersection(h).area))

issues=[]
for (owner,layer),g in req.items():
 for o in c['objects']:
  if o['uuid'] in r['retired_objects'] or o['net']=='PWR_AGND' or not o['layers'].get(layer):continue
  h=shape(o['layers'][layer]).buffer(.21)
  area=g.intersection(h).area
  if area>1e-6:issues.append(dict(owner=owner,layer=layer,kind='retained-object',uuid=o['uuid'],net=o['net'],missing_area_mm2=area))
 for route in r['routes']+r['connections']:
  if route['layer']!=layer or route['net']=='PWR_AGND':continue
  area=g.intersection(LineString(route['path_mm']).buffer(route['width_mm']/2+.21)).area
  if area>1e-6:issues.append(dict(owner=owner,layer=layer,kind='new-route',label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),missing_area_mm2=area))
 for route,via in zip(r['routes'],r['vias']):
  if via['net']=='PWR_AGND':continue
  area=g.intersection(Point(via['position_mm']).buffer(.51)).area
  if area>1e-6:issues.append(dict(owner=owner,layer=layer,kind='new-via',ref=route['ref'],pin=route['pin'],missing_area_mm2=area))

from hardware.fabrication.integrate_two_board_signal import REPO,sha
inputs=[Path(__file__).resolve(),p/'routes.json',p/'placement.json',STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json',REPO/'hardware/fabrication/route_nf_surface.py']
report=dict(source_sha256={str(q.relative_to(REPO)):sha(q) for q in inputs},requirements=details,quiet_owner_conflicts=conflicts,foreign_copper_conflicts=issues,passed=not conflicts and not issues,scope='Minimum required route projections and declared ground-contact envelopes only. Does not prove connecting copper, zone-fill necks, main-return trimming, star-only contacts or old-reference preservation.',fabrication_released=False)
(p/'quiet-region-screen.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['passed'],report
print(json.dumps(dict(passed=True,quiet_regions=len(details),quiet_owner_conflicts=len(conflicts),foreign_copper_conflicts=len(issues))))
