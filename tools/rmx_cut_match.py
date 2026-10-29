#!/usr/bin/env python3
"""Frozen prospective original-reference programs for active Cut/Add."""
import argparse
import json
from pathlib import Path
import numpy as np
from tools import rmx_isolate_modes as iso
from tools.reference_audio import save_json,sha256,write_wav
from tools.noise_statistics import float_wav
from tools.rmx_factory_match import new_directory,run,IDENTITY
from tools.rmx_filter_match import screen
from tools.rmx_drums import require


def bindings():return iso.source_hashes()|{n:sha256(Path(n)) for n in ['tools/rmx_cut_match.py','tools/isolate_cut_probe.cpp','research/audio/experiments/CutAdd.h','research/audio/experiments/CutFilterCoefficients.h']}


def source(stage):
 if stage=='discovery':return iso.source()
 seed={'fresh':0x43555431,'lifecycle':0x43555441,'fresh2':0x43555451,'lifecycle2':0x43555461}[stage];rng=np.random.default_rng(seed);t=np.arange(iso.FRAMES)/48000
 x=rng.normal(0,.007,(iso.FRAMES,2))+np.column_stack((.035*np.sin(2*np.pi*(37*t+653*t*t)),.031*np.cos(2*np.pi*(971*t+103*t*t))))
 for start,stop,gain in [(0,63,.02),(63,22173,1),(22173,62971,0),(62971,105997,3),(105997,173051,.08),(173051,227317,0),(227317,309713,2),(309713,iso.FRAMES,.5)]:x[start:stop]*=gain
 pulses=np.zeros_like(x);at=np.unique(rng.integers(0,iso.FRAMES,107));pulses[at]=rng.uniform(-.4,.4,(len(at),2));pulses[31]=[.11,-.23]
 return {k:v.astype('<f4') for k,v in dict(program=x,pulses=pulses).items()}


def recipe(stage):
 if stage=='discovery':return [c for c in iso.recipe() if c['mode']=='cutadd']
 if stage=='lifecycle2':
  rng=np.random.default_rng(0x43555462);rows=[]
  for i,c in enumerate(iso.recipe('gate-lifecycle')):
   changes=[]
   for e in c['changes']:
    e=e.copy()
    if e['frame']:e['frame']+=149
    if e['band']<3:
     if i<12:e['raw']=[13,91,171,239][i%4]
     elif i>=20:e['raw']=int(rng.integers(256)) if e['frame']!=345322 else 128
    changes.append(e)
   rows.append(c|dict(name=f'isolate-cut-lifecycle2-{i:02d}',changes=changes,mode='cutadd',variant='cut-lifecycle2',block=[29,73,509,2039][i%4]))
  return rows
 if stage=='lifecycle':
  cases=iso.recipe('gate-lifecycle2')
  return [c|dict(name=c['name'].replace('lifecycle2-gatedrive','cut-lifecycle'),mode='cutadd',variant='cut-lifecycle') for c in cases]
 rows=[];values=[0,11,64,92,93,118,122,123,124,127,128,130,131,132,147,148,157,166,187,192,236,237,246,255];rng=np.random.default_rng(0x43555432)
 for i in range(28):
  changes=[]
  for n,frame in enumerate([79,31037,64193,96113,120097,144319,192193,227431,240277,288419,312479]):
   band=(i+n)%3;raw=values[(i*3+n)%len(values)];changes.append(dict(frame=frame,band=band,raw=raw))
   if n%3==0:changes.extend(dict(frame=frame+17,band=b,raw=int(rng.choice(values))) for b in range(3) if b!=band)
  changes.extend(dict(frame=345239,band=b,raw=128) for b in range(3))
  rows.append(dict(name=f'isolate-cut-{stage}-{i:02d}',source='program' if i%2==0 else 'pulses',mode='cutadd',variant='cut-fresh',block=[17,67,263,1021,4093,32,513][i%7],bpm=120,changes=changes))
 if stage=='fresh2':
  for i,c in enumerate(rows):
   c['block']=[31,79,257,1024,3203,63,4096][i%7]
   for n,e in enumerate(c['changes']):
    e['frame']+=113
    if e['frame']<345352:e['raw']=values[(i*5+n*3+11)%len(values)]
 return rows


def predict(a):
 require(a.stage!='discovery','Use fresh stage');source_binding=bindings();binary=sha256(a.renderer);root=new_directory(a.session);(root/'predictions').mkdir();outputs={}
 for name,x in source(a.stage).items():write_wav(root/(name+'.wav'),48000,x.ravel())
 for c in recipe(a.stage):
  path=root/'predictions'/(c['name']+'.tsv');path.write_text(iso.schedule(c));out=path.with_suffix('.wav');run([a.renderer,root/(c['source']+'.wav'),out,path]);outputs[c['name']]=sha256(out)
 require(source_binding==bindings() and binary==sha256(a.renderer),'Prediction changed')
 save_json(root/'prediction.json',dict(kind='cutadd-frozen-prediction',stage=a.stage,cases=recipe(a.stage),source_sha256=source_binding,renderer=str(a.renderer.resolve()),renderer_sha256=binary,output_sha256=outputs))


