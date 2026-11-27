"""Conservative surface-only supply screen for retained startup cells on TBP72."""
import json,math
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.plan_two_board_aux_local_distribution import anchored_fields
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing
CAP=STAGING/'two-board-power-routing-inputs-aux-ground-reuse-01/capture.json'
OUT=STAGING/'two-board-aux-startup-supply-plan-02'

def run():
 assert not OUT.exists()
 cap=json.loads(CAP.read_text())
 for n,h in cap['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 fields,excluded=anchored_fields(cap)
 main=next(o['group'] for o in cap['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
 aux=next(o['group'] for o in cap['objects'] if o.get('ref')=='P_U102' and o.get('pin')=='1')
 adjacent={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}
 routing.WIDTH=.3;routing.SIGNAL_LAYERS=tuple(adjacent)
 screen=MountScreen(dict(cap,zones=[z for z in cap['zones'] if z['keepout']]))
 # Preserve all currently referenced inner-track copper, with conservative
 # surface clearance plus plane-minimum-width allowance, including quiet grounds.
 protected={l:[] for l in adjacent}
 for o in cap['objects']:
  if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers']
  for outer,inner in adjacent.items():
   if layer!=inner:continue
   band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
   for (fl,gid),field in fields.items():
    if fl==outer:
     covered=band.intersection(field)
     if not covered.is_empty:protected[outer].append(covered.buffer(.435))
 protected={l:unary_union(gs) for l,gs in protected.items()}
 class ReferencedScreen(MountScreen):
  def legal(self,net,layer,points):
   line=LineString(points)
   return fields[adjacent[layer],main].covers(line.buffer(.15)) and not line.intersects(protected[layer]) and super().legal(net,layer,points)
 grid_screen=ReferencedScreen(dict(cap,zones=[z for z in cap['zones'] if z['keepout']]))
 selected=[o for o in cap['objects'] if (o.get('ref'),o.get('pin')) in [('E_U19','4'),('E_U35','8'),('E_C78','1')]]
 source=[o for o in cap['objects'] if o['group']==aux]
 rows=[]
 for start in selected:
  options=[]
  # Include the local bypass join as a separate alternative; it is not a source feed.
  targets=source+[o for o in selected if o['group']!=start['group'] and math.dist(o['position_mm'],start['position_mm'])<8]
  for end in targets:
   for layer in start['layers'].keys()&end['layers'].keys()&adjacent.keys():
    for xy in [end['position_mm']]+([end['end_mm']] if 'end_mm' in end else []):
     dist=math.dist(start['position_mm'],xy)
     if 0<dist<=30:options.append((dist,layer,end['uuid'],xy,end['group']))
  counts=dict(candidates=0,obstacle=0,reference=0,retained_reference=0);best={}
  for distance,layer,target,end,gid in sorted(options)[:80]:
   category='source_feed' if gid==aux else 'local_join'
   for path in routing.candidate_paths(start['position_mm'],end):
    path=[p for i,p in enumerate(path) if not i or p!=path[i-1]]
    if len(path)<2:continue
    line=LineString(path)
    if line.length>40 or category in best and line.length>=best[category]['length_mm']:continue
    counts['candidates']+=1
    if not screen.legal('PWR_V2V5_AUX',layer,path):counts['obstacle']+=1;continue
    if not fields[adjacent[layer],main].covers(line.buffer(.15)):counts['reference']+=1;continue
    if line.intersects(protected[layer]):counts['retained_reference']+=1;continue
    best[category]=dict(net='PWR_V2V5_AUX',layer=layer,width_mm=.3,path_mm=path,length_mm=line.length,target_uuid=target,target_group=gid,source_group=start['group'],reference_layer=adjacent[layer],native_validation_pending=True)
  grid_attempts=[]
  if fields['In6.Cu',main].covers(Point(start['position_mm']).buffer(.15)):
   candidates=[o for o in sorted(options) if o[4]==aux][:3]
   for distance,layer,target,end,gid in candidates:
    path=grid_screen.grid_path('PWR_V2V5_AUX',layer,start['position_mm'],end,budget=12000)
    grid_attempts.append(dict(target_uuid=target,budget=12000,found=bool(path)))
    if path:
     line=LineString(path)
     if line.length<=40 and ('source_feed' not in best or line.length<best['source_feed']['length_mm']):
      best['source_feed']=dict(net='PWR_V2V5_AUX',layer=layer,width_mm=.3,path_mm=path,length_mm=line.length,target_uuid=target,target_group=gid,source_group=start['group'],reference_layer=adjacent[layer],native_validation_pending=True)
  counts['grid_attempts']=grid_attempts
  rows.append(dict(ref=start['ref'],pin=start['pin'],layers=list(start['layers']),screen_counts=counts,options=best))
 sources=[Path(__file__),CAP,*[REPO/'hardware/fabrication'/n for n in ['plan_two_board_aux_local_distribution.py','route_two_board_power_local_v2.py','route_two_board_power_local.py','route_nf_surface.py']]]
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},rows=rows,excluded_unanchored_fragments=excluded,source_group=aux,main_ground_group=main,new_vias=0,native_validation_pending=True,board_changed=False,qualification_complete=False,limitations=['Options are independent alternatives, not a simultaneously routed board.','No vias, no zone modification, no component movement; bounded candidate search does not prove impossibility.','Full native fill, DRC, group preservation and reference review required before acceptance.'])
 OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':run()
