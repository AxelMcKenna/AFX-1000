import json
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union,nearest_points
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
c=json.loads(Path('hardware/fabrication/staging/digital-control-pulldowns-inputs-45/capture.json').read_text());screen=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS)
for ref,pin in [('U3005','5'),('R3017','1'),('R3010','1'),('U2003','22'),('U2002','6'),('R1040','2'),('U3002','30'),('U3001','29'),('U3002','4'),('U3002','29'),('U3003','4')]:
 p=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin);net=p['net'];face=next(iter(p['layers']));start=Point(p['position_mm'])
 free=screen.outline.difference(unary_union([g.buffer(d+.0005,quad_segs=32) for n,g,d in screen.geometry[face] if n!=net]));regions=[free] if free.geom_type=='Polygon' else list(free.geoms);region=next((g for g in regions if g.covers(start)),None)
 vf=screen.via_outline.difference(screen.obstacles(net));available=region.intersection(vf) if region else None
 r=dict(ref=ref,pin=pin,net=net,face=face,free_region_area=region.area if region else 0,region_bounds=region.bounds if region else None,via_area=available.area if available else 0)
 if available and not available.is_empty:
  q=nearest_points(start,available)[1];r.update(nearest_via=list(q.coords)[0],nearest_distance=start.distance(q),via_area_within8=available.intersection(start.buffer(8)).area)
 print(json.dumps(r),flush=True)
