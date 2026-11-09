import json,time
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_visibility_escape import route
surface.WIDTH=layers.WIDTH=.2;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');surface.MARGIN=.01
c=json.loads(Path('hardware/fabrication/staging/digital-eight-control-inputs-51/capture.json').read_text());s=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS)
d=json.loads(Path('/private/tmp/afx-digital-continuous-escapes.json').read_text());results=[]
for row in d['rows']:
 if row['net']!='/LED/SERIAL_2':continue
 net,face=row['net'],row['face'];free=s.outline.difference(unary_union([g.buffer(clearance+.0005,quad_segs=32) for n,g,clearance in s.geometry[face] if n!=net]))
 regions=[free] if free.geom_type=='Polygon' else list(free.geoms)
 reg=next((g for g in regions if g.covers(Point(row['start']))),None)
 if reg is None:continue
 for opt in row['options'][:2]:
  if not s.via_legal(net,opt['via_mm']):continue
  path=route(s,net,face,row['start'],opt['via_mm'],reg,time.monotonic()+15)
  result=dict(ref=row['ref'],net=net,via=opt['via_mm'],path=path);results.append(result);print(result,flush=True)
Path('/private/tmp/afx-test-visibility-escape.json').write_text(json.dumps(results,indent=2))
