"""Actual-pad-side bounded input routing, with explicit via escape geometry."""
import json,math,uuid,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
import hardware.fabrication.route_nf_surface as S
R=Path(__file__).resolve().parent;I=R.parent/'signal_input';S.SIGNAL_LAYERS=('F.Cu','B.Cu','In3.Cu','In5.Cu')
c=json.loads((I/'capture-r7/capture.json').read_text());screen=S.Screen(c);obj={o['uuid']:o for o in c['objects']};routes=[];vias=[];blocked=[];cache={}
ground_returns=[]
in1=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu'])
return_field=in1.buffer(.0015)
# Reference the introduced front copper. Existing pad/track copper is retained;
# sensitive-net exclusions remain source-derived and explicitly accounted.
front_allow={};sensitive={o['net']for o in c['objects']if o.get('ref')in ['A_U301','A_U302','A_U303','A_U304']and o.get('pin')in ['2','6']}
keep=unary_union([S.shape(z['polygons'])for z in c['zones']if z['keepout']and not z['prohibit_tracks']and z['layer']=='In1.Cu'])
base_legal=screen.legal
def ref_legal(net,layer,path):
 if not base_legal(net,layer,path):return False
 if layer!='F.Cu':return True
 if net not in front_allow:
  copper=unary_union([S.shape(o['layers']['F.Cu'])for o in c['objects']if o['net']==net and o['layers'].get('F.Cu')])
  holes=unary_union([S.shape(ps).buffer(.215)for o in c['objects']if o['net']==net and(o['kind']=='PCB_VIA'or o['kind']=='PAD'and any(o['drill_mm']))for ps in o['layers'].values()if ps])
  lowcap=unary_union([S.shape(ps).buffer(.5)for o in c['objects']if o['net']==net for l,ps in o['layers'].items()if l in ['F.Cu','B.Cu']and ps]).intersection(keep)if net in sensitive else Point().buffer(0)
  front_allow[net]=prep(in1.buffer(.0015).union(copper).union(holes).union(lowcap).buffer(-.100001))
 return front_allow[net].covers(LineString(path))
screen.legal=ref_legal
obs=[(o,S.shape(ps))for o in c['objects']for ps in o['layers'].values()if ps];tree=STRtree([g for _,g in obs])
def vialegal(p,net):
 pt=Point(p)
 if any(math.dist(p,q)<.86 for q in ground_returns):return False
 for ix in tree.query(pt.buffer(.52)):
  o,g=obs[int(ix)]
  if o['net']==net and o['kind']=='PCB_TRACK':continue
  if pt.distance(g)<.51:return False
 if any(o['kind']=='PCB_VIA'and math.dist(p,o['position_mm'])<.86 for o in c['objects']):return False
 if any(math.dist(p,v['at'])<.86 for v in vias):return False
 return not any(n!=net and pt.distance(g)<.62 for n,l,g in screen.added)
def return_site(p):
 for v in ground_returns:
  if .86<=math.dist(p,v)<=2.5 and any(LineString(path).length<=2.5 and LineString(path).buffer(.1).difference(Point(p).buffer(.515)).difference(return_field).area<1e-6 for path in S.candidate_paths(p,v)):return v
 for i,j in return_offsets:
  q=[round(p[0]+i,6),round(p[1]+j,6)];pt=Point(q)
  if not in1.covers(pt.buffer(.31)):continue
  if not any(LineString(path).length<=2.5 and LineString(path).buffer(.1).difference(Point(p).buffer(.515)).difference(return_field).area<1e-6 for path in S.candidate_paths(p,q)):continue
  if any(obs[int(ix)][0]['kind']=='PCB_TRACK'and obs[int(ix)][0]['net']=='LINK_AGND'and pt.distance(obs[int(ix)][1])<.51 for ix in tree.query(pt.buffer(.52))):continue
  if any(obs[int(ix)][0]['net']!='LINK_AGND'and pt.distance(obs[int(ix)][1])<.51 for ix in tree.query(pt.buffer(.52))):continue
  if any(o['kind']=='PCB_VIA'and math.dist(q,o['position_mm'])<.86 for o in c['objects']):continue
  if any(math.dist(q,v['at'])<.86 for v in vias):continue
  if any(n!='LINK_AGND'and pt.distance(g)<.62 for n,l,g in screen.added):continue
  return q
 return None
return_offsets=sorted([(i*.25,j*.25)for i in range(-10,11)for j in range(-10,11)if .9<=math.hypot(i*.25,j*.25)<=2.5],key=lambda x:math.hypot(*x))
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
    valid=[];pts=sorted(([round(p[0]+i*.2,6),round(p[1]+j*.2,6)]for i in range(-25,26)for j in range(-25,26)),key=lambda q:math.dist(p,q))
    for q in pts:
     if math.dist(p,q)>5:break
     if not vialegal(q,net):continue
     ret=return_site(q)
     if ret is None:continue
     paths=[x for x in S.candidate_paths(p,q)if LineString(x).length<6.5 and screen.legal(net,side,x)]
     paths=[x for x in paths if LineString(x).distance(Point(ret))>.51]
     if paths:valid.append((q,min(paths,key=lambda x:LineString(x).length)))
     if len(valid)==6:break
    cache[key]=valid
   for q,path in cache[key]:
    ret=return_site(q)
    if ret is not None and vialegal(q,net)and screen.legal(net,side,path)and LineString(path).distance(Point(ret))>.51:out.append({'at':q,'uid':u,'spur':path,'side':side,'return':ret})
 return out