def capture(a):
 require(a.stage!='discovery','Discovery already retained');frozen=json.loads((a.session/'prediction.json').read_text());require(frozen['source_sha256']==bindings() and frozen['cases']==recipe(a.stage),'Frozen source changed');require(sha256(Path(frozen['renderer']))==frozen['renderer_sha256'],'Frozen binary changed');inventory=json.loads(run([a.host,'inventory',a.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Original identity changed');save_json(a.session/'inventory.json',inventory);rows=[]
 for c in recipe(a.stage):
  require(sha256(a.session/'predictions'/(c['name']+'.wav'))==frozen['output_sha256'][c['name']],'Prediction changed');p=a.session/(c['name']+'.json');save_json(p,iso.plan_for(c,inventory));run([a.host,'render',a.plugin,a.session/(c['source']+'.wav'),p,a.session/c['name'],c['block']]);rows.append(c|dict(receipt_sha256=sha256(a.session/c['name']/'receipt.json')));print('CAPTURED',c['name'],flush=True)
 require(frozen['source_sha256']==bindings(),'Capture source changed');save_json(a.session/'matrix.json',dict(kind='cutadd-fresh-original',cases=rows,source_sha256=frozen['source_sha256']))


def compare(a):
 bound=bindings();binary=sha256(a.renderer);root=new_directory(a.output);rows=[];sources=source(a.stage)
 if a.stage!='discovery':
  frozen=json.loads((a.session/'prediction.json').read_text());require(sha256(Path(frozen['renderer']))==frozen['renderer_sha256'],'Frozen binary changed')
 for c in recipe(a.stage):
  reference,provenance=iso.original(a,c,expected_source=sources[c['source']]);schedule=root/(c['name']+'.tsv');schedule.write_text(iso.schedule(c));out=schedule.with_suffix('.wav');run([a.renderer,a.session/(c['source']+'.wav'),out,schedule]);rate,candidate=float_wav(out);require(rate==48000 and reference.shape==candidate.shape,'Candidate extent changed');complete_peak=float(np.max(np.abs(candidate-reference)));sample_bits=bool(np.array_equal(candidate.view('u4'),reference.view('u4')))
  reference=reference[32:];candidate=candidate[32:];whole=screen(reference,candidate);windows=[dict(kind=k,start=s,stop=t,score=screen(reference[s:t],candidate[s:t])) for k,s,t in [('pre-control',256,96000),('activation',96079,98127),('held',98127,240173),('return-edge',240173,242221),('return',242221,iso.FRAMES-32)]]
  if a.stage!='discovery':
   points=sorted(set(e['frame'] for e in c['changes']))
   for i,frame in enumerate(points):
    stop=points[i+1] if i+1<len(points) else iso.FRAMES-32
    for kind,start,end in [('control-edge',max(0,frame-64),min(stop,frame+2048)),('control-held',min(stop,frame+2048),stop)]:
     if end>start:windows.append(dict(kind=kind,start=start,stop=end,score=screen(reference[start:end],candidate[start:end])))
   require(sha256(a.session/'predictions'/(c['name']+'.wav'))==frozen['output_sha256'][c['name']],'Frozen output changed')
   if not a.regression:require(frozen['source_sha256']==bound and frozen['renderer_sha256']==binary and frozen['output_sha256'][c['name']]==sha256(out),'Prospective source/binary/output changed')
  passed=whole['passed'] and all(w['score']['passed'] for w in windows);rows.append(provenance|dict(passed=passed,whole=whole,windows=windows,candidate_sha256=sha256(out),schedule_sha256=sha256(schedule),maximum_complete_sample_difference=complete_peak,complete_sample_bit_identity=sample_bits));print('PASS' if passed else 'FAIL',c['name'],flush=True)
 require(bound==bindings() and binary==sha256(a.renderer),'Candidate changed during comparison')
 save_json(root/'comparison.json',dict(kind='rmx220-cutadd-research',stage=a.stage,passed=all(r['passed'] for r in rows),cases=rows,source_sha256=bound,renderer_sha256=binary,prospective=a.stage!='discovery' and not a.regression,live_engine=a.live,scope='Default48k, input-only120BPM, fixed32/32, unchanged1% independent per-channel whole/edge/held/return gates. Other profiles/rates and hardware unqualified.'))


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 for name in ['predict','capture','compare']:
  q=s.add_parser(name);q.add_argument('--stage',choices=['discovery','fresh','lifecycle','fresh2','lifecycle2'],default='discovery');q.add_argument('--session',type=Path,required=True)
  if name!='predict':q.add_argument('--host',type=Path,required=True)
  if name=='capture':q.add_argument('--plugin',type=Path,required=True)
  else:q.add_argument('--renderer',type=Path,required=True)
  if name=='compare':q.add_argument('--output',type=Path,required=True);q.add_argument('--regression',action='store_true');q.add_argument('--live',action='store_true')
 a=p.parse_args();globals()[a.command](a)
if __name__=='__main__':main()
