import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_startup_completion_routes_v8.py').read_text();exec(s[:s.index('# Restore every')])
done=json.loads(Path('/private/tmp/startup-completion-routes-v8.json').read_text())
new=copy.deepcopy(done['routes']);extra=copy.deepcopy(done['extra_vias']);joins=copy.deepcopy(done['joins']);deferred=copy.deepcopy(done['deferred'])
for r in new:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in extra:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
 if (v['ref'],v['pin']) not in cellvias:cellvias[v['ref'],v['pin']]=v
label='FOLLOW3 to digital eFuse enable';key=('E_U34','7');witness=('E_R120','1');o=pads[witness]
for xy in [[147.5,135.5],[147.5,136.5],[146,136],[145.5,136],[145.5,134],[144,133.5],[144,135.5],[148,136.5]]:
 if not screen.via_legal(o['net'],xy) or any(Point(xy).distance(q)<.6 for q in qfields):continue
 path=screen.simple(o['net'],'B.Cu',o['position_mm'],xy,25)
 if not path:continue
 v=dict(ref=witness[0],pin=witness[1],net=o['net'],position_mm=xy,size_mm=.6,drill_mm=.3)
 print('TRY FOLLOW3',xy,flush=True)
 r=connect(cellvias[key],[v],label)
 if r:
  viaadd(v);add(o['net'],'B.Cu',path[1],label+' surface transition');r['target_uuid']=o['uuid'];r['target']=list(witness);joins.append(r);deferred=[d for d in deferred if d['label']!=label];break
# Attach the pulldown to an already connected segment of the analog enable
# route, rather than forcing it to the crowded final eFuse via.
label='Analog enable pulldown signal';key=('E_R96','1');a=cellvias[key];targets=[]
for route in new:
 if route['label'].startswith('Analog enable to eFuse') and route['net']==a['net']:
  g=LineString(route['path_mm']);point=g.interpolate(g.project(Point(a['position_mm'])))
  for xy in [list(point.coords[0]),*route['path_mm']]:targets.append(dict(net=a['net'],ref='E_U13',pin='1',position_mm=xy,layers={route['layer']:True}))
r=connect(a,targets,label)
if r:joins.append(r);deferred=[d for d in deferred if d['label']!=label]
Path('/private/tmp/startup-completion-routes-v9.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2)+'\n')
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
