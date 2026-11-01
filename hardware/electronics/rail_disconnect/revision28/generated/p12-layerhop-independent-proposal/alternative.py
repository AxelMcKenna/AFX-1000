from pathlib import Path
import sys,json,math
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect
R=Path('/private/tmp/afx-e28-p12-layerhop');t=read_sexpr((R/'candidate0-oldformat.kicad_pcb').read_text());r=Router(t);rows=[]
for net,layer,source,target,extent in [('E28_MASTER_ENABLE',3,(14.4,10.2),(12.6,12),4),('P12_OV_OK',3,(13.35,10.8),(14.875,20.25),10)]:
 got,why=connect(r,dict(net=net,xy=source,layers=(layer,)),[dict(xy=target,kind='ACTUAL_RETAINED_TRACK_OR_MAIN_VIA')],radius=extent,step=.05,budget=400000)
 row=dict(net=net,layer=layer,route=got,reason=why)
 if got:row['length_mm']=sum(math.dist(a,b) for a,b in zip(got['path'],got['path'][1:]))
 rows.append(row);print(net,bool(got),why,row.get('length_mm'),flush=True)
(R/'alternative-routes.json').write_text(json.dumps(rows,indent=2)+'\n');(R/'alternative-oldformat.kicad_pcb').write_text(sexpr(t)+'\n')
