"""Source-bound isolated native verification of the new display carrier."""
import json,hashlib,subprocess,uuid
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[3]
EMPTY=['buttons_obstacle_clearance','buttons_motion_clearance','buttons_existing_carrier_clearance','buttons_fastener_clearance','buttons_lid_clearance','buttons_guide_clearance','buttons_light_path','buttons_guide_preservation_low','buttons_guide_preservation_high']
POSITIVE=['buttons_light_cap_rest','buttons_light_cap_pressed','buttons_down_retention','buttons_up_retention']
PARTS=['buttons_guide','buttons_guide_left','buttons_guide_right']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text());assert policy['allowed_isolated_image']==IMAGE and policy['isolated_Linux_restart_authorized_by_user']
 assert not (ROOT/'BUTTON-NATIVE-FAILED.json').exists()
 sources=[ROOT/'buttons.scad',ROOT/'board-data.scad',ROOT/'caps.scad',ROOT/'run.py',ROOT.parent/'ring_follow_on/ring.scad',ROOT.parent/'ring_follow_on/board-data.scad',ROOT.parent/'led_follow_on/banks.scad',ROOT.parent/'led_follow_on/meters.scad',ROOT.parent/'led_follow_on/meter-board-data.scad',ROOT.parent/'led_follow_on/bank-board-data.scad',ROOT.parent/'led_follow_on/button_motion.scad',ROOT.parent/'selectors.scad',ROOT.parent/'display.scad',ROOT.parent.parent/'two_board_print_01/housing.scad',ROOT.parent.parent/'two_board_print_01/captured.scad',ROOT.parent.parent/'a11/controls.scad',ROOT.parent.parent/'a11/generated/button-fixture.scad']
 bindings={str(p.relative_to(REPO)):sha(p) for p in sources};rows=[]
 for part in EMPTY+POSITIVE+PARTS:
  out=ROOT/'native-r5'/part;out.mkdir(parents=True,exist_ok=False);target=out/(part+'.stl')
  cmd=command(['--hardwarnings','--backend='+'Manifold','--export-format=binstl','-D','part='+json.dumps(part),'-o',str(target),str(ROOT/'buttons.scad')]);name='afx-tbh04-'+uuid.uuid4().hex[:12];cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
  try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);log=p.stdout+p.stderr
  except subprocess.TimeoutExpired:
   subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10);(ROOT/'BUTTON-NATIVE-FAILED.json').write_text(json.dumps(dict(part=part,reason='timeout')));raise
  fatal=p.returncode not in (0,1) or any(s in log for s in ['WARNING:','ERROR:','Segmentation fault','Abort trap']) or(p.returncode==1 and 'Current top level object is empty.' not in log)
  m=mesh(target) if target.exists() else None;row=dict(part=part,returncode=p.returncode,image=IMAGE,runtime_failure=fatal,statistics=m,empty='Current top level object is empty.' in log)
  (out/'native.log').write_text(log);(out/'result.json').write_text(json.dumps(row,indent=2)+'\n')
  if fatal:(ROOT/'BUTTON-NATIVE-FAILED.json').write_text(json.dumps(row,indent=2));raise RuntimeError(log)
  if part in EMPTY:assert row['empty'] and m is None,(part,m)
  else:assert m and m['closed_oriented_boundary'] and m['volume_mm3']>0,(part,m)
  if part in ['buttons_light_cap_rest','buttons_light_cap_pressed']:assert abs(m['volume_mm3']-3.825)<.003,(part,m)
  if part in ['buttons_down_retention','buttons_up_retention']:assert abs(m['volume_mm3']-.45)<.003,(part,m)
  rows.append(row);print(part,'empty' if m is None else 'valid solid',flush=True)
 for path,h in bindings.items():assert sha(REPO/path)==h,path
 (ROOT/'verification.json').write_text(json.dumps(dict(scope='Button PCB and emitter placement; modeled fit only',source_sha256=bindings,cases=rows),indent=2)+'\n')
if __name__=='__main__':main()
