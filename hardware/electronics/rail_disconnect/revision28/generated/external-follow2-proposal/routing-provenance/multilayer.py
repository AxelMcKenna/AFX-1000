import sys,json,math,inspect,uuid,textwrap
from pathlib import Path
import numpy as np
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.power_distribution.p03.route import coded,named
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision26 import router as aid
R=Path(__file__).parent;aid.STEP=.1;t=coded(read_sexpr((R/'stage1.kicad_pcb').read_text()))
# Expand ONLY the inherited helper's obsolete45mm grid to the actual54.5mm E28 outline.
# Physical pads/tracks/vias/NPTH reserves stay hard. Saved pours may refill around signals.
source=inspect.getsource(aid.Router.masks).replace('    def masks(', 'def masks(',1)
source='\n'.join(line[4:] if line.startswith('    ') else line for line in source.splitlines())
# function's first line was already dedented; retain remaining relative indentation.
source=textwrap.dedent(inspect.getsource(aid.Router.masks))
source=source.replace('self.yy > 44.5','self.yy > 53.75')
ns=dict(np=np,math=math,CLEARANCE=.2,STEP=.1)
exec(compile(source,'<captured-E26-mask-height-only-adaptation>','exec'),ns)
class ActualGridRouter(Router):
 def __init__(self,tree):
  super().__init__(tree);self.nx=round(156/aid.STEP)+1;self.ny=round(54.5/aid.STEP)+1;self.xx=np.arange(self.nx)[:,None]*aid.STEP;self.yy=np.arange(self.ny)[None,:]*aid.STEP
 def masks(self,net,width):
  blocked,via=ns['masks'](self,net,width);via|=(self.xx<.81)|(self.xx>155.19)|(self.yy<.81)|(self.yy>53.69)
  for g in self.geometry:
   if g['kind']=='via' and g['net']==net and g.get('layers')==tuple(range(6)):
    x,y=(round(v/aid.STEP) for v in g['xy'])
    if 0<=x<self.nx and 0<=y<self.ny:via[x,y]=False
  return blocked,via
rt=ActualGridRouter(t);rt.max_search_nodes=500000;rt.search_bias=1.4
for p in [(67.075,50.625),(51.6375,49.3),(50.5125,46.675),(52.9625,50.375),(51.6375,48)]:rt.geometry.append(dict(kind='via',net='OWNER_FUTURE_RECEIVER',layers=tuple(range(6)),radius=.3,xy=p))
# Replay only the successful actual-F escape. Its .6/.3 receiving barrel is new.
ana_doc=json.loads((R/'ANA-routes.json').read_text());assert ana_doc['Fescape']
rt.path('ANA_PG1',0,ana_doc['Fescape']['path'],.2);rt.via('ANA_PG1',ana_doc['newvia'])
rows=[]
for net,start,end in [('E28_OUT_VALID_ACTIVE',(46.4875,48.575),(97.7,48)),('ANA_PG1',tuple(ana_doc['newvia']),(77.1,16.7))]:
 before=len(t);ok=rt.connect(dict(net=net,xy=start,layers=tuple(range(6))),dict(net=net,xy=end,layers=tuple(range(6))),.2);row=dict(net=net,start=start,end=end,success=ok,search=rt.last_search,new_objects=len(t)-before);rows.append(row);print(row,flush=True)
inv=json.loads((R.parent/'source-residual-components.json').read_text())['inventory']['E28_ANA_FOLLOW2']['components'][1];targets=[n for n in inv if n['kind']=='PCB_VIA'];targets.sort(key=lambda n:math.dist(n['position_mm'],(39.35,14)))
for target in targets[:2]:
 before=len(t);ok=rt.connect(dict(net='E28_ANA_FOLLOW2',xy=(39.35,14),layers=tuple(range(6))),dict(net='E28_ANA_FOLLOW2',xy=target['position_mm'],layers=tuple(range(6))),.2);row=dict(net='E28_ANA_FOLLOW2',target=target,success=ok,search=rt.last_search,new_objects=len(t)-before);rows.append(row);print(row,flush=True)
 if ok:break
for i,n in enumerate(t):
 if isinstance(n,list) and n and n[0] in ['segment','via'] and not children(n,'uuid'):n.append([a('uuid'),a(str(uuid.uuid5(uuid.NAMESPACE_URL,'afx-joint-multilayer:'+str(i)+sexpr(n))))])
(R/'multilayer.kicad_pcb').write_text(sexpr(named(t))+'\n');(R/'multilayer.json').write_text(json.dumps(dict(tasks=rows,actual_grid_mm=.1,actual_board_height_mm=54.5,track_width_mm=.2,unchanged_clearance_mm=.2,new_barrels_size_drill_mm=[.6,.3],all_literal_old_force_quiet_GND_hard_except_declared_bypass_stubs=True),indent=2)+'\n')
(R/'captured-mask-adaptation.py.txt').write_text(source+'\n')
