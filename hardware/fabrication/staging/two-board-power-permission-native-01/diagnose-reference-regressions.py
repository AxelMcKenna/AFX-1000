import json,sys
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
sys.path.insert(0,str(Path.cwd()))
from hardware.fabrication.route_nf_surface import shape
st=Path('hardware/fabrication/staging');b=json.loads((st/'two-board-power-routing-inputs-2267-startup-completion-06/capture.json').read_text());a=json.loads((st/'two-board-power-routing-inputs-2237-permission-01/capture.json').read_text());r=json.loads((st/'two-board-power-permission-native-01/permission-routing.json').read_text());layers=a['copper_layers'];new={o['uuid']:o for o in a['objects']};rows=[]
def references(c):
 refs={}
 for z in c['zones']:
  if z['net']!='PWR_AGND':continue
  for p in z['polygons']:
   g=Polygon(p['outer'],p['holes']);contacts=[o for o in c['objects'] if o['net']=='PWR_AGND' and o['layers'].get(z['layer']) and g.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9]
   if not contacts:continue
   gids={o['group'] for o in contacts};assert len(gids)==1
   refs.setdefault((z['layer'],next(iter(gids))),[]).append(g)
 return {k:unary_union(gs) for k,gs in refs.items()}
rb,ra=references(b),references(a);holes={}
for o in b['objects']:
 if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
holes={n:unary_union(xs) for n,xs in holes.items()}
for o in b['objects']:
 if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
 layer,=o['layers'];li=layers.index(layer);adj={layers[i] for i in [li-1,li+1] if 0<=i<len(layers)};g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
 if o['net'] in holes:g=g.difference(holes[o['net']])
 if g.is_empty:continue
 for (rl,gid),ref in rb.items():
  if rl not in adj or g.difference(ref.buffer(.0015)).area>=1e-6:continue
  anchor=next(u for u in b['all_groups'][gid] if u in new);missing=g.difference(ra[rl,new[anchor]['group']].buffer(.0015))
  if missing.area>=1e-6:rows.append(dict(scope='retained',uuid=o['uuid'],net=o['net'],layer=layer,reference_layer=rl,area_mm2=missing.area,bounds=missing.bounds,path=[o['position_mm'],o['end_mm']]))
print('LOST',len(rows),flush=True)
for row in rows:print(row,flush=True)
newrows=[];holes={}
for o in a['objects']:
 if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
holes={n:unary_union(xs) for n,xs in holes.items()};ground={l:unary_union([shape(z['polygons']) for z in a['zones'] if z['net']=='PWR_AGND' and z['layer']==l]) for l in layers}
for route in r['routes']:
 if route['net']=='PWR_AGND':continue
 g=LineString(route['path_mm']).buffer(route['width_mm']/2)
 if route['net'] in holes:g=g.difference(holes[route['net']])
 li=layers.index(route['layer']);adj=[layers[i] for i in [li-1,li+1] if 0<=i<len(layers)];miss={l:g.difference(ground[l].buffer(.0015)) for l in adj};best=min(miss,key=lambda l:miss[l].area)
 if miss[best].area>=1e-6:newrows.append(dict(scope='new',label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),net=route['net'],layer=route['layer'],reference_layer=best,area_mm2=miss[best].area,bounds=miss[best].bounds,path=route['path_mm']))
print('NEW GAPS',len(newrows),flush=True)
for row in newrows:print(row,flush=True)
Path('/private/tmp/permission-reference-diagnostic.json').write_text(json.dumps(dict(lost_prior_reference=rows,new_reference_gaps=newrows,validation_passed=False),indent=2)+'\n')
