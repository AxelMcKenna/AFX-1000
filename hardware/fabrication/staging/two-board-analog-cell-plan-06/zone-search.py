import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import STAGING
from hardware.fabrication.route_nf_surface import shape
p=json.loads((STAGING/'two-board-analog-cell-plan-06/routes.json').read_text());c=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text());retire=set(p['retired_objects'])
assign={'E_R97':'In1.Cu','E_C39':'In6.Cu','E_R96':'In1.Cu','E_R101':'In6.Cu','E_C41':'In6.Cu','E_R100':'In6.Cu','E_R117':'In1.Cu','E_C49':'In1.Cu','E_R116':'In1.Cu'}
allroutes=p['routes']+p['connections'];viapairs=list(zip(p['routes'],p['vias']))+[(dict(owner=v['owner'],ref=v['ref'],pin=v['pin']),v) for v in p['extra_quiet_vias']];required={};shapes={};contacts={}
for owner in ['E_U13','E_U14','E_U32']:
 for layer in ['In1.Cu','In6.Cu']:
  parts=[];points=[]
  for r in allroutes:
   if r['owner']!=owner or r['net']=='PWR_AGND':continue
   if {'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}.get(r['layer'])!=layer:continue
   g=LineString(r['path_mm']).buffer(r['width_mm']/2)
   for v in p['vias']+[o for o in c['objects'] if o['kind']=='PCB_VIA' and o['uuid'] not in retire]:
    if v['net']==r['net']:g=g.difference(Point(v['position_mm']).buffer(.515))
   parts.append(g)
  if owner=='E_U32' and layer=='In1.Cu':
   o=next(o for o in c['objects'] if o['uuid']=='9770d677-f9b1-5431-97a0-f8f2ad480648')
   g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
   for v in c['objects']:
    if v['kind']=='PCB_VIA' and v['net']==o['net'] and v['uuid'] not in retire:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
   parts.append(g)
  cs=[]
  for r,v in viapairs:
   if r['owner']!=owner or v['net']!='PWR_AGND':continue
   if r['ref']==owner and (r['pin']=='8' or (r['pin'] in ['2','4'] and layer=='In1.Cu')) or assign.get(r['ref'])==layer or r['ref']=='E_C49_REFERENCE_BRIDGE' or (r['ref']=='E_R97' and layer=='In6.Cu'):
    parts.append(Point(v['position_mm']).buffer(.301));points.append(v['position_mm']);cs.append(dict(ref=r['ref'],pin=r['pin'],xy=v['position_mm']))
  required[owner,layer]=unary_union(parts);contacts[owner,layer]=cs
  shapes[owner,layer]=required[owner,layer].convex_hull.buffer(.4)
for (owner,layer),g in shapes.items():
 obstacles=[]
 for o in c['objects']:
  if o['uuid'] in retire or not o['layers'].get(layer):continue
  obstacles.append(shape(o['layers'][layer]).buffer(.215,quad_segs=32))
 for r in allroutes:
  if r['layer']==layer and (r['net']!='PWR_AGND' or r['owner']!=owner):obstacles.append(LineString(r['path_mm']).buffer(r['width_mm']/2+.215,quad_segs=32))
 for r,v in viapairs:
  if v['net']!='PWR_AGND' or r['owner']!=owner:obstacles.append(Point(v['position_mm']).buffer(.515,quad_segs=32))
 for (other,l),h in required.items():
  if l==layer and other!=owner:obstacles.append(h.buffer(.215,quad_segs=32))
 shapes[owner,layer]=g.difference(unary_union(obstacles))
# Partition any overlap outside mandatory regions deterministically.
for layer in ['In1.Cu','In6.Cu']:
 keys=[k for k in shapes if k[1]==layer]
 for i,k in enumerate(keys):
  for other in keys[i+1:]:
   shapes[other]=shapes[other].difference(shapes[k].buffer(.215,quad_segs=32))
results=[]
for (owner,layer),g in shapes.items():
 regions=list(g.geoms) if hasattr(g,'geoms') else [g];out=[]
 regions=[q for q in regions if q.intersection(required[owner,layer]).area>1e-8]
 g=unary_union(regions)
 for q in regions:
  anchors=[dict(ref=r['ref'],pin=r['pin'],xy=v['position_mm']) for r,v in viapairs if v['net']=='PWR_AGND' and r['owner']==owner and q.intersects(Point(v['position_mm']).buffer(.3))]
  reqarea=q.intersection(required[owner,layer]).area
  out.append(dict(area_mm2=q.area,required_area_mm2=reqarea,anchors=anchors))
 record=dict(owner=owner,layer=layer,components=out,required_uncovered_mm2=required[owner,layer].difference(g.buffer(.0015)).area,polygons=[dict(outer=list(q.exterior.coords),holes=[list(h.coords) for h in q.interiors]) for q in regions])
 results.append(record)
 print(json.dumps({k:v for k,v in record.items() if k!='polygons'}),flush=True)
(STAGING/'two-board-analog-cell-plan-06/quiet-shapes.json').write_text(json.dumps(dict(regions=results,extra_quiet_assignments=assign,fabrication_released=False),indent=2)+'\n')
