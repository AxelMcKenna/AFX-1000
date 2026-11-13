"""Plan local bypass supply/return and IN/EN tie on the regulator face."""
import json
from pathlib import Path
from shapely.geometry import box,Point,LineString,shape as geo_shape
from shapely.ops import unary_union,nearest_points
from ..routed.plan import sha,shape,astar
from ..main_feeds.routing_zones import obstacles
H=Path(__file__).resolve().parent

def run():
 c=json.loads((H/'capture-01/capture.json').read_text());by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qi=set(q['retained_object_uuids']);qz={r['zone_uuid'] for r in q['plane_exclusions']};refs=['c10eec5d-cf1f-58da-8d6d-48ce5d70e70d','d41ab58e-16e9-5d76-8b14-dc335aff8371','d5d0775a-fea7-5f03-bf2b-e5c7ca690024','dfd01f0a-edcf-55b7-aecb-2d44a419b9b3'];assert not set(refs)&qz;ref=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in refs]);cp=[186.875,127.6];cn=[183.925,127.6];newpads={'P_C907.1':('/P_power_supply/AUX_PREREG5',box(cp[0]-.575,cp[1]-.9,cp[0]+.575,cp[1]+.9)),'P_C907.2':('PWR_AGND',box(cn[0]-.575,cn[1]-.9,cn[0]+.575,cn[1]+.9))};geoms={k:(v['net'],shape(v['layers']['F.Cu'])) for k,v in by.items() if 'F.Cu' in v['layers']};geoms.update(newpads);copper=[(o['net'],shape(o['layers']['F.Cu']),o['uuid']) for o in c['objects'] if 'F.Cu' in o['layers']]+[(n,g,k) for k,(n,g) in newpads.items()];keep=[]
 for path in [H.parent/'main_feeds/contact-keepouts.json',H.parent/'vin_escape/main-mount-keepouts.json']:
  for f in json.loads(path.read_text())['features']:
   if f['properties'].get('board','power')=='power' and 'F.Cu' in f['properties']['layers']:keep.append(geo_shape(f['geometry']))
 rows=[]
 for source,target,width in [('P_C907.1','P_U102.8',.3),('P_C907.2','P_U102.9',.4),('P_U102.8','P_U102.5',.25)]:
  net,start=geoms[source];tn,end=geoms[target];assert net==tn;blocked=unary_union([g.buffer(.2+width/2+.002) for n,g,u in copper if n!=net or u in qi]+[g.buffer(width/2+.002) for g in keep]+[obstacles(c['zones'],'F.Cu',net,width)]);ga=start.intersection(ref.buffer(-width/2-.002)).difference(blocked.buffer(.000001));gb=end.intersection(ref.buffer(-width/2-.002)).difference(blocked.buffer(.000001));path=None;nodes=0
  if not ga.is_empty and not gb.is_empty:
   a,b=nearest_points(ga,gb);path,nodes=astar(list(a.coords)[0],list(b.coords)[0],blocked,ref,width,margin=5,step=.1)
  row={'source':source,'target':target,'net':net,'layer':'F.Cu','width_mm':width,'path_mm':path,'search_nodes':nodes,'source_legal_area_mm2':ga.area,'target_legal_area_mm2':gb.area};rows.append(row);print(source,target,bool(path),nodes,flush=True)
  if path:g=LineString(path).buffer(width/2);row['length_mm']=LineString(path).length;copper.append((net,g,'new:'+source))
 (H/'loop-plan.json').write_text(json.dumps({'capture_sha256':sha(H/'capture-01/capture.json'),'script_sha256':sha(Path(__file__)),'reference_zone_uuids':refs,'new_capacitor':{'reference':'P_C907','position_mm':[185.4,127.6],'orientation_kicad_degrees':180,'layer':'F.Cu','MPN':'C1206C106K3RACTU'},'routes':rows,'qualified':False},indent=2)+'\n')
if __name__=='__main__':run()
