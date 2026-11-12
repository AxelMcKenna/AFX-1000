"""Bounded front-surface analog input routes; immutable I2C-r4 is the base."""
import json,math,uuid,hashlib
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
import hardware.fabrication.route_nf_surface as surface
R=Path(__file__).resolve().parent;I=R.parent/'i2c_routing';surface.SIGNAL_LAYERS=('F.Cu',)
c=json.loads((I/'capture-after-r4/capture.json').read_text());screen=surface.Screen(c);objects={o['uuid']:o for o in c['objects']};routes=[];blocked=[]
nets=sorted(n for n in c['open_nets']if n.startswith('/A_INPUT/'));nets.sort(key=lambda n:(not('BUF_IN'in n),not('BUF_OUT'in n),n))
for net in nets:
 gs=[list(v)for v in c['all_groups'].values()if objects[v[0]]['net']==net]
 while len(gs)>1:
  choices=[]
  for i,g in enumerate(gs):
   for j,h in enumerate(gs[i+1:],i+1):
    for u in g:
     if objects[u]['kind']!='PAD'or not objects[u]['layers'].get('F.Cu'):continue
     for v in h:
      if objects[v]['kind']!='PAD'or not objects[v]['layers'].get('F.Cu'):continue
      p,q=objects[u]['position_mm'],objects[v]['position_mm'];choices.append((math.dist(p,q),i,j,u,v,p,q))
  chosen=None
  for dist,i,j,u,v,p,q in sorted(choices):
   paths=[path for path in surface.candidate_paths(p,q)if screen.legal(net,'F.Cu',path)]
   if paths:chosen=(min(paths,key=lambda p:LineString(p).length),i,j,u,v,dist);break
  if chosen is None:
   for dist,i,j,u,v,p,q in sorted(choices)[:6]:
    path=screen.grid_path(net,'F.Cu',p,q,budget=35000)
    if path is not None and LineString(path).length<=2*dist+5:chosen=(path,i,j,u,v,dist);break
  if chosen is None:blocked.append({'net':net,'remaining_groups':gs});break
  path,i,j,u,v,dist=chosen;line=LineString(path);r={'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':path,'length_mm':line.length,'straight_distance_mm':dist,'from_pad':u,'to_pad':v};routes.append(r);screen.added.append((net,'F.Cu',line));gs[i]+=gs[j];gs.pop(j);print(net,round(line.length,3),flush=True)
p=I/'native-r4/signal_main.kicad_pcb';t=read_sexpr(p.read_text())
for k,r in enumerate(routes):
 for j,(p,q)in enumerate(zip(r['path_mm'],r['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),r['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-r1-{k}-{j}'))]])
o=R/'candidate-r1';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n')
paths=[Path(__file__),I/'native-r4/signal_main.kicad_pcb',I/'capture-after-r4/capture.json']
report={'scope':'Front-surface input net planning screen only; analog/reference/native review mandatory','source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'routes':routes,'blocked':blocked,'expected_opens':246-len(routes),'no_added_vias_or_zones':True}
(o/'routing.json').write_text(json.dumps(report,indent=2)+'\n');print('routes',len(routes),'blocked',len(blocked))
