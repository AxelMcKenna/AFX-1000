import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import STAGING,REPO,sha
from hardware.fabrication.route_nf_surface import shape
cp=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json';c=json.loads(cp.read_text());obj={o['uuid']:o for o in c['objects']}
localpath=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json';startpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json';replacepath=STAGING/'two-board-power-digital-reference-native-02/digital-reference-track-routing.json'
local,start,repl=[json.loads(p.read_text()) for p in [localpath,startpath,replacepath]];routes=[];seen=set()
for source,rs in [('support',local['routes']),('startup',start['routes'])]:
 for r in rs:
  if source=='support' and r.get('label')==repl['retired_route']['label']:r=repl['replacement_route']
  if r['net']=='PWR_AGND' or not all(u in obj for u in r['segment_uuids']):continue
  key=json.dumps([r['net'],r['layer'],r['path_mm']])
  if key in seen:continue
  seen.add(key);routes.append((source,r))
rows=[]
for source,r in routes:
 if r['layer'] not in ['F.Cu','B.Cu']:continue
 layer={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[r['layer']]
 g=LineString(r['path_mm']).buffer(r['width_mm']/2)
 for o in c['objects']:
  if o['kind']=='PCB_VIA' and o['net']==r['net']:g=g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
 fields=unary_union([shape(z['polygons']) for z in c['zones'] if z['net']=='PWR_AGND' and z['layer']==layer]);auth=unary_union([shape(z['authored_outline']) for z in c['zones'] if z['net']=='PWR_AGND' and z['layer']==layer]);missing=g.difference(fields.buffer(.0015))
 if missing.area<1e-6:continue
 hits=[]
 for o in c['objects']:
  if o['net']=='PWR_AGND' or not o['layers'].get(layer):continue
  area=missing.intersection(shape(o['layers'][layer]).buffer(.2)).area
  if area>1e-8:hits.append(dict(uuid=o['uuid'],net=o['net'],kind=o['kind'],xy=o['position_mm'],end=o.get('end_mm'),area_mm2=area))
 row=dict(source=source,label=r.get('label',r.get('ref','')+'.'+r.get('pin','')),route=r,reference_layer=layer,missing_mm2=missing.area,missing_bounds=missing.bounds,outside_authored_mm2=missing.difference(auth.buffer(.0015)).area,foreign_copper=hits)
 rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='route'}),flush=True)
result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [cp,localpath,startpath,replacepath]},gaps=rows,screened_unique_active_paths=len(routes),fabrication_released=False)
Path('/private/tmp/digital-reference-gaps45.json').write_text(json.dumps(result,indent=2)+'\n')
