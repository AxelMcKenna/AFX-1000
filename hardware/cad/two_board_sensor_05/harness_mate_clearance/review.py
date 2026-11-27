"""Verify selected native results, cable continuity, pad datums and source freshness."""
import ast
import hashlib
import json
import math
import re
from pathlib import Path
import trimesh
from hardware.electronics.common.sexpr import read_sexpr, children, first
R=Path(__file__).resolve().parent; REPO=R.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((R/'contract.json').read_text()); native=json.loads((R/'trial-r5/review.json').read_text())
for d in [c,native]:
 for name,h in d['source_sha256'].items(): assert sha(REPO/name)==h,name
assert native['all_expected_results_pass'] and len(native['cases'])==21
rows={x['case']:x for x in native['cases']}
assert abs(rows['prior_mates_collision_positive']['mesh']['volume_mm3']-14.949935237887985)<1e-4
for name in ['panel_mates_clearance','latest_pot_clearance','supports_components_clearance']:
 assert rows[name]['empty'] and rows[name]['mesh'] is None
route=(R/'route.scad').read_text().split('module cable_route(){')[1].split('\n}')[0]
segments=[(ast.literal_eval(a),ast.literal_eval(b)) for a,b in re.findall(r'cable_segment\((\[[^]]+\]),(\[[^]]+\])\);',route)]
assert len(segments)==4 and all(a[1]==b[0] for a,b in zip(segments,segments[1:]))
assert [segments[0][0]]+[s[1]for s in segments]==c['routing_envelope_polyline_mm']
assert abs(sum(math.dist(a,b)for a,b in segments)-c['polyline_length_mm'])<1e-9
assert not c['fixed_precut_length_qualified'] and c['starting_blank_mm']==100
main=R.parent/'signal_input/native-r7/signal_main.kicad_pcb'
fps={next(v[2]for v in children(f,'property')if v[1]=='Reference'):f for f in children(read_sexpr(main.read_text()),'footprint')}
f=fps['D_J1010'];pose=first(f,'at');angle=math.radians(float(pose[3]));pads={str(p[1]):p for p in children(f,'pad')}
for row in c['pin_mapping']:
 p=pads[str(row['main_pin'])];at=first(p,'at');x,y=map(float,at[1:3]);xyz=[float(pose[1])+x*math.cos(angle)+y*math.sin(angle),float(pose[2])-x*math.sin(angle)+y*math.cos(angle),8.35]
 assert math.dist(xyz,row['main_pad_world_mm'])<1e-6 and first(p,'net')[1]==row['main_net']
for ref,xy in [('D_H2',[250,57]),('D_H5',[294,88])]:assert list(map(float,first(fps[ref],'at')[1:3]))==xy
solids=[]
for name in ['saddle_main_positive','saddle_sensor_positive','lid_main_positive','lid_sensor_positive']:
 p=R/'trial-r5'/name/(name+'.stl');m=trimesh.load_mesh(p);assert m.is_watertight and len(m.split())==1 and m.volume>0
 solids.append(dict(part=name,watertight=True,connected_components=1,sha256=sha(p)))
paths=[R/n for n in ['route.scad','baseline.scad','panel_mates.scad','pot_receiving.scad','run.py','review.py','contract.json','source-contract.json','README.md','SELF-REVIEW.md','trial-r5/review.json','preview.py','preview-r5.png']]
report=dict(source_sha256={str(p.relative_to(REPO)):sha(p)for p in paths},native_cases=21,solids=solids,old_collision_reproduced=True,continuous_path=True,pad_datums_verified=True,complete_installed_fit=False,fabrication_released=False)
assert not (R/'review.json').exists();(R/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('Verified21 cases,4 connected solids, cable continuity and pad datums')
