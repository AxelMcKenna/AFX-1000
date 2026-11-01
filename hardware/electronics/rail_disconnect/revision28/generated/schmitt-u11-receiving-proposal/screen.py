import sys,json,math,hashlib,heapq,itertools,copy
from pathlib import Path
import numpy as np
from shapely.geometry import Point,LineString,box,Polygon
from shapely.ops import unary_union
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.receiver_local_escape import escape
ROOT=Path('/private/tmp/afx-u11-independent')
SOURCE=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/electronics/rail_disconnect/revision28/generated/schmitt-u37-backbone-clear-work')
blob=(SOURCE/'rail_disconnect.kicad_pcb').read_bytes();tree=read_sexpr(blob.decode());r=Router(tree)
pad=next(p for p in r.by_ref['U11'] if p['pin']=='5');net=pad['net'];px,py=pad['xy'];print('pad',pad,flush=True)
# Mark only unambiguously ordinary digital control tracks as negotiable.
soft=lambda n: any(s in n for s in ['_SCHMITT','_PG','READY','FAULT','TIMEOUT','ALL_RAILS_ALLOW','MASTER','ARMED','RUN_LOGIC','NOT_RUN','REFERENCE_OK','_REF_OK','_OV_OK','_UV_OK']) and n not in ['PROTECT_REF']
names={str(n[1]):str(n[2]).lstrip('/') for n in children(tree,'net')}
index={}
for n in children(tree,'segment'):
 key=(names[str(first(n,'net')[1])],str(first(n,'layer')[1]),tuple(float(v)-100 for v in first(n,'start')[1:3]),tuple(float(v)-100 for v in first(n,'end')[1:3]),float(first(n,'width')[1]))
 index[key]=n
shapes=[]
for i,g in enumerate(r.geometry):
 if g['net'] in ['BULK_BODY_NOVIA',net]:continue
 if g['kind']=='line':
  base=LineString([g['start'],g['end']]).buffer(g['width']/2,resolution=12)
  key=(g['net'],('F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu')[g['layers'][0]],tuple(g['start']),tuple(g['end']),g['width'])
  node=index.get(key);negotiable=bool(node and soft(g['net']))
 elif g['kind']=='via':base=Point(g['xy']).buffer(g['radius'],resolution=16);node=None;negotiable=False
 else:
  x,y=g['xy'];w,h=g['size'];base=box(x-w/2,y-h/2,x+w/2,y+h/2);node=None;negotiable=False
 if not base.buffer(.53).intersects(box(5.5,11.5,12,20)):continue
 shapes.append(dict(geometry=g,shape=base,node=node,soft=negotiable,uuid=str(first(node,'uuid')[1]) if node else None))
print('localshapes',len(shapes),'softsegments',sum(x['soft'] for x in shapes),flush=True)
# Finite-grid search uses exact rounded-distance obstacle envelopes of Router.
step=.025;xs=np.arange(5.5,12.0001,step);ys=np.arange(11.5,20.0001,step);xx=xs[:,None];yy=ys[None,:]
HF=np.zeros((len(xs),len(ys)),bool);HV=HF.copy();SF=np.zeros_like(HF,dtype=np.int16);SV=SF.copy()

def hit(g,extra):
 if g['kind']=='line':
  ax,ay=g['start'];bx,by=g['end'];dx=bx-ax;dy=by-ay;t=np.clip(((xx-ax)*dx+(yy-ay)*dy)/max(dx*dx+dy*dy,1e-30),0,1)
  return (xx-ax-t*dx)**2+(yy-ay-t*dy)**2<(g['width']/2+extra)**2
 if g['kind']=='via':return (xx-g['xy'][0])**2+(yy-g['xy'][1])**2<(g['radius']+extra)**2
 x,y=g['xy'];w,h=g['size'];return np.maximum(abs(xx-x)-w/2,0)**2+np.maximum(abs(yy-y)-h/2,0)**2<extra**2
for row in shapes:
 g=row['geometry'];a=hit(g,.320001);v=hit(g,.520001)
 if row['soft']:
  if 0 in g['layers']:SF+=a
  SV+=v
 else:
  if 0 in g['layers']:HF|=a
  HV|=v
start=(round((px-xs[0])/step),round((py-ys[0])/step));print('start-hard',HF[start], 'soft',SF[start],flush=True)
if HF[start]:raise RuntimeError('start hard')
# Each removed-track traversal costs enough to prefer a short small repair;
# exact unique object costs are recomputed on resulting candidate paths.
cost={start:0};prev={};queue=[(0,start)];seen=set();targets=[]
while queue:
 score,p=heapq.heappop(queue)
 if p in seen:continue
 seen.add(p)
 if not HV[p] and math.dist((xs[p[0]],ys[p[1]]),(px,py))>.1:
  targets.append((score+20*SV[p],p))
  if len(targets)>2000:break
 for dx,dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
  q=p[0]+dx,p[1]+dy
  if not(0<=q[0]<len(xs) and 0<=q[1]<len(ys)) or HF[q]:continue
  nc=score+math.hypot(dx,dy)*step+5*SF[q]
  if nc<cost.get(q,1e30):cost[q]=nc;prev[q]=p;heapq.heappush(queue,(nc,q))
print('visited',len(seen),'targets',len(targets),flush=True)
choices=[]
for _,end in sorted(targets)[:250]:
 path=[end]
 while path[-1]!=start:path.append(prev[path[-1]])
 path.reverse();points=[(float(xs[p[0]]),float(ys[p[1]])) for p in path];points[0]=(px,py)
 line=LineString(points).buffer(.300001,resolution=16);via=Point(points[-1]).buffer(.500001,resolution=16)
 hard=[];removed=[]
 for row in shapes:
  g=row['geometry'];contact=(0 in g['layers'] and line.intersects(row['shape'])) or via.intersects(row['shape'])
  if not contact:continue
  (removed if row['soft'] else hard).append(row)
 if hard:continue
 sig=tuple(sorted(x['uuid'] for x in removed))
 choices.append(dict(end=points[-1],points=points,removed=removed,signature=sig,length=LineString(points).length))
choices.sort(key=lambda c:(len(c['removed']),c['length']))
unique=[]
for c in choices:
 if any(c['signature']==q['signature'] for q in unique):continue
 unique.append(c)
 if len(unique)>=8:break

def describe(row):
 g=row['geometry'];return dict(uuid=row['uuid'],geometry=g,source_object=sexpr(row['node']) if row['node'] else None)
report=dict(source=str(SOURCE),source_pcb_sha256=hashlib.sha256(blob).hexdigest(),pad=pad,step=step,bounds=[5.5,11.5,12,20],
 all_old_vias_pads_ports_force_quiet_GND_tracks_hard=True,soft_track_rule='Explicitdigitalnamesonly; noforce/supply/quiet/GNDtracks',
 visited=len(seen),local_objects=[describe(s) for s in shapes],candidates=[])
for c in unique:
 # Compress only collinear runs. Real segment clearance is checked already.
 pts=[c['points'][0]];direction=None
 for a,b in zip(c['points'],c['points'][1:]):
  d=(round((b[0]-a[0])/step),round((b[1]-a[1])/step))
  if direction is not None and d!=direction:pts.append(a)
  direction=d
 pts.append(c['points'][-1])
 report['candidates'].append(dict(via=c['end'],F_path=pts,length=c['length'],removed_objects=[describe(s) for s in c['removed']],hard_objects_removed=0))
(ROOT/'screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['candidates'],indent=2),flush=True)
assert (SOURCE/'rail_disconnect.kicad_pcb').read_bytes()==blob
