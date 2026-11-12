"""One fresh isolated native export per call; no quarantined host CAD runtime."""
import argparse, hashlib, json, subprocess, uuid
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('part');p.add_argument('--revision',default='r1');p.add_argument('--entry',default='housing.scad');p.add_argument('--backend',choices=['Manifold','CGAL'],default='Manifold');a=p.parse_args()
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text())
 assert policy['allowed_isolated_image']==IMAGE and policy['isolated_Linux_restart_authorized_by_user']
 assert not (REPO/'hardware/cad/a12/controlled_restart/ISOLATED-RUN-FAILED.json').exists()
 assert not (ROOT/'NATIVE-FAILED.json').exists(), 'Stop: inspect native runtime failure before another invocation'
 out=ROOT/'generated'/a.revision/a.part;out.mkdir(parents=True,exist_ok=False)
 target=out/(a.part+'.stl');entry=ROOT/a.entry
 sources=list(ROOT.glob('*.scad'))+[REPO/'hardware/cad/a11/controls.scad',REPO/'hardware/cad/a11/generated/button-fixture.scad',REPO/'hardware/cad/a11/mechanisms.scad']
 hashes={str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
 cmd=command(['--hardwarnings','--backend='+a.backend,'--export-format=binstl','-D','part='+json.dumps(a.part),'-o',str(target),str(entry)])
 name='afx-tbh01-'+uuid.uuid4().hex[:12];cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
 try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=60);log=r.stdout+r.stderr
 except subprocess.TimeoutExpired:
  subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10)
  (ROOT/'NATIVE-FAILED.json').write_text(json.dumps(dict(part=a.part,reason='timeout')));raise
 (out/'native.log').write_text(log)
 fatal=r.returncode not in (0,1) or any(s in log for s in ('WARNING:','ERROR:','Segmentation fault','Abort trap')) or (r.returncode==1 and 'Current top level object is empty.' not in log)
 result=dict(part=a.part,returncode=r.returncode,image=IMAGE,backend=a.backend,source_sha256=hashes,runtime_failure=fatal,statistics=mesh(target) if target.exists() else None,empty='Current top level object is empty.' in log)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 if fatal:(ROOT/'NATIVE-FAILED.json').write_text(json.dumps(result,indent=2));raise RuntimeError(log)
 print(json.dumps(result))
if __name__=='__main__':main()
