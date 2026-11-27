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
old+=json.loads((B/'r34_panel_inputs/routes.json').read_text())['edges']+json.loads((B/'r37_tap_auto/routes.json').read_text())['edges']
segments=[(e['id'],np.array(a),np.array(b)) for e in old for a,b in zip(e['points_mm'],e['points_mm'][1:])]
A=np.array([a for _,a,b in segments]);C=np.array([b for _,a,b in segments]);lo=np.minimum(A,C);hi=np.maximum(A,C)
old+=json.loads((B/'r38_nudge_up/routes.json').read_text())['edges']
segments=[(e['id'],np.array(a),np.array(b)) for e in old for a,b in zip(e['points_mm'],e['points_mm'][1:])]
A=np.array([a for _,a,b in segments]);C=np.array([b for _,a,b in segments]);lo=np.minimum(A,C);hi=np.maximum(A,C)
def route(index,angle,low):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_isolate_'+str(index)+':1']
 w=Wire([196+2.54*index,48.46,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,39.04-low)
 w.arc(T,[T[1],-T[0],0],12,angle-180)
 assert w.p[0]>end[0]+36
 w.line([end[0]+36,w.p[1],low]);w.arc([-1,0,0],[0,1,0],12,90)
 w.line([w.p[0],80+3*index,low]);w.arc([0,1,0],[-1,0,0],12,180)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>end[1]+run
 w.line([end[0],end[1]+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 return w
if __name__=='__main__':
 rows=[]
 for index in [0,1]:
  for angle in [200,205,210,215,220]:
   for low in [25.8,27,28.6,30.2]:
    try:w=route(index,angle,low)
    except AssertionError:continue
    minimum=999;who=None
    for a,b in zip(w.points,w.points[1:]):
     lowers=np.linalg.norm(np.maximum(0,np.maximum(np.minimum(a,b),lo)-np.minimum(np.maximum(a,b),hi)),axis=1)
     for i in np.where(lowers<minimum)[0]:
      d=distance(a,b,A[i],C[i])
      if d<minimum:minimum=d;who=segments[i][0]
    rows.append({'index':index,'angle':angle,'low':low,'minimum_polyline_centerline_gap_mm':minimum,'nearest':who,'native_verified':False})
 rows.sort(key=lambda r:r['minimum_polyline_centerline_gap_mm'],reverse=True)
 (H/'corridor-search.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows[:20],indent=2))
