"""Final source binding and printable-solid review, separate from physical acceptance."""
import json,hashlib
from pathlib import Path
import trimesh
R=Path(__file__).resolve().parent;REPO=R.parents[3]
review=json.loads((R/'trial-r5/review.json').read_text());contract=json.loads((R/'contract.json').read_text())
for d in [review,contract]:
 for path,h in d['source_sha256'].items():assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,path
assert review['all_expected_results_pass']and len(review['cases'])==20
rows=[]
for n in ['saddle_main_positive','saddle_sensor_positive','lid_main_positive','lid_sensor_positive']:
 p=R/'trial-r5'/n/(n+'.stl');m=trimesh.load_mesh(p);assert m.is_watertight and len(m.split())==1 and m.volume>0
 rows.append({'part':n,'watertight':True,'connected_components':1,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
source=json.loads((R/'source-contract.json').read_text())
for path,h in source['source_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
legacy=next(x for x in review['cases']if x['case']=='legacy_pot_collision_positive');assert abs(legacy['mesh']['volume_mm3']-source['expected_legacy_collision_mm3'])<1e-4
assert next(x for x in review['cases']if x['case']=='latest_pot_clearance')['empty']
paths=[R/'source-contract.json',R/'pot-body-source.scad.txt',R/'pot_receiving.scad',R/'SELF-REVIEW.md',Path(__file__),R/'route.scad',R/'contract.json',R/'trial-r5/review.json',R/'README.md',R/'preview.py',R/'preview-r5.png']
report={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'native_cases':20,'solids':rows,'physical_qualified':False,'complete_bus_harness_closed':False,'all_selected_checks_pass':True}
(R/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS 20 native cases, 4 single-component watertight clamp solids, all source bindings')
