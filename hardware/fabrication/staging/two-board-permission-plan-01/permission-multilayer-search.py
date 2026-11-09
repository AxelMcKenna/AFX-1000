exec(open('/private/tmp/finish_permission_allow_v3.py').read().split('o=pads[key];candidates=[]')[0])
from permission_multilayer import search
xy=[141.5,141.5];v=dict(ref='E_U29',pin='1',net=net,position_mm=xy,size_mm=.6,drill_mm=.3);assert screen.via_legal(net,xy)
escape=screen.simple(net,'B.Cu',pads[key]['position_mm'],xy,15);assert escape
targets=[]
for vv in [*vias,*extra]:
 if vv['net']==net:targets.append(dict(vv,layers=c['copper_layers']))
for route in new:
 if route['net']!=net:continue
 g=LineString(route['path_mm'])
 for d in range(math.ceil(g.length)+1):targets.append(dict(position_mm=list(g.interpolate(min(d,g.length)).coords[0]),layers=[route['layer']]))
result=search(screen,net,xy,targets,qfields);assert result,'No bounded multilayer path'
legs,points=result
viaadd(v);add(net,'B.Cu',escape[1],'E_U29.1 escape')
for pt in points:viaadd(dict(v,position_mm=list(pt)))
for i,(layer,path) in enumerate(legs):add(net,layer,path,label+f' multilayer {i+1}')
joins.append(dict(label=label,source=['E_U29','1'],target_uuid=None,target=['E_U42','3'],net=net));deferred=[r for r in deferred if r['label']!=label]
Path('/private/tmp/permission-routes-v3.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2)+'\n')
print('RESULT',len(joins),len(new),len(extra),len(deferred),'new transition vias',points,flush=True)
