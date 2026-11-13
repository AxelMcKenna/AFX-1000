"""Check actual filled return copper and bounded new signal transition exception."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString,shape as geo_shape
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..vin_escape.verify import saved_fill
from ..routed.plan import sha
H=Path(__file__).resolve().parent;Q=H.parent
m=json.loads((H/'review-manifest-02.json').read_text());t=read_sexpr((H/m['bundle_name']/'power_protection.kicad_pcb').read_text());old=read_sexpr((Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb').read_text());q=json.loads((Q/'routed/quiet-exclusion.json').read_text());quiet={r['zone_uuid'] for r in q['plane_exclusions']}
def ref(tree,layer):return unary_union([saved_fill(z) for z in children(tree,'zone') if str(first(z,'net')[1])=='PWR_AGND' and str(first(z,'layer')[1])==layer and str(first(z,'uuid')[1]) not in quiet])
rows=[];ret=[]
for layer,adj in [('F.Cu','In1.Cu'),('B.Cu','In6.Cu')]:
 prior=ref(old,adj);current=ref(t,adj);exception=prior.difference(current);via=Point(185.2,123.5).buffer(.3,resolution=128);missing=via.difference(current).area;assert missing<1e-9,(layer,missing);ret.append({'surface':layer,'adjacent_layer':adj,'return_via_fill_uncovered_mm2':missing,'actual_antipad_removed_mm2':exception.area})
 for i,r in enumerate(m['routes']):
  if r['layer']!=layer:continue
  copper=LineString(r['path_mm']).buffer(r['width_mm']/2,resolution=128);outside=copper.difference(current).area;unallowed=copper.difference(current.union(exception)).area;assert unallowed<1e-9,(i,unallowed)
  if outside>1e-9:assert i in [0,1] and copper.difference(current).difference(Point(186.1,123.5).buffer(.508,resolution=128)).area<1e-9
  rows.append({'route':i,'layer':layer,'actual_track_antipad_exception_mm2':outside,'outside_ground_or_exact_removed_antipad_mm2':unallowed})
# Exact source-bound mechanical contact regions apply independently of reference.
for rel,digest in [('main_feeds/contact-keepouts.json','9975b35aeb05140e87408b99d9f373c6a69588591cfa4eadfdf03cddad577d4d'),('vin_escape/main-mount-keepouts.json','38854f6356625631ad32ec4578c989c2c3e06a6f8c48754ec768c55f53e04d71')]:
 p=Q/rel;assert sha(p)==digest
 for feature in json.loads(p.read_text())['features']:
  if feature['properties'].get('board','power')!='power':continue
  region=geo_shape(feature['geometry'])
  for r in m['routes']:
   if r['layer'] in feature['properties']['layers']:assert not region.intersects(LineString(r['path_mm']).buffer(r['width_mm']/2))
  for xy in [[186.1,123.5],[185.2,123.5]]:assert not region.intersects(Point(xy).buffer(.3))
r={'status':'PASS','candidate_sha256':sha(H/m['bundle_name']/'power_protection.kicad_pcb'),'return_pair_center_distance_mm':.9,'return_reference':ret,'routes':rows,'mechanical_contacts_clear':True,'qualified':False};(H/'transition-review.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
