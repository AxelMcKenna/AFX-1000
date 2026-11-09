import sys,copy,json,math
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
plan=Path('hardware/fabrication/staging/two-board-permission-plan-03/plan.json')
done=json.loads(plan.read_text());retired='292630b4-8a36-50b7-ba5c-702909f64dda';done['retired_objects']=[retired]
s=Path('/private/tmp/plan_permission_routes_v1.py').read_text();s=s[:s.index('# Reserve all fixed')].replace("p=json.loads(Path('/private/tmp/permission-cells-v2.json').read_text())","p=copy.deepcopy(done)")
exec(s)
cap=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-03/capture.json').read_text())
label='E_R107 PG pullup AUX supply'
done['routes']=[r for r in done['routes'] if not r.get('label','').startswith(label)]
done['extra_vias']=[v for v in done['extra_vias'] if not(v.get('ref')=='E_R107' and v.get('pin')=='2')]
for r in done['routes']:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in done['extra_vias']:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
# Restore the existing ANA_PG0 connection while clearing the projection of
# the R95 supply escape, including the copper at its pad end.
o=next(o for o in c['objects'] if o['uuid']==retired);net=o['net'];layer='In6.Cu';geom=list(screen.geometry[layer])
for r in done['routes']:
 if r['layer']!='B.Cu' or r['net']=='PWR_AGND':continue
 g=LineString(r['path_mm']).buffer(r['width_mm']/2)
 hs=[Point(v['position_mm']).buffer(.515) for v in [*vias,*done['extra_vias']] if v['net']==r['net']]
 g=g.difference(unary_union(hs))
 if not g.is_empty:screen.geometry[layer].append((None,g,.41))
ground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['layer']=='In5.Cu' and z['net']=='PWR_AGND'])
holes=ownholes.get(net,Point().buffer(0));allowed=ground.buffer(.001).union(holes)
screen.geometry[layer].append((None,screen.outline.difference(allowed),.1001));screen.trees[layer]=STRtree([g for n,g,d in screen.geometry[layer]])
r=screen.simple(net,layer,o['position_mm'],o['end_mm'],35);path=r[1] if r else screen.grid_path(net,layer,o['position_mm'],o['end_mm'],budget=120000)
assert path,'ANA_PG0 detour not found'
r=dict(net=net,layer=layer,width_mm=o['width_mm'],path_mm=path,label='ANA_PG0 restored around R95 supply projection');done['routes'].append(r);screen.added.append((net,layer,LineString(path)));print('ANA_PG0 REPLACEMENT',path,flush=True)
screen.geometry[layer]=geom;screen.trees[layer]=STRtree([g for n,g,d in geom])
# Reuse the existing AUX via at 141.5,136.5; no new intermediate via needed.
o=pads['E_R107','2'];net=o['net'];target=next(o for o in objects if o['kind']=='PCB_VIA' and o['net']==net and o['position_mm']==[141.5,136.5]);cent=o['position_mm']
source=routing.shape(next(z['polygons'] for z in c['zones'] if z['net']=='PWR_5V_DIG_SRC' and z['layer']=='In4.Cu'))
ground=unary_union([routing.shape(z['polygons']) for z in cap['zones'] if z['layer']=='In6.Cu' and z['net']=='PWR_AGND']);holes=ownholes.get(net,Point().buffer(0))
choices=[]
for ix in range(2800,2841):
 for iy in range(2580,2651):
  xy=[round(ix*.05,4),round(iy*.05,4)];pt=Point(xy)
  if not screen.via_legal(net,xy) or any(pt.distance(q)<.6 for q in qfields):continue
  surface=screen.simple(net,'B.Cu',cent,xy,12)
  if not surface:continue
  if LineString(surface[1]).buffer(.1).difference(ground.buffer(.0015).union(holes).union(pt.buffer(.515))).area>=1e-6:continue
  choices.append((pt.distance(source)<.515,math.dist(cent,xy),xy,surface[1],pt.distance(source)))
print('R107 ESCAPES',len(choices),flush=True)
for cuts,d,xy,surface,dsource in sorted(choices):
 r=screen.simple(net,'In2.Cu',xy,target['position_mm'],30);path=r[1] if r else screen.grid_path(net,'In2.Cu',xy,target['position_mm'],budget=40000)
 if not path:continue
 done['extra_vias'].append(dict(ref='E_R107',pin='2',net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
 done['routes'].extend([dict(net=net,layer='B.Cu',width_mm=.2,path_mm=surface,label=label+' surface transition'),dict(net=net,layer='In2.Cu',width_mm=.2,path_mm=path,label=label+' to existing AUX via')])
 print('R107 REPAIRED',xy,'source gap',dsource,'surface',surface,'inner',path,flush=True);break
else:
 print('SOURCE_CLEAR_CANDIDATES',sum(not x[0] for x in choices),flush=True)
 raise AssertionError('No R107 escape and In2 join')
Path('/private/tmp/permission-routes-v6.json').write_text(json.dumps(done,indent=2)+'\n')
