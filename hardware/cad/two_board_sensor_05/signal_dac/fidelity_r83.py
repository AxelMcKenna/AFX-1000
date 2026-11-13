"""Independently compare native fractured regions with exported unfractured regions."""
import json,hashlib
from pathlib import Path
from shapely.geometry import Polygon
from shapely import make_valid
from shapely.ops import unary_union
R=Path(__file__).resolve().parent
rows=[]
def region(ps):
 return unary_union([make_valid(Polygon(p['outer'],p['holes'])) for p in ps])
for name in ['../signal_input/capture-r7','capture-r83']:
 p=R/name/'capture.json';c=json.loads(p.read_text());zones={(z['uuid'],z['layer']):z for z in c['zones']}
 for f in c['zone_unfracture_fidelity']:
  key=(f['uuid'],f['layer']);raw=region(f['raw_filled_polygons']);out=region(zones[key]['polygons'])
  delta=raw.symmetric_difference(out).area
  # Fracture slits become lines under make_valid; compare areal support both ways.
  outside=max(raw.difference(out.buffer(2e-6)).area,out.difference(raw.buffer(2e-6)).area)
  row={'capture':name,'zone':key,'symmetric_difference_mm2':delta,'area_limit_mm2':f['maximum_symmetric_difference_area_mm2'],'outside_2nm_buffer_mm2':outside}
  rows.append(row)
  assert delta<=f['maximum_symmetric_difference_area_mm2']+1e-8,row
  assert outside<1e-8,row
report={'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R.parent/'signal_input/capture-r7/capture.json',R/'capture-r83/capture.json']},'cases':rows,'pass':True}
(R/'fidelity-r83.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(rows))
