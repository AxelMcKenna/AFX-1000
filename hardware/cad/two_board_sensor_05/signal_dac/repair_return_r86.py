"""Add a physical return via/corridor for the failed r85 THRESH_LOWER transition."""
import json,hashlib,math,shutil
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;p=[63.9125,89.9];q=[64.1125,90.9];c=json.loads((R/'capture-r85/capture.json').read_text());r=json.loads((R/'candidate-r84/routing.json').read_text());pt=Point(q)
assert .86<math.dist(p,q)<2.5
for o in c['objects']:
 if o['kind']=='PCB_VIA':assert math.dist(q,o['position_mm'])>=.86
 for ps in o['layers'].values():
  if not ps:continue
  g=shape(ps)
  if o['net']!='LINK_AGND':assert pt.distance(g)>=.51,(o['uuid'],o['net'])
  if o['kind']=='PAD'and not any(o['drill_mm']):assert pt.distance(g)>=.27,o['uuid']
signal=next(o for o in c['objects']if o['kind']=='PCB_VIA'and o['position_mm']==p);hole=unary_union([shape(ps)for ps in signal['layers'].values()]).buffer(.215)
fields={l:unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']==l]).buffer(2e-6)for l in ['In1.Cu','In4.Cu','In6.Cu']};assert fields['In1.Cu'].covers(pt.buffer(.31))
gaps={l:LineString([p,q]).buffer(.1).difference(hole).difference(f).area for l,f in fields.items()};assert gaps['In1.Cu']<1e-6
v=next(v for v in r['vias']if v['at']==p);old=v['return_at'];v['return_at']=q
next(v for v in r['used_return_sites']if v['signal_at']==p)['return_at']=q;r['planned_ground_returns'].append(q)
r['return_repair']={'signal_at':p,'before_return_at':old,'after_return_at':q,'actual_r85_field_gaps_mm2':gaps,'In4_gap_requires_new_physical_corridor':True,'no_field_tolerance_change':True}
paths=[Path(__file__),R/'candidate-r84/routing.json',R/'candidate-r84/signal_main.kicad_pcb',R/'capture-r85/capture.json',R/'native-r85/review.json'];r['return_repair_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
out=R/'candidate-r86';out.mkdir(exist_ok=False);shutil.copy2(R/'candidate-r84/signal_main.kicad_pcb',out/'signal_main.kicad_pcb');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print(r['return_repair'])
