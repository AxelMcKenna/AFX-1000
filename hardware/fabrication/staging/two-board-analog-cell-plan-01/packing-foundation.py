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
BASE=STAGING/'two-board-power-permission-native-04'
c=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text());seed=json.loads(Path('/private/tmp/analog-cell-seed.json').read_text())
board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')}
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
side_reconciliations=[]
accepted={r['ref']:r for r in json.loads((STAGING/'two-board-permission-plan-04/plan.json').read_text())['side_reconciliations']}
for r in placement['parts']:
 if r['id'] in fps and r['side']!=first(fps[r['id']],'layer')[1][0]:
  assert r['id'] in accepted and accepted[r['id']]['old_side']==r['side'] and accepted[r['id']]['current_side']==first(fps[r['id']],'layer')[1][0] and not r['tails_relative_xy']
  b=r['body_relative_xy'];assert abs(b[0]+b[2])<1e-7 and abs(b[1]+b[3])<1e-7
  side_reconciliations.append(dict(ref=r['id'],old_side=r['side'],current_side=first(fps[r['id']],'layer')[1][0]))
  r['side']=first(fps[r['id']],'layer')[1][0]
records={r['id']:r for r in placement['parts']}
cells=seed['cells'];moving=set(seed['moving']);retire=set(seed['retired_objects'])
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
 obstacles['F'].append(('fanout-'+ref,box(x+.15,y-1.6,x+1.45,y+1.6)))
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

def place(ref,anchor,pin_target=None,exact=None,pin2_target=None):
 candidates=[]
 sites=[(0,exact[0],exact[1],False)] if exact else sorted((math.hypot(ix*.25,iy*.25),[round(anchor[0]+ix*.25,4),round(anchor[1]+iy*.25,4)],rot,flip) for ix in range(-24,25) for iy in range(-24,25) if math.hypot(ix*.25,iy*.25)<=6 for rot in [0,90,180,270] for flip in [False,True])
 for d,xy,rot,flip in sites:
  t=trial(ref,xy,rot,flip)
  if not t:continue
  f,g,os=t
  p1=next(o for o in os if o['pin']=='1')['position_mm']
  score=math.dist(p1,pin_target or anchor)+.12*d
  if pin2_target:score+=math.dist(next(o for o in os if o['pin']=='2')['position_mm'],pin2_target)
  candidates.append((score,d,xy,rot,flip,t))
  if len(candidates)>=60:break
 assert candidates,ref
 score,d,xy,rot,flip,(f,g,os)=min(candidates,key=lambda r:r[:2]);side=first(f,'layer')[1][0];added.append((side,g));newobjects.extend(os);moves[ref]=[xy,rot,flip]
 print(ref,xy,rot,side,'pin1dist',round(math.dist(next(o for o in os if o['pin']=='1')['position_mm'],pin_target or anchor),3),flush=True)
 return os
cap_pads={}
for ref,ilm,dvdt,capref,pulldown in cells:
 p7=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='7')
 cap_pads[ref]=place(capref,[p7[0]+4,p7[1]+2],p7)
for ref,ilm,dvdt,capref,pulldown in cells:
 p9=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='9')
 p7=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='7')
 p1=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='1')
 place(ilm,[p9[0]+2.5,p9[1]-1],p9)
 cp=next(o['position_mm'] for o in cap_pads[ref] if o['pin']=='1')
 place(dvdt,[(cp[0]+p7[0])/2,(cp[1]+p7[1])/2],p7,pin2_target=cp)
 place(pulldown,[p1[0]-2.5,p1[1]-1],p1)
updated=dict(fps)
for ref,(xy,rot,flip) in moves.items():
 updated[ref]=rotate_footprint(fps[ref],xy,rot)
 if flip:updated[ref]=flip_layers(updated[ref])
mechanical_check(updated,set(moves),placement)
Path('/private/tmp/analog-cell-placement-v2.json').write_text(json.dumps(dict(moves=moves,retired_objects=sorted(retire),reconciled_existing_passive_sides=side_reconciliations),indent=2))
