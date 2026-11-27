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
old+=json.loads((B/'r39_isolate_pair/routes.json').read_text())['edges']
segments=[(e['id'],np.array(a),np.array(b)) for e in old for a,b in zip(e['points_mm'],e['points_mm'][1:])]
A=np.array([a for _,a,b in segments]);C=np.array([b for _,a,b in segments]);lo=np.minimum(A,C);hi=np.maximum(A,C)
def route(index,angle,low,tilt=0,lift=0,postrise=0):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_isolate_'+str(index)+':1']
 w=Wire([196+2.54*index,48.46,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 if lift:w.line([w.p[0],w.p[1],w.p[2]+lift])
 w.arc([0,0,1],T,12,90)
 if postrise:w.s_curve(T,[0,0,1],12,postrise)
 if index==2 or angle<170:
  if angle>180:w.arc(T,[T[1],-T[0],0],12,angle-180)
  else:w.arc(T,[-T[1],T[0],0],12,180-angle)
  w.s_curve([-1,0,0],[0,tilt,-math.sqrt(1-tilt**2)],12,(39.04+lift+postrise-low)/math.sqrt(1-tilt**2))
 else:
  w.s_curve(T,[tilt*T[1],-tilt*T[0],-math.sqrt(1-tilt**2)],12,(39.04+lift+postrise-low)/math.sqrt(1-tilt**2))
  if angle>180:w.arc(T,[T[1],-T[0],0],12,angle-180)
  else:w.arc(T,[-T[1],T[0],0],12,180-angle)
 if index==3:
  delta=end[1]-w.p[1]
  w.s_curve([-1,0,0],[0,1 if delta>0 else -1,0],12,abs(delta))
  rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[0]>end[0]+run
  w.line([end[0]+run,end[1],low]);w.s_curve([-1,0,0],[0,0,1],12,rise)
  return w
 assert w.p[0]>end[0]-13
 w.line([end[0]-13,w.p[1],low]);w.arc([-1,0,0],[0,1,0],12,90)
 w.line([w.p[0],100-4*(index-2),low]);w.arc([0,1,0],[1,0,0],12.5,180)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>end[1]+run
 w.line([end[0],end[1]+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 return w
if __name__=='__main__':
 for name,index,angle,low,tilt,lift,postrise in [('S10',2,202,28.6,0,.08,0),('S11',3,130,31.2,-.2,0,.8)]:
  w=route(index,angle,low,tilt,lift,postrise)
  print(name, 'host planning only; use verify.py and native evidence',len(w.points))
