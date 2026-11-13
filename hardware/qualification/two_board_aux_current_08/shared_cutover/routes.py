"""Reconnect local bypass pairs after explicit shared-branch isolation."""
import json,copy
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union,nearest_points
from ..routed.plan import shape,astar,sha
H=Path(__file__).resolve().parent

def run():
 c=json.loads((H.parent/'bypass_local/capture-01/capture.json').read_text());cut=json.loads((H/'plan.json').read_text());moves={r['uuid']:r['new_net'] for r in cut['pin_moves']};objects=[copy.deepcopy(o) for o in c['objects'] if o['uuid'] not in cut['removed_track_uuids']]
 for o in objects:o['net']=moves.get(o['uuid'],o['net'])
 by={(o['ref'],o['pin']):o for o in objects if o.get('ref')};routes=[];fail=[]
 for ar,ap,br,bp,layer,width in [('E_U29','8','E_C74','1','B.Cu',.25),('E_U31','8','E_C76','1','F.Cu',.25),('P_U102','8','P_U102','5','F.Cu',.25)]:
  a=by[ar,ap];b=by[br,bp];assert a['net']==b['net'] and layer in a['layers'] and layer in b['layers'];refid='13cfea4d-d36e-5757-b531-ed680e4c4562' if layer=='F.Cu' else '4b63f119-2e71-5d61-96f6-8b78a1f5c6cb';ref=shape(next(z['polygons'] for z in c['zones'] if z['uuid']==refid));ga=shape(a['layers'][layer]).intersection(ref.buffer(-width/2-.002));gb=shape(b['layers'][layer]).intersection(ref.buffer(-width/2-.002));row={'source':ar+'.'+ap,'target':br+'.'+bp,'source_uuid':a['uuid'],'target_uuid':b['uuid'],'net':a['net'],'layer':layer,'width_mm':width,'reference_zone_uuid':refid};path=None
  if not ga.is_empty and not gb.is_empty:
   start,end=nearest_points(ga,gb);blocked=unary_union([shape(o['layers'][layer]).buffer(.2+width/2+.002) for o in objects if layer in o['layers'] and o['net']!=a['net']]);path,n=astar(list(start.coords)[0],list(end.coords)[0],blocked,ref,width,margin=6,step=.1)
  if path:row.update(path_mm=path,length_mm=LineString(path).length,reference_uncovered_mm2=LineString(path).buffer(width/2).difference(ref).area);routes.append(row)
  else:fail.append(row)
 result={'cut_plan_sha256':sha(H/'plan.json'),'router_sha256':sha(Path(__file__)),'routes':routes,'failures':fail,'qualified':False};(H/'routes.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':run()
