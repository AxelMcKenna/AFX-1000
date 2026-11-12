"""Source-bound fresh retention exports using the authorized isolated Linux image."""
import hashlib,json,subprocess,uuid
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2];BASE=ROOT.parent/'two_board_print_01'
PARTS=[]
EMPTY=['rotor_insertion_clearance','cap_insertion_clearance']
POSITIVE=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text())
 assert policy['allowed_isolated_image']==IMAGE and policy['isolated_Linux_restart_authorized_by_user']
 assert not (ROOT/'NATIVE-FAILED.json').exists()
 assert not (REPO/'hardware/cad/a12/controlled_restart/ISOLATED-RUN-FAILED.json').exists()
 bindings=json.loads((BASE/'verification.json').read_text())['geometry_source_sha256']
 for p,h in bindings.items():assert sha(REPO/p)==h,p
 sources={**bindings,str((ROOT/'retention.scad').relative_to(REPO)):sha(ROOT/'retention.scad')}
 rows=[]
 for part in EMPTY+POSITIVE+PARTS:
  out=ROOT/'generated-insertion-r4'/part;out.mkdir(parents=True,exist_ok=False);target=out/(part+'.stl')
  cmd=command(['--hardwarnings','--backend='+('CGAL' if part in PARTS else 'Manifold'),'--export-format=binstl','-D','part='+json.dumps(part),'-o',str(target),str(ROOT/'retention.scad')])
  name='afx-tbh03-'+uuid.uuid4().hex[:12];cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
  try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);log=p.stdout+p.stderr
  except subprocess.TimeoutExpired:
   subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10);(ROOT/'NATIVE-FAILED.json').write_text(json.dumps(dict(part=part,reason='timeout')));raise
  fatal=p.returncode not in (0,1) or any(s in log for s in ['WARNING:','ERROR:','Segmentation fault','Abort trap']) or (p.returncode==1 and 'Current top level object is empty.' not in log)
  m=mesh(target) if target.exists() else None
  row=dict(part=part,returncode=p.returncode,image=IMAGE,backend='CGAL' if part in PARTS else 'Manifold',source_sha256=sources,runtime_failure=fatal,statistics=m,empty='Current top level object is empty.' in log)
  (out/'native.log').write_text(log);(out/'result.json').write_text(json.dumps(row,indent=2)+'\n')
  if fatal:(ROOT/'NATIVE-FAILED.json').write_text(json.dumps(row,indent=2));raise RuntimeError(log)
  if part in EMPTY:assert row['empty'] and m is None,part
  else:assert m and m['closed_oriented_boundary'] and m['volume_mm3']>0,part
  rows.append(row);print(part,'empty' if m is None else 'valid solid',flush=True)
 (ROOT/'insertion-review-r4.json').write_text(json.dumps(dict(scope='lever axial retention add-on; r6 housing and arm unchanged',source_sha256=sources,cases=rows),indent=2)+'\n')
if __name__=='__main__':main()