def route_layers(net):return ('F.Cu','B.Cu','In3.Cu'if net.endswith('_L')else'In5.Cu')
nets=sorted(n for n in c['open_nets']if n.startswith('/A_DAC/'))
priority=['CM_DRV','BIAS','IV_','RX_NEG','CM_SUM','BUF_IN','RX_POS','HP_NODE','BUF_OUT','RX_OUT']
nets.sort(key=lambda n:(0 if n.endswith('_L')else 1,next((i for i,k in enumerate(priority)if k in n),99),n))
allgs={net:[list(v)for v in c['all_groups'].values()if obj[v[0]]['net']==net]for net in nets}
for side,pins in [('L',['1','2']),('R',['7','6'])]:
 net='/A_DAC/BUF_OUT_'+side;gs=allgs[net];u,v=[next(o for o in c['objects']if o.get('ref')=='A_U305'and o.get('pin')==pin)for pin in pins];path=[u['position_mm'],v['position_mm']];assert screen.legal(net,'F.Cu',path)
 routes.append({'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':path,'role':'join','join':len(routes)});screen.added.append((net,'F.Cu',LineString(path)));i,j=sorted([next(i for i,g in enumerate(gs)if o['uuid']in g)for o in [u,v]]);gs[i]+=gs[j];gs.pop(j)
for net in nets:
 gs=allgs[net]
 while len(gs)>1:
  opts={(i,l):options(g,net,l)for i,g in enumerate(gs)for l in route_layers(net)};choices=[];trials=[]
  for i in range(len(gs)):
   for j in range(i+1,len(gs)):
    for layer in route_layers(net):
     pairs=sorted(((math.dist(o['at'],v['at']),o,v)for o in opts[i,layer]for v in opts[j,layer]),key=lambda x:x[0])
     for dist,o,v in pairs[:12]:
      spurs=[x for x in [o,v]if x['spur']]
      if len(spurs)==2 and dist<.86:continue
      trials.append((dist,i,j,layer,o,v,spurs))
      for path in S.candidate_paths(o['at'],v['at']):
       if LineString(path).length>2*dist+5:continue
       if screen.legal(net,layer,path)and all(LineString(path).distance(Point(x['return']))>.51 for x in spurs):
        cost=LineString(path).length+sum(LineString(x['spur']).length+2 for x in spurs);choices.append((cost,i,j,layer,path,spurs));break
  if not choices:
   for dist,i,j,layer,o,v,spurs in sorted(trials,key=lambda x:x[0])[:24]:
    path=screen.grid_path(net,layer,o['at'],v['at'],budget=12000)
    if path is not None and LineString(path).length<2*dist+5 and all(LineString(path).distance(Point(x['return']))>.51 for x in spurs):choices.append((LineString(path).length+sum(LineString(x['spur']).length+2 for x in spurs),i,j,layer,path,spurs));break
  if not choices:blocked.append({'net':net,'remaining_groups':gs});break
  cost,i,j,layer,path,spurs=min(choices,key=lambda x:x[0]);job=sum(r['role']=='join'for r in routes)
  for sp in spurs:
   if sp['return']not in ground_returns:
    ground_returns.append(sp['return'])
    for l in S.SIGNAL_LAYERS:screen.added.append(('LINK_AGND',l,Point(sp['return']).buffer(.2)))
   vias.append({'net':net,'at':sp['at'],'from_pad':sp['uid'],'size_mm':.6,'drill_mm':.3})
   for l in S.SIGNAL_LAYERS:screen.added.append((net,l,Point(sp['at']).buffer(.2)))
   routes.append({'net':net,'layer':sp['side'],'width_mm':.2,'path_mm':sp['spur'],'role':'escape','join':job});screen.added.append((net,sp['side'],LineString(sp['spur'])))
  routes.append({'net':net,'layer':layer,'width_mm':.2,'path_mm':path,'role':'join','join':job});screen.added.append((net,layer,LineString(path)));gs[i]+=gs[j];gs.pop(j);print(net,layer,round(cost,3),flush=True)
t=read_sexpr((I/'native-r7/signal_main.kicad_pcb').read_text())
for k,r in enumerate(routes):
 for j,(p,q)in enumerate(zip(r['path_mm'],r['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),r['layer']],[a('net'),r['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r16-{k}-{j}'))]])
for k,v in enumerate(vias):
 v['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r16-via-{k}'));t.append([a('via'),[a('at'),*v['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),v['net']],[a('uuid'),v['uuid']]])
o=R/'candidate-r16';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');paths=[Path(__file__),I/'native-r7/signal_main.kicad_pcb',I/'capture-r7/capture.json'];joins=sum(r['role']=='join'for r in routes)
(o/'routing.json').write_text(json.dumps({'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'routes':routes,'vias':vias,'blocked':blocked,'expected_opens':230-joins,'planned_ground_returns':ground_returns,'reference_additions_pending':True},indent=2)+'\n');print('joins',joins,'vias',len(vias),'blocked',len(blocked))
