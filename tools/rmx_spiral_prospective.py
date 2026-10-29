#!/usr/bin/env python3
"""Seal prospective Spiral predictions and independently score/sanitize fresh captures."""
import argparse,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from tools import rmx_spiral_static_match as match
from tools import rmx_spiral_programs as programs
from tools.reference_audio import save_json,sha256
from tools.noise_statistics import float_wav
from tools.rmx_factory_match import new_directory
from tools.rmx_drums import require


def seal(a):
 f=json.loads((a.session/'prediction.json').read_text());cases=programs.recipe(a.stage);require(f['stage']==a.stage and f['cases']==cases and f['source_sha256']==match.bindings() and sha256(Path(f['renderer']))==f['renderer_sha256'],'Frozen candidate differs')
 require(all(not (a.session/c['name']).exists() and sha256(a.session/'predictions'/(c['name']+'.wav'))==f['output_sha256'][c['name']] for c in cases),'Original already exists or predictions changed')
 save_json(a.session/'prediction-chronology.json',dict(kind='spiral-static-pre-capture-seal',created_utc=datetime.now(timezone.utc).isoformat(),stage=a.stage,programs=len(cases),prediction_sha256=sha256(a.session/'prediction.json'),source_sha256=match.bindings(),sealer_sha256=sha256(Path(__file__))))


def score(a,b):
 rows=[]
 for channel in range(2):
  x=a[:,channel].astype(np.float64);y=b[:,channel].astype(np.float64);energy=float(np.sum(x*x));error=x-y;absolute=float(np.sqrt(np.mean(error*error)));relative=float(np.sqrt(np.sum(error*error)/energy)) if energy>1e-20 else None
  rows.append(dict(relative_rms_error=relative,absolute_error_rms=absolute,passed=relative<=.01 if relative is not None else absolute<=1e-8))
 return dict(passed=all(r['passed'] for r in rows),channels=rows)


