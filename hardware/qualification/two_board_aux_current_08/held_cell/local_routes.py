"""Route the held reservoir/LDO cell against actual filled native reference copper."""
import json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union,nearest_points
from shapely.prepared import prep
from ..routed.plan import shape,astar,sha
H=Path(__file__).resolve().parent

def run():
 cp=H/'capture-04/capture.json';c=json.loads(cp.read_text());plane=json.loads((H/'plane-plan-03.json').read_text());reference=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in [plane['new_zone_uuid'],plane['main_source_zone_uuid']]]);by={(o['ref'],o['pin']):o for o in c['objects'] if o.get('ref')};q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quietids=set(q['retained_object_uuids']);quietzones={x['zone_uuid'] for x in q['plane_exclusions']};copper={l:[(o['net'],shape(o['layers'][l]),o['uuid']) for o in c['objects'] if l in o['layers']] for l in c['copper_layers']};routes=[];fails=[];vias=[]
 pairs=[('P_R902','2','P_C902','1',.8),('P_C902','1','P_C905','1',.8),('P_C905','1','P_C903','1',.5),('P_C903','1','P_U901','1',.4),('P_U901','1','P_U901','3',.25),('P_U901','5','P_C904','1',.4),('P_C904','1','P_R903','1',.5),('P_R903','1','P_U902','2',.2),('P_U902','2','P_C906','1',.2),('P_R902','1','P_U902','1',.2)]
 def route(a,b,net,width,label,record_failure=True):
  blocked=unary_union([g.buffer(.2+width/2+.002) for n,g,u in copper['B.Cu'] if n!=net or u in quietids]);ga=a.intersection(reference.buffer(-width/2-.002)).difference(blocked.buffer(.000001));gb=b.intersection(reference.buffer(-width/2-.002)).difference(blocked.buffer(.000001));path=None;nodes=0
  if not ga.is_empty and not gb.is_empty:
   start,end=nearest_points(ga,gb);blocked=unary_union([g.buffer(.2+width/2+.002) for n,g,u in copper['B.Cu'] if n!=net or u in quietids]);path,nodes=astar(list(start.coords)[0],list(end.coords)[0],blocked,reference,width,margin=5,step=.1)
  row={'source':label[0],'target':label[1],'net':net,'layer':'B.Cu','width_mm':width,'search_nodes':nodes}
  if path:
   g=LineString(path).buffer(width/2);row.update(path_mm=path,length_mm=LineString(path).length,reference_uncovered_mm2=g.difference(reference).area);routes.append(row);copper['B.Cu'].append((net,g,'new:'+str(len(routes))))
  elif record_failure:fails.append(row)
  return path
 for ref,pin,ideal in [('P_C902','2',[157,171.5]),('P_C905','2',[157,165.9]),('P_U901','2',[147.3,168.7]),('P_C903','2',[146.4,162.75]),('P_C904','2',[137,167.75]),('P_R903','2',[139.85,172.3]),('P_U902','5',[147,172.7]),('P_C906','2',[147.1,174.75])]:
  o=by[ref,pin];assert o['net']=='PWR_AGND'
  forbidden=prep(unary_union([g.buffer(.502) for l in copper for n,g,u in copper[l] if n!='PWR_AGND' or u in quietids]+[shape(polys).buffer(.402) for p in c['objects'] if p['kind']=='PAD' for polys in p['layers'].values()]+[shape(z['polygons']).buffer(.502) for z in c['zones'] if z['keepout'] or z['net']!='PWR_AGND' or z['uuid'] in quietzones]))
  positions=sorted(([ideal[0]+dx*.1,ideal[1]+dy*.1] for dx in range(-20,21) for dy in range(-20,21)),key=lambda p:math.dist(p,ideal));legal=[p for p in positions if not forbidden.intersects(Point(p)) and reference.covers(Point(p).buffer(.35))];path=None
  for pos in legal[:32]:
   path=route(shape(o['layers']['B.Cu']),Point(pos),'PWR_AGND',.2 if ref=='P_U902' else .3,[ref+'.'+pin,'via:'+ref],record_failure=False)
   if path:
    vias.append({'name':ref,'position_mm':pos,'size_mm':.6,'drill_mm':.3,'net':'PWR_AGND'})
    for l in copper:copper[l].append(('PWR_AGND',Point(pos).buffer(.3),'via:'+ref))
    break
  if not path:fails.append({'source':ref+'.'+pin,'reason':'No route to any of first32 legal all-layer via sites in bounded local search','legal_via_sites':len(legal)})
 for ar,ap,br,bp,w in pairs:
  a=by[ar,ap];b=by[br,bp];assert a['net']==b['net'] and 'B.Cu' in a['layers'] and 'B.Cu' in b['layers'];route(shape(a['layers']['B.Cu']),shape(b['layers']['B.Cu']),a['net'],w,[ar+'.'+ap,br+'.'+bp])
 result={'capture_sha256':sha(cp),'planner_sha256':sha(Path(__file__)),'reference_zone_uuids':[plane['main_source_zone_uuid'],plane['new_zone_uuid']],'routes':routes,'new_vias':vias,'failures':fails,'qualified':False};(H/'local-routes.json').write_text(json.dumps(result,indent=2)+'\n');print({'routes':len(routes),'vias':len(vias),'failures':fails})
if __name__=='__main__':run()
