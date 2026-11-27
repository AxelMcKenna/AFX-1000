"""Conservative exclusion of every retained ground object authored by quiet-network passes."""
import json
from pathlib import Path
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from .verify import HERE,sha

def run(root):
 stage=root/'hardware/fabrication/staging';cp=stage/'two-board-power-routing-inputs-aux-local-distribution-03/capture.json';cap=json.loads(cp.read_text());objects={o['uuid']:o for o in cap['objects']};plan=json.loads((HERE/'plan.json').read_text());files=[stage/'two-board-power-digital-startup-native-02/digital-startup-routing.json',stage/'two-board-power-analog-cells-native-03/analog-cell-routing.json'];ids=set();pins=set();zoneids=set();owners=set()
 for file in files:
  d=json.loads(file.read_text())
  for q in d['quiet_ground_islands']:
   owners.add(q['ref']);zoneids.update(q['zone_uuids'])
   for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]:ids.add(v['uuid'])
  for r in d['routes']:
   if r['net']=='PWR_AGND':
    ids.update(r['segment_uuids'])
    if 'ref' in r and 'pin' in r:pins.add((r['ref'],str(r['pin'])))
  for v in d['vias']:
   if v['net']=='PWR_AGND':ids.add(v['uuid'])
 for o in cap['objects']:
  if o['net']=='PWR_AGND' and ((o.get('ref'),o.get('pin')) in pins or o.get('ref') in owners):ids.add(o['uuid'])
 retained=ids&objects.keys();retired=ids-objects.keys();evidence=[]
 for i,r in enumerate(plan['routes']):
  g=LineString(r['path_mm']).buffer(r['width_mm']/2)
  for u in retained:
   if r['layer'] in objects[u]['layers']:
    p=unary_union([Polygon(x['outer'],x['holes']) for x in objects[u]['layers'][r['layer']]]);assert g.distance(p)>.2,(i,u)
 for v in plan['new_vias']:
  g=Point(v['position_mm']).buffer(v['size_mm']/2)
  for u in retained:
   for layer,polys in objects[u]['layers'].items():
    p=unary_union([Polygon(x['outer'],x['holes']) for x in polys]);assert g.distance(p)>.2,(v,u,layer)
 for z in cap['zones']:
  if z['uuid'] not in zoneids:continue
  p=unary_union([Polygon(x['outer'],x['holes']) for x in z['authored_outline']]);distances=[Point(v['position_mm']).buffer(v['size_mm']/2).distance(p) for v in plan['new_vias']]+[LineString(r['path_mm']).buffer(r['width_mm']/2).distance(p) for r in plan['routes'] if r['layer']==z['layer']];assert min(distances)>.2;evidence.append({'zone_uuid':z['uuid'],'layer':z['layer'],'minimum_new_copper_distance_mm':min(distances)})
 result={'source_sha256':{str(p.relative_to(root)) if p.is_relative_to(root) else 'plan.json':sha(p) for p in [cp,*files,HERE/'plan.json']},'quiet_network_count':len(owners),'retained_quiet_pass_ground_object_count':len(retained),'retained_object_uuids':sorted(retained),'historical_retired_object_uuids':sorted(retired),'plane_exclusions':evidence,'all_layer_vias_checked':len(plan['new_vias']),'all_new_surface_tracks_checked':sum(len(r['path_mm'])-1 for r in plan['routes']),'new_contacts_with_retained_quiet_pass_ground_copper':0,'scope':'Conservatively includes all retained AGND objects authored by both quiet-network passes, not merely seven star vias; applies only to this local buck candidate'}
 (HERE/'quiet-exclusion.json').write_text(json.dumps(result,indent=2)+'\n');print({k:result[k] for k in ['quiet_network_count','retained_quiet_pass_ground_object_count','new_contacts_with_retained_quiet_pass_ground_copper']})
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
