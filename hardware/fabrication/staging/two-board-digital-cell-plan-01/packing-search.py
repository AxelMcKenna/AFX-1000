import copy,json,math
from pathlib import Path
from shapely.geometry import box,Point
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import first,children,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop
from hardware.fabrication.route_two_board_buck_cell import position,angle,transform_object,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-digital-distribution-native-02'
c=json.loads((STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json').read_text());prior=json.loads((BASE/'digital-distribution-routing.json').read_text())
board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')}
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
side_reconciliations=[]
for r in placement['parts']:
 if r['id'] in fps and r['side']!=first(fps[r['id']],'layer')[1][0]:
  assert r['id'].startswith(('P_R','P_C')) and not r['tails_relative_xy']
  b=r['body_relative_xy'];assert abs(b[0]+b[2])<1e-7 and abs(b[1]+b[3])<1e-7
  side_reconciliations.append(dict(ref=r['id'],old_side=r['side'],current_side=first(fps[r['id']],'layer')[1][0]))
  r['side']=first(fps[r['id']],'layer')[1][0]
records={r['id']:r for r in placement['parts']}
cells=[('E_U15','E_R105','E_R106','E_C43'),('E_U16','E_R109','E_R110','E_C45'),('E_U17','E_R113','E_R114','E_C47'),('E_U33','E_R121','E_R122','E_C51')]
moving={r for cell in cells for r in cell[1:]}|{'E_C44','E_C48','E_C52'};retire=set()
for r,v in zip(prior['routes'],prior['vias']):
 if r['ref'] in moving or (r['ref'].startswith('E_U') and r['pin']=='8'):retire.update([v['uuid'],*r['segment_uuids']])
objects=[o for o in c['objects'] if o.get('ref') not in moving and o['uuid'] not in retire]
obstacles={'F':[],'B':[]}
for ref,f in fps.items():
 if ref in moving:continue
 for side in ['F','B']:
  try:obstacles[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
  except AssertionError:pass
 r=records.get(ref)
 if r:
  delta=angle(f)-r['angle'];x,y=position(f)
  mb=lambda b:translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
  obstacles[r['side']].append((ref,mb(r['body_relative_xy'])))
  if r['tails_relative_xy']:obstacles['B'].extend((ref,mb(b)) for b in r['tails_relative_xy'])
  for e in r['additional_planar_reserves']:obstacles[e['side']].append((ref,mb(e['bounds'])))
# Reserve space for simultaneous through-via escapes from pins 7/8/9.
for ref,*_ in cells:
 o=next(o for o in objects if o.get('ref')==ref and o.get('pin')=='8');x,y=o['position_mm']
 obstacles['B'].append(('fanout-'+ref,box(x+.15,y-1.6,x+1.45,y+1.6)))
trees={s:STRtree([g for r,g in obs]) for s,obs in obstacles.items()};added=[];newobjects=[];moves={}
geo={l:[(o,shape(o['layers'][l])) for o in objects if o['layers'].get(l)] for l in c['copper_layers']};gt={l:STRtree([g for o,g in rows]) for l,rows in geo.items()}
holes=[(Point(o['position_mm']),(max(o['drill_mm']) if isinstance(o.get('drill_mm'),list) else o.get('drill_mm',0))/2) for o in objects if o.get('drill_mm') and (any(o['drill_mm']) if isinstance(o['drill_mm'],list) else True)]

def flip_layers(f):
 f=copy.deepcopy(f)
 def visit(n):
  if not isinstance(n,list):return
  for i,v in enumerate(n):
   if isinstance(v,list):visit(v)
   elif isinstance(v,str) and v.startswith(('F.','B.')):n[i]=('B.' if v.startswith('F.') else 'F.')+v[2:]
  if n and n[0]=='justify':
   n[:]=[v for v in n if v!='mirror']
 visit(f)
 return f

def trial(ref,xy,rot,flip=False):
 f=rotate_footprint(fps[ref],xy,rot)
 if flip:f=flip_layers(f)
 side=first(f,'layer')[1][0];g=box(*courtyard(f,side+'.CrtYd'));q=g.buffer(.3,join_style=2)
 if any(q.intersection(obstacles[side][int(i)][1]).area>1e-8 for i in trees[side].query(q)):return
 if any(s==side and q.intersection(h).area>1e-8 for s,h in added):return
 os=[transform_object(o,position(fps[ref]),xy,rot) for o in c['objects'] if o.get('ref')==ref]
 if flip:
  for o in os:o['layers']={('B.Cu' if l=='F.Cu' else 'F.Cu' if l=='B.Cu' else l):ps for l,ps in o['layers'].items()}
 for o in os:
  for l,ps in o['layers'].items():
   h=shape(ps)
   for i in gt[l].query(h.buffer(.211)):
    other,gg=geo[l][int(i)]
    if other['net']!=o['net'] and h.distance(gg)<.21-1e-7:return
   if any(h.distance(p)-r<.15 for p,r in holes):return
   for other in newobjects:
    if other['net']!=o['net'] and other['layers'].get(l) and h.distance(shape(other['layers'][l]))<.21:return
 return f,g,os

def place(ref,anchor,pin_target=None,exact=None):
 candidates=[]
 sites=[(0,exact[0],exact[1],False)] if exact else sorted((math.hypot(ix*.25,iy*.25),[round(anchor[0]+ix*.25,4),round(anchor[1]+iy*.25,4)],rot,flip) for ix in range(-24,25) for iy in range(-24,25) if math.hypot(ix*.25,iy*.25)<=6 for rot in [0,90,180,270] for flip in ([False] if ref in {'E_C44','E_C48','E_C52'} else [False,True]))
 for d,xy,rot,flip in sites:
  t=trial(ref,xy,rot,flip)
  if not t:continue
  f,g,os=t
  p1=next(o for o in os if o['pin']=='1')['position_mm']
  score=math.dist(p1,pin_target or anchor)+.12*d
  candidates.append((score,d,xy,rot,flip,t))
  if len(candidates)>=60:break
 assert candidates,ref
 score,d,xy,rot,flip,(f,g,os)=min(candidates,key=lambda r:r[:2]);side=first(f,'layer')[1][0];added.append((side,g));newobjects.extend(os);moves[ref]=[xy,rot,flip]
 print(ref,xy,rot,side,'pin1dist',round(math.dist(next(o for o in os if o['pin']=='1')['position_mm'],pin_target or anchor),3),flush=True)
 return os
# Place the three input caps as a compact bank immediately below the cells.
for r,xy,rot in [('E_C44',[134,124.8],-90),('E_C48',[138,124.8],0),('E_C52',[149,135.5],-90)]:place(r,xy)
for ref,ilm,dvdt,capref in [cells[2],cells[1],cells[0],cells[3]]:
 p9=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='9')
 p7=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='7')
 place(ilm,[p9[0]+2.5,p9[1]-1],p9)
 os=place(dvdt,[p7[0]+2.5,p7[1]+1],p7)
 p2=next(o['position_mm'] for o in os if o['pin']=='2');place(capref,p2,p2)
updated=dict(fps)
for ref,(xy,rot,flip) in moves.items():
 updated[ref]=rotate_footprint(fps[ref],xy,rot)
 if flip:updated[ref]=flip_layers(updated[ref])
mechanical_check(updated,set(moves),placement)
Path('/private/tmp/digital-cell-placement.json').write_text(json.dumps(dict(moves=moves,retired_objects=sorted(retire),reconciled_existing_passive_sides=side_reconciliations),indent=2))
