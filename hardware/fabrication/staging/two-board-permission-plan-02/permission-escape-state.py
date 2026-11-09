import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_permission_routes_v1.py').read_text();exec(s[:s.index('# Reserve all fixed')])
done=json.loads(Path('/private/tmp/permission-routes-v2.json').read_text());key=('E_U29','1');label='ALL_RAILS_ALLOW to U29';net=pads[key]['net']
new=[copy.deepcopy(r) for r in done['routes'] if r['label']!='E_U29.1 escape'];extra=[copy.deepcopy(v) for v in done['extra_vias'] if (v['ref'],v['pin'])!=key];joins=copy.deepcopy(done['joins']);deferred=copy.deepcopy(done['deferred'])
for r in new:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in extra:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
 if (v['ref'],v['pin']) not in cellvias:cellvias[v['ref'],v['pin']]=v
# A localized In4 path is acceptable only with In5 ground reference and
# preserved projections under every old/new In3 control trace.
for obj in objects:
 if obj['net']=='PWR_AGND':continue
 if obj['layers'].get('In3.Cu'):
  g=routing.shape(obj['layers']['In3.Cu'])
  if obj['kind']=='PCB_TRACK' and obj['net'] in ownholes:g=g.difference(ownholes[obj['net']])
  if not g.is_empty:screen.geometry['In4.Cu'].append((None,g,.41))
 if obj['layers'].get('In5.Cu'):screen.geometry['In4.Cu'].append((obj['net'],routing.shape(obj['layers']['In5.Cu']),.41))
for route in new:
 if route['layer']!='In3.Cu' or route['net']=='PWR_AGND':continue
 g=LineString(route['path_mm']).buffer(.1)
 hs=[Point(v['position_mm']).buffer(.515) for v in [*vias,*extra] if v['net']==route['net']]
 g=g.difference(unary_union(hs))
 if not g.is_empty:screen.geometry['In4.Cu'].append((None,g,.41))
screen.trees['In4.Cu']=STRtree([g for n,g,d in screen.geometry['In4.Cu']])
o=pads[key];candidates=[]
for xy in [[141.5,141.5],[142.,141.5],[142.,142.],[141.5,142.5],[142.5,142.5],[143.,143.],[143.5,143.5],[144.,144.],[141.5,140.5]]:
 if not screen.via_legal(net,xy):continue
 v=dict(ref=key[0],pin=key[1],net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
 ls=[l for l in ['In2.Cu','In3.Cu','In6.Cu'] if inner_free(v,l)];path=screen.simple(net,'B.Cu',o['position_mm'],xy,15)
 print('ESCAPE OPTION',xy,ls,bool(path),flush=True)
 if path and ls:candidates.append((v,path[1]))
for v,path in candidates:
 targets=[dict(vv,ref='E_U42',pin='3') for vv in [*vias,*extra] if vv['net']==net]
 for route in new:
  if route['net']!=net:continue
  g=LineString(route['path_mm']);pt=g.interpolate(g.project(Point(v['position_mm'])))
  for xy in [list(pt.coords[0]),*route['path_mm']]:targets.append(dict(net=net,ref='E_U42',pin='3',position_mm=xy,layers={route['layer']:True}))
 result=connect(v,targets,label,layers=('In4.Cu','In2.Cu','In3.Cu','In6.Cu'))
 if result:
  viaadd(v);add(net,'B.Cu',path,'E_U29.1 escape');joins.append(result);deferred=[r for r in deferred if r['label']!=label];print('COMPLETED',v['position_mm'],flush=True);break
else:
 print('NO COMPLETE ESCAPE',flush=True);raise SystemExit(1)
Path('/private/tmp/permission-routes-v3.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2)+'\n')
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
