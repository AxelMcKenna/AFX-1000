import sys,json,math,copy,heapq
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from hardware.fabrication.integrate_two_board_signal import STAGING
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
c=json.loads((STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json').read_text());prior=json.loads((STAGING/'two-board-power-digital-distribution-native-02/digital-distribution-routing.json').read_text());local=json.loads((STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json').read_text());refs=['E_U15','E_U16','E_U17','E_U33']
retire=set()
for r,v in zip(prior['routes'],prior['vias']):
 if r.get('ref') in refs and r['pin'] in ['2','4']:retire.update([v['uuid'],*r['segment_uuids']])
master_retire={'a3779d0d-f669-5472-b488-b258b343c226','6b1f1723-2fab-5bda-82f9-3010ac5cd3f7','13c6dbca-4093-5fb8-be44-9b46b483850d','757125ea-9a34-5e1b-a58e-93f50b41debc','2d158a61-2804-5043-8716-5e5ded9b5889'}
retire.update(master_retire)
fixed=[dict(net='/E_rail_disconnect/E28_MASTER_ENABLE',layer='B.Cu',width_mm=.2,path_mm=[[133.25,118.475],[132.25,118.75]],label='U29 master-enable local tie')]
star=next(q['star_via'] for q in local['quiet_ground_islands'] if q['ref']=='E_U17');star_old=star['position_mm'];star_new=[135.81,121.925];retire.add(star['uuid'])
for r in local['routes']:
 if r.get('ref')=='E_U17' and r.get('pin')=='8':
  retire.update(r['segment_uuids']);fixed.append(dict(net='PWR_AGND',layer='F.Cu',width_mm=.2,path_mm=[[135.06,121.725],[135.61,121.725],star_new],label='U17 ground-pin escape',chip='E_U17'))
 elif r.get('chip')=='E_U17' and r.get('quiet_return') and not r['label'].startswith('E_C47'):
  assert r['path_mm'][-1]==star_old;retire.add(r['segment_uuids'][-1]);fixed.append(dict(net='PWR_AGND',layer=r['layer'],width_mm=.2,path_mm=[r['path_mm'][-2],star_new],label=r['label']+' last segment',chip='E_U17'))
cap_return=next(r for r in local['routes'] if r.get('label')=='E_C47.2 quiet');retire.update(cap_return['segment_uuids'])
capvia=[137.21,130.0875]
fixed.append(dict(net='PWR_AGND',layer='B.Cu',width_mm=.2,path_mm=[cap_return['path_mm'][0],capvia],label='E_C47 local quiet return',chip='E_U17'))
extra_quiet_vias=[dict(ref='E_C47',pin='2',owner='E_U17',net='PWR_AGND',position_mm=capvia)]
c['objects']=[o for o in c['objects'] if o['uuid'] not in retire]
for i,r in enumerate(fixed):
 for j,(p,q) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  g=LineString([p,q]).buffer(.1);c['objects'].append(dict(uuid='fixed-'+str(i)+'-'+str(j),net=r['net'],kind='PCB_TRACK',position_mm=p,end_mm=q,width_mm=.2,layers={r['layer']:[dict(outer=list(g.exterior.coords),holes=[])]}))
