"""Final source binding and printable-solid review, separate from physical acceptance."""
import json,hashlib
from pathlib import Path
import trimesh
R=Path(__file__).resolve().parent;REPO=R.parents[3]
review=json.loads((R/'trial-r6/review.json').read_text());contract=json.loads((R/'contract.json').read_text())
for d in [review,contract]:
 for path,h in d['source_sha256'].items():assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,path
assert review['all_expected_results_pass']and len(review['cases'])==18
rows=[]
for n in ['saddle_main_positive','saddle_sensor_positive','lid_main_positive','lid_sensor_positive']:
 p=R/'trial-r6'/n/(n+'.stl');m=trimesh.load_mesh(p);assert m.is_watertight and len(m.split())==1 and m.volume>0
 rows.append({'part':n,'watertight':True,'connected_components':1,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
paths=[Path(__file__),R/'route.scad',R/'contract.json',R/'trial-r6/review.json',R/'README.md',R/'preview.py',R/'preview-r6.png']
report={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'native_cases':18,'solids':rows,'physical_qualified':False,'complete_bus_harness_closed':False,'all_selected_checks_pass':True}
(R/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS 18 native cases, 4 single-component watertight clamp solids, all source bindings')
