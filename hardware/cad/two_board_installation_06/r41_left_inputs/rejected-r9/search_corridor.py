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
old+=json.loads((B/'r40_isolate_upper_pair/routes.json').read_text())['edges']
segments=[(e['id'],np.array(a),np.array(b)) for e in old for a,b in zip(e['points_mm'],e['points_mm'][1:])]
A=np.array([a for _,a,b in segments]);C=np.array([b for _,a,b in segments]);lo=np.minimum(A,C);hi=np.maximum(A,C)
def route(angle=130,low=27,lane=128.5):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_nudge_down:1']
 w=Wire([203.62,51,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,39.04-low)
 w.arc(T,[-T[1],T[0],0],12,180-angle)
 assert w.p[0]>lane+12
 w.line([lane+12,w.p[1],low]);w.arc([-1,0,0],[0,-1,0],12,90)
 shift=np.array([end[0]-lane,0,end[2]-low]);offset=np.linalg.norm(shift);run=24*math.sin(math.acos(1-offset/24));assert w.p[1]>end[1]+run
 w.line([lane,end[1]+run,low]);w.s_curve([0,-1,0],shift/offset,12,offset)
 return w
def route_early_rise(angle=130,low=27.2,lane=129,rise_end=63):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_nudge_down:1']
 w=Wire([203.62,51,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,39.04-low)
 w.arc(T,[-T[1],T[0],0],12,180-angle)
 assert w.p[0]>lane+12
 w.line([lane+12,w.p[1],low]);w.arc([-1,0,0],[0,-1,0],12,90)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>=rise_end+run
 w.line([lane,rise_end+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 shift=end[0]-lane;run=24*math.sin(math.acos(1-abs(shift)/24));assert w.p[1]>end[1]+run
 w.line([lane,end[1]+run,end[2]]);w.s_curve([0,-1,0],[math.copysign(1,shift),0,0],12,abs(shift))
 return w
def route_west_rise(angle=130,low=27.2,lane=129,rise_end_x=145):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_nudge_down:1']
 w=Wire([203.62,51,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,39.04-low)
 w.arc(T,[-T[1],T[0],0],12,180-angle)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[0]>=rise_end_x+run
 w.line([rise_end_x+run,w.p[1],low]);w.s_curve([-1,0,0],[0,0,1],12,rise)
 assert w.p[0]>=lane+12
 w.line([lane+12,w.p[1],end[2]]);w.arc([-1,0,0],[0,-1,0],12,90)
 shift=end[0]-lane;run=24*math.sin(math.acos(1-abs(shift)/24));assert w.p[1]>end[1]+run
 w.line([lane,end[1]+run,end[2]]);w.s_curve([0,-1,0],[math.copysign(1,shift),0,0],12,abs(shift))
 return w
def route_source(angle=130,low=23.6,first_drop=2,straight=0):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_source_input:1']
 w=Wire([198.54,51,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,first_drop)
 if straight:w.line(w.p+np.array(T)*straight)
 w.arc(T,[T[1],-T[0],0],12,angle-90)
 w.s_curve([0,1,0],[0,0,-1],12,39.04-first_drop-low)
 assert w.p[1]<104;w.line([w.p[0],104,low]);w.arc([0,1,0],[-1,0,0],12,90)
 w.line([end[0]+12,w.p[1],low]);w.arc([-1,0,0],[0,-1,0],12,90)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>end[1]+run
 w.line([end[0],end[1]+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 return w
def route_source_west(angle=155.4,low=24.6,first_drop=1,turn_x=145):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_source_input:1']
 w=Wire([198.54,51,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,first_drop)
 w.arc(T,[-T[1],T[0],0],12,180-angle)
 assert w.p[0]>turn_x;w.line([turn_x,w.p[1],w.p[2]]);w.arc([-1,0,0],[0,1,0],12,90)
 w.s_curve([0,1,0],[0,0,-1],12,39.04-first_drop-low)
 assert w.p[1]<104;w.line([w.p[0],104,low]);w.arc([0,1,0],[-1,0,0],12,90)
 w.line([end[0]+12,w.p[1],low]);w.arc([-1,0,0],[0,-1,0],12,90)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>end[1]+run
 w.line([end[0],end[1]+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 return w
def route_source_low_west(angle=155,low=24.6,first_drop=2,west_z=28.6,turn_x=149):
 end=json.loads((B/'r12_ground/ground-routes.json').read_text())['endpoints_mm']['button_source_input:1']
 w=Wire([198.54,51,27.04]);az=math.radians(angle);T=[math.cos(az),math.sin(az),0]
 w.arc([0,0,1],T,12,90);w.s_curve(T,[0,0,-1],12,first_drop)
 w.arc(T,[-T[1],T[0],0],12,180-angle)
 w.s_curve([-1,0,0],[0,0,-1],12,39.04-first_drop-west_z)
 assert w.p[0]>turn_x;w.line([turn_x,w.p[1],w.p[2]]);w.arc([-1,0,0],[0,1,0],12,90)
 w.s_curve([0,1,0],[0,0,-1],12,west_z-low)
 assert w.p[1]<104;w.line([w.p[0],104,low]);w.arc([0,1,0],[-1,0,0],12,90)
 w.line([end[0]+12,w.p[1],low]);w.arc([-1,0,0],[0,-1,0],12,90)
 rise=end[2]-low;run=24*math.sin(math.acos(1-rise/24));assert w.p[1]>end[1]+run
 w.line([end[0],end[1]+run,low]);w.s_curve([0,-1,0],[0,0,1],12,rise)
 return w
if __name__=='__main__':
 rows=[]
 for angle in [125,130,135,140]:
  for low in [25.2,26.8,27.2,28.6]:
   for lane in [128,128.5,129]:
    try:w=route(angle,low,lane)
    except AssertionError:continue
    minimum=999;who=None
    for a,b in zip(w.points,w.points[1:]):
     lowers=np.linalg.norm(np.maximum(0,np.maximum(np.minimum(a,b),lo)-np.minimum(np.maximum(a,b),hi)),axis=1)
     for i in np.where(lowers<minimum)[0]:
      d=distance(a,b,A[i],C[i])
      if d<minimum:minimum=d;who=segments[i][0]
    rows.append(dict(angle=angle,low=low,lane=lane,gap=minimum,nearest=who))
 rows.sort(key=lambda r:r['gap'],reverse=True);(H/'corridor-search.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows[:10],indent=2))
