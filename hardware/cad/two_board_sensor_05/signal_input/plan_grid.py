"""Actual-side input routing; B-side reference additions require separate stage."""
import json,math,uuid,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
import hardware.fabrication.route_nf_surface as surface
R=Path(__file__).resolve().parent;I=R.parent/'i2c_routing';surface.SIGNAL_LAYERS=('F.Cu','B.Cu')
c=json.loads((I/'capture-after-r4/capture.json').read_text());screen=surface.Screen(c);obj={o['uuid']:o for o in c['objects']};routes=[];vias=[];blocked=[]
obstacles=[]
for o in c['objects']:
 for ps in o['layers'].values():
  if ps:obstacles.append((o,surface.shape(ps)))
tree=STRtree([g for _,g in obstacles]);cache={}
def vialegal(p,net):
 pt=Point(p)
 for ix in tree.query(pt.buffer(.52)):
  o,g=obstacles[int(ix)]
  if o['net']==net and o['kind']=='PCB_TRACK':continue
  if pt.distance(g)<.51:return False
 if any(o['kind']=='PCB_VIA'and math.dist(p,o['position_mm'])<.86 for o in c['objects']):return False
 if any(math.dist(p,v['at'])<.86 for v in vias):return False
 if any(n!=net and pt.distance(g)<.51 for n,l,g in screen.added):return False
 return True
def options(g,net):
 out=[{'at':v['at'],'uid':v['from_pad'],'spur':None}for v in vias if v['net']==net and v['from_pad']in g]
 for uid in g:
  o=obj[uid]
  if o['kind']not in ['PAD','PCB_VIA']:continue
  if o['layers'].get('B.Cu'):out.append({'at':o['position_mm'],'uid':uid,'spur':None})
  elif o['layers'].get('F.Cu'):
   p=o['position_mm']
   if uid not in cache:
    pts=sorted(([round(p[0]+i*.2,6),round(p[1]+j*.2,6)]for i in range(-15,16)for j in range(-15,16)),key=lambda q:math.dist(p,q));valid=[]
    for q in pts:
     if math.dist(p,q)>3.5:break
     if vialegal(q,net)and screen.legal(net,'F.Cu',[p,q]):valid.append(q)
     if len(valid)==5:break
    cache[uid]=valid
   for q in cache[uid]:
    if vialegal(q,net)and screen.legal(net,'F.Cu',[p,q]):out.append({'at':q,'uid':uid,'spur':[p,q]})
 return out
nets=sorted(n for n in c['open_nets']if n.startswith('/A_INPUT/'));nets.sort(key=lambda n:(not('BUF_IN'in n),not('BUF_OUT'in n),n))
for net in nets:
 gs=[list(v)for v in c['all_groups'].values()if obj[v[0]]['net']==net]
 while len(gs)>1:
  choices=[]
  for i,g in enumerate(gs):
   for j,h in enumerate(gs[i+1:],i+1):
    for u in g:
     if obj[u]['kind']!='PAD'or not obj[u]['layers'].get('F.Cu'):continue
     for v in h:
      if obj[v]['kind']!='PAD'or not obj[v]['layers'].get('F.Cu'):continue
      p,q=obj[u]['position_mm'],obj[v]['position_mm']
      for path in surface.candidate_paths(p,q):
       if screen.legal(net,'F.Cu',path):choices.append((LineString(path).length,i,j,'F.Cu',path,[]));break
  # Compare short inner paths against available surface detours; via penalty favours surface.
  for i,g in enumerate(gs):
   oo=options(g,net)
   for j,h in enumerate(gs[i+1:],i+1):
    pairs=sorted(((math.dist(o['at'],v['at']),o,v)for o in oo for v in options(h,net)),key=lambda x:x[0])
    for dist,o,v in pairs[:18]:
     spurs=[x for x in [o,v]if x['spur']]
     if len(spurs)==2 and math.dist(o['at'],v['at'])<.86:continue
     for path in surface.candidate_paths(o['at'],v['at']):
      if screen.legal(net,'B.Cu',path):
       cost=LineString(path).length+sum(LineString(x['spur']).length+1.5 for x in spurs);choices.append((cost,i,j,'B.Cu',path,spurs));break
  if not choices:
   trial=[]
   for i,g in enumerate(gs):
    for j,h in enumerate(gs[i+1:],i+1):
     for layer in ['F.Cu','B.Cu']:
      left=options(g,net)if layer=='B.Cu'else[{'at':obj[u]['position_mm'],'uid':u,'spur':None}for u in g if obj[u]['kind']=='PAD'and obj[u]['layers'].get(layer)]
      right=options(h,net)if layer=='B.Cu'else[{'at':obj[u]['position_mm'],'uid':u,'spur':None}for u in h if obj[u]['kind']=='PAD'and obj[u]['layers'].get(layer)]
      for o in left:
       for v in right:trial.append((math.dist(o['at'],v['at']),i,j,layer,o,v))
   for dist,i,j,layer,o,v in sorted(trial,key=lambda x:x[0])[:24]:
    spurs=[x for x in [o,v]if x['spur']]
    if len(spurs)==2 and math.dist(o['at'],v['at'])<.86:continue
    path=screen.grid_path(net,layer,o['at'],v['at'],budget=60000)
    if path is not None and LineString(path).length<=2*dist+5:
     cost=LineString(path).length+sum(LineString(x['spur']).length+1.5 for x in spurs);choices.append((cost,i,j,layer,path,spurs));break
  if not choices:blocked.append({'net':net,'remaining_groups':gs});break
  cost,i,j,layer,path,spurs=min(choices,key=lambda x:x[0]);job=len(routes)
  for sp in spurs:
   if not any(v['at']==sp['at']and v['net']==net for v in vias):
    vias.append({'net':net,'at':sp['at'],'from_pad':sp['uid'],'size_mm':.6,'drill_mm':.3})
    for l in surface.SIGNAL_LAYERS:screen.added.append((net,l,Point(sp['at']).buffer(.2)))
   routes.append({'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':sp['spur'],'role':'escape','join':job});screen.added.append((net,'F.Cu',LineString(sp['spur'])))
  routes.append({'net':net,'layer':layer,'width_mm':.2,'path_mm':path,'role':'join','join':job});screen.added.append((net,layer,LineString(path)));gs[i]+=gs[j];gs.pop(j);print(net,layer,round(cost,3),flush=True)
p=I/'native-r4/signal_main.kicad_pcb';t=read_sexpr(p.read_text())
for k,r in enumerate(routes):
 for j,(p,q)in enumerate(zip(r['path_mm'],r['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),r['layer']],[a('net'),r['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-r4-{k}-{j}'))]])
for k,v in enumerate(vias):t.append([a('via'),[a('at'),*v['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),v['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-r4-via-{k}'))]])
o=R/'candidate-r4';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');paths=[Path(__file__),I/'native-r4/signal_main.kicad_pcb',I/'capture-after-r4/capture.json'];joins=sum(x['role']=='join'for x in routes)
(o/'routing.json').write_text(json.dumps({'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'routes':routes,'vias':vias,'blocked':blocked,'expected_opens':246-joins,'new_zones':False,'scope':'Input stage planning candidate; native and analog/reference checks pending'},indent=2)+'\n');print('joins',joins,'vias',len(vias),'blocked',len(blocked))
