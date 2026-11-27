"""Source-bound main-ground return routing from actual Si8751 GND pin 4."""
import json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union,nearest_points
from ..routed.plan import shape,astar,sha
H=Path(__file__).resolve().parent

def run():
 cp=H/'capture-01/capture.json';c=json.loads(cp.read_text());main='00b41082-e346-59e4-aee2-f34d9b87e697';ref=shape(next(z['polygons'] for z in c['zones'] if z['uuid']=='13cfea4d-d36e-5757-b531-ed680e4c4562'));by={(o['ref'],o['pin']):o for o in c['objects'] if o.get('ref')};routes=[];fail=[];vias=[]
 quiet=json.loads((H.parent/'routed/quiet-exclusion.json').read_text())
 quietids=set(quiet['retained_object_uuids']);quietzones={q['zone_uuid'] for q in quiet['plane_exclusions']}
 # All disconnected AGND copper is forbidden except the selected source group.
 # This protects quiet and unrelated AGND groups without relying on names alone.
 for r,p in [('E_C29','2'),('E_C36','2'),('E_U1','4'),('E_U2','4'),('E_U3','4'),('E_U4','4')]:
  o=by[r,p];assert o['net']=='PWR_AGND' and 'F.Cu' in o['layers'];width=.3;sourcegeom=shape(o['layers']['F.Cu']);startregion=sourcegeom.intersection(ref.buffer(-width/2-.002));targets=[t for t in c['objects'] if t['group']==main and t['uuid'] not in quietids and 'F.Cu' in t['layers'] and math.dist(o['position_mm'],t['position_mm'])<8]
  blocked=unary_union([shape(t['layers']['F.Cu']).buffer(.352) for t in c['objects'] if 'F.Cu' in t['layers'] and (t['group'] not in [main,o['group']] or t['uuid'] in quietids)]+[shape(z['polygons']).buffer(.352) for z in c['zones'] if z['layer']=='F.Cu' and (z['keepout'] or z['net']!='PWR_AGND' or z['uuid'] in quietzones)])
  candidates=[]
  if not startregion.is_empty:
   for t in sorted(targets,key=lambda t:math.dist(o['position_mm'],t['position_mm']))[:16]:
    endregion=shape(t['layers']['F.Cu']).intersection(ref.buffer(-width/2-.002))
    if endregion.is_empty:continue
    a,b=nearest_points(startregion,endregion);start=list(a.coords)[0];end=list(b.coords)[0]
    path,n=astar(start,end,blocked,ref,width,margin=3,step=.15)
    if path:candidates.append((LineString(path).length,t,path,n));break
  row={'source':r+'.'+p,'source_uuid':o['uuid'],'source_group':o['group'],'source_pad_net':o['net'],'reference_zone_uuid':'13cfea4d-d36e-5757-b531-ed680e4c4562','source_center_reference_gap_mm':ref.distance(Point(o['position_mm'])),'pad_reference_start_region_mm2':startregion.area}
  if candidates:
   length,t,path,n=min(candidates,key=lambda x:x[0]);row.update(target_uuid=t['uuid'],target_group=main,layer='F.Cu',width_mm=width,path_mm=path,length_mm=length,search_nodes=n,reference_uncovered_mm2=LineString(path).buffer(width/2).difference(ref).area);routes.append(row)
  else:
   forbidden=unary_union([shape(polys).buffer(.502) for t in c['objects'] for layer,polys in t['layers'].items() if t['group'] not in [main,o['group']] or t['uuid'] in quietids]+[shape(polys).buffer(.402) for t in c['objects'] if t['kind']=='PAD' for polys in t['layers'].values()]+[shape(z['polygons']).buffer(.502) for z in c['zones'] if z['keepout'] or z['net']!='PWR_AGND' or z['uuid'] in quietzones])
   positions=sorted(([o['position_mm'][0]+dx*.25,o['position_mm'][1]+dy*.25] for dx in range(-12,13) for dy in range(-12,13)),key=lambda xy:math.dist(xy,o['position_mm']))
   found=None
   for pos in positions:
    if forbidden.intersects(Point(pos)) or not ref.covers(Point(pos).buffer(.35)) or startregion.is_empty:continue
    start=list(nearest_points(startregion,Point(pos))[0].coords)[0];path,n=astar(start,pos,blocked,ref,width,margin=3,step=.15)
    if path:found=(pos,path,n);break
   if found:
    pos,path,n=found;v={'name':r+'_'+p,'position_mm':pos,'size_mm':.6,'drill_mm':.3,'net':'PWR_AGND'};vias.append(v);row.update(target_new_via=v['name'],target_group=main,layer='F.Cu',width_mm=width,path_mm=path,length_mm=LineString(path).length,search_nodes=n,reference_uncovered_mm2=LineString(path).buffer(width/2).difference(ref).area);routes.append(row)
   else:fail.append(row)
 out={'source_capture_sha256':sha(cp),'planner_sha256':sha(Path(__file__)),'routes':routes,'failures':fail,'new_vias':vias,'new_zones':[],'qualified':False};(H/'plan.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':run()
