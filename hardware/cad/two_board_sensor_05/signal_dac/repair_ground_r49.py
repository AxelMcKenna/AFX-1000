"""Relocate one new ground drill away from a same-net SMD solder land."""
import json,math,hashlib,shutil
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.fabrication.route_nf_surface import shape,candidate_paths
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-r48/capture.json').read_text());r=json.loads((R/'candidate-r47/routing.json').read_text());old=[116.95,73.7375];bad='a69587fe-7a70-5853-8765-d3a8ae28d618';affected=[x for x in r['used_return_sites']if x['return_at']==old];assert len(affected)==1;signal=affected[0]['signal_at']
foreign=[shape(ps)for o in c['objects']if o['net']!='LINK_AGND'for ps in o['layers'].values()if ps];pads=[shape(ps)for o in c['objects']if o['kind']=='PAD'and not any(o['drill_mm'])for ps in o['layers'].values()if ps];tree=STRtree(foreign);ptree=STRtree(pads)
field=unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu']).buffer(2e-6)
points=sorted(([round(old[0]+i*.1,6),round(old[1]+j*.1,6)]for i in range(-20,21)for j in range(-20,21)),key=lambda q:math.dist(q,old))
chosen=None
for q in points:
 pt=Point(q)
 if math.dist(q,signal)>2.5 or not field.covers(pt.buffer(.11)):continue
 if any(pt.distance(foreign[int(i)])<.51 for i in tree.query(pt.buffer(.52))):continue
 if any(pt.distance(pads[int(i)])<.27 for i in ptree.query(pt.buffer(.28))):continue
 if any(o['uuid']!=bad and o['kind']=='PCB_VIA'and math.dist(q,o['position_mm'])<.86 for o in c['objects']):continue
 if not any(LineString(path).length<=2.5 and LineString(path).buffer(.1).difference(Point(signal).buffer(.515)).difference(field).area<1e-6 for path in candidate_paths(signal,q)):continue
 chosen=q;break
assert chosen,'No bounded solder-safe ground site'
for x in affected:x['return_at']=chosen
r['planned_ground_returns']=[chosen if p==old else p for p in r['planned_ground_returns']]
for v in r['vias']:
 if v.get('return_at')==old:v['return_at']=chosen
r['ground_drill_repair']={'before_mm':old,'after_mm':chosen,'reason':'same-net ground SMD drill overlap','minimum_center_to_SMD_copper_screen_mm':.27}
r['ground_repair_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'capture-r48/capture.json',R/'candidate-r47/routing.json',R/'candidate-r47/signal_main.kicad_pcb']}
out=R/'candidate-r49';out.mkdir(exist_ok=False);shutil.copy2(R/'candidate-r47/signal_main.kicad_pcb',out/'signal_main.kicad_pcb');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print(r['ground_drill_repair'])