def audit(a):
 root=new_directory(a.output);bound=match.bindings();verifier=sha256(Path(__file__));f=json.loads((a.session/'prediction.json').read_text());seal=json.loads((a.session/'prediction-chronology.json').read_text());native=json.loads(a.comparison.read_text());recipe=programs.recipe(a.stage);old={r['case']:r for r in native['cases']}
 require(f['source_sha256']==seal['source_sha256']==native['source_sha256']==bound and f['renderer_sha256']==native['renderer_sha256']==sha256(Path(f['renderer'])) and seal['sealer_sha256']==verifier and seal['prediction_sha256']==sha256(a.session/'prediction.json'),'Candidate or pre-capture seal changed')
 require(f['cases']==recipe and set(old)=={c['name'] for c in recipe},'Coverage differs');matrix=json.loads((a.session/'matrix.json').read_text());require(matrix['prediction_sha256']==sha256(a.session/'prediction.json') and [c['name'] for c in matrix['cases']]==[c['name'] for c in recipe],'Capture coverage differs')
 symbols=subprocess.check_output(['nm','-C',str(a.sanitizer)],text=True);require('___asan_init' in symbols and '___ubsan_handle_' in symbols,'Replay lacks sanitizers');san_hash=sha256(a.sanitizer);inputs=programs.sources(a.stage);rows=[]
 for c in recipe:
  r,p,controls,direction,x=match.original(a.session/c['name'],a.host);require(datetime.fromisoformat(seal['created_utc'])<datetime.fromisoformat(r['created_at_utc']),'Original predates prediction seal');require(direction==c['direction'] and r['maximum_block_size']==c['block'] and r['frames']==programs.FRAMES and p['tail_seconds']==0,'Original case differs')
  expected=dict(AutoButton=1,QuantizeButton=0,InputButton=1,XpadButton=0,IsolatorButton=0,DefaultSwitch=1,UserSwitch=0,SceneVolume=c['main']/255,Sub1Volume=c['time']/255,Sub2Volume=c['pitch']/255);expected[programs.BUTTONS[c['direction']]]=1
  require(controls==expected,'Original recipe differs');source=a.session/(c['source']+'.wav');rate,input_audio=float_wav(source);require(rate==48000 and np.array_equal(input_audio,inputs[c['source']]) and sha256(source)==f['input_sha256'][c['source']],'Source recipe differs')
  row=old[c['name']];index=native['cases'].index(row);candidate=a.comparison.parent/f'{index:04d}-candidate.wav';require(sha256(candidate)==row['candidate_sha256']==f['output_sha256'][c['name']]==sha256(a.session/'predictions'/(c['name']+'.wav')),'Prospective output differs');rate,y=float_wav(candidate);require(rate==48000 and y.shape==x.shape==(programs.FRAMES,2),'Candidate extent differs');x=x[32:];y=y[32:] if native.get('callback_transport',False) else y[:len(x)];dry=match.transport(input_audio,input_audio,c['block'])[32:] if native.get('callback_transport',False) else input_audio[:len(x)];whole=score(x,y);wet=score(x.astype(float)-dry,y.astype(float)-dry)
  for independent,recorded in [(whole,row['whole']),(wet,row['wet'])]:
   require(independent['passed']==recorded['passed'],'Independent verdict differs')
   for v,w in zip(independent['channels'],recorded['channels'],strict=True):
    for k in ['relative_rms_error','absolute_error_rms']:require(v[k] is w[k] if v[k] is None else np.isclose(v[k],w[k],rtol=1e-12,atol=1e-15),'Independent score differs')
  windows=[]
  for start in range(0,len(x),48000):
   stop=min(start+48000,len(x));windows.append(dict(start=start,stop=stop,whole=score(x[start:stop],y[start:stop]),wet=score(x[start:stop].astype(float)-dry[start:stop],y[start:stop].astype(float)-dry[start:stop])))
  out=root/(c['name']+'.wav');run=subprocess.run([str(a.sanitizer),str(source),str(out),c['direction'],str(c['main']),str(c['time']),str(c['pitch']),'0']+([str(c['block'])] if native.get('callback_transport',False) else []),capture_output=True,text=True,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),timeout=120);require(run.returncode==0 and not run.stderr,'Sanitizer failed: '+run.stderr);require(sha256(out)==row['candidate_sha256'],'Sanitizer audio differs')
  passed=whole['passed'] and wet['passed'] and all(w['whole']['passed'] and w['wet']['passed'] for w in windows);rows.append(dict(case=c['name'],passed=passed,whole=whole,wet=wet,windows=windows,sanitizer_byte_identical=True,receipt_sha256=sha256(a.session/c['name']/'receipt.json'),candidate_sha256=sha256(candidate)));print('AUDITED',c['name'],passed,flush=True)
 require(bound==match.bindings() and verifier==sha256(Path(__file__)) and san_hash==sha256(a.sanitizer),'Audit inputs changed');save_json(root/'verification.json',dict(kind='spiral-static-prospective-independent-audit',passed=all(r['passed'] for r in rows),stage=a.stage,programs=len(rows),cases=rows,source_sha256=bound,verifier_sha256=verifier,sanitizer_sha256=san_hash,comparison_sha256=sha256(a.comparison),prediction_sha256=sha256(a.session/'prediction.json'),seal_sha256=sha256(a.session/'prediction-chronology.json'),scope='Static Default48k/120BPM. Source/binary/audio predictions sealed before every original recording. Independent1%channel whole/wet/one-second windows and complete optimized/sanitized WAV byte identity. No live-wrapper, moving-control or hardware qualification.'))
 return 0 if all(r['passed'] for r in rows) else 1


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 for name in ['seal','audit']:
  q=s.add_parser(name);q.add_argument('--stage',choices=['main','pitch','mixed','fresh2'],required=True);q.add_argument('--session',type=Path,required=True)
  if name=='audit':
   for k in ['host','sanitizer','comparison','output']:q.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();return globals()[a.command](a)
if __name__=='__main__':raise SystemExit(main())
