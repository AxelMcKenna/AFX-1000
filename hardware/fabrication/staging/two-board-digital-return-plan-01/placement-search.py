import sys,json,math,copy
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union,nearest_points
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import STAGING,prop
from hardware.fabrication.route_two_board_buck_cell import transform_object,position,angle,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
import hardware.fabrication.route_nf_surface as routing
base=STAGING/'two-board-power-analog-cells-native-03';cp=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json';c=json.loads(cp.read_text())
fps={prop(f,'Reference')[2]:f for f in children(read_sexpr((base/'power_protection.kicad_pcb').read_text()),'footprint')};ref='E_R104';oldfp=fps[ref];oldxy=position(oldfp)
retire={'1dd9bec8-1c57-5df5-8c3d-434fe890aa2b','ba13481d-23e8-50bf-bcfd-a72f9671b4b1','82aed1c5-991b-5b8c-afcf-95a9ec58a71b'}
fixed=[o for o in c['objects'] if o.get('ref')!=ref and o['uuid'] not in retire]
rows={l:[(o,routing.shape(o['layers'][l])) for o in fixed if o['layers'].get(l)] for l in c['copper_layers']};trees={l:STRtree([g for o,g in rr]) for l,rr in rows.items()}
q=json.loads((STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())['quiet_ground_islands'][0];own={v['uuid'] for v in [q['star_via'],*q['control_vias']]}
# Physical surface-copper graph: zones deliberately do not participate.
while True:
 prev=set(own)
 for l in ['F.Cu','B.Cu']:
  for o,g in rows[l]:
   if o['uuid'] not in own:continue
   for i in trees[l].query(g.buffer(.000002)):
    other,h=rows[l][int(i)]
    if other['net']=='PWR_AGND' and g.distance(h)<.000002:own.add(other['uuid'])
 if prev==own:break
holes=[]
for o in fixed:
 d=o.get('drill_mm',0);rad=(max(d) if isinstance(d,list) else d)/2
 if rad:holes.append((Point(o['position_mm']),rad))
obs={l:[] for l in ['F.Cu','B.Cu']}
for name,f in fps.items():
 if name==ref:continue
 for l in obs:
  try:obs[l].append(box(*courtyard(f,l[0]+'.CrtYd')))
  except AssertionError:pass
otrees={l:STRtree(gs) for l,gs in obs.items()}
foreign=lambda net,o:o['net']!=net or net=='PWR_AGND' and o['uuid'] not in own

def legal(net,l,ps,pads):
 g=LineString(ps)
 for i in trees[l].query(g.buffer(.311)):
  o,h=rows[l][int(i)]
  if foreign(net,o) and g.distance(h)<.31-1e-7:return False
 for o in pads:
  if o['net']!=net and g.distance(routing.shape(o['layers'][l]))<.31-1e-7:return False
 return True

def route(net,l,start,end,pads):
 opts=[]
 for ps in routing.candidate_paths(start,end):
  ps=[list(p) for i,p in enumerate(ps) if not i or list(p)!=list(ps[i-1])]
  if len(ps)<2:continue
  if legal(net,l,ps,pads):opts.append((LineString(ps).length,ps))
 return min(opts,key=lambda x:x[0]) if opts else None
padold=[o for o in c['objects'] if o.get('ref')==ref];valid=[]
for l in ['B.Cu','F.Cu']:
 ground=unary_union([LineString([o['position_mm'],o['end_mm']]) if o['kind']=='PCB_TRACK' else Point(o['position_mm']) for o,g in rows[l] if o['uuid'] in own]);end=[139.5,113.]
 for ix in range(540,589):
  for iy in range(436,477):
   xy=[ix*.25,iy*.25]
   for rot in [0,90,180,270]:
    f=rotate_footprint(oldfp,xy,rot)
    # Two-pad 0805 courtyard is symmetric; face swap does not change bounds.
    g=box(*courtyard(f,'B.CrtYd'));infl=g.buffer(.3,join_style=2)
    if any(infl.intersection(obs[l][int(i)]).area>1e-8 for i in otrees[l].query(infl)):continue
    pads=[transform_object(o,oldxy,xy,rot) for o in padold]
    if l=='F.Cu':
     for o in pads:o['layers']={'F.Cu':o['layers']['B.Cu']}
    ok=True
    for o in pads:
     gg=routing.shape(o['layers'][l])
     for i in trees[l].query(gg.buffer(.211)):
      other,h=rows[l][int(i)]
      if foreign(o['net'],other) and gg.distance(h)<.21-1e-7:ok=False;break
     if not ok or any(gg.distance(pt)-rad<.15-1e-7 for pt,rad in holes):ok=False;break
    if not ok:continue
    p1=next(o for o in pads if o['pin']=='1');p2=next(o for o in pads if o['pin']=='2')
    a=route(p1['net'],l,p1['position_mm'],end,pads)
    if not a or a[0]>6:continue
    targets=[v['position_mm'] for v in [q['star_via'],*q['control_vias']]]+[list(nearest_points(Point(p2['position_mm']),ground)[1].coords[0])]
    opts=[v for t in targets if (v:=route('PWR_AGND',l,p2['position_mm'],t,pads)) and v[0]<6]
    if not opts:continue
    b=min(opts,key=lambda x:x[0])
    if LineString(a[1]).distance(LineString(b[1]))<.41:continue
    # Avoid non-ground copper on the adjacent reference; plane boundaries can
    # subsequently be extended but foreign antipads cannot be waived.
    adj={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[l];sg=LineString(a[1]).buffer(.1)
    for o in fixed:
     if o['kind']=='PCB_VIA' and o['net']==p1['net']:sg=sg.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    if any(o['net']!='PWR_AGND' and sg.intersection(h.buffer(.2)).area>1e-7 for o,h in rows[adj]):continue
    valid.append(dict(xy=xy,rotation=rot,flip=l=='F.Cu',layer=l,enable=a[1],ground=b[1],enable_length_mm=a[0],ground_length_mm=b[0],score=a[0]+b[0],pads=[dict(pin=o['pin'],xy=o['position_mm']) for o in pads]))
valid.sort(key=lambda x:x['score'])
result=dict(retired_objects=sorted(retire),surface_owned_ground_objects=sorted(own),candidates=valid[:60],candidate_count=len(valid),scope='Courtyard, pad/copper/drill, bounded surface path and foreign-reference-copper screen. Native pose, mechanical body/context, planes and full connectivity remain pending.')
Path('/private/tmp/r104-placement-search.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(count=len(valid),best=valid[:4])),flush=True)
