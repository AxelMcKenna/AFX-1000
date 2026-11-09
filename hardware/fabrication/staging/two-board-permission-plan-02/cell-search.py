import sys,copy,json,math
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import box,Point,LineString
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import first,children,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop
from hardware.fabrication.route_two_board_buck_cell import position,angle,transform_object,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
routing.SIGNAL_LAYERS=('F.Cu','B.Cu')
BASE=STAGING/'two-board-power-startup-completion-native-06'
c=json.loads((STAGING/'two-board-power-routing-inputs-2267-startup-completion-06/capture.json').read_text())
board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')}
moving={'E_U42','E_C85'}
prior=json.loads((STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())
retired=set()
for o in c['objects']:
 if o.get('ref') in moving:assert len(c['all_groups'][o['group']])==1
objects=[o for o in c['objects'] if o.get('ref') not in moving and o['uuid'] not in retired]
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text());reconciled=[]
for r in placement['parts']:
 if r['id'] in fps and r['side']!=first(fps[r['id']],'layer')[1][0]:
  assert r['id'].startswith(('P_R','P_C','E_R','E_C')) and not r['tails_relative_xy'];b=r['body_relative_xy'];assert abs(b[0]+b[2])<1e-7 and abs(b[1]+b[3])<1e-7
  reconciled.append(dict(ref=r['id'],old_side=r['side'],current_side=first(fps[r['id']],'layer')[1][0]));r['side']=first(fps[r['id']],'layer')[1][0]
