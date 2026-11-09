import json,math
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from shapely import contains_xy
from shapely.ops import unary_union
import hardware.fabrication.route_nf_surface as surface
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
surface.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=("F.Cu","In3.Cu","In5.Cu","B.Cu")
p=Path('hardware/fabrication/staging');c=json.loads((p/'digital-eight-led-fanout-inputs-56/capture.json').read_text());s=DigitalViaScreen(c,signal_layers=('F.Cu','In3.Cu','In5.Cu','B.Cu'))
es=json.loads((p/'digital-eight-led-fanouts-01/construction.json').read_text())['selected_escapes']
rows=[]
for e in es:
 net=e['net'];ends=[o for o in c['objects'] if o['net']==net and o['kind']=='PAD' and o.get('ref','').startswith('J')]
 print(net,[(o.get('ref'),o.get('pin'),o['position_mm']) for o in ends],flush=True)
 for step in [.1,.05]:
  xs=np.arange(0,114+step,step);ys=np.arange(0,60+step,step);xx,yy=np.meshgrid(xs,ys)
  obs=unary_union([g.buffer(d+.000001) for n,g,d in s.geometry['In5.Cu'] if n!=net]);free=contains_xy(s.outline,xx,yy)&~contains_xy(obs,xx,yy);lab,n=label(free,structure=np.ones((3,3)))
  def groups(xy):
   x,y=map(lambda v:round(v/step),xy);out=set()
   for dx in range(-2,3):
    for dy in range(-2,3):
     ix,iy=x+dx,y+dy
     if 0<=ix<len(xs) and 0<=iy<len(ys) and lab[iy,ix] and s.legal(net,'In5.Cu',[xy,[xs[ix],ys[iy]]]):out.add(int(lab[iy,ix]))
   return out
  start=groups(e['via_mm']);end=set().union(*(groups(o['position_mm']) for o in ends));row=dict(net=net,step=step,start_groups=sorted(start),end_groups=sorted(end),same_component=bool(start&end),regions=n);rows.append(row);print(row,flush=True)
Path('/private/tmp/afx-led-connectivity-diagnostic.json').write_text(json.dumps(rows,indent=2))
