from pathlib import Path
import sys,json
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect
R=Path('/private/tmp/afx-e28-p12-layerhop');t=read_sexpr((R/'candidate0-oldformat.kicad_pcb').read_text());r=Router(t);rows=[]
for net,layer,source,target,extent in [
 ('P12_OV_OK',2,(13.35,10.8),(9.375,17),8),
 ('E28_MASTER_ENABLE',3,(14.4,10.2),(12.6,12),4)]:
 got,why=connect(r,dict(net=net,xy=source,layers=(layer,)),[dict(xy=target,kind='ACTUAL_RETAINED_TRACK_ENDPOINT')],radius=extent,step=.05,budget=400000)
 rows.append(dict(net=net,layer=layer,route=got,reason=why));print(net,bool(got),why,flush=True)
 if got:print(got,flush=True)
print('P19buf hardanchors',flush=True)
for g in r.geometry:
 if g['net']=='P19_OV_OK_SCHMITT' and (g['kind']!='line' or any(9<x[0]<18 and 7<x[1]<15 for x in [g['start'],g['end']])):print(g,flush=True)
(R/'routes-attempt.json').write_text(json.dumps(rows,indent=2)+'\n');(R/'candidate1-oldformat.kicad_pcb').write_text(sexpr(t)+'\n')
