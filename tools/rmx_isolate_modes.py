#!/usr/bin/env python3
"""Original-reference discovery for Cut/Add, Trans/Roll and Gate/Drive."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_drums import require
from tools.rmx_drums_fx import source_hashes as core_hashes
from tools.rmx_factory_match import new_directory,run,IDENTITY
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE
from tools.rmx_release import plan_for as release_plan

FRAMES=384000
MODES={'cutadd':1,'transroll':2,'gatedrive':3}
BUTTONS={'cutadd':'CutAddButton','transroll':'TransRollButton','gatedrive':'GateDriveButton'}
BANDS=['IsoLowVolume','IsoMidVolume','IsoHiVolume']


def source(stage='discovery'):
    if stage in ['gate-fresh','gate-fresh2','gate-lifecycle','gate-lifecycle2']:
        seed={'gate-fresh':0x49534f31,'gate-fresh2':0x49534f41,'gate-lifecycle':0x49534f51,'gate-lifecycle2':0x49534f61}[stage]
        t=np.arange(FRAMES)/48000;rng=np.random.default_rng(seed)
        x=rng.normal(0,.008,(FRAMES,2))
        x+=np.column_stack((.05*np.sin(2*np.pi*(19*t+800*t*t)),.04*np.sin(2*np.pi*(190*t+270*t*t))))
        if stage!='gate-fresh':x+=np.column_stack((.011*np.cos(2*np.pi*97*t),.017*np.sin(2*np.pi*7919*t)))
        for start,stop,gain in [(0,79,.02),(79,23179,1),(23179,61937,0),(61937,105931,4),(105931,174007,.1),(174007,226193,0),(226193,311997,2),(311997,FRAMES,.5)]:x[start:stop]*=gain
        pulses=np.zeros_like(x);at=np.unique(rng.integers(0,FRAMES,101));pulses[at]=rng.uniform(-.4,.4,(len(at),2))
        return {k:v.astype('<f4') for k,v in dict(program=x,pulses=pulses).items()}
    t=np.arange(FRAMES)/48000;x=np.random.default_rng(0x49534f01).normal(0,.004,(FRAMES,2))
    x += np.column_stack((.03*np.sin(2*np.pi*73*t)+.017*np.sin(2*np.pi*1181*t)+.009*np.sin(2*np.pi*7907*t),.025*np.sin(2*np.pi*101*t)+.013*np.cos(2*np.pi*1597*t)+.011*np.sin(2*np.pi*8999*t)))
    envelope=np.zeros(FRAMES)
    for start,stop,gain in [(48000,96000,1),(96000,102000,6),(102000,120000,1),(120000,144000,.1),(144000,192000,3),(240000,312000,7),(312000,360000,.5)]:envelope[start:stop]=gain
    x*=envelope[:,None];pulses=np.zeros_like(x);at=[31,48061,95993,96097,120239,144301,168359,192421,216487,239999,240241,264301,288373,312437]
    pulses[at]=np.random.default_rng(0x49534f02).uniform(-.25,.25,(len(at),2))
    return {k:v.astype('<f4') for k,v in dict(program=x,pulses=pulses).items()}


def recipe(stage='discovery'):
    if stage in ['gate-lifecycle','gate-lifecycle2']:
        second=stage=='gate-lifecycle2';rows=[];rng=np.random.default_rng(0x49534f62 if second else 0x49534f52)
        for i in range(32):
            changes=[]
            if i<12:
                changes=[dict(frame=0,band=i//4,raw=([3,83,173,241] if second else [0,64,192,255])[i%4])]
                changes.extend(dict(frame=f+(37 if second else 0),band=3,raw=on) for f,on in [(120003,0),(168079,1),(205817,0),(224031,1),(312437,0)])
            elif i<20:
                at=([3,29,47,83,158,211,96193,240061] if second else [1,31,32,79,160,193,96079,240173])[i-12];changes=[dict(frame=0,band=3,raw=0),dict(frame=0,band=i%3,raw=0 if i%2 else 255),dict(frame=at,band=3,raw=1),dict(frame=at+([2,31,95,161] if second else [1,17,63,159])[i%4],band=3,raw=0),dict(frame=at+12017,band=3,raw=1)]
            else:
                for index,frame in enumerate([31001,65017,96079,120031,144301,192173,240241,288373,312437]):
                    if second:frame+=113
                    changes.append(dict(frame=frame,band=3,raw=index%2))
                    changes.extend(dict(frame=frame+17,band=b,raw=int(rng.integers(256))) for b in range(3))
                changes.append(dict(frame=345173,band=3,raw=1))
                changes.extend(dict(frame=345173,band=b,raw=128) for b in range(3))
            prefix='lifecycle2' if second else 'lifecycle';rows.append(dict(name=f'isolate-{prefix}-gatedrive-{i:02d}',source='program' if i%2==0 else 'pulses',mode='gatedrive',variant=prefix,block=([47,83,389,3203] if second else [31,65,511,2048])[i%4],bpm=120,changes=sorted(changes,key=lambda e:e['frame'])))
        return rows
    if stage in ['gate-fresh','gate-fresh2']:
        second=stage=='gate-fresh2';rng=np.random.default_rng(0x49534f42 if second else 0x49534f32);rows=[]
        for i in range(28):
            src='program' if i%2==0 else 'pulses';changes=[]
            if i<12:changes=[dict(frame=(27139 if second else 39139)+i*97,band=i//4,raw=([107,108,147,148] if second else [9,106,149,239])[i%4]),dict(frame=270173+i*31,band=i//4,raw=128)]
            else:
                for frame in sorted(rng.integers(7001,320000,18)):
                    changes.append(dict(frame=int(frame),band=int(rng.integers(3)),raw=int(rng.integers(256))))
                changes.extend(dict(frame=345173,band=b,raw=128) for b in range(3))
            prefix='fresh2' if second else 'fresh';rows.append(dict(name=f'isolate-{prefix}-gatedrive-{i:02d}',source=src,mode='gatedrive',variant=prefix,block=([33,79,513,4093] if second else [16,63,257,1024])[i%4],bpm=120,changes=changes))
        return rows
    rows=[]
    for src,block in [('program',127),('pulses',509)]:
        for mode in MODES:
            rows.append(dict(name=f'isolate-{src}-{mode}-baseline',source=src,mode=mode,variant='baseline',block=block,bpm=120,changes=[]))
            for band in range(3):
                for raw in [0,64,192,255]:rows.append(dict(name=f'isolate-{src}-{mode}-band{band}-raw{raw}',source=src,mode=mode,variant='gesture',block=block,bpm=120,changes=[dict(frame=96079,band=band,raw=raw),dict(frame=240173,band=band,raw=128)]))
    return rows


def source_hashes():return core_hashes()|{n:sha256(Path(n)) for n in ['tools/rmx_isolate_modes.py','tools/isolate_modes_probe.cpp','tools/rmx_release.py','research/audio/experiments/IsolateNeutral.h']}


def plan_for(c,inventory):
    plan=release_plan(dict(effect='echo',bpm=c['bpm'],changes=[]),inventory)
    def setting(name,value):
        p=next(p for p in inventory['parameters'] if p['name']==name);return {k:p[k] for k in ['name','id','index']}|dict(value=value)
    for p in plan['parameters']:
        if p['name']==BUTTONS[c['mode']]:p['value']=1
    plan['parameters'] += [setting(name,128/255) for name in BANDS]
    plan['events']=[setting(BANDS[e['band']] if e['band']<3 else BUTTONS[c['mode']],e['raw']/255 if e['band']<3 else e['raw'])|dict(frame=e['frame'],type='parameter') for e in c['changes']]
    return plan


def schedule(c):return f'RMX_ISOLATE_MODES {2 if any(e["band"]>2 for e in c["changes"]) else 1}\n{MODES[c["mode"]]} {c["block"]} {c["bpm"]}\n'+''.join(f'{e["frame"]} {e["band"]} {e["raw"]}\n' for e in c['changes'])


def capture(a):
    if a.stage!='discovery':
        prediction=json.loads((a.session/'prediction.json').read_text());require(prediction['source_sha256']==source_hashes(),'Frozen source changed');require(prediction['cases']==recipe(a.stage),'Frozen recipes changed');require(sha256(Path(prediction['renderer']))==prediction['renderer_sha256'],'Frozen renderer changed')
        root=a.session
    else:root=new_directory(a.session)
    binding=source_hashes();inventory=json.loads(run([a.host,'inventory',a.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original');save_json(root/'inventory.json',inventory)
    if a.stage=='discovery':
        for name,x in source(a.stage).items():write_wav(root/(name+'.wav'),48000,x.ravel())
    rows=[]
    for c in recipe(a.stage):
        path=root/(c['name']+'.json');save_json(path,plan_for(c,inventory));run([a.host,'render',a.plugin,root/(c['source']+'.wav'),path,root/c['name'],c['block']]);rows.append(c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json')));print('CAPTURED',c['name'],flush=True)
    require(binding==source_hashes(),'Discovery source changed');save_json(root/'matrix.json',dict(kind='rmx220-isolate-modes-discovery',cases=rows,source_sha256=binding))


def original(a,c):
    folder=a.session/c['name'];r=json.loads((folder/'receipt.json').read_text());inventory=json.loads((a.session/'inventory.json').read_text());plan=plan_for(c,inventory)
    require(r['complete'] and r['role']=='reference' and r['sample_rate']==48000 and r['frames']==FRAMES and r['maximum_block_size']==c['block'] and r['host_sha256']==sha256(a.host) and all(r['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong reference extent/identity')
    require(json.loads((folder/'plan.json').read_text())==plan,'Original plan differs')
    for name,key in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==r[key],'Original artifact changed')
    input_path=a.session/(c['source']+'.wav');require(sha256(input_path)==sha256(Path(r['input_path']))==r['input_sha256'],'Original input changed');rate,x=float_wav(input_path);require(rate==48000 and np.array_equal(x,source(a.stage)[c['source']]),'Source samples differ')
    for b in r['plugin']['binary_files']:require(sha256(Path(r['plugin']['bundle'])/b['path'])==b['sha256'],'Original binary changed')
    entries=json.loads((folder/'parameter-log.json').read_text())['entries'];requests=[p|dict(frame=-1) for p in plan['parameters']]+plan['events'];require(len(entries)==len(requests),'Original control count differs');final={}
    for request,event in zip(requests,entries,strict=True):
        expected=float(np.float32(request['value']));require(all(request[k]==event[k] for k in ['name','id','index','frame']) and np.float32(event['requested_value'])==expected and abs(event['immediate_readback']-expected)<1e-14,'Original requested/readback control differs');final[request['name']]=expected
    after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<1e-14 for k,v in final.items()),'Final original controls differ')
    row=next(row for row in json.loads((a.session/'matrix.json').read_text())['cases'] if row['name']==c['name']);require(row==c|dict(receipt_sha256=sha256(folder/'receipt.json')),'Original matrix differs')
    rate,x=float_wav(folder/'audio.wav');require(rate==48000 and x.shape==(FRAMES,2),'Original extent differs')
    return x,dict(case=c['name'],receipt_sha256=sha256(folder/'receipt.json'),output_sha256=r['output_sha256'],plan_sha256=r['plan_sha256'],input_sha256=r['input_sha256'])


def compare(a):
    binding=source_hashes();binary=sha256(a.renderer);root=new_directory(a.output);rows=[]
    for c in recipe(a.stage):
        reference,provenance=original(a,c);path=root/(c['name']+'.tsv');path.write_text(schedule(c));out=root/(c['name']+'.wav');run([a.renderer,a.session/(c['source']+'.wav'),out,path]);rate,candidate=float_wav(out);require(rate==48000 and candidate.shape==reference.shape,'Candidate extent differs');reference,candidate=reference[32:],candidate[32:];whole=screen(reference,candidate)
        windows=[dict(kind=k,start=s,stop=t,score=screen(reference[s:t],candidate[s:t])) for k,s,t in [('pre-control',256,96000),('activation',96079,98127),('held',98127,240173),('return-edge',240173,242221),('return',242221,FRAMES-32)]]
        if a.stage!='discovery':
            points=sorted(set(e['frame'] for e in c['changes']))
            for i,frame in enumerate(points):
                stop=points[i+1] if i+1<len(points) else FRAMES-32
                for kind,start,end in [('control-edge',max(0,frame-64),min(stop,frame+2048)),('control-held',min(stop,frame+2048),stop)]:
                    if end>start:windows.append(dict(kind=kind,start=start,stop=end,score=screen(reference[start:end],candidate[start:end])))
        passed=whole['passed'] and all(w['score']['passed'] for w in windows);rows.append(provenance|dict(passed=passed,whole=whole,windows=windows,candidate_sha256=sha256(out),schedule_sha256=sha256(path)));print('PASS' if passed else 'FAIL',c['name'],flush=True)
        if a.stage!='discovery':
            frozen=json.loads((a.session/'prediction.json').read_text());require(sha256(Path(frozen['renderer']))==frozen['renderer_sha256'],'Frozen binary changed');require(sha256(a.session/'predictions'/(c['name']+'.wav'))==frozen['output_sha256'][c['name']],'Frozen output changed')
            if not a.regression:require(frozen['source_sha256']==binding and frozen['renderer_sha256']==binary and frozen['output_sha256'][c['name']]==sha256(out),'Prospective source/binary/output changed')
    require(binding==source_hashes() and binary==sha256(a.renderer),'Candidate changed');save_json(root/'comparison.json',dict(kind='rmx220-isolate-modes-comparison',passed=all(r['passed'] for r in rows),cases=rows,source_sha256=binding,renderer_sha256=binary,acceptance=ACCEPTANCE,prospective=a.stage!='discovery' and not a.regression,scope='Input-only Default48k/120BPM, fixed32/32, unchanged1% whole/held/edge/return per-channel gates. No fitting, wrapper or hardware qualification. Discovery and regression results are development evidence.'))


def predict(a):
    require(a.stage!='discovery','Prediction needs fresh stage');binding=source_hashes();binary=sha256(a.renderer);root=new_directory(a.session);(root/'predictions').mkdir();outputs={}
    for name,x in source(a.stage).items():write_wav(root/(name+'.wav'),48000,x.ravel())
    for c in recipe(a.stage):
        path=root/'predictions'/(c['name']+'.tsv');path.write_text(schedule(c));out=path.with_suffix('.wav');run([a.renderer,root/(c['source']+'.wav'),out,path]);outputs[c['name']]=sha256(out)
    require(binding==source_hashes() and binary==sha256(a.renderer),'Prediction source/binary changed');save_json(root/'prediction.json',dict(kind='isolate-frozen-prediction',stage=a.stage,cases=recipe(a.stage),source_sha256=binding,renderer=str(a.renderer.resolve()),renderer_sha256=binary,output_sha256=outputs))


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ['predict','capture','compare']:
        q=s.add_parser(name)
        q.add_argument('--stage',choices=['discovery','gate-fresh','gate-fresh2','gate-lifecycle','gate-lifecycle2'],default='discovery');q.add_argument('--session',type=Path,required=True)
        if name!='predict':q.add_argument('--host',type=Path,required=True)
        if name=='capture':q.add_argument('--plugin',type=Path,required=True)
        else:
            q.add_argument('--renderer',type=Path,required=True)
            if name=='compare':q.add_argument('--output',type=Path,required=True)
        if name=='compare':q.add_argument('--regression',action='store_true')
    a=p.parse_args();globals()[a.command](a)


if __name__=='__main__':main()
