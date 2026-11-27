"""Fresh isolated Linux native checks; never invoke host CAD."""
import json, subprocess, uuid, hashlib
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command, IMAGE, DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parents[2]
CASES=['spring_negative_stop_positive','spring_arm_preservation_clearance','spring_bracket_preservation_clearance','spring_loop_right_retention_positive','spring_loop_left_retention_positive','spring_hardware_controls_clearance','spring_hardware_shell_clearance','spring_hardware_components_clearance','spring_hardware_carrier_clearance','spring_body_lever_clearance','spring_arm_shell_clearance','spring_arm_components_clearance','spring_arm_controls_clearance','spring_arm_carrier_clearance','spring_arm_bracket_clearance','spring_bracket_controls_clearance','spring_bracket_carrier_clearance','spring_stop_positive','lever_arm_spring','spring_bracket']
def main():
 import sys
 tag=sys.argv[1]; names=sys.argv[2:] or ['population_carrier_clearance','population_shell_clearance','population_controls_clearance','population_rotor_clearance']
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text())
 assert policy['isolated_Linux_restart_authorized_by_user'] and policy['allowed_isolated_image']==IMAGE
 assert not (ROOT/'NATIVE-FAILED.json').exists()
 subprocess.run([DOCKER,'info','--format','{{.ServerVersion}}'],capture_output=True,text=True,check=True,timeout=10)
 sources={}
 def bind(p):
  import re
  p=p.resolve()
  if str(p.relative_to(REPO)) in sources:return
  sources[str(p.relative_to(REPO))]=hashlib.sha256(p.read_bytes()).hexdigest()
  for v in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/v)
 bind(ROOT/'population.scad')
 sources[str(Path(__file__).resolve().relative_to(REPO))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 rows=[]
 for name in names:
  out=ROOT/tag/name;out.mkdir(parents=True,exist_ok=False);target=out/(name+'.stl')
  args=command(['--hardwarnings','--backend='+('CGAL' if name in ['spring_bracket','lever_arm_spring'] else 'Manifold'),'--export-format=binstl','-D','part='+json.dumps(name),'-o',str(target),str(ROOT/'population.scad')])
  container='afx-tbh05-'+uuid.uuid4().hex[:12];args[2:2]=['--name',container,'--memory','2g','--cpus','2']
  try:p=subprocess.run(args,capture_output=True,text=True,timeout=60);log=p.stdout+p.stderr
  except subprocess.TimeoutExpired:
   subprocess.run([DOCKER,'rm','-f',container],capture_output=True,timeout=10);(ROOT/'NATIVE-FAILED.json').write_text(json.dumps({'case':name,'reason':'timeout'}));raise
  fatal=p.returncode not in (0,1) or any(x in log for x in ['WARNING:','ERROR:','Segmentation fault','Abort trap']) or(p.returncode==1 and 'Current top level object is empty.' not in log)
  row={'case':name,'image':IMAGE,'empty':'Current top level object is empty.' in log,'runtime_failure':fatal,'source_sha256':sources,'mesh':mesh(target) if target.exists() else None}
  (out/'native.log').write_text(log);(out/'result.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
  print(name,json.dumps(row),flush=True)
  if fatal:(ROOT/'NATIVE-FAILED.json').write_text(json.dumps(row));raise RuntimeError(log)
 expected_empty=[r for r in rows if r['case'].endswith('_clearance')]
 assert all(r['empty'] and r['mesh'] is None for r in expected_empty), 'Geometry interference: inspect recorded collision meshes'
 for r in rows:
  if r not in expected_empty:assert r['mesh'] and r['mesh']['closed_oriented_boundary'] and r['mesh']['volume_mm3']>0 and r['mesh']['min_mm'][2]>=0
 (ROOT/tag/'review.json').write_text(json.dumps({'scope':'Modeled mechanical interface only; no sensor PCB, magnetic or physical qualification','source_sha256':sources,'cases':rows,'all_expected_results_pass':True},indent=2)+'\n')
if __name__=='__main__':main()
