"""Bounded main-LDO input routing with foreign same-layer fills as obstacles."""
import json
from pathlib import Path
from shapely.geometry import LineString,shape as geo_shape
from shapely.ops import unary_union,nearest_points
from ..routed.plan import sha,shape,astar
from ..main_feeds.routing_zones import obstacles
H=Path(__file__).resolve().parent

def run():
 cp=H/'capture-01/capture.json';c=json.loads(cp.read_text());by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};a,b=by['P_C901.1'],by['P_C102.1'];assert a['net']==b['net'];net=a['net'];layer='B.Cu';width=.3
 q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet=set(q['retained_object_uuids']);qzones={z['zone_uuid'] for z in q['plane_exclusions']};refids=['4b63f119-2e71-5d61-96f6-8b78a1f5c6cb','78fadc71-5bdb-5968-8ca8-0e3b4b40722f','38c31b6e-bfc4-5702-b059-ff9efeabba60','566e3f0a-1a65-5cbd-a101-d18d1b8abd56'];reference=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in refids]);keep=[]
 for f in json.loads((H.parent/'main_feeds/contact-keepouts.json').read_text())['features']+json.loads((H.parent/'vin_escape/main-mount-keepouts.json').read_text())['features']:
  if layer in f['properties']['layers'] and f['properties'].get('board','power')=='power':keep.append(geo_shape(f['geometry']))
 allowed=[z['uuid'] for z in c['zones'] if z['layer']==layer and z['net']=='PWR_AGND' and z['uuid'] not in qzones and not z['keepout']];blocked=unary_union([shape(o['layers'][layer]).buffer(.2+width/2+.002) for o in c['objects'] if layer in o['layers'] and (o['net']!=net or o['uuid'] in quiet)]+[obstacles(c['zones'],layer,net,width,allowed)]+[g.buffer(width/2+.002) for g in keep]);source=unary_union([shape(o['layers'][layer]) for o in c['objects'] if o['group']==a['group'] and layer in o['layers']]);ga=source.intersection(reference.buffer(-width/2-.002)).difference(blocked.buffer(.000001));gb=shape(b['layers'][layer]).intersection(reference.buffer(-width/2-.002)).difference(blocked.buffer(.000001));path=None;nodes=0
 if not ga.is_empty and not gb.is_empty:
  start,end=nearest_points(ga,gb);path,nodes=astar(list(start.coords)[0],list(end.coords)[0],blocked,reference,width,margin=8,step=.1)
 result={'capture_sha256':sha(cp),'script_sha256':sha(Path(__file__)),'source_group':a['group'],'target':'P_C102.1','net':net,'width_mm':width,'layer':layer,'reference_zone_uuids':refids,'source_legal_area_mm2':ga.area,'target_legal_area_mm2':gb.area,'search_nodes':nodes,'path_mm':path,'qualified':False}
 if path:
  geom=LineString(path).buffer(width/2);result.update(length_mm=LineString(path).length,cutback_zone_uuids=[z['uuid'] for z in c['zones'] if z['uuid'] in allowed and geom.buffer(.202).intersects(shape(z['polygons']))])
 result.update(new_vias=[],failures=[] if path else ['No route'],routes=[{'source':'P_C901.1','target':'P_C102.1','net':net,'width_mm':width,'layer':layer,'path_mm':path}] if path else [])
 (H/'plan.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='path_mm'});print('routed',bool(path))
if __name__=='__main__':run()
