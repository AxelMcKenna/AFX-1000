"""Pinned isolated Linux executor; output alone is writable, host CAD never launched."""
import subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
out=R/sys.argv[1];out.mkdir(exist_ok=False)
args=['/usr/local/bin/docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges=true','--pids-limit','256','--memory','3g','--cpus','2','--tmpfs','/tmp:rw,nosuid,size=256m','--env','HOME=/tmp','--env',f'PYTHONPATH={REPO}','--mount',f'type=bind,source={REPO},target={REPO},readonly','--mount',f'type=bind,source={out},target={out}','kicad/kicad@sha256:c8f05703e865a1caa7266851cf4986dd01d5fb1148e4f63382b6a73466ba7e71','python3',str(R/sys.argv[2]),*sys.argv[3:]]
p=subprocess.run(args,capture_output=True,text=True,timeout=180);(out/'run.log').write_text(p.stdout+p.stderr);print(p.stdout+p.stderr);assert p.returncode==0
