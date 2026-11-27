"""Fresh bounded Linux native evidence for ground routing candidate."""
import argparse,json,hashlib,subprocess,uuid
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('part');p.add_argument('--revision',default='r1');a=p.parse_args()
 policy=json.loads((REPO/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text());assert policy['allowed_isolated_image']==IMAGE and policy['isolated_Linux_restart_authorized_by_user']
 assert not (ROOT/'NATIVE-FAILED.json').exists()
 assert not (REPO/'hardware/cad/a12/controlled_restart/ISOLATED-RUN-FAILED.json').exists()
 out=ROOT/'native'/(a.part+'-'+a.revision);out.mkdir(parents=True,exist_ok=False);target=out/(a.part+'.stl')
 cmd=command(['--hardwarnings','--backend=Manifold','--export-format=binstl','-D','part='+json.dumps(a.part),'-o',str(target),str(ROOT/'probe.scad')]);name='afx-tbh06-'+uuid.uuid4().hex[:10];cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
 try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=60);log=r.stdout+r.stderr
 except subprocess.TimeoutExpired:
  subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10);(ROOT/'NATIVE-FAILED.json').write_text('timeout');raise
 (out/'native.log').write_text(log)
 fatal=r.returncode not in (0,1) or any(s in log for s in ('WARNING:','ERROR:','Segmentation fault','Abort trap')) or (r.returncode==1 and 'Current top level object is empty.' not in log)
 sources=[]
 def bind(p):
  p=p.resolve()
  if p in sources:return
  sources.append(p)
  if p.suffix=='.scad':
   import re
   for q in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):bind(p.parent/q)
 bind(ROOT/'probe.scad');sources += [ROOT/'ground-routes.json',ROOT/'build.py',Path(__file__)]
 result=dict(part=a.part,image=IMAGE,returncode=r.returncode,runtime_failure=fatal,empty='Current top level object is empty.' in log,mesh=mesh(target) if target.exists() else None,source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 if fatal:(ROOT/'NATIVE-FAILED.json').write_text(json.dumps(result));raise RuntimeError(log)
 print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))
if __name__=='__main__':main()
