import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_permission_routes_v1.py').read_text();exec(s[:s.index('# Reserve all fixed')])
done=json.loads(Path('/private/tmp/permission-routes-v3.json').read_text());cap=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-01/capture.json').read_text())
labels=['E_U31.8 escape','E_R119.2 escape','E_R107 PG pullup AUX supply','ANA PG2 to Schmitt receiver hop 2','E_R95 PG pullup AUX supply hop 1','E_R115 PG pullup AUX supply hop 2','Buffered global master to NF header hop 1']
original={r['label']:r for r in done['routes'] if r['label'] in labels}
retained=[r for r in done['routes'] if r['label'] not in labels]
for r in retained:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in done['extra_vias']:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
replacements={}
for label in labels:
 r=original[label];net=r['net'];layer=r['layer'];basegeom=list(screen.geometry[layer])
 if layer=='In6.Cu':
  for obj in objects:
   if obj['net']=='PWR_AGND' or not obj['layers'].get('In5.Cu'):continue
   g=routing.shape(obj['layers']['In5.Cu'])
   if obj['kind']=='PCB_TRACK' and obj['net'] in ownholes:g=g.difference(ownholes[obj['net']])
   if not g.is_empty:screen.geometry[layer].append((None,g,.41))
  for route in [*routes,*retained,*replacements.values()]:
   if route['layer']!='B.Cu' or route['net']=='PWR_AGND':continue
   g=LineString(route['path_mm']).buffer(route['width_mm']/2)
   hs=[Point(v['position_mm']).buffer(.515) for v in [*vias,*done['extra_vias']] if v['net']==route['net']]
   g=g.difference(unary_union(hs))
   if not g.is_empty:screen.geometry[layer].append((None,g,.41))
 else:
  ref='In1.Cu' if layer=='F.Cu' else 'In6.Cu'
  ground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['layer']==ref and z['net']=='PWR_AGND'])
  hs=[Point(o['position_mm']).buffer(o['width_mm']/2+.215) for o in cap['objects'] if o['kind']=='PCB_VIA' and o['net']==net]
  allowed=ground.buffer(.001).union(unary_union(hs))
  screen.geometry[layer].append((None,screen.outline.difference(allowed),.1001))
 screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
 result=screen.simple(net,layer,r['path_mm'][0],r['path_mm'][-1],240)
 path=result[1] if result else screen.grid_path(net,layer,r['path_mm'][0],r['path_mm'][-1],budget=120000)
 if path:replacements[label]=dict(r,path_mm=path);print('REPLACED',label,path,flush=True)
 else:print('FAILED',label,flush=True)
 screen.added.append((net,layer,LineString(path or r['path_mm'])))
 screen.geometry[layer]=basegeom;screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
for i,r in enumerate(done['routes']):
 if r['label'] in replacements:done['routes'][i]=replacements[r['label']]
# Join the ground region above the analog control traces to its existing
# main In5 return. Avoid every distinct same-net branch and quiet-return via.
main=pads['P_C103','2']['group'];qvias={v['uuid'] for q in quiet for v in q['control_vias']+q['extra_quiet_vias']}
oldground=unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['net']=='PWR_AGND' and z['layer']=='In6.Cu']);newground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['net']=='PWR_AGND' and z['layer']=='In6.Cu']);lost=oldground.difference(newground)
choices=[]
for x in [i*.25 for i in range(160,220)]:
 for y in [i*.25 for i in range(432,472)]:
  xy=[x,y];pt=Point(xy)
  if not lost.covers(pt) or not screen.via_legal('PWR_AGND',xy) or any(pt.distance(q)<.6 for q in qfields):continue
  if any(o['net']=='PWR_AGND' and (o['group']!=main or o['uuid'] in qvias) and any(pt.distance(routing.shape(ps))<.51 for ps in o['layers'].values() if ps) for o in objects):continue
  # Direct existing main-ground contact is available on In5.
  if not any(z['net']=='PWR_AGND' and z['layer']=='In5.Cu' and routing.shape(z['polygons']).covers(pt) for z in c['zones']):continue
  choices.append((math.dist(xy,[43.6,110.5]),xy))
if choices:
 xy=min(choices)[1];done['extra_vias'].append(dict(ref='MAIN_REFERENCE',pin='R95',net='PWR_AGND',position_mm=xy,size_mm=.6,drill_mm=.3,role='main_reference_stitch'));print('GROUND STITCH',xy,flush=True)
else:print('NO GROUND STITCH',flush=True)
Path('/private/tmp/permission-routes-v4.json').write_text(json.dumps(done,indent=2)+'\n')
print('RESULT',len(replacements),'of',len(labels),'ground stitches',bool(choices),flush=True)
