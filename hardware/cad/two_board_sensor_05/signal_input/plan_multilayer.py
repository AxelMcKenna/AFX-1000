"""Actual-pad-side bounded input routing, with explicit via escape geometry."""
import json,math,uuid,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
import hardware.fabrication.route_nf_surface as S
R=Path(__file__).resolve().parent;I=R.parent/'i2c_routing';S.SIGNAL_LAYERS=('F.Cu','B.Cu','In3.Cu')
c=json.loads((I/'capture-after-r4/capture.json').read_text());screen=S.Screen(c);obj={o['uuid']:o for o in c['objects']};routes=[];vias=[];blocked=[];cache={}
obs=[(o,S.shape(ps))for o in c['objects']for ps in o['layers'].values()if ps];tree=STRtree([g for _,g in obs])
def vialegal(p,net):
 pt=Point(p)
 for ix in tree.query(pt.buffer(.52)):
  o,g=obs[int(ix)]
  if o['net']==net and o['kind']=='PCB_TRACK':continue
  if pt.distance(g)<.51:return False
 if any(o['kind']=='PCB_VIA'and math.dist(p,o['position_mm'])<.86 for o in c['objects']):return False
 if any(math.dist(p,v['at'])<.86 for v in vias):return False
 return not any(n!=net and pt.distance(g)<.51 for n,l,g in screen.added)
def options(g,net,layer):
 out=[{'at':v['at'],'uid':v['from_pad'],'spur':None}for v in vias if v['net']==net and v['from_pad']in g]
 for u in g:
  o=obj[u]
  if o['kind']not in ['PAD','PCB_VIA']:continue
  if o['layers'].get(layer):out.append({'at':o['position_mm'],'uid':u,'spur':None});continue
  sides=[l for l in ['F.Cu','B.Cu']if o['layers'].get(l)]
  for side in sides:
   p=o['position_mm'];key=(u,side)
   if key not in cache:
    valid=[];pts=sorted(([round(p[0]+i*.2,6),round(p[1]+j*.2,6)]for i in range(-15,16)for j in range(-15,16)),key=lambda q:math.dist(p,q))
    for q in pts:
     if math.dist(p,q)>3.5:break
     if not vialegal(q,net):continue
     paths=[x for x in S.candidate_paths(p,q)if LineString(x).length<4.5 and screen.legal(net,side,x)]
     if paths:valid.append((q,min(paths,key=lambda x:LineString(x).length)))
     if len(valid)==6:break
    cache[key]=valid
   for q,path in cache[key]:
    if vialegal(q,net)and screen.legal(net,side,path):out.append({'at':q,'uid':u,'spur':path,'side':side})
 return out
nets=sorted(n for n in c['open_nets']if n.startswith('/A_INPUT/'));nets.sort(key=lambda n:(not('BUF_IN'in n),not('BUF_OUT'in n),n))
for net in nets:
 gs=[list(v)for v in c['all_groups'].values()if obj[v[0]]['net']==net]
 while len(gs)>1:
  opts={(i,l):options(g,net,l)for i,g in enumerate(gs)for l in S.SIGNAL_LAYERS};choices=[];trials=[]
  for i in range(len(gs)):
   for j in range(i+1,len(gs)):
    for layer in S.SIGNAL_LAYERS:
     pairs=sorted(((math.dist(o['at'],v['at']),o,v)for o in opts[i,layer]for v in opts[j,layer]),key=lambda x:x[0])
     for dist,o,v in pairs[:12]:
      spurs=[x for x in [o,v]if x['spur']]
      if len(spurs)==2 and dist<.86:continue
      trials.append((dist,i,j,layer,o,v,spurs))
      for path in S.candidate_paths(o['at'],v['at']):
       if LineString(path).length>2*dist+5:continue
       if screen.legal(net,layer,path):
        cost=LineString(path).length+sum(LineString(x['spur']).length+2 for x in spurs);choices.append((cost,i,j,layer,path,spurs));break
  if not choices:
   for dist,i,j,layer,o,v,spurs in sorted(trials,key=lambda x:x[0])[:24]:
    path=screen.grid_path(net,layer,o['at'],v['at'],budget=60000)
    if path is not None and LineString(path).length<2*dist+5:choices.append((LineString(path).length+sum(LineString(x['spur']).length+2 for x in spurs),i,j,layer,path,spurs));break
  if not choices:blocked.append({'net':net,'remaining_groups':gs});break
  cost,i,j,layer,path,spurs=min(choices,key=lambda x:x[0]);job=sum(r['role']=='join'for r in routes)
  for sp in spurs:
   vias.append({'net':net,'at':sp['at'],'from_pad':sp['uid'],'size_mm':.6,'drill_mm':.3})
   for l in S.SIGNAL_LAYERS:screen.added.append((net,l,Point(sp['at']).buffer(.2)))
   routes.append({'net':net,'layer':sp['side'],'width_mm':.2,'path_mm':sp['spur'],'role':'escape','join':job});screen.added.append((net,sp['side'],LineString(sp['spur'])))
  routes.append({'net':net,'layer':layer,'width_mm':.2,'path_mm':path,'role':'join','join':job});screen.added.append((net,layer,LineString(path)));gs[i]+=gs[j];gs.pop(j);print(net,layer,round(cost,3),flush=True)
t=read_sexpr((I/'native-r4/signal_main.kicad_pcb').read_text())
for k,r in enumerate(routes):
 for j,(p,q)in enumerate(zip(r['path_mm'],r['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),r['layer']],[a('net'),r['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-r5-{k}-{j}'))]])
for k,v in enumerate(vias):
 v['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-r5-via-{k}'));t.append([a('via'),[a('at'),*v['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),v['net']],[a('uuid'),v['uuid']]])
o=R/'candidate-r5';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');paths=[Path(__file__),I/'native-r4/signal_main.kicad_pcb',I/'capture-after-r4/capture.json'];joins=sum(r['role']=='join'for r in routes)
(o/'routing.json').write_text(json.dumps({'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'routes':routes,'vias':vias,'blocked':blocked,'expected_opens':246-joins,'reference_additions_pending':True},indent=2)+'\n');print('joins',joins,'vias',len(vias),'blocked',len(blocked))
