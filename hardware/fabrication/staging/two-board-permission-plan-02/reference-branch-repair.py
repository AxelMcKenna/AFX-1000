import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_permission_routes_v1.py').read_text();exec(s[:s.index('# Reserve all fixed')])
done=json.loads(Path('/private/tmp/permission-routes-v4.json').read_text());cap=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-01/capture.json').read_text())
changes={'E_R119.2 escape':[143.8,133.9],'E_R115 PG pullup AUX supply hop 2':[51.4,135.4]}
for route in done['routes']:
 if route['label'] not in changes and route['label']!='E_R107 PG pullup AUX supply':screen.added.append((route['net'],route['layer'],LineString(route['path_mm'])))
for v in done['extra_vias']:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
for label,end in changes.items():
 r=next(r for r in done['routes'] if r['label']==label)
 if label=='E_R115 PG pullup AUX supply hop 2':r['layer']='In2.Cu'
 net=r['net'];layer=r['layer'];basegeom=list(screen.geometry[layer]);ref={'B.Cu':'In6.Cu','In2.Cu':'In1.Cu','In6.Cu':'In5.Cu'}[layer]
 ground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['layer']==ref and z['net']=='PWR_AGND']);hs=[Point(o['position_mm']).buffer(o['width_mm']/2+.215) for o in cap['objects'] if o['kind']=='PCB_VIA' and o['net']==net];allowed=ground.buffer(.001).union(unary_union(hs))
 screen.geometry[layer].append((None,screen.outline.difference(allowed),.1001));screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
 result=screen.simple(net,layer,r['path_mm'][0],end,50);path=result[1] if result else screen.grid_path(net,layer,r['path_mm'][0],end,budget=120000)
 assert path,(label,'No covered branch')
 r['path_mm']=path;screen.added.append((net,layer,LineString(path)));print('REPAIRED',label,path,flush=True)
 screen.geometry[layer]=basegeom;screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
done['extra_vias']=[v for v in done['extra_vias'] if v['position_mm']!=[42.8,133.1]]
# Fine surface escape search; retain the no-quiet-via restriction.
label='E_R107 PG pullup AUX supply';o=pads['E_R107','2'];net=o['net'];ground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['layer']=='In6.Cu' and z['net']=='PWR_AGND']);holes=unary_union([Point(v['position_mm']).buffer(.515) for v in [*vias,*done['extra_vias']] if v['net']==net]);candidates=[]
for d,xy in sorted((math.dist(o['position_mm'],[x*.05,y*.05]),[x*.05,y*.05]) for x in range(2826,2838) for y in range(2614,2640)):
 if d>7 or not screen.via_legal(net,xy) or any(Point(xy).distance(q)<.6 for q in qfields):continue
 v=dict(ref='E_R107',pin='2',net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
 if not any(inner_free(v,l) for l in ['In2.Cu','In3.Cu','In6.Cu']):continue
 result=screen.simple(net,'B.Cu',o['position_mm'],xy,12)
 if not result:continue
 area=LineString(result[1]).buffer(.1).difference(ground.buffer(.0015).union(holes).union(Point(xy).buffer(.515))).area
 if area>=1e-6:continue
 candidates.append((v,result[1]));print('R107 CANDIDATE',xy,flush=True)
 if len(candidates)>=12:break
# Protect retained In5 signals as well as bottom projections from In6 cuts.
for obj in objects:
 if obj['net']=='PWR_AGND' or not obj['layers'].get('In5.Cu'):continue
 g=routing.shape(obj['layers']['In5.Cu'])
 if obj['kind']=='PCB_TRACK' and obj['net'] in ownholes:g=g.difference(ownholes[obj['net']])
 if not g.is_empty:screen.geometry['In6.Cu'].append((None,g,.41))
screen.trees['In6.Cu']=STRtree([g for n,g,d in screen.geometry['In6.Cu']])
for v,path in candidates:
 targets=[dict(t,ref='E_U29',pin='8') for t in [*vias,*done['extra_vias']] if t['net']==net]
 result=connect(v,targets,label)
 if not result:continue
 # connect adds legs/new vias to the scratch arrays; copy them into this plan.
 done['routes']=[r for r in done['routes'] if r['label']!=label]
 done['routes'].append(dict(net=net,layer='B.Cu',width_mm=.2,path_mm=path,label=label+' surface transition'))
 done['routes'].extend(new);done['extra_vias'].extend(extra);done['extra_vias'].append(v)
 print('R107 CONNECTED',v['position_mm'],flush=True);break
else:raise AssertionError('No covered R107 supply transition')
renames={'Buffered AUX valid to startup chain':'Native AUX valid to U42 input','Buffered AUX valid to U24':'Native AUX valid to U24','NF AUX valid to Schmitt receiver':'Buffered NF AUX valid to header'}
for row in [*done['routes'],*done['joins']]:
 for old,new in renames.items():row['label']=row['label'].replace(old,new)
Path('/private/tmp/permission-routes-v5.json').write_text(json.dumps(done,indent=2)+'\n')
print('RESULT',len(done['joins']),len(done['routes']),len(done['extra_vias']),len(done['deferred']),flush=True)