records={r['id']:r for r in placement['parts']};obstacles={'F':[],'B':[]}
for ref,f in fps.items():
 if ref in moving:continue
 for side in ['F','B']:
  try:obstacles[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
  except AssertionError:pass
 rec=records.get(ref)
 if rec:
  delta=angle(f)-rec['angle'];x,y=position(f);mb=lambda b:translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
  obstacles[rec['side']].append((ref,mb(rec['body_relative_xy'])))
  if rec['tails_relative_xy']:obstacles['B'].extend((ref,mb(b)) for b in rec['tails_relative_xy'])
  for e in rec['additional_planar_reserves']:obstacles[e['side']].append((ref,mb(e['bounds'])))
trees={s:STRtree([g for r,g in obs]) for s,obs in obstacles.items()}
geo={l:[(o,shape(o['layers'][l])) for o in objects if o['layers'].get(l)] for l in c['copper_layers']};gt={l:STRtree([g for o,g in rows]) for l,rows in geo.items()}
holes=[(Point(o['position_mm']),(max(o['drill_mm']) if isinstance(o.get('drill_mm'),list) else o.get('drill_mm',0))/2) for o in objects if o.get('drill_mm') and (any(o['drill_mm']) if isinstance(o['drill_mm'],list) else True)]
newobjects=[];added=[];moves={};cells=[];screen=ViaScreen(dict(c,objects=objects,zones=[]))
quietids={u for q in prior['quiet_ground_islands'] for u in q['zone_uuids']};quietfields=[shape(z['authored_outline']) for z in c['zones'] if z['uuid'] in quietids]
ground=[(o,shape(ps)) for o in objects if o['net']=='PWR_AGND' for ps in o['layers'].values() if ps];groundtree=STRtree([g for o,g in ground])
def trial(ref,xy,rot,others=[]):
 f=rotate_footprint(fps[ref],xy,rot);side=first(f,'layer')[1][0];g=box(*courtyard(f,side+'.CrtYd'));q=g.buffer(.3,join_style=2)
 if any(q.intersection(obstacles[side][int(i)][1]).area>1e-8 for i in trees[side].query(q)):return
 if any(s==side and q.intersection(h).area>1e-8 for s,h in added+others):return
 os=[transform_object(o,position(fps[ref]),xy,rot) for o in c['objects'] if o.get('ref')==ref]
 for o in os:
  for l,ps in o['layers'].items():
   h=shape(ps)
   if any(geo[l][int(i)][0]['net']!=o['net'] and h.distance(geo[l][int(i)][1])<.21-1e-7 for i in gt[l].query(h.buffer(.211))):return
   if any(h.distance(p)-r<.15 for p,r in holes):return
   if any(other['net']!=o['net'] and other['layers'].get(l) and h.distance(shape(other['layers'][l]))<.21 for other in newobjects):return
   if any(other!=o['net'] and layer==l and h.distance(geom)<.31 for other,layer,geom in screen.added):return
 return f,g,os

def makecell(ref,cap,xy,orientation):
 rot=orientation-angle(fps[ref]);t=trial(ref,xy,rot)
 if not t:return
 f,g,os=t;side=first(f,'layer')[1][0];layer=side+'.Cu'
 canonical=[transform_object(o,position(fps[ref]),[0,0],-angle(fps[ref])) for o in c['objects'] if o.get('ref')==ref]
 # Derive geometry from actual pad locations, so F/B pin order is preserved.
 mapping={}
 for sign in [-1,1]:
  row=sorted([o for o in canonical if sign*o['position_mm'][0]>0],key=lambda o:o['position_mm'][1]);assert len(row)==4
  for o,delta in zip(row,[(sign*2.5,-1.5),(sign*3.4,-.5),(sign*3.4,.5),(sign*2.5,1.5)]):mapping[o['pin']]=list(delta)
 turn=lambda p:list(translate(rotate(Point(p),-orientation,origin=(0,0)),*xy).coords[0])
 vcc=next(o for o in canonical if o['pin']=='8');sx=1 if vcc['position_mm'][0]>0 else -1;sy=1 if vcc['position_mm'][1]>0 else -1
 capxy=turn([sx*4.8,sy*2.1]);caprot=orientation-angle(fps[cap])+(180 if sx<0 else 0)
 ct=trial(cap,capxy,caprot,[(side,g)])
 if not ct:return
 cf,cg,cos=ct;assert first(cf,'layer')[1][0]==side
 pads=os+cos;padgeos=[(o,l,shape(ps)) for o in pads+newobjects for l,ps in o['layers'].items() if ps]
 routes=[];vias=[]
 for o in os:
  via=dict(ref=ref,pin=o['pin'],net=o['net'],position_mm=turn(mapping[o['pin']]),size_mm=.6,drill_mm=.3)
  cp=next(p['position_mm'] for p in canonical if p['pin']==o['pin'])
  escape=turn([(1 if cp[0]>0 else -1)*2.15,cp[1]])
  vias.append(via);routes.append(dict(ref=ref,pin=o['pin'],net=o['net'],layer=layer,width_mm=.2,path_mm=[o['position_mm'],escape,via['position_mm']]))
 capone=next(o for o in cos if o['pin']=='1');captwo=next(o for o in cos if o['pin']=='2');vccvia=next(v for v in vias if v['pin']=='8')
 routes.append(dict(ref=cap,pin='1',net=capone['net'],layer=layer,width_mm=.2,path_mm=[vccvia['position_mm'],capone['position_mm']]))
 direction=rotate(Point(sx*1.05,0),-orientation,origin=(0,0));capg=[captwo['position_mm'][0]+direction.x,captwo['position_mm'][1]+direction.y]
 vias.append(dict(ref=cap,pin='2',net='PWR_AGND',position_mm=capg,size_mm=.6,drill_mm=.3));routes.append(dict(ref=cap,pin='2',net='PWR_AGND',layer=layer,width_mm=.2,path_mm=[captwo['position_mm'],capg]))
 for i,v in enumerate(vias):
  pt=Point(v['position_mm'])
  if not screen.via_legal(v['net'],v['position_mm']):return
  if any(pt.distance(h)<(.51 if o['net']!=v['net'] else .31) for o,l,h in padgeos):return
  if any(pt.distance(Point(w['position_mm']))<(.81 if w['net']!=v['net'] else .56) for w in vias[:i]):return
  if v['net']=='PWR_AGND':
   if any(pt.distance(q)<.51 for q in quietfields):return
   if any(pt.distance(ground[int(i)][1])<.51 for i in groundtree.query(pt.buffer(.511))):return
 for i,r in enumerate(routes):
  line=LineString(r['path_mm'])
  if not screen.legal(r['net'],layer,r['path_mm']):return
  if any(l==layer and o['net']!=r['net'] and line.distance(h)<.31 for o,l,h in padgeos):return
  if any(v['net']!=r['net'] and line.distance(Point(v['position_mm']))<.61 for v in vias):return
  if any(q['net']!=r['net'] and line.distance(LineString(q['path_mm']))<.41 for q in routes[:i]):return
  if r['net']=='PWR_AGND' and any(o['net']=='PWR_AGND' and line.distance(h)<.31 for o,h in geo[layer]):return
 return dict(ref=ref,cap=cap,moves={ref:[xy,rot,False],cap:[capxy,caprot,False]},routes=routes,vias=vias),[(side,g),(side,cg)],pads

def choose(ref,cap,center):
 candidates=[];count=0
 for d,xy,orientation in sorted((math.hypot(ix*.5,iy*.5),[center[0]+ix*.5,center[1]+iy*.5],a) for ix in range(-48,49) for iy in range(-48,49) if math.hypot(ix*.5,iy*.5)<=24 for a in [0,90,180,270]):
  result=makecell(ref,cap,xy,orientation);count+=1
  if count%1000==0:print('SEARCH',ref,count,round(d,2),flush=True)
  if result:
   candidates.append((d,result));print('CANDIDATE',ref,xy,orientation,flush=True)
   if len(candidates)>=6:break
 if not candidates:raise RuntimeError((ref,'no cell with all-pin fanout and bypass'))
 d,(cell,courts,pads)=min(candidates,key=lambda x:x[0]);cells.append(cell);added.extend(courts);newobjects.extend(pads);moves.update(cell['moves'])
 for route in cell['routes']:screen.added.append((route['net'],route['layer'],LineString(route['path_mm'])))
 for v in cell['vias']:
  screen.vias.append((v['net'],v['position_mm']));holes.append((Point(v['position_mm']),.15))
  for l in routing.SIGNAL_LAYERS:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
 print('DONE',ref,cell['moves'],flush=True)
 Path('/private/tmp/permission-cells-v2-partial.json').write_text(json.dumps(dict(cells=cells,moves=moves,retired_objects=sorted(retired),side_reconciliations=reconciled),indent=2))
choose('E_U42','E_C85',[100,137])
updated=dict(fps)
for ref,(xy,rot,flip) in moves.items():updated[ref]=rotate_footprint(fps[ref],xy,rot)
mechanical_check(updated,set(moves),placement)
Path('/private/tmp/permission-cells-v2.json').write_text(json.dumps(dict(cells=cells,moves=moves,retired_objects=sorted(retired),side_reconciliations=reconciled,all_pin_fanout_screened=True,native_validation_pending=True),indent=2))
