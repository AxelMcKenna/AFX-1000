import sys,json
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
R=Path('/private/tmp/afx-e28-p12-layerhop');r=Router(read_sexpr((R/'candidate0-oldformat.kicad_pcb').read_text()))
for name in ['P12_OV_OK','P19_OV_OK_SCHMITT','E28_MASTER_ENABLE','V5_REG_OV_OK_SCHMITT']:
 print(name)
 for g in r.geometry:
  if g['net']!=name:continue
  if g['kind']=='line':
   if all(5<p[0]<25 and 6<p[1]<23 for p in [g['start'],g['end']]):print(g)
  else:print(g)