from shapely.affinity import translate
oldstar=next(o for o in json.loads((STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json').read_text())['objects'] if o['uuid']==star['uuid'])
movedstar=copy.deepcopy(oldstar);movedstar['uuid']='relocated-U17-star';movedstar['position_mm']=star_new
for l,ps in movedstar['layers'].items():
 g=translate(routing.shape(ps),star_new[0]-star_old[0],star_new[1]-star_old[1]);movedstar['layers'][l]=[dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]
c['objects'].append(movedstar)
for i,v in enumerate(extra_quiet_vias):
 g=Point(v['position_mm']).buffer(.3);c['objects'].append(dict(uuid='extra-quiet-'+str(i),net='PWR_AGND',kind='PCB_VIA',position_mm=v['position_mm'],width_mm=.6,drill_mm=.3,layers={l:[dict(outer=list(g.exterior.coords),holes=[])] for l in c['copper_layers']}))
routing.SIGNAL_LAYERS=('F.Cu','B.Cu');screen=ViaScreen(dict(c,zones=[]));rows={l:[(o,routing.shape(o['layers'][l])) for o in c['objects'] if o['layers'].get(l)] for l in routing.SIGNAL_LAYERS};trees={l:STRtree([g for o,g in rr]) for l,rr in rows.items()};routes=[];vias=[];deferred=[]
# Quiet control ties must not join bulk ground on either face or another cell.
allowed={ref:{o['uuid'] for o in c['objects'] if o.get('ref')==ref and o['net']=='PWR_AGND'} for ref in refs}
for r in local['routes']:
 ref=r.get('chip',r.get('ref'))
 if ref in refs and r['net']=='PWR_AGND':allowed[ref].update(r['segment_uuids'])
for q in local['quiet_ground_islands']:allowed[q['ref']].add(q['star_via']['uuid'])
allowed['E_U17'].update(['relocated-U17-star','extra-quiet-0'])
for o in c['objects']:
 if o.get('ref') in ['E_R113','E_C47'] and o['net']=='PWR_AGND':allowed['E_U17'].add(o['uuid'])
for o in c['objects']:
 if o['uuid'].startswith('fixed-') and o['net']=='PWR_AGND':allowed['E_U17'].add(o['uuid'])
def quiet_route(ref,layer,ps):
 g=LineString(ps)
 for i in trees[layer].query(g.buffer(.31)):
  o,h=rows[layer][int(i)]
  if o['net']=='PWR_AGND' and o['uuid'] not in allowed[ref] and g.distance(h)<.31-1e-8:return False
 for r,v in zip(routes,vias):
  if r['net']=='PWR_AGND' and r['ref']!=ref:
   if g.distance(Point(v['position_mm']))<.61:return False
   if r['layer']==layer and g.distance(LineString(r['path_mm']))<.41:return False
 return True

grounds=[(o['uuid'],routing.shape(ps)) for o in c['objects'] if o['net']=='PWR_AGND' for ps in o['layers'].values() if ps]
gtree=STRtree([g for u,g in grounds])

def via_ok(ref,net,xy):
 if not screen.via_legal(net,xy):return False
 if net!='PWR_AGND':return True
 pt=Point(xy)
 if any(grounds[int(i)][0] not in allowed[ref] and pt.distance(grounds[int(i)][1])<.51 for i in gtree.query(pt.buffer(.511))):return False
 if any(r['net']=='PWR_AGND' and r['ref']!=ref and math.dist(xy,v['position_mm'])<.81 for r,v in zip(routes,vias)):return False
 return True

def choices(ref,pin,limit=20):
 o=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin);x,y=o['position_mm'];net=o['net'];res=[]
 sites=sorted((math.hypot(i*.2,j*.2),[round(x+i*.2,4),round(y+j*.2,4)]) for i in range(-22,10) for j in range(-22,23) if .6<=math.hypot(i*.2,j*.2)<=4.4)
 for d,xy in sites:
  if not via_ok(ref,net,xy):continue
  candidates=[]
  for ps in routing.candidate_paths([x,y],xy):
   ps=[list(p) for i,p in enumerate(ps) if not i or list(p)!=list(ps[i-1])]
   if len(ps)<2:continue
   length=LineString(ps).length
   if length>5.5 or not screen.legal(net,'F.Cu',ps):continue
   if net=='PWR_AGND' and not quiet_route(ref,'F.Cu',ps):continue
   candidates.append((length,ps))
  if candidates:
   length,ps=min(candidates);res.append((length,dict(ref=ref,pin=pin,net=net,layer='F.Cu',width_mm=.2,path_mm=ps),dict(net=net,position_mm=xy)))
  if len(res)>=limit:break
 if len(res)<5 or pin=='3':
  origin=(x,y);queue=[(0.,(0,0))];cost={(0,0):0.};parent={};edgecache={};found={tuple(v[2]['position_mm']) for v in res};visits=0
  xyof=lambda k:[round(x+k[0]*.1,4),round(y+k[1]*.1,4)]
  def edge(a,b):
   key=tuple(sorted((a,b)))
   if key not in edgecache:
    ps=[xyof(a),xyof(b)];edgecache[key]=screen.legal(net,'F.Cu',ps) and (net!='PWR_AGND' or quiet_route(ref,'F.Cu',ps))
   return edgecache[key]
  while queue and visits<10000:
   dist,key=heapq.heappop(queue)
   if dist>cost[key]+1e-9:continue
   if dist>7:break
   visits+=1;xy=xyof(key)
   if dist>.6 and key[0]%2==0 and key[1]%2==0 and tuple(xy) not in found and via_ok(ref,net,xy):
    chain=[key]
    while chain[-1]!=(0,0):chain.append(parent[chain[-1]])
    points=[xyof(k) for k in reversed(chain)];simple=[points[0]];i=0
    while i<len(points)-1:
     j=len(points)-1
     while j>i+1 and not(screen.legal(net,'F.Cu',[points[i],points[j]]) and (net!='PWR_AGND' or quiet_route(ref,'F.Cu',[points[i],points[j]]))):j-=1
     simple.append(points[j]);i=j
    length=LineString(simple).length
    res.append((length,dict(ref=ref,pin=pin,net=net,layer='F.Cu',width_mm=.2,path_mm=simple),dict(net=net,position_mm=xy)));found.add(tuple(xy))
    if len(res)>=limit:break
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
    k=(key[0]+dx,key[1]+dy);d=dist+.1*math.hypot(dx,dy)
    if d>=cost.get(k,1e9)-1e-9 or not edge(key,k):continue
    cost[k]=d;parent[k]=key;heapq.heappush(queue,(d,k))
 return sorted(res,key=lambda v:v[0])
def push(r,v):
 routes.append(r);vias.append(v);screen.vias.append((v['net'],v['position_mm']));screen.added.append((r['net'],'F.Cu',LineString(r['path_mm'])))
 for l in routing.SIGNAL_LAYERS:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
def pop():routes.pop();vias.pop();screen.vias.pop();del screen.added[-3:]
attempts=0
def cell(ref,pins):
 global attempts
 attempts+=1
 if attempts>1000:return False
 if not pins:return True
 for length,r,v in choices(ref,pins[0],20):
  push(r,v)
  if cell(ref,pins[1:]):return True
  pop()
 return False
for ref in ['E_U15','E_U16','E_U17','E_U33']:
 attempts=0
 print('SEARCH',ref,flush=True)
 # Fix supply-good escape first, then allocate its neighboring ground pins.
 pins=['3','2','4']+(['1'] if ref!='E_U15' else [])
 if not cell(ref,pins):deferred.append(ref);print('FAIL',ref,flush=True)
 else:print('DONE',ref,[(r['pin'],v['position_mm']) for r,v in zip(routes,vias) if r['ref']==ref],flush=True)
Path('/private/tmp/digital-startup-fanout.json').write_text(json.dumps(dict(routes=routes,vias=vias,retired_objects=sorted(retire),fixed_routes=fixed,extra_quiet_vias=extra_quiet_vias,relocated_star=dict(old_uuid=star['uuid'],old_position_mm=star_old,position_mm=star_new),deferred=deferred),indent=2))
