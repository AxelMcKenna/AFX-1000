import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_startup_completion_routes_v8.py').read_text();exec(s[:s.index('# Restore every')])
done=json.loads(Path('/private/tmp/startup-completion-routes-v10.json').read_text());cap=json.loads((STAGING/'two-board-power-routing-inputs-2267-startup-completion-05/capture.json').read_text())
labels=['PG3 Schmitt output to U30 hop 2','Restore U34 PG2 Schmitt input hop 1','FOLLOW2 to digital eFuse enable','ANA PG1 to Schmitt receiver hop 1','Analog enable to eFuse hop 1']
original={r['label']:r for r in done['routes'] if r['label'] in labels}
for r in done['routes']:
 if r['label'] not in labels:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in done['extra_vias']:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
replacements={}
for label in labels:
 r=original[label];net=r['net'];layer=r['layer'];basegeom=list(screen.geometry[layer])
 if layer=='In6.Cu':
  for route in routes:
   if route['layer']!='B.Cu' or route['net']=='PWR_AGND':continue
   g=LineString(route['path_mm']).buffer(route['width_mm']/2)
   if route['net'] in newholes:g=g.difference(unary_union(newholes[route['net']]))
   if not g.is_empty:screen.geometry[layer].append((None,g,.41))
 else:
  ground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['layer']=='In1.Cu' and z['net']=='PWR_AGND'])
  holes=unary_union([Point(o['position_mm']).buffer(o['width_mm']/2+.215) for o in cap['objects'] if o['kind']=='PCB_VIA' and o['net']==net])
  allowed=ground.buffer(.001).union(holes)
  screen.geometry[layer].append((None,screen.outline.difference(allowed),.1001))
 screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
 result=screen.simple(net,layer,r['path_mm'][0],r['path_mm'][-1],200)
 path=result[1] if result else screen.grid_path(net,layer,r['path_mm'][0],r['path_mm'][-1],budget=90000)
 if path:
  replacements[label]=dict(r,path_mm=path);print('REPLACED',label,path,flush=True)
 else:print('FAILED',label,flush=True)
 screen.added.append((net,layer,LineString(path or r['path_mm'])))
 screen.geometry[layer]=basegeom;screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
for i,r in enumerate(done['routes']):
 if r['label'] in replacements:done['routes'][i]=replacements[r['label']]
Path('/private/tmp/startup-completion-routes-v11.json').write_text(json.dumps(done,indent=2)+'\n')
print('RESULT',len(replacements),'of',len(labels),flush=True)
