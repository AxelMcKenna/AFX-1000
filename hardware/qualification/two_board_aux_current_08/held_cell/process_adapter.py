"""Bounded process adapter that preserves crashes and timeouts before promotion."""
import json,subprocess,time,hashlib
from pathlib import Path

def run_recorded(command,folder,timeout=180,input_paths=()):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
 report={'command':list(command),'timeout_seconds':timeout,'status':'started','input_sha256':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in input_paths}}
 path=folder/'process.json';path.write_text(json.dumps(report,indent=2)+'\n');started=time.monotonic()
 try:
  p=subprocess.run(command,capture_output=True,timeout=timeout);stdout=p.stdout;stderr=p.stderr;report.update(returncode=p.returncode,status='passed' if p.returncode==0 else 'failed',signal=-p.returncode if p.returncode<0 else None)
 except subprocess.TimeoutExpired as e:stdout=e.stdout or b'';stderr=e.stderr or b'';report.update(returncode=None,status='timeout',signal=None)
 except OSError as e:stdout=b'';stderr=str(e).encode();report.update(returncode=None,status='launch_failed',signal=None)
 report['elapsed_seconds']=time.monotonic()-started
 for name,data in [('stdout.log',stdout),('stderr.log',stderr)]:
  (folder/name).write_bytes(data);report[name+'_sha256']=hashlib.sha256(data).hexdigest()
 report['inputs_unchanged']={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in report['input_sha256'].items()}
 path.write_text(json.dumps(report,indent=2)+'\n')
 return report
