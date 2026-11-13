"""New paired via with F.Cu source stub, avoiding every non-AGND fill."""
import json,math
from pathlib import Path
from shapely.geometry import Point,LineString,shape as geo_shape
from shapely.ops import unary_union,nearest_points
from ..routed.plan import sha,shape,astar
from ..main_feeds.routing_zones import obstacles
H=Path(__file__).resolve().parent;SRC=H.parent/'main_feeds';VIN=[198.,118.6];RETURN=[198.8,118.8];NET='/P_power_supply/VIN_IC'
def run():
 c=json.loads((SRC/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet=set(q['retained_object_uuids']);quietz={z['zone_uuid'] for z in q['plane_exclusions']};by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};sites=json.loads((H/'local-sites.json').read_text());site=next(r for r in sites['legal_paired_sites'] if r['vin_via_mm']==VIN);assert RETURN in site['return_sites_mm'];assert math.dist(VIN,RETURN)<1
 for pt in [VIN,RETURN]:assert min(math.dist(pt,o['position_mm']) for o in c['objects'] if o['kind']=='PCB_VIA')>.55
 refs={'F.Cu':['d41ab58e-16e9-5d76-8b14-dc335aff8371'],'B.Cu':['4b63f119-2e71-5d61-96f6-8b78a1f5c6cb','78fadc71-5bdb-5968-8ca8-0e3b4b40722f','38c31b6e-bfc4-5702-b059-ff9efeabba60','566e3f0a-1a65-5cbd-a101-d18d1b8abd56']};routes=[];fail=[];cutbacks=set(site['cutback_zone_uuids']);reference={l:unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in ids]) for l,ids in refs.items()};mechanical=json.loads((SRC/'contact-keepouts.json').read_text())
 for label,layer,start,end,width in [('stub','F.Cu',shape(by['P_U101.1']['layers']['F.Cu']),Point(VIN),.25),('feed','B.Cu',Point(VIN),shape(by['P_C900.1']['layers']['B.Cu']),.3)]:
  ref=reference[layer];allowedids=[z['uuid'] for z in c['zones'] if z['layer']==layer and z['net']=='PWR_AGND' and z['uuid'] not in quietz and not z['keepout']];mech=unary_union([geo_shape(f['geometry']) for f in mechanical['features'] if layer in f['properties']['layers']]);blocked=unary_union([shape(o['layers'][layer]).buffer(.2+width/2+.002) for o in c['objects'] if layer in o['layers'] and (o['net']!=NET or o['uuid'] in quiet)]+[Point(RETURN).buffer(.3+.2+width/2+.002),mech.buffer(width/2+.002),obstacles(c['zones'],layer,NET,width,allowedids)]);ga=start.intersection(ref.buffer(-width/2-.002)).difference(blocked.buffer(.000001));gb=end.intersection(ref.buffer(-width/2-.002)).difference(blocked.buffer(.000001));path=None;nodes=0
  if not ga.is_empty and not gb.is_empty:
   a,b=nearest_points(ga,gb);path,nodes=astar(list(a.coords)[0],list(b.coords)[0],blocked,ref,width,margin=6,step=.1)
  row={'source':'P_U101.1' if label=='stub' else 'via:VIN','target':'via:VIN' if label=='stub' else 'P_C900.1','net':NET,'layer':layer,'width_mm':width,'search_nodes':nodes};print(label,bool(path),nodes,flush=True)
  if path:
   g=LineString(path).buffer(width/2);row.update(path_mm=path,length_mm=LineString(path).length);routes.append(row);cutbacks.update(z['uuid'] for z in c['zones'] if z['uuid'] in allowedids and g.buffer(.202).intersects(shape(z['polygons'])))
  else:fail.append(row)
 result={'capture_sha256':sha(SRC/'capture-01/capture.json'),'source_board_sha256':sha(H.parent/'precision/native-01/power_protection.kicad_pcb'),'planner_sha256':sha(Path(__file__)),'local_site_screen_sha256':sha(H/'local-sites.json'),'zone_helper_sha256':sha(SRC/'routing_zones.py'),'mechanical_keepouts_sha256':sha(SRC/'contact-keepouts.json'),'quiet_exclusions_sha256':sha(H.parent/'routed/quiet-exclusion.json'),'reference_zone_uuids':refs,'routes':routes,'failures':fail,'new_vias':[{'name':'VIN','net':NET,'position_mm':VIN,'size_mm':.6,'drill_mm':.3},{'name':'VIN_return','net':'PWR_AGND','position_mm':RETURN,'size_mm':.6,'drill_mm':.3}],'return_pair_mm':math.dist(VIN,RETURN),'declared_cutback_zone_uuids':sorted(cutbacks),'cutback_net':'PWR_AGND','qualified':False};(H/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':run()
