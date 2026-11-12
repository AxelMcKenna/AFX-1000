"""Source-binding and manufacturable-solid audit of selected final checkpoints."""
from pathlib import Path
import hashlib,json,trimesh
R=Path(__file__).resolve().parent;REPO=R.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports=['verified-r3/review.json','spring-verified-r2/review.json','population-verified-r1/review.json']
for f in reports:
 d=json.loads((R/f).read_text());assert d['all_expected_results_pass']
 for p,h in d['source_sha256'].items():assert sha(REPO/p)==h,p
p=R/'pcb/native-r3/review.json';d=json.loads(p.read_text())
for f,h in d['source_sha256'].items():assert sha(R/f)==h,f
assert sha(R/'pcb/native-r3/sensor.kicad_pcb')==d['output_pcb_sha256']
c=json.loads((R/'population-contract.json').read_text());assert c['checked_pcb_sha256']==d['output_pcb_sha256'];assert c['population_scad_sha256']==sha(R/'population.scad')
meshes={}
for f in ['spring-verified-r2/lever_arm_spring/lever_arm_spring.stl','spring-verified-r2/spring_bracket/spring_bracket.stl','verified-r3/sensor_carrier/sensor_carrier.stl','verified-r3/sensor_cap/sensor_cap.stl']:
 m=trimesh.load_mesh(R/f);v={'watertight':bool(m.is_watertight),'consistent_winding':bool(m.is_winding_consistent),'components':len(m.split(only_watertight=False)),'volume_mm3':float(m.volume),'sha256':sha(R/f)};assert v['watertight'] and v['consistent_winding'] and v['components']==1 and v['volume_mm3']>0;meshes[f]=v
bound=['carrier.scad','spring.scad','population.scad','pcb_capture.py','population-contract.json','pcb/native-r3/sensor.kicad_pcb','pcb/native-r3/review.json',*reports,'spring_preview.py','spring-preview.png','pcb/visual-r1/front.svg','pcb/visual-r1/back.svg','pcb/README.md','SPRING.md','final_review.py']
(R/'final-review.json').write_text(json.dumps({'scope':'Self-review, not independent audit or physical qualification','all_selected_native_source_bindings_current':True,'native_case_counts':{'carrier':12,'spring':20,'populated_pcb':4},'meshes':meshes,'files_sha256':{f:sha(R/f)for f in bound},'visual_review':'Front/back copper and replacement lever/carrier preview inspected; no disconnected copper or observed geometry defect. Final assembly preview omits hardware/spring and is labelled accordingly.','remaining_gates':['Combined latest controls/cooling integration belongs to root','Confirm spring loop orientation and receiving dimensions','Magnet grade, bond and field/AGC qualification','Print tolerances, load/return-force and cycle tests','Complete harness strain relief and full I2C bus electrical acceptance','Fabrication export/release review']},indent=2)+'\n')
print('All selected source bindings and four printable one-component solids pass.')
