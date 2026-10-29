#!/usr/bin/env python3
"""Independently rescore and sanitize a static Spiral reference comparison."""
import argparse,json,os,subprocess
from pathlib import Path
import numpy as np
from tools import rmx_spiral_static_match as match
from tools.rmx_spiral_prospective import score
from tools.reference_audio import save_json,sha256
from tools.noise_statistics import float_wav
from tools.rmx_factory_match import new_directory
from tools.rmx_drums import require


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['comparison','original-root','host','renderer','sanitizer','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();root=new_directory(a.output);bound=match.bindings();verifier=sha256(Path(__file__));score_verifier=sha256(Path('tools/rmx_spiral_prospective.py'));native=json.loads(a.comparison.read_text());require(native['source_sha256']==bound and native['renderer_sha256']==sha256(a.renderer) and native['host_sha256']==sha256(a.host),'Compared source/binary differs')
 symbols=subprocess.check_output(['nm','-C',str(a.sanitizer)],text=True);require('___asan_init' in symbols and '___ubsan_handle_' in symbols,'Missing sanitizers');binaries={str(v):sha256(v) for v in [a.renderer,a.sanitizer]};rows=[];transported=native.get('callback_transport',False)
 for index,row in enumerate(native['cases']):
  folder=a.original_root/row['session']/row['case'];r,plan,controls,direction,x=match.original(folder,a.host);require(sha256(folder/'receipt.json')==row['receipt_sha256'] and r['output_sha256']==row['original_sha256'],'Original provenance differs');raw={k:round(controls[k]*255) for k in ['SceneVolume','Sub1Volume','Sub2Volume']};require(raw==row['controls_raw'],'Original controls differ')
  candidate=a.comparison.parent/f'{index:04d}-candidate.wav';require(sha256(candidate)==row['candidate_sha256'],'Candidate changed');rate,y=float_wav(candidate);require(rate==48000 and y.shape==x.shape,'Extent differs');_,input_audio=float_wav(Path(r['input_path']));dry=np.zeros_like(x);dry[:min(len(dry),len(input_audio))]=input_audio[:len(dry)]
  x=x[32:];y=y[32:] if transported else y[:len(x)];dry=match.transport(dry,dry,r['maximum_block_size'])[32:] if transported else dry[:len(x)]
  whole=score(x,y);wet=score(x.astype(float)-dry,y.astype(float)-dry)
  for independent,recorded in [(whole,row['whole']),(wet,row['wet'])]:
   require(independent['passed']==recorded['passed'],'Independent verdict differs')
   for v,w in zip(independent['channels'],recorded['channels'],strict=True):
    for k in ['relative_rms_error','absolute_error_rms']:require(v[k] is w[k] if v[k] is None else np.isclose(v[k],w[k],rtol=1e-12,atol=1e-15),'Independent score differs')
  windows=[]
  for start in range(0,len(x),48000):
   stop=min(start+48000,len(x));windows.append(dict(start=start,stop=stop,whole=score(x[start:stop],y[start:stop]),wet=score(x[start:stop].astype(float)-dry[start:stop],y[start:stop].astype(float)-dry[start:stop])))
  out=root/f'{index:04d}-sanitizer.wav';command=[str(a.sanitizer),r['input_path'],str(out),direction,str(raw['SceneVolume']),str(raw['Sub1Volume']),str(raw['Sub2Volume']),str(plan['tail_seconds'])]+([str(r['maximum_block_size'])] if transported else []);run=subprocess.run(command,capture_output=True,text=True,timeout=120,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'));require(run.returncode==0 and not run.stderr,'Sanitizer failed: '+run.stderr);require(sha256(out)==row['candidate_sha256'],'Sanitizer audio differs')
  passed=whole['passed'] and wet['passed'] and all(w['whole']['passed'] and w['wet']['passed'] for w in windows);rows.append(dict(case=row['case'],session=row['session'],passed=passed,whole=whole,wet=wet,windows=windows,sanitizer_byte_identical=True,candidate_sha256=row['candidate_sha256'],receipt_sha256=row['receipt_sha256']));print('AUDITED',row['case'],passed,flush=True)
 require(bound==match.bindings() and verifier==sha256(Path(__file__)) and score_verifier==sha256(Path('tools/rmx_spiral_prospective.py')) and all(sha256(Path(p))==h for p,h in binaries.items()),'Audit inputs changed');save_json(root/'verification.json',dict(kind='spiral-static-independent-regression-audit',passed=all(r['passed'] for r in rows),programs=len(rows),cases=rows,source_sha256=bound,verifier_sha256=verifier,score_verifier_sha256=score_verifier,renderer_sha256=binaries,comparison_sha256=sha256(a.comparison),callback_transport=transported,scope='Existing reference programs, independent1%per-channel whole/wet/one-second windows and complete optimized/sanitized WAV byte identity. No prospective or live-wrapper/hardware claim.'))
 return 0 if all(r['passed'] for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
