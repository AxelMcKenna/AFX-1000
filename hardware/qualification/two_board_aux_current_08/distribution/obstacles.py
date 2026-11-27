"""Separate endpoint reference gaps from foreign-copper clearance barriers."""
import json
from pathlib import Path
from shapely.ops import unary_union
from ..routed.plan import shape,sha
H=Path(__file__).resolve().parent

def run():
 c=json.loads((H/'capture-02/capture.json').read_text());p=json.loads((H/'plan.json').read_text());ref=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in p['reference_zone_uuids']]);by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};rows=[];q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet={z['zone_uuid'] for z in q['plane_exclusions']};other=[z for z in c['zones'] if z['layer']=='In6.Cu' and z['net']=='PWR_AGND' and z['uuid'] not in quiet and z['uuid'] not in p['reference_zone_uuids']]
 for r in p['failures']:
  endpoints=[]
  for key in ['source','target']:
   o=by[r[key]];g=shape(o['layers'][r['layer']]);endpoints.append({'pin':r[key],'net':o['net'],'pad_reference_overlap_mm2':g.intersection(ref).area,'pad_reference_distance_mm':g.distance(ref),'trace_center_reference_area_mm2':g.intersection(ref.buffer(-r['width_mm']/2-.002)).area,'after_foreign_clearance_area_mm2':r[key+'_legal_area_mm2'],'other_nonquiet_In6_overlaps':[{'zone_uuid':z['uuid'],'overlap_mm2':g.intersection(shape(z['polygons'])).area} for z in other if g.intersects(shape(z['polygons']))]})
  rows.append({'source':r['source'],'target':r['target'],'width_mm':r['width_mm'],'search_nodes':r['search_nodes'],'endpoints':endpoints})
 result={'capture_sha256':sha(H/'capture-02/capture.json'),'plan_sha256':sha(H/'plan.json'),'script_sha256':sha(Path(__file__)),'failed_routes':rows,'scope':'Endpoint gaps are relative to the two selected contiguous main-reference fills. Other nonquiet In6 fills are reported separately, not silently treated as absent.','other_reference_candidates':[{'zone_uuid':z['uuid'],'distance_from_selected_mm':shape(z['polygons']).distance(ref),'main_group_contacts':[o['uuid'] for o in c['objects'] if o['net']=='PWR_AGND' and o['group']=='00b41082-e346-59e4-aee2-f34d9b87e697' and 'In6.Cu' in o['layers'] and shape(o['layers']['In6.Cu']).intersects(shape(z['polygons']))]} for z in other],'qualified':False};(H/'obstacles.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':run()
