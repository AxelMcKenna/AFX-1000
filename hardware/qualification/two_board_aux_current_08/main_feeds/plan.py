"""Bounded same-surface routing screen; exact reference and retained quiet exclusion."""
import json
from pathlib import Path
from shapely.geometry import LineString,shape as geo_shape
from shapely.ops import unary_union,nearest_points
from ..routed.plan import shape,astar,sha
H=Path(__file__).resolve().parent

def run():
 cp=H/'capture-01/capture.json';c=json.loads(cp.read_text());plane=json.loads((H.parent/'held_cell/plane-plan-03.json').read_text());bridge=json.loads((H.parent/'reference_bridge/plan.json').read_text());refs=[plane['new_zone_uuid'],plane['main_source_zone_uuid'],bridge['new_zone_uuid'],bridge['other_main_zone_uuid']];reference=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in refs]);by={(o['ref'],o['pin']):o for o in c['objects'] if o.get('ref')};q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quietids=set(q['retained_object_uuids']);copper=[(o['net'],shape(o['layers']['B.Cu']),o['uuid']) for o in c['objects'] if 'B.Cu' in o['layers']];routes=[];fails=[]
 pairs=[('P_R115','1','P_C900','1',.3),('P_C901','1','P_C102','1',.3)]
 keepouts=json.loads((H/'contact-keepouts.json').read_text());mechanical=unary_union([geo_shape(f['geometry']) for f in keepouts['features'] if 'B.Cu' in f['properties']['layers']])
 for ar,ap,br,bp,width in pairs:
  a,b=by[ar,ap],by[br,bp];assert a['net']==b['net'];net=a['net'];blocked=unary_union([g.buffer(.2+width/2+.002) for n,g,u in copper if n!=net or u in quietids]+[mechanical.buffer(width/2+.002)]);ga=shape(a['layers']['B.Cu']).intersection(reference.buffer(-width/2-.002)).difference(blocked.buffer(.000001));gb=shape(b['layers']['B.Cu']).intersection(reference.buffer(-width/2-.002)).difference(blocked.buffer(.000001));path=None;nodes=0
  if not ga.is_empty and not gb.is_empty:
   start,end=nearest_points(ga,gb);path,nodes=astar(list(start.coords)[0],list(end.coords)[0],blocked,reference,width,margin=5,step=.15)
  row={'source':ar+'.'+ap,'target':br+'.'+bp,'net':net,'layer':'B.Cu','width_mm':width,'search_nodes':nodes,'source_legal_area_mm2':ga.area,'target_legal_area_mm2':gb.area}
  if path:
   g=LineString(path).buffer(width/2);row.update(path_mm=path,length_mm=LineString(path).length,reference_uncovered_mm2=g.difference(reference).area);routes.append(row);copper.append((net,g,'new:'+str(len(routes))))
  else:fails.append(row)
  result={'capture_sha256':sha(cp),'planner_sha256':sha(Path(__file__)),'mechanical_keepouts_sha256':sha(H/'contact-keepouts.json'),'reference_zone_uuids':refs,'routes':routes,'failures':fails,'new_vias':[],'qualified':False};(H/'plan.json').write_text(json.dumps(result,indent=2)+'\n');print(row['source'],row['target'],'routed' if path else 'failed',nodes,flush=True)
if __name__=='__main__':run()
