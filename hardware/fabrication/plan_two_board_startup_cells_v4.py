"""Place local bypasses and plan supply/return completion for eight startup logic ICs."""
import copy,json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_two_board_buck_cell import position,transform_object,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
BASE=STAGING/'two-board-power-startup-references-native-04'
CAP=STAGING/'two-board-power-routing-inputs-2210-startup-references-04/capture.json'
OUT=STAGING/'two-board-startup-cells-plan-04'


def run():
 assert not OUT.exists()
 c=json.loads(CAP.read_text())
 for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 b=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(b,'footprint')}
 objects=copy.deepcopy(c['objects']);old={o['uuid']:o for o in objects};moves={};routes=[];vias=[];joins=[];cells=[];deferred=[]
 placementpath=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placementpath.read_text());reconciled=[]
 for row in placement['parts']:
  if row['id'] in fps:
   side=str(first(fps[row['id']],'layer')[1])[0]
   if row['side']!=side:reconciled.append(dict(ref=row['id'],old_side=row['side'],current_side=side));row['side']=side
 routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
 quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
 quietids={u for path in quietpaths for q in json.loads(path.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
 zmap={z['uuid']:z for z in c['zones']};quiet=[routing.shape(zmap[u]['authored_outline']) for u in quietids]
 main5=routing.shape(zmap['2fff880c-5da4-5609-a6d1-dfc1d5b3e287']['polygons'])
 main6=routing.shape(zmap['4b63f119-2e71-5d61-96f6-8b78a1f5c6cb']['polygons'])
 ground_anchor=unary_union([main5,main6])
 def pad(ref,pin,os=None):return next(o for o in (objects if os is None else os) if o.get('ref')==ref and o.get('pin')==pin)
 def screen(os):
  viaobjects=[]
  for i,v in enumerate(vias):
   g=Point(v['position_mm']).buffer(.3,quad_segs=64)
   viaobjects.append(dict(uuid='planned-via-'+str(i),kind='PCB_VIA',net=v['net'],position_mm=v['position_mm'],width_mm=.6,drill_mm=.3,layers={l:[dict(outer=list(g.exterior.coords),holes=[])] for l in c['copper_layers']}))
  s=ViaScreen(dict(c,objects=os+viaobjects,zones=[]))
  for r in routes:s.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
  return s
 def addroute(label,net,path):
  rr=dict(label=label,net=net,layer='B.Cu',width_mm=.2,path_mm=path);routes.append(rr);return rr
 def pad_checker(ref):
  rows=[]
  for o in objects:
   if o.get('ref')==ref:continue
   for layer,ps in o['layers'].items():
    if layer in ['F.Cu','B.Cu'] and ps:rows.append((layer,routing.shape(ps)))
  tree=STRtree([g for l,g in rows])
  def clear(os):
   for o in os:
    if o.get('ref')!=ref:continue
    for layer,ps in o['layers'].items():
     if not ps:continue
     g=routing.shape(ps)
     for idx in tree.query(g.buffer(.26)):
      other,h=rows[int(idx)]
      if other==layer and g.distance(h)<.26:return False
   return True
  return clear
 # Regression checks: the two trial-03 capacitor moves collided with existing
 # tracks/vias despite clear component courtyards. Reject both complete pads.
 rejected_trial=STAGING/'two-board-startup-cells-plan-03/plan.json'
 previous=json.loads(rejected_trial.read_text())
 for ref,(xy,rot,flip) in previous['moves'].items():
  trial=[transform_object(o,position(fps[ref]),xy,rot) if o.get('ref')==ref else o for o in objects]
  assert not pad_checker(ref)(trial),('Failed to reject known pad collision',ref)
 def ground_fit(s,start,power_route):
  s.added.append(('PWR_V2V5_AUX','B.Cu',LineString(power_route)))
  try:
   for _,xy in sorted((math.hypot(dx,dy),[round(start[0]+dx/5,6),round(start[1]+dy/5,6)]) for dx in range(-10,11) for dy in range(-10,11) if 3<=math.hypot(dx,dy)<=10):
    pt=Point(xy)
    if not ground_anchor.covers(pt.buffer(.31)) or any(pt.distance(g)<=.515 for g in quiet) or not s.via_legal('PWR_AGND',xy):continue
    if s.simple('PWR_AGND','B.Cu',start,xy,3):return True
   return False
  finally:s.added.pop()
 def powerpath(s,start,end):
  options=[]
  for path in routing.candidate_paths(start,end):
   path=[list(p) for i,p in enumerate(path) if not i or list(p)!=list(path[i-1])]
   if len(path)<2:continue
   g=LineString(path)
   if g.length<=4.5 and s.legal('PWR_V2V5_AUX','B.Cu',path) and g.buffer(.1).difference(main6.buffer(.0015)).area<1e-6:options.append((g.length,path))
  return min(options)[1] if options else None
 for i in range(21,29):
  chip=f'E_U{i}';cap=f'E_C{i+45}';cpads=[o for o in objects if o.get('ref')==cap]
  assert all(len(c['all_groups'][o['group']])==1 for o in cpads)
  supply=pad(chip,'14');ground=pad(chip,'7');assert supply['net']=='PWR_V2V5_AUX' and ground['net']=='PWR_AGND'
  assert len(c['all_groups'][supply['group']])==len(c['all_groups'][ground['group']])==1
  clearpads=pad_checker(cap)
  s=screen(objects);p=powerpath(s,supply['position_mm'],pad(cap,'1')['position_mm']);chosen=None
  if p and ground_fit(s,pad(cap,'2')['position_mm'],p):chosen=(None,objects,fps[cap],p)
  elif not main6.buffer(.0015).covers(Point(supply['position_mm']).buffer(.1)):
   deferred.append(dict(chip=chip,reason='Supply pad lacks full adjacent In6 ground coverage; existing inner routing or reference outline needs coordinated repair'));continue
  else:
   candidates=[];origin=position(fps[cap])
   for rot in [0,90,180,270]:
    rotated=transform_object(pad(cap,'1'),origin,origin,rot)['position_mm']
    for distance in [1.5,1.9,2.3,2.7,3.1]:
     for dx,dy in [(0,1),(1,0),(0,-1),(-1,0),(1,1),(-1,1),(1,-1),(-1,-1)]:
      xy=[supply['position_mm'][0]+dx*distance,supply['position_mm'][1]+dy*distance]
      target=[origin[0]+xy[0]-rotated[0],origin[1]+xy[1]-rotated[1]]
      f=rotate_footprint(fps[cap],target,rot)
      trialfps=dict(fps,**{cap:f})
      try:mechanical_check(trialfps,{cap},placement)
      except AssertionError:continue
      os=[transform_object(o,origin,target,rot) if o.get('ref')==cap else o for o in objects]
      if not clearpads(os):continue
      ss=screen(os);pp=powerpath(ss,supply['position_mm'],pad(cap,'1',os)['position_mm'])
      if pp and ground_fit(ss,pad(cap,'2',os)['position_mm'],pp):candidates.append((LineString(pp).length,target,rot,os,f,pp))
     if candidates:break
    if candidates:break
   if candidates:
    _,target,rot,os,f,p=min(candidates,key=lambda v:v[0]);chosen=([target,rot,False],os,f,p)
  if not chosen:deferred.append(dict(chip=chip,reason='No short referenced bypass placement/path found'));continue
  move,objects,f,p=chosen;fps[cap]=f
  if move:moves[cap]=move
  addroute(chip+' bypass','PWR_V2V5_AUX',p);joins.append(dict(net='PWR_V2V5_AUX',left=[chip,'14'],right=[cap,'1']))
  cell=dict(chip=chip,bypass=cap,bypass_length_mm=LineString(p).length,ground_paths=[])
  groundpins=[(chip,'7'),(cap,'2')]+([(chip,'9'),(chip,'12')] if chip=='E_U22' else [])
  for ref,pin in groundpins:
   o=pad(ref,pin);assert o['net']=='PWR_AGND' and len(c['all_groups'][o['group']])==1
   start=o['position_mm'];s=screen(objects);options=[]
   for v in vias:
    if v['net']!='PWR_AGND' or math.dist(start,v['position_mm'])>2.5:continue
    pp=s.simple('PWR_AGND','B.Cu',start,v['position_mm'],3)
    if pp:options.append((pp[0],False,v['position_mm'],pp[1]))
   sites=sorted((math.hypot(dx,dy),[round(start[0]+dx/10,6),round(start[1]+dy/10,6)]) for dx in range(-20,21) for dy in range(-20,21) if 6<=math.hypot(dx,dy)<=20)
   for _,xy in sites:
    pt=Point(xy)
    if not ground_anchor.covers(pt.buffer(.31)) or any(pt.distance(g)<=.515 for g in quiet) or not s.via_legal('PWR_AGND',xy):continue
    pp=s.simple('PWR_AGND','B.Cu',start,xy,3)
    if pp:options.append((pp[0],True,xy,pp[1]));break
   if not options:deferred.append(dict(chip=chip,pad=ref+'.'+pin,reason='No local through-ground transition to existing main In5/In6'));continue
   _,new,xy,pp=min(options,key=lambda v:v[0]);rr=addroute(ref+'.'+pin+' return','PWR_AGND',pp)
   if new:vias.append(dict(net='PWR_AGND',position_mm=xy,size_mm=.6,drill_mm=.3))
   joins.append(dict(net='PWR_AGND',left=[ref,pin],right=['P_C103','2']))
   cell['ground_paths'].append(rr)
  cells.append(cell);print(chip,'bypass',round(cell['bypass_length_mm'],3),'grounds',len(cell['ground_paths']),'move',move,flush=True)
 for chip in ['E_U21','E_U22','E_U23']:
  left,right=pad(chip,'3'),pad(chip,'4');assert left['net']==right['net'] and left['group']!=right['group']
  pp=[left['position_mm'],right['position_mm']];s=screen(objects)
  if s.legal(left['net'],'B.Cu',pp) and LineString(pp).buffer(.1).difference(main6.buffer(.0015)).area<1e-6:
   addroute(chip+' local feedback',left['net'],pp);joins.append(dict(net=left['net'],left=[chip,'3'],right=[chip,'4']))
  else:deferred.append(dict(chip=chip,reason='Local feedback lacks physical/reference screen'))
 sources=[Path(__file__),CAP,rejected_trial,STAGING/'two-board-power-startup-cells-native-01/drc.json',placementpath,*quietpaths,BASE/'power_protection.kicad_pcb',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_layer_detours.py','route_two_board_buck_cell.py','repack_two_board_buck_input.py']],STAGING/'assembly-layout-04/allocation.json']
 OUT.mkdir();d=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},moves=moves,routes=routes,vias=vias,joins=joins,cells=cells,deferred=deferred,side_reconciliations=reconciled,expected_closed_connections=len(joins),reference_zone_ids=['2fff880c-5da4-5609-a6d1-dfc1d5b3e287','4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'],native_validation_pending=True,fabrication_released=False)
 (OUT/'plan.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(cells=len(cells),joins=len(joins),vias=len(vias),moves=moves,deferred=deferred)),flush=True)


if __name__=='__main__':run()
