#!/usr/bin/env python3
"""Compare development Spiral gestures with explicit callback and control delivery."""
import argparse,json
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion as motion
from tools import rmx_spiral_static_match as static
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_drums import require
from tools.reference_audio import save_json,sha256
from tools.noise_statistics import float_wav
from tools.rmx_filter_match import screen


def bindings():return static.bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_spiral_motion_match.py','tools/rmx_spiral_motion.py','tools/spiral_motion_probe.cpp','research/audio/experiments/SpiralMotion.h']}


def schedule(c):
 rows=[f"RMX_SPIRAL_MOTION 2 {int(c['direction']=='down')} {c['block']} {c['main']} {c['time']} {c['pitch']} {int(c['initial_enabled'])}"] if 'initial_enabled' in c else [f"RMX_SPIRAL_MOTION 1 {int(c['direction']=='down')} {c['block']} {c['main']} {c['time']} {c['pitch']}"]
 ids=dict(main=0,time=1,pitch=2,enabled=3,direction=4)
 rows += [f"{e['frame']} {ids[e['control']]} {e['raw']}" for e in c['changes']]
 return '\n'.join(rows)+'\n'


def transport(clock,block,changes):
 result=clock.copy();pending=np.zeros((32,2),dtype=clock.dtype);received=available=head=generated=change=start=0
 while start<len(clock):
  while change<len(changes) and changes[change]['frame']==start:change+=1
  count=min(block,len(clock)-start)
  if change<len(changes):count=min(count,changes[change]['frame']-start)
  read=written=0
  while read<count:
   take=min(32-received,count-read);received+=take;read+=take;emit=min(available,count-written);result[start+written:start+written+emit]=pending[head:head+emit];written+=emit;available-=emit;head+=emit
   if received==32:
    pending[:]=0;n=min(32,len(clock)-generated);pending[:n]=clock[generated:generated+n];generated+=32;received=0;available=32;head=0
  start+=count
 return result


def original(a,c,expected_source=None):
 folder=a.session/c['name'];r=json.loads((folder/'receipt.json').read_text());require(r['complete'] and r['role']=='reference' and r['host_sha256']==sha256(a.host) and all(r['plugin'][k]==v for k,v in IDENTITY.items()) and r['maximum_block_size']==c['block'],'Original identity/recipe differs')
 for n,k in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/n)==r[k],'Original artifact changed')
 for b in r['plugin']['binary_files']:require(sha256(Path(r['plugin']['bundle'])/b['path'])==b['sha256'],'Original binary changed')
 inventory=json.loads((a.session/'inventory.json').read_text());plan=motion.plan_for(c,inventory);require(json.loads((folder/'plan.json').read_text())==plan,'Original plan differs');source=a.session/(c['source']+'.wav');require(sha256(source)==r['input_sha256']==sha256(Path(r['input_path'])),'Input changed')
 requested=[p|dict(frame=-1) for p in plan['parameters']]+plan['events'];actual=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(requested)==len(actual),'Control delivery count differs');final={}
 for req,event in zip(requested,actual,strict=True):require(all(req[k]==event[k] for k in ['name','id','index','frame']) and np.float32(req['value'])==np.float32(event['requested_value']) and abs(event['immediate_readback']-float(np.float32(req['value'])))<=1e-6,'Control delivery differs');final[req['name']]=float(np.float32(req['value']))
 after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-6 for k,v in final.items()),'Final controls differ');rate,x=float_wav(folder/'audio.wav');sr,input_audio=float_wav(source);require(rate==sr==48000 and x.shape==input_audio.shape and x.shape[1]==2,'Extent differs');require(np.array_equal(input_audio,motion.programs.sources('mixed')['program'] if expected_source is None else expected_source),'Stimulus differs');return r,x,input_audio


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['session','host','renderer','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();bound=bindings();binary=sha256(a.renderer);root=new_directory(a.output);rows=[]
 for c in motion.recipe():
  r,x,input_audio=original(a,c);path=root/(c['name']+'.tsv');path.write_text(schedule(c));out=path.with_suffix('.wav');run([a.renderer,a.session/(c['source']+'.wav'),out,path]);rate,y=float_wav(out);require(rate==48000 and y.shape==x.shape,'Candidate extent differs');x=x[32:];y=y[32:];dry=transport(input_audio,c['block'],c['changes'])[32:];whole=screen(x,y);wet=screen(x.astype(float)-dry,y.astype(float)-dry);windows=[]
  for i,e in enumerate(c['changes']):
   stop=c['changes'][i+1]['frame'] if i+1<len(c['changes']) else len(x)
   for kind,start,end in [('edge',max(0,e['frame']-64),min(stop,e['frame']+2048)),('held',min(stop,e['frame']+2048),stop)]:
    if end>start:windows.append(dict(kind=kind,start=start,stop=end,whole=screen(x[start:end],y[start:end]),wet=screen(x[start:end].astype(float)-dry[start:end],y[start:end].astype(float)-dry[start:end])))
  passed=whole['passed'] and wet['passed'] and all(w['whole']['passed'] and w['wet']['passed'] for w in windows);rows.append(dict(case=c['name'],passed=passed,whole=whole,wet=wet,windows=windows,receipt_sha256=sha256(a.session/c['name']/'receipt.json'),candidate_sha256=sha256(out),schedule_sha256=sha256(path)));print('PASS' if passed else 'FAIL',c['name'],flush=True)
 require(bound==bindings() and binary==sha256(a.renderer),'Candidate changed');save_json(root/'comparison.json',dict(kind='spiral-motion-development-comparison',passed=all(r['passed'] for r in rows),cases=rows,source_sha256=bound,renderer_sha256=binary,scope='Eight development-only Original control/button programs. Fixed32/32 boundary and explicit callback splits; whole/wet and event windows1%perchannel. No prospective/sanitizer/live/hardware qualification.'))
 return 0 if all(r['passed'] for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
