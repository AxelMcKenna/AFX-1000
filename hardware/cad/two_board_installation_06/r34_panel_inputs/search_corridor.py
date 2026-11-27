"""Host-only corridor candidates; exact native obstacles remain mandatory."""
import json,math
from pathlib import Path
import numpy as np
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
from hardware.cad.two_board_installation_06.r12_ground.verify import distance
H=Path(__file__).resolve().parent;B=H.parent
bows=json.loads((B/'r22_ground_signal_clearance/bows.json').read_text())
old=json.loads((B/'r14_left_ground/left-routes.json').read_text())['edges']+[e for e in json.loads((B/'r15_right_ground/right-routes.json').read_text())['edges'] if e['id'] not in bows['replaces_wires']]+bows['edges']+json.loads((B/'r20_scene_signal/route.json').read_text())['edges']+json.loads((B/'r21_adjacent_signals/routes.json').read_text())['edges']
segments=[(e['id'],np.array(a),np.array(b)) for e in old for a,b in zip(e['points_mm'],e['points_mm'][1:])]
A=np.array([a for _,a,b in segments]);C=np.array([b for _,a,b in segments]);lo=np.minimum(A,C);hi=np.maximum(A,C)
end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_scene_4:1']
rows=[]
for angle in [180,185,190,195,200,205,210,215,220,225]:
 for low in [25.8,27.1,30.8,31.2]:
  for tilt in [-.5,-.3,-.15,0,.15,.3,.5]:
   w=Wire([226.08,48.46,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
   w.arc([0,0,1],T,12,90);w.s_curve(T,[tilt*T[1],-tilt*T[0],-math.sqrt(1-tilt**2)],12,(39.04-low)/math.sqrt(1-tilt**2));w.arc(T,[-T[1],T[0],0],14,360-angle)
   if end[0]-14<=w.p[0]:continue
   w.line([end[0]-14,w.p[1],low]);w.arc([1,0,0],[0,1,0],14,90)
   if w.p[1]>end[1]-18:continue
   w.line([end[0],end[1]-18,low]);dz=end[2]-low;r=(18**2+dz**2)/(2*dz);w.arc([0,1,0],[0,0,1],r,math.degrees(2*math.atan2(dz,18)))
   minimum=999;who=None
   for a,b in zip(w.points,w.points[1:]):
    lowers=np.linalg.norm(np.maximum(0,np.maximum(np.minimum(a,b),lo)-np.minimum(np.maximum(a,b),hi)),axis=1)
    for i in np.where(lowers<minimum)[0]:
     d=distance(a,b,A[i],C[i])
     if d<minimum:minimum=d;who=segments[i][0]
   rows.append({'angle':angle,'low':low,'tilt':tilt,'minimum_polyline_centerline_gap_mm':minimum,'nearest':who,'min_y':min(p[1] for p in w.points),'native_verified':False})
rows.sort(key=lambda r:r['minimum_polyline_centerline_gap_mm'],reverse=True)
(H/'corridor-search.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows[:12],indent=2))
