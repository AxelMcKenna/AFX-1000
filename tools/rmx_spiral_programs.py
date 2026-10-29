#!/usr/bin/env python3
"""Freeze independent static Spiral programs before their original recordings."""
import argparse,json
from pathlib import Path
import numpy as np
from tools.rmx_drums import require
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_spiral_return import BUTTONS
from tools import rmx_spiral_static_match as match

FRAMES=480000


def sources(stage):
 seed={'main':0x53504d31,'pitch':0x53505031,'mixed':0x53505831,'fresh2':0x53504632}[stage];rng=np.random.default_rng(seed);x=np.zeros((FRAMES,2),dtype='<f4');n=96000;t=np.arange(n)/48000
 z=rng.normal(0,.006,(n,2))+np.column_stack((.027*np.sin(2*np.pi*(43*t+217*t*t))+.013*np.sin(2*np.pi*3701*t),.031*np.cos(2*np.pi*(97*t+463*t*t))+.011*np.cos(2*np.pi*6173*t)))
 for start,stop,gain in [(0,11873,.2),(11873,28717,2),(28717,39019,0),(39019,67031,.1),(67031,n,1)]:z[start:stop]*=gain
 x[48000:144000]=z
 for i in [48031,97117,145031,168193,190129]:x[i]+=rng.uniform(-.12,.12,2)
 pulses=np.zeros_like(x)
 for i in [48031,48379,62971,96113,113197,144319,168193,190129]:pulses[i]=rng.uniform(-.27,.27,2)
 return dict(program=x,pulses=pulses)


def recipe(stage):
 rows=[]
 if stage=='fresh2':
  rng=np.random.default_rng(0x53504633);boundary=[0,1,3,4,5,8,9,28,29,63,64,65,66,127,128,129,130,131,192,254,255];pitch=[0,1,63,127,128,129,130,131,192,254,255]
  for i in range(192):
   main=i//2 if i<66 else int(rng.choice(boundary)) if i<128 else int(rng.integers(256))
   rows.append(dict(name=f'spiral-fresh2-{i:03d}',direction=['up','down'][i%2],main=main,time=int(rng.integers(256)),pitch=pitch[(i*7)%len(pitch)] if i<128 else int(rng.integers(256)),source='pulses' if i%3==0 else 'program',block=[8,17,31,32,79,127,263,1021,4093,4096][i%10]))
  return rows
 if stage in ['main','pitch']:
  for direction in ['up','down']:
   for raw in range(256):rows.append(dict(name=f'spiral-{stage}-{direction}-{raw:03d}',direction=direction,main=raw if stage=='main' else 128,time=([0,64,128,192,255] if stage=='main' else [0,11,63,127,128,191,255])[raw%(5 if stage=='main' else 7)],pitch=0 if stage=='main' else raw,source='program',block=[32,64,127,128,257,511,1024][raw%7]))
 else:
  rng=np.random.default_rng(0x53505832);main=[0,1,3,4,5,7,8,9,16,28,29,31,32,33,62,63,64,65,66,127,128,129,130,131,154,192,224,246,252,253,254,255];pitch=[0,1,64,127,128,129,130,131,192,254,255]
  for i in range(96):rows.append(dict(name=f'spiral-mixed-{i:03d}',direction=['up','down'][i%2],main=main[i%len(main)] if i<64 else int(rng.integers(256)),time=int(rng.integers(256)),pitch=pitch[(i*3)%len(pitch)] if i<64 else int(rng.integers(256)),source='program' if i%3 else 'pulses',block=[32,79,263,1021,4093,64][i%6]))
 return rows


def predict(a):
 root=new_directory(a.session);bound=match.bindings();binary=sha256(a.renderer);(root/'predictions').mkdir();outputs={}
 for n,x in sources(a.stage).items():write_wav(root/(n+'.wav'),48000,x.ravel())
 for c in recipe(a.stage):
  out=root/'predictions'/(c['name']+'.wav');run([a.renderer,root/(c['source']+'.wav'),out,c['direction'],c['main'],c['time'],c['pitch'],0,c['block']]);outputs[c['name']]=sha256(out)
 require(bound==match.bindings() and binary==sha256(a.renderer),'Prediction source changed');save_json(root/'prediction.json',dict(kind='spiral-static-frozen-prediction',stage=a.stage,cases=recipe(a.stage),source_sha256=bound,renderer=str(a.renderer.resolve()),renderer_sha256=binary,output_sha256=outputs,input_sha256={n:sha256(root/(n+'.wav')) for n in sources(a.stage)}))


def capture(a):
 frozen=json.loads((a.session/'prediction.json').read_text());require(frozen['source_sha256']==match.bindings() and frozen['cases']==recipe(a.stage) and sha256(Path(frozen['renderer']))==frozen['renderer_sha256'],'Frozen prediction changed');inventory=json.loads(run([a.host,'inventory',a.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original');save_json(a.session/'inventory.json',inventory)
 def setting(name,value):
  matches=[p for p in inventory['parameters'] if p['name']==name];require(len(matches)==1,'Original parameter differs '+name);return {k:matches[0][k] for k in ['id','index','name']}|dict(value=value)
 rows=[]
 for c in recipe(a.stage):
  require(sha256(a.session/(c['source']+'.wav'))==frozen['input_sha256'][c['source']] and sha256(a.session/'predictions'/(c['name']+'.wav'))==frozen['output_sha256'][c['name']],'Frozen audio changed')
  values=dict(AutoButton=1,QuantizeButton=0,InputButton=1,XpadButton=0,IsolatorButton=0,DefaultSwitch=1,UserSwitch=0,SceneVolume=c['main']/255,Sub1Volume=c['time']/255,Sub2Volume=c['pitch']/255);values[BUTTONS[c['direction']]]=1
  plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,sample_rate=48000,bpm=120,tail_seconds=0,parameters=[setting(k,v) for k,v in values.items()],events=[]);path=a.session/(c['name']+'.json');save_json(path,plan);run([a.host,'render',a.plugin,a.session/(c['source']+'.wav'),path,a.session/c['name'],c['block']]);rows.append(c|dict(receipt_sha256=sha256(a.session/c['name']/'receipt.json')));print('CAPTURED',c['name'],flush=True)
 require(frozen['source_sha256']==match.bindings(),'Capture source changed');save_json(a.session/'matrix.json',dict(kind='spiral-static-prospective-original',stage=a.stage,cases=rows,prediction_sha256=sha256(a.session/'prediction.json')))


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 for name in ['predict','capture']:
  q=s.add_parser(name);q.add_argument('--stage',choices=['main','pitch','mixed','fresh2'],required=True);q.add_argument('--session',type=Path,required=True)
  if name=='predict':q.add_argument('--renderer',type=Path,required=True)
  else:q.add_argument('--host',type=Path,required=True);q.add_argument('--plugin',type=Path,required=True)
 a=p.parse_args();globals()[a.command](a)
if __name__=='__main__':main()
