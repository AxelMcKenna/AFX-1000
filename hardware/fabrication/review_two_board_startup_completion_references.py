"""Screen retained support routes after adding startup ground references."""
import json
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape

def run():
 out=STAGING/'two-board-power-startup-completion-native-02';cp=STAGING/'two-board-power-routing-inputs-2270-startup-completion-02/capture.json';base=STAGING/'two-board-power-digital-startup-native-02'
 prior=STAGING/'two-board-power-digital-reference-native-02';local=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json'
 sources=[Path(__file__),cp,out/'startup-completion-review.json',base/'digital-startup-routing.json',local,prior/'digital-reference-track-routing.json',REPO/'hardware/fabrication/route_nf_surface.py',*[STAGING/'two-board-power-input-tvs-native-01'/n for n in ['fast-ov-routing.json','fast-ov-return-routing.json']]]
 for p in [cp,out/'startup-completion-review.json']:
  for n,h in json.loads(p.read_text())['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 c=json.loads(cp.read_text());objects={o['uuid']:o for o in c['objects']};layers=c['copper_layers'];grounds={layer:unary_union([shape(z['polygons']) for z in c['zones'] if z['layer']==layer and z['net']=='PWR_AGND']) for layer in layers}
 def screen(route):
  g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  for o in objects.values():
   if o['kind']=='PCB_VIA' and o['net']==route['net'] and o['net']!='PWR_AGND':g=g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
  i=layers.index(route['layer']);adj=[layers[j] for j in [i-1,i+1] if 0<=j<len(layers)]
  return dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),net=route['net'],surface_layer=route['layer'],screen_area_mm2=g.area,adjacent_uncovered_mm2={l:g.difference(grounds[l].buffer(.0015)).area for l in adj})
 fast=[]
 for p in sources[-2:]:fast.extend(r for r in json.loads(p.read_text())['routes'] if all(u in objects for u in r['segment_uuids']))
 assert len(fast)==33;fast=[screen(r) for r in fast];assert all(min(r['adjacent_uncovered_mm2'].values())<1e-6 for r in fast)
 replacement=json.loads((prior/'digital-reference-track-routing.json').read_text());retained=[]
 for r in json.loads(local.read_text())['routes']:
  if r.get('label')==replacement['retired_route']['label']:r=replacement['replacement_route']
  if r['net']!='PWR_AGND':retained.append(screen(r))
 assert len(retained)==28
 startup=[screen(r) for r in json.loads((base/'digital-startup-routing.json').read_text())['routes'] if r['net']!='PWR_AGND' and all(u in objects for u in r['segment_uuids'])];assert len(startup)==15
 source=next(z for z in c['zones'] if z['net']=='PWR_5V_DIG_SRC' and z['layer']=='In4.Cu');g=shape(source['polygons']);source_area=g.area
 for o in objects.values():
  if o['net']==source['net'] and o['layers'].get('In5.Cu'):g=g.difference(shape(o['layers']['In5.Cu']).buffer(.215))
 main=next(o['group'] for o in objects.values() if o.get('ref')=='P_C103' and o.get('pin')=='2');references=[]
 for z in c['zones']:
  if z['net']!='PWR_AGND' or z['layer']!='In5.Cu':continue
  for p in z['polygons']:
   pg=Polygon(p['outer'],p['holes']);contacts={o['group'] for o in objects.values() if o['net']=='PWR_AGND' and o['layers'].get('In5.Cu') and pg.buffer(.0015).intersection(shape(o['layers']['In5.Cu'])).area>1e-9}
   if main in contacts:assert contacts=={main};references.append(pg)
 uncovered=g.difference(unary_union(references).buffer(.0015)).area
 full=lambda rows:sum(min(r['adjacent_uncovered_mm2'].values())<1e-6 for r in rows)
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retained_support_reference=retained,retained_support_fully_referenced_sections=full(retained),new_startup_reference=startup,new_startup_fully_referenced_sections=full(startup),fast_OV_reference=fast,source_plane_area_mm2=source_area,source_In5_screen_area_mm2=g.area,source_In5_uncovered_mm2=uncovered,full_startup_reference_complete=full(startup)==len(startup),reference_projection_only=True,current_thermal_timing_noise_qualified=False,fabrication_released=False)
 with (out/'retained-startup-completion-reference-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['retained_support_fully_referenced_sections','new_startup_fully_referenced_sections','source_plane_area_mm2','source_In5_uncovered_mm2','full_startup_reference_complete']}))
if __name__=='__main__':run()
