"""Diagnose the coplanar wafer/substrate witness using frozen original CAD sources."""
import json,subprocess,uuid
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    data,c,k,_=w.load_manifest(HERE/'candidate.json');check=k['r23_mates_base_ground_supports'];identity,failed=w.job('check',check,c)
    previous=json.loads((failed/'result.json').read_text());assert not previous['passed'] and not previous['runtime_failure']
    out=HERE/'direct-source-check';out.mkdir(exist_ok=False)
    for name in ['result.json','geometry.scad','geometry.stl','native.log']:(out/('mesh-'+name)).write_bytes((failed/name).read_bytes())
    for path,h in identity['sources'].items():
        if not path.endswith('.scad'):continue
        raw=(w.ROOT/path).read_bytes();assert w.sha(w.ROOT/path)==h
        target=out/'sources'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    source=out/'geometry.scad';source.write_text(w.scad(c,check['left'],check['right'],out/'sources'))
    target=out/'geometry.stl';name='afx-r23-direct-'+uuid.uuid4().hex[:10]
    cmd=w.command(['--hardwarnings','--backend=Manifold','--export-format=binstl','-o',str(target),str(source)]);cmd[2:2]=['--name',name,'--memory','2g','--cpus','2']
    try:
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=60);log=proc.stdout+proc.stderr
    except subprocess.TimeoutExpired:
        subprocess.run([w.DOCKER,'rm','-f',name],capture_output=True,timeout=10);(out/'timeout.json').write_text(json.dumps({'timeout_seconds':60,'container':name}));raise
    (out/'native.log').write_text(log);w.assert_current(identity)
    empty='Current top level object is empty.' in log
    failure=proc.returncode not in (0,1) or any(x in log for x in ['WARNING:','ERROR:','Segmentation fault','Abort trap']) or (proc.returncode==1 and not empty)
    result={'identity':identity,'original_mesh_failure_retained':True,'image':w.IMAGE,'returncode':proc.returncode,'runtime_failure':failure,'empty':empty,'mesh':w.mesh(target) if target.exists() else None,'passed':empty and not failure,'source_sha256':{w.relative(Path(__file__)):w.sha(Path(__file__)),w.relative(source):w.sha(source)},'fabrication_released':False}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({x:result[x] for x in ['passed','runtime_failure','empty','mesh']})
if __name__=='__main__':run()
