"""Bounded additive I2C paths, retaining all existing objects and assignments."""
import json,copy,uuid,inspect,math,heapq,itertools,textwrap
from pathlib import Path
from shapely.geometry import LineString,Point
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
import hardware.fabrication.route_nf_surface as surface
R=Path(__file__).resolve().parent;REPO=R.parents[3]
cap=json.loads((R/'capture-baseline/capture.json').read_text());surface.SIGNAL_LAYERS=('In3.Cu','B.Cu')
screen=surface.Screen(cap);routes=[]
code=textwrap.dedent(inspect.getsource(surface.Screen.grid_path)).replace('-50','-200').replace('+50','+200')
exec(code,globals());screen.grid_path=grid_path.__get__(screen)

via_sites=[]
# Reach the long existing SCL backside trunk before dense LED breakout pockets.
trunk=next(o for o in cap['objects']if o['uuid']=='b27ea3fe-b33e-5268-a6fb-972d5013cbb8')
def via_legal(pt,net):
 point=Point(pt)
 for o in cap['objects']:
  if o['kind']=='PCB_VIA' and math.dist(pt,o['position_mm'])<.86:return False
  if o['net']==net and o['kind']=='PCB_TRACK':continue
  for ps in o['layers'].values():
   if ps and point.distance(surface.shape(ps))<.51:return False
 return True
via_spurs={}
for i in range(1,39):
 frac=i/40;p=[trunk['position_mm'][j]+frac*(trunk['end_mm'][j]-trunk['position_mm'][j])for j in range(2)]
 for dx,dy in [(0,0),(.75,0),(-.75,0),(1.5,0),(-1.5,0),(2.5,0),(-2.5,0),(0,.75),(0,-.75)]:
  q=[p[0]+dx,p[1]+dy]
  if (q==p or screen.legal('LINK_SCL','B.Cu',[p,q])) and via_legal(q,'LINK_SCL'):
   via_sites.append(q);via_spurs[tuple(q)]=[p,q]
assert via_sites
jobs=[('SCLpull','LINK_SCL',[177.5,81.4125],[[175,87]],'B.Cu'),('SDApull','LINK_SDA',[172.5,81.4125],[[175,84.5]],'B.Cu'),('SCLbridge','LINK_SCL',[175,87],via_sites,'In3.Cu'),('SDAbridge','LINK_SDA',[175,84.5],[[188.5,68.9]],'In3.Cu')]
new_vias=[]
for name,net,start,ends,layer in jobs:
 path=None
 for end in ends:
  path=next((v for v in surface.candidate_paths(start,end)if screen.legal(net,layer,v)),None)
  if path is not None:break
 if path is None:
  for end in ends[:5]:
   path=screen.grid_path(net,layer,start,end,budget=120000)
   if path is not None:break
 print(name,path,flush=True);assert path is not None
 routes.append({'name':name,'net':net,'layer':layer,'width_mm':.2,'path_mm':path});screen.added.append((net,layer,LineString(path)))
 if name=='SCLbridge':
  new_vias.append({'net':net,'at':end})
  spur=via_spurs[tuple(end)]
  if math.dist(*spur)>1e-6:routes.append({'name':'SCLviaescape','net':net,'layer':'B.Cu','width_mm':.2,'path_mm':spur})
p=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb';t=read_sexpr(p.read_text())
for route in routes:
 for i,(p,q)in enumerate(zip(route['path_mm'],route['path_mm'][1:])):
  uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH05-i2c-r1-{route["name"]}-{i}'));t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),route['layer']],[a('net'),route['net']],[a('uuid'),uid]])
for v in new_vias:
 t.append([a('via'),[a('at'),*v['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),v['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH05-I2C-SCL-via'))]])
# Extend digital adjacent reference across the short formerly unreferenced audio-side escapes.
z=copy.deepcopy(next(v for v in children(t,'zone')if first(v,'uuid')[1]=='267071c0-8479-5b13-8615-47bcbff10ed7'))
z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['filled_polygon','polygon'])];first(z,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH05-i2c-r1-reference'))
xs=[p[0]for r in routes for p in r['path_mm']];ys=[p[1]for r in routes for p in r['path_mm']]
bounds=[171,67.5,193,89]
x0,y0,x1,y1=bounds;z.append([a('priority'),1]);z.append([a('polygon'),[a('pts'),*[ [a('xy'),x,y]for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]]])
t.append(z);z4=copy.deepcopy(z);first(z4,'layer')[1]='In4.Cu';first(z4,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH05-i2c-r1-reference4'));t.append(z4);out=R/'candidate-r2';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps({'scope':'Only four I2C bridges and adjacent ground extension; not full board acceptance','source_sha256':cap['source_sha256'],'routes':routes,'new_vias':new_vias,'ground_extension':{'net':'LINK_AGND','layers':['In4.Cu','In6.Cu'],'priority':1,'bounds_mm':bounds,'uuid':first(z,'uuid')[1]},'native_verification_pending':True},indent=2)+'\n')
