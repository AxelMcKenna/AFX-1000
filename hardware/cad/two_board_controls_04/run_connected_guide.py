"""Native checks for the center-island correction; print guides must be connected."""
import json,hashlib,subprocess,uuid,trimesh
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
R=Path(__file__).resolve().parent;REPO=R.parents[2]
EMPTY=['ring_guide_preservation_final','buttons_guide_preservation_low_final','buttons_guide_preservation_high_final','buttons_guide_clearance_final']
POSITIVE=['buttons_down_retention_final']
PARTS=['ring_guide_final','buttons_guide_final','ring_guide_left_final','ring_guide_right_final','buttons_guide_left_final','buttons_guide_right_final']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text());assert policy['allowed_isolated_image']==IMAGE and policy['isolated_Linux_restart_authorized_by_user']
 old=json.loads((R/'button_follow_on/verification.json').read_text())['source_sha256'];bindings=dict(old)
 for p in [R/'connected_guide.scad',Path(__file__)]:bindings[str(p.relative_to(REPO))]=sha(p)
 rows=[]
 for part in EMPTY+POSITIVE+PARTS:
  out=R/'connected-guide-r1'/part;out.mkdir(parents=True,exist_ok=False);target=out/(part+'.stl');name='afx-guide-'+uuid.uuid4().hex[:10]
  cmd=command(['--hardwarnings','--backend=Manifold','--export-format=binstl','-D','part='+json.dumps(part),'-o',str(target),str(R/'connected_guide.scad')]);cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
  try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
  except subprocess.TimeoutExpired:
   subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10);raise
  log=p.stdout+p.stderr;(out/'native.log').write_text(log);m=mesh(target) if target.exists() else None;row=dict(part=part,returncode=p.returncode,statistics=m,empty='Current top level object is empty.' in log)
  if part in PARTS:row['connected_components']=len(trimesh.load_mesh(target).split())
  (out/'result.json').write_text(json.dumps(row,indent=2)+'\n');assert not any(s in log for s in ['WARNING:','ERROR:','Segmentation fault','Abort trap']),log
  if part in EMPTY:assert p.returncode==1 and row['empty'] and m is None,(part,m)
  else:
   assert p.returncode==0 and m and m['closed_oriented_boundary'] and m['volume_mm3']>0,(part,m)
   if part in PARTS:assert row['connected_components']==1,row
   else:assert abs(m['volume_mm3']-.45)<.003,row
  rows.append(row);print(part,'pass',flush=True)
 for k,h in bindings.items():assert sha(REPO/k)==h,k
 (R/'connected-guide-review.json').write_text(json.dumps(dict(image=IMAGE,source_sha256=bindings,cases=rows,scope='Removes only unretained guide island; each full/split guide is a single connected closed solid; all50 button seats retained'),indent=2)+'\n')
if __name__=='__main__':main()
