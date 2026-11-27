"""Bounded paired-via access screen with source pin identities and all-layer obstacles."""
import json,math
from pathlib import Path
from shapely.geometry import box,Point,LineString
from shapely.ops import unary_union
from shapely.prepared import prep
from ..routed.plan import shape,sha
H=Path(__file__).resolve().parent
c=json.loads((H/'capture-02/capture.json').read_text());by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};net='/P_power_supply/AUX_PREREG5';assert all(by[p]['net']==net for p in ['P_C102.1','P_C907.1','P_U102.8','P_U102.5']);q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qi=set(q['retained_object_uuids']);qz={z['zone_uuid'] for z in q['plane_exclusions']};region=box(185,122,195,132);obj=[(o,unary_union([shape(g) for g in o['layers'].values()])) for o in c['objects'] if region.buffer(1).contains(Point(o['position_mm'])) or any(shape(g).intersects(region) for g in o['layers'].values())];zones=[(z,shape(z['polygons'])) for z in c['zones']]
def blocked(n):
 # Ground antipads are only proposed, not authorized; every other net's filled copper stays an obstacle.
 return unary_union([g.buffer(.502) for o,g in obj if o['net']!=n or o['uuid'] in qi]+[g.buffer(.502) for z,g in zones if z['net'] not in [n,'PWR_AGND'] or z['uuid'] in qz])
sb=prep(blocked(net));gb=prep(blocked('PWR_AGND'));smd=prep(unary_union([shape(g).buffer(.30) for o in c['objects'] if o['kind']=='PAD' and len(o['layers'])<3 for g in o['layers'].values()]));grounds={l:unary_union([g for z,g in zones if z['layer']==l and z['net']=='PWR_AGND' and z['uuid'] not in qz]) for l in ['In1.Cu','In6.Cu']}
rows=[]
for label in ['P_C907.1','P_U102.5']:
 target=by[label];near=Point(target['position_mm']);candidates=[]
 for ix in range(1850,1951):
  for iy in range(1220,1321):
   p=Point(ix/10,iy/10)
   if p.distance(near)>3 or sb.intersects(p) or smd.intersects(p):continue
   pairs=[]
   for dx in range(-9,10,2):
    for dy in range(-9,10,2):
     dist=math.hypot(dx,dy)/10
     if not .8<=dist<=1:continue
     g=Point(p.x+dx/10,p.y+dy/10)
     if gb.intersects(g) or smd.intersects(g):continue
     if not all(r.covers(g.buffer(.3)) for r in grounds.values()):continue
     pairs.append({'position_mm':[g.x,g.y],'spacing_mm':dist})
   if pairs:candidates.append({'position_mm':[p.x,p.y],'target_distance_mm':p.distance(near),'paired_ground_candidates':pairs})
 candidates.sort(key=lambda v:v['target_distance_mm']);rows.append({'target':label,'candidates':candidates});print(label,len(candidates),candidates[:2],flush=True)
(H/'screen.json').write_text(json.dumps({'capture_sha256':sha(H/'capture-02/capture.json'),'script_sha256':sha(Path(__file__)),'via_size_mm':.6,'drill_mm':.3,'clearance_mm':.2,'smd_drill_edge_guard_mm':.15,'rows':rows,'qualified':False},indent=2)+'\n')
