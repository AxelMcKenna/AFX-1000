import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_permission_routes_v1.py').read_text();exec(s[:s.index('# Reserve all fixed')])
done=json.loads(Path('/private/tmp/permission-routes-v1.json').read_text());new=copy.deepcopy(done['routes']);extra=copy.deepcopy(done['extra_vias']);joins=copy.deepcopy(done['joins']);deferred=copy.deepcopy(done['deferred'])
for r in new:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in extra:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
 if (v['ref'],v['pin']) not in cellvias:cellvias[v['ref'],v['pin']]=v
for source,target,label in [(('E_U29','1'),('E_U42','3'),'ALL_RAILS_ALLOW to U29'),(('E_U31','7'),('E_U14','1'),'Analog follower to eFuse')]:
 a=cellvias[source];targets=[]
 for route in new:
  if route['net']!=a['net']:continue
  g=LineString(route['path_mm']);nearest=g.interpolate(g.project(Point(a['position_mm'])))
  for xy in [list(nearest.coords[0]),*route['path_mm']]:
   if math.dist(xy,a['position_mm'])<1:continue
   # Exclude the source's own isolated escape.
   if route.get('label')==f'{source[0]}.{source[1]} escape':continue
   targets.append(dict(net=a['net'],ref=target[0],pin=target[1],position_mm=xy,layers={route['layer']:True}))
 result=connect(a,targets,label)
 if result:joins.append(result);deferred=[r for r in deferred if r['label']!=label]
# R107 can branch on the bottom to the existing source-backed AUX group.
key=('E_R107','2');o=pads[key];net=o['net'];gid=pads['E_U29','8']['group'];targets=[]
for t in objects:
 if t['group']!=gid or not t['layers'].get('B.Cu'):continue
 if t['kind']=='PCB_TRACK':
  g=LineString([t['position_mm'],t['end_mm']]);pt=g.interpolate(g.project(Point(o['position_mm'])));targets.extend([list(pt.coords[0]),t['position_mm'],t['end_mm']])
 else:targets.append(t['position_mm'])
# The completed supply joins already connect these vias to U29's source group.
for v in [*vias,*extra]:
 if v['net']==net:targets.append(v['position_mm'])
label='E_R107 PG pullup AUX supply';candidates=[]
for xy in targets:
 result=screen.simple(net,'B.Cu',o['position_mm'],xy,35)
 if result:candidates.append(result)
if candidates:
 result=min(candidates,key=lambda r:r[0]);add(net,'B.Cu',result[1],label);joins.append(dict(label=label,source=list(key),target_uuid=pads['E_U29','8']['uuid'],target=['E_U29','8'],net=net));deferred=[r for r in deferred if r['label']!=label];print('SURFACE JOIN',label,result[1],flush=True)
else:print('NO SURFACE JOIN',label,flush=True)
Path('/private/tmp/permission-routes-v2.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2)+'\n')
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
