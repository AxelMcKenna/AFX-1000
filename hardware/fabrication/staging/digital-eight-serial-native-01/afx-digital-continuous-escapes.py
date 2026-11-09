import json,math
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union,nearest_points
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.audit_candidate import sha
surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
cp=Path('hardware/fabrication/staging/digital-eight-led-clean-inputs-52/capture.json');c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
s=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS);objects={o['uuid']:o for o in c['objects']};rows=[]
for key,ids in c['groups'].items():
 net=objects[ids[0]]['net']
 if net.startswith('/LED/LED_') or any(objects[i]['layers'].get('In5.Cu') for i in ids):continue
 freevias=s.via_outline.difference(s.obstacles(net))
 for uid in ids:
  o=objects[uid]
  if o['kind']!='PAD':continue
  for face,ps in o['layers'].items():
   if face not in surface.SIGNAL_LAYERS or not ps:continue
   start=Point(o['position_mm']);obs=unary_union([g.buffer(d+.000001) for n,g,d in s.geometry[face] if n!=net]);free=s.outline.difference(obs)
   regions=[free] if free.geom_type=='Polygon' else list(free.geoms)
   regions=[g for g in regions if g.covers(start)]
   choices=[];area=0
   for region in regions:
    available=region.intersection(freevias).intersection(start.buffer(8)).buffer(-.005)
    if available.is_empty:continue
    geoms=[available] if available.geom_type=='Polygon' else list(available.geoms)
    for g in geoms:
     if g.area<1e-8:continue
     area+=g.area;p=nearest_points(start,g)[1];xy=[p.x,p.y];assert s.via_legal(net,xy)
     direct=next((path for path in surface.candidate_paths(o['position_mm'],xy) if s.legal(net,face,path)),None)
     choices.append(dict(via_mm=xy,distance_mm=start.distance(p),region_area_mm2=g.area,direct_path=direct))
   choices.sort(key=lambda r:r['distance_mm']);row=dict(net=net,group=key,ref=o['ref'],pin=o['pin'],face=face,start=o['position_mm'],trace_regions=len(regions),legal_via_region_area_within_8mm=area,options=choices[:16]);rows.append(row)
   print(net,o['ref'],o['pin'],face,'area',round(area,4),'choices',len(choices),'direct',sum(bool(r['direct_path']) for r in choices),flush=True)
Path('/private/tmp/afx-digital-continuous-escapes.json').write_text(json.dumps(dict(source_sha256={str(cp.resolve()):sha(cp),str(Path(__file__)):sha(Path(__file__))},rows=rows),indent=2))
