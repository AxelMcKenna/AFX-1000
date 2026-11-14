"""Source-bound isolated native verification of the new display carrier."""
import json,hashlib,subprocess,uuid
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]
EMPTY=['selector_obstacle_clearance','selector_body_clearance','selector_lead_clearance','selector_fastener_clearance','selector_guide_clearance','selector_lid_clearance']
POSITIVE=['selector_board_up_retention']
PARTS=['settings_bracket','selector_lid','selector_guide','selector_lid_left','selector_lid_right','selector_guide_left','selector_guide_right']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text());assert policy['allowed_isolated_image']==IMAGE and policy['isolated_Linux_restart_authorized_by_user']
 assert not (ROOT/'SELECTOR-NATIVE-FAILED.json').exists()
 sources=[ROOT/'selectors.scad',ROOT/'display.scad',ROOT/'run_selectors.py',ROOT.parent/'two_board_print_01/housing.scad',ROOT.parent/'two_board_print_01/captured.scad',ROOT.parent/'a11/controls.scad',ROOT.parent/'a11/mechanisms.scad',ROOT.parent/'a11/generated/button-fixture.scad']
 bindings={str(p.relative_to(REPO)):sha(p) for p in sources};rows=[]
 for part in EMPTY+POSITIVE+PARTS:
  out=ROOT/'selectors-r6'/part;out.mkdir(parents=True,exist_ok=False);target=out/(part+'.stl')
  cmd=command(['--hardwarnings','--backend='+('CGAL' if part in PARTS else 'Manifold'),'--export-format=binstl','-D','part='+json.dumps(part),'-o',str(target),str(ROOT/'selectors.scad')]);name='afx-tbh04-'+uuid.uuid4().hex[:12];cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
  try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);log=p.stdout+p.stderr
  except subprocess.TimeoutExpired:
   subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10);(ROOT/'SELECTOR-NATIVE-FAILED.json').write_text(json.dumps(dict(part=part,reason='timeout')));raise
  fatal=p.returncode not in (0,1) or any(s in log for s in ['WARNING:','ERROR:','Segmentation fault','Abort trap']) or(p.returncode==1 and 'Current top level object is empty.' not in log)
  m=mesh(target) if target.exists() else None;row=dict(part=part,returncode=p.returncode,image=IMAGE,runtime_failure=fatal,statistics=m,empty='Current top level object is empty.' in log)
  (out/'native.log').write_text(log);(out/'result.json').write_text(json.dumps(row,indent=2)+'\n')
  if fatal:(ROOT/'SELECTOR-NATIVE-FAILED.json').write_text(json.dumps(row,indent=2));raise RuntimeError(log)
  if part in EMPTY:assert row['empty'] and m is None,(part,m)
  else:assert m and m['closed_oriented_boundary'] and m['volume_mm3']>0,(part,m)
  rows.append(row);print(part,'empty' if m is None else 'valid solid',flush=True)
 (ROOT/'selector-verification.json').write_text(json.dumps(dict(scope='Selector bracket and explicit breakout boards; modeled fit only',source_sha256=bindings,cases=rows),indent=2)+'\n')
if __name__=='__main__':main()
