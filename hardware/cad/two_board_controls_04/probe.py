"""Single controlled geometry export after identified tangent repair."""
import json,hashlib,subprocess,uuid
from pathlib import Path
from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command,IMAGE,DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
R=Path(__file__).resolve().parent
assert (R/'NATIVE-FAILED.json').exists()
out=R/'controlled-probe';out.mkdir(exist_ok=False)
name='afx-tbh04-probe-'+uuid.uuid4().hex[:8];target=out/'tray.stl'
cmd=command(['--hardwarnings','--backend=CGAL','--export-format=binstl','-D','part="tray"','-o',str(target),str(R/'display.scad')]);cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
except subprocess.TimeoutExpired:
 subprocess.run([DOCKER,'rm','-f',name],capture_output=True,timeout=10);raise
log=p.stdout+p.stderr;(out/'native.log').write_text(log)
assert p.returncode==0 and not any(s in log for s in ['WARNING:','ERROR:']),log
m=mesh(target);assert m['closed_oriented_boundary'] and m['volume_mm3']>0,m
(out/'result.json').write_text(json.dumps(dict(reason='Replace circle-to-wall tangent by overlapping 6x4 mm necks; geometry warning not runtime crash',source_sha256=hashlib.sha256((R/'display.scad').read_bytes()).hexdigest(),statistics=m,image=IMAGE),indent=2)+'\n')
print(m)
