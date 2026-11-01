from pathlib import Path
import json,sys,heapq,math,hashlib
from collections import defaultdict
from shapely.geometry import LineString,Point,box
from shapely.ops import unary_union
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.power_distribution.p03.route import PowerRouter,coded
R=Path('/private/tmp/afx-p03-strict-current');SOURCE=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/electronics/power_distribution/p03/candidates/aux-u10-combined')
old=json.load(open(SOURCE/'generated/aux-local-loop-verification.json'))

def check(path):
 blob=path.read_bytes();t=read_sexpr(blob.decode());track=[]
 for s in children(t,'segment'):
  if str(first(s,'layer')[1])!='F.Cu':continue
  track.append(dict(net=str(first(s,'net')[1]).lstrip('/'),width=float(first(s,'width')[1]),start=tuple(round(float(v)-100,6) for v in first(s,'start')[1:3]),end=tuple(round(float(v)-100,6) for v in first(s,'end')[1:3]),uuid=str(first(s,'uuid')[1])))
 rr=PowerRouter(coded(t));rows=[]
 for row in old['actual_direct_front_paths']:
  cap=row['cap'];net=row['net'];minimum=row['minimum_authored_width_mm'];upin=row['U102_pin'];cpin=row['pin'];start=next(p for p in rr.by_ref[cap] if p['pin']==cpin and p['layers']==(0,));end=next(p for p in rr.by_ref['U102'] if p['pin']==upin and p['layers']==(0,));assert start['net']==end['net']==net
  # Strict localphysicalcell only. No zone, otherpad, barrel, or off-F layer is
  # inserted as a graph bridge. AuthoredFcentrelines must physicallymeet.
  bbox=box(19,11,33.5,26.5)
  selected=[x for x in track if x['net']==net and x['width']>=minimum-1e-9 and bbox.covers(LineString([x['start'],x['end']]))]
  union=unary_union([LineString([x['start'],x['end']]) for x in selected]);lines=list(union.geoms) if hasattr(union,'geoms') else [union]
  graph=defaultdict(dict)
  for l in lines:
   if l.is_empty:continue
   coords=[tuple(round(v,6) for v in x) for x in l.coords]
   for a0,b0 in zip(coords,coords[1:]):
    dd=math.dist(a0,b0)
    if dd:graph[a0][b0]=min(dd,graph[a0].get(b0,1e30));graph[b0][a0]=min(dd,graph[b0].get(a0,1e30))
  a0=tuple(start['xy']);b0=tuple(end['xy']);cost={a0:0};prev={};q=[(0,a0)];seen=set()
  while q:
   score,p=heapq.heappop(q)
   if p in seen:continue
   seen.add(p)
   if p==b0:break
   for n,d in graph.get(p,{}).items():
    if score+d<cost.get(n,1e30):cost[n]=score+d;prev[n]=p;heapq.heappush(q,(score+d,n))
  found=b0 in seen;points=[]
  if found:
   points=[b0]
   while points[-1]!=a0:points.append(prev[points[-1]])
   points.reverse()
  rows.append(dict(cap=cap,pin=cpin,U102_pin=upin,net=net,minimum_authored_width_mm=minimum,
   actual_cap_and_regulator_sameF=True,exact_authored_front_track_path_present=found,
   actual_new_points_local_mm=points,actual_new_authored_centreline_length_mm=cost.get(b0),
   old_receipt_centreline_length_mm=row['centreline_length_mm'],local_bbox_mm=[19,11,33.5,26.5],
   zones_or_vertical_or_via_pad_bridges_used=False,selected_actual_Fsegment_count=len(selected),
   physical_hole_annulus_cap_and_RF_effects_qualified=False))
 return dict(pcb_sha256=hashlib.sha256(blob).hexdigest(),six_paths=rows,all_six_actual_front_paths_present=all(x['exact_authored_front_track_path_present'] for x in rows),old_literal_contract_not_claimed_unchanged=True,physical_qualified=False)
report=check(R/'centered2/power_p03.kicad_pcb');(R/'six-front-paths-new.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['all_six_actual_front_paths_present']
