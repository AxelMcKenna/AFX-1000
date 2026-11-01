import sys,json,copy,math
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.receiver_local_escape import escape
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect
R=Path('/private/tmp/afx-u11-restoration');tree=read_sexpr((R/'reconstructed-candidate0.kicad_pcb').read_text());r=Router(tree);rows=[]
for ref,pin,target,radius in [('U36','2',(6.75,14.6),6),('U11','4',(6.75,14.6),6)]:
 p=next(p for p in r.by_ref[ref] if p['pin']==pin)
 got,reason=connect(r,p,[dict(xy=target,kind='OLDVIA')],radius=radius,step=.025,budget=300000)
 rows.append(dict(ref=ref,pin=pin,route=got,reason=reason));print(ref,pin,got,reason,flush=True)
# Any final extra drill must respect all literal existing geometry.
if rows[-1]['route'] is None:
 p=next(p for p in r.by_ref['U11'] if p['pin']=='4')
 got,reason=escape(r,p,maxdistance=5,step=.025)
 rows.append(dict(ref='U11',pin='4',extra_drill=True,route=got,reason=reason));print('P12escape',got,reason,flush=True)
# Dump actual remaining N19raw geometry near receiving cut before choosing endpoint.
raw=[]
for g in r.geometry:
 if g['net']=='N19_OV_OK':raw.append(g)
(R/'N19raw-retained-geometry.json').write_text(json.dumps(raw,indent=2)+'\n')
(R/'restoration-attempts.json').write_text(json.dumps(rows,indent=2)+'\n')
(R/'partial-restored-oldformat.kicad_pcb').write_text(sexpr(tree)+'\n')
