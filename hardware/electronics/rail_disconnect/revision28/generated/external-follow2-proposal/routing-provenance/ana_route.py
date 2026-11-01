from pathlib import Path
import json,math
R=Path(__file__).parent;p=R/'build.py';namespace={'__file__':str(p),'__name__':'joint_literal_replay'};exec(compile(p.read_text().split('# First join OUT_VALID')[0],str(p),'exec'),namespace)
from surface_local import connect
rt=namespace['rt'];t=namespace['t'];point=(66.55,51.86)
from hardware.electronics.rail_disconnect.routing.check import point_segment
bad=[]
for g in rt.geometry:
 if g['net'] in ['ANA_PG1','BULK_BODY_NOVIA']:continue
 if g['kind']=='line':d=point_segment(point,g['start'],g['end'])-g['width']/2
 elif g['kind']=='via':d=math.dist(point,g['xy'])-g['radius']
 else:d=math.hypot(*(max(abs(point[i]-g['xy'][i])-g['size'][i]/2,0) for i in (0,1)))
 if d<.500001:bad.append(dict(geometry=g,distance=d))
print('receiverbarrel blockers',bad,flush=True);assert not bad
result=dict(newvia=point,newvia_blockers=bad,Fescape=None,inner_attempts=[])
got,why=connect(rt,dict(net='ANA_PG1',xy=[60.3,52.25],layers=(0,)),[dict(xy=point,kind='NEW_ACTUAL_HARD_CLEAR_RECEIVER')],radius=9,step=.025,budget=300000);print('ANA Fescape',bool(got),why,flush=True);result['Fescape']=got;result['Fescape_reason']=why
if got:
 rt.via('ANA_PG1',point);inv=json.loads((R.parent/'source-residual-components.json').read_text())['inventory']['ANA_PG1']['components'][0]
 for layer in [3,4,2,1,5]:
  targets=[];seen=set()
  for n in inv:
   if layer not in n['layers'] or n['kind'] not in ['PAD','PCB_VIA','PCB_TRACK']:continue
   for xy in [n['position_mm']]+([n['end_mm']] if 'end_mm' in n else []):
    if tuple(xy) in seen:continue
    seen.add(tuple(xy));targets.append(dict(xy=xy,kind=n['kind'],uuid=n['uuid']))
  yes,reason=connect(rt,dict(net='ANA_PG1',xy=point,layers=(layer,)),targets,radius=44,step=.1,budget=350000)
  result['inner_attempts'].append(dict(layer=layer,route=yes,reason=reason));print('ANA inner',layer,bool(yes),reason,flush=True)
  if yes:break
(R/'ANA-routes.json').write_text(json.dumps(result,indent=2)+'\n')
