#!/usr/bin/env python3
"""Capture and compare original Release effects with fixed latency and raw gates."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_drums import require
from tools.rmx_drums_fx import source_hashes as base_hashes
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE

FRAMES=384000
TYPES=dict(backspin=0,echo=1,brake=2)
BUTTONS=dict(backspin='BackSpinSwitch',echo='EchoSwitch',brake='VinylBrakeSwitc')


def waves(stage="discovery"):
    t=np.arange(FRAMES)/48000
    fresh=stage!="discovery"
    fresh2=stage=="fresh-v2"
    tone=np.column_stack((.12*np.sin(2*np.pi*(701 if fresh2 else 659 if fresh else 997)*t),.08*np.cos(2*np.pi*(2017 if fresh2 else 1867 if fresh else 1283)*t)))
    chirp=np.column_stack((.09*np.sin(2*np.pi*((137 if fresh2 else 113 if fresh else 97)*t+(89 if fresh2 else 71 if fresh else 83)*t*t)),.07*np.cos(2*np.pi*((263 if fresh2 else 229 if fresh else 187)*t+(157 if fresh2 else 149 if fresh else 131)*t*t))))
    program=np.random.default_rng(0x72656c50 if fresh2 else 0x72656c40 if fresh else 0x72656c30).normal(0,.025,(FRAMES,2))+np.column_stack((.05*np.sin(2*np.pi*79*t),.04*np.sin(2*np.pi*1141*t)))
    pulses=np.zeros_like(tone);at=[9600,48061,95993,96097,120239,144301,168359,192421,216487,239999,240241,264301,288373,312437]
    if fresh:at=[31,199,47867,91103,91241,108101,132007,156091,181019,209911,239917,271163,312001,359993]
    if fresh2:at=[i+353 for i in at]
    pulses[at]=np.random.default_rng(0x72656c51 if fresh2 else 0x72656c41 if fresh else 0x72656c31).uniform(-.2,.2,(len(at),2))
    return {k:v.astype('<f4') for k,v in dict(tone=tone,chirp=chirp,program=program,pulses=pulses).items()}


def recipe(stage="discovery"):
    if stage!="discovery":
        patterns={
            "low-boundary":[(91117,109),(271141,0)],
            "mid-boundary":[(91117,110),(271141,0)],
            "high-boundary":[(91117,210),(271141,0)],
            "motion":[(91117,1),(117131,109),(144017,110),(170039,209),(196057,210),(222079,255),(271141,0)],
            "retrigger":[(48061,170),(119983,0),(167129,255),(239917,0),(288103,85),(359911,0)],
            "cold":[(0,255),(131137,0)],
            "short":[(91117,170),(91191,0),(132013,85),(132029,0),(181019,255),(181181,0)]}
        rows=[]
        for source,block in [("tone",73),("pulses",257),("chirp",127),("program",509)]:
            rows.append(dict(name="fresh-release-"+source+"-baseline",source=source,effect="echo",variant="baseline",bpm=120,block=block,changes=[]))
            for effect in TYPES:
                for name,events in patterns.items():rows.append(dict(name=f"fresh-release-{source}-{effect}-{name}",source=source,effect=effect,variant=name,bpm=120,block=block,changes=[dict(frame=f,raw=v) for f,v in events]))
        if stage=="fresh-v2":
            for row in rows:
                row['name']=row['name'].replace('fresh-release-','fresh2-release-')
                row['changes']=[e|dict(frame=e['frame']+449 if e['frame'] else 0) for e in row['changes']]
        return rows
    rows=[]
    for source,block in [('tone',128),('pulses',193),('chirp',509),('program',37)]:
        rows.append(dict(name='release-'+source+'-baseline',source=source,effect='echo',variant='baseline',bpm=120,block=block,changes=[]))
        for effect in TYPES:
            for raw in [85,170,255]:rows.append(dict(name=f'release-{source}-{effect}-{raw}',source=source,effect=effect,variant='lever',bpm=120,block=block,changes=[dict(frame=96079,raw=raw),dict(frame=240173,raw=0)]))
    return rows


def source_hashes():return base_hashes()|{n:sha256(Path(n)) for n in ['tools/rmx_release.py','tools/release_probe.cpp']}


def plan_for(c,inventory):
    def setting(name,value):
        p=next(p for p in inventory['parameters'] if p['name']==name);return {k:p[k] for k in ['name','id','index']}|dict(value=value)
    values=dict(OutputVolume=0,AutoButton=0,QuantizeButton=0,InputButton=1,XpadButton=0,DefaultSwitch=1,UserSwitch=0,ReleaseLever=0)
    for name in ['IsolatorButton','CutAddButton','TransRollButton','GateDriveButton','RollButton','OverDubButton','HoldButton','BankShiftButton','XpadTouch','MuteButton','DeleteButton','BpfEchoButton','EchoButton','NoiseButton','SpiralUpButton','ReverbUpButton','HpfEchoButton','LpfEchoButton','CrushEchoButton','SpiralDownButto','ReverbDownButto','KickButton','SnareButton','ClapButton','HihatButton',*BUTTONS.values()]:values[name]=0
    values[BUTTONS[c['effect']]]=1
    return dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,sample_rate=48000,bpm=c['bpm'],tail_seconds=0,parameters=[setting(k,v) for k,v in values.items()],events=[setting('ReleaseLever',e['raw']/255)|dict(frame=e['frame'],type='parameter') for e in c['changes']])


def schedule(c):return f'RMX_RELEASE 1\n{TYPES[c["effect"]]} {c["block"]} {c["bpm"]}\n'+''.join(f'{e["frame"]} {e["raw"]}\n' for e in c['changes'])


def frozen(args):
    require(args.prediction is not None,'Fresh programs require a frozen prediction')
    prediction=json.loads(args.prediction.read_text())
    require(prediction['kind']=='rmx220-release-frozen-fresh-prediction' and prediction['cases']==recipe(args.stage) and prediction['acceptance']==ACCEPTANCE,'Wrong prediction recipe/gates')
    require(prediction['source_sha256']==source_hashes() and prediction['renderer_sha256']==sha256(args.renderer),'Prediction source/binary changed')
    return prediction


def capture(args):
    if args.stage!='discovery':frozen(args)
    binding=source_hashes();root=new_directory(args.session);inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original');save_json(root/'inventory.json',inventory)
    if args.stage!='discovery':save_json(root/'predictions.json',json.loads(args.prediction.read_text()))
    for name,x in waves(args.stage).items():write_wav(root/(name+'.wav'),48000,x.ravel())
    if args.stage!='discovery':require(all(sha256(root/(name+'.wav'))==value for name,value in frozen(args)['inputs_sha256'].items()),'Prediction inputs changed')
    rows=[]
    for c in recipe(args.stage):
        path=root/(c['name']+'.json');save_json(path,plan_for(c,inventory));run([args.host,'render',args.plugin,root/(c['source']+'.wav'),path,root/c['name'],c['block']]);rows.append(c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json')));print('CAPTURED',c['name'],flush=True)
    require(binding==source_hashes(),'Capture source changed');save_json(root/'matrix.json',dict(kind='rmx220-release-'+args.stage,cases=rows,source_sha256=binding,prediction_sha256=sha256(args.prediction) if args.stage!='discovery' else None));return 0


def original(args,c):
    if args.stage!='discovery':require(json.loads((args.session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction)==sha256(args.session/'predictions.json'),'Captured prediction differs')
    folder=args.session/c['name'];r=json.loads((folder/'receipt.json').read_text());inventory=json.loads((args.session/'inventory.json').read_text());plan=plan_for(c,inventory)
    require(r['complete'] and r['role']=='reference' and r['sample_rate']==48000 and r['frames']==FRAMES and r['maximum_block_size']==c['block'] and r['host_sha256']==sha256(args.host) and all(r['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong original capture')
    require(json.loads((folder/'plan.json').read_text())==plan,'Original plan differs')
    for name,key in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==r[key],'Original artifact changed')
    source=args.session/(c['source']+'.wav');require(sha256(source)==sha256(Path(r['input_path']))==r['input_sha256'],'Original source changed')
    rate,x=float_wav(source);require(rate==48000 and np.array_equal(x,waves(args.stage)[c['source']]),'Source samples differ')
    for b in r['plugin']['binary_files']:require(sha256(Path(r['plugin']['bundle'])/b['path'])==b['sha256'],'Original binary changed')
    requests=[p|dict(frame=-1) for p in plan['parameters']]+plan['events'];log=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(log)==len(requests),'Control log differs');final={}
    for req,actual in zip(requests,log):
        expected=float(np.float32(req['value']));require(all(req[k]==actual[k] for k in ['name','id','index','frame']) and float(np.float32(actual['requested_value']))==expected and abs(actual['immediate_readback']-(float(np.float32(int(np.float32(req['value'])*np.float32(3))/3)) if req['name']=='ReleaseLever' else expected))<=1e-14,'Requested/readback control differs');final[req['name']]=float(np.float32(int(np.float32(req['value'])*np.float32(3))/3)) if req['name']=='ReleaseLever' else expected
    after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-14 for k,v in final.items()),'Final controls differ')
    stored=next(row for row in json.loads((args.session/'matrix.json').read_text())['cases'] if row['name']==c['name']);require(stored==c|dict(receipt_sha256=sha256(folder/'receipt.json')),'Matrix differs')
    rate,a=float_wav(folder/'audio.wav');require(rate==48000 and a.shape==(FRAMES,2),'Original extent differs')
    return a,dict(case=c['name'],receipt_sha256=sha256(folder/'receipt.json'),output_sha256=r['output_sha256'],input_sha256=r['input_sha256'],plan_sha256=r['plan_sha256'])


def compare(args):
    if args.stage!='discovery' and not args.regression:frozen(args)
    binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    for c in recipe(args.stage):
        a,provenance=original(args,c);path=root/(c['name']+'.tsv');path.write_text(schedule(c));out=root/(c['name']+'.wav');run([args.renderer,args.session/(c['source']+'.wav'),out,path]);rate,b=float_wav(out);require(rate==48000 and a.shape==b.shape,'Candidate extent differs');a,b=a[32:],b[32:];whole=screen(a,b);intervals=([('pre-control',256,96000),('active',96079,240173),('return',240173,FRAMES-32)] if args.stage=='discovery' else [('segment',e['frame'],c['changes'][i+1]['frame'] if i+1<len(c['changes']) else FRAMES-32) for i,e in enumerate(c['changes'])])
        if args.stage!='discovery' and c['changes'] and c['changes'][0]['frame']>256:intervals.insert(0,('pre-control',256,c['changes'][0]['frame']))
        for e in c['changes']:intervals += [('edge',e['frame'],min(FRAMES-32,e['frame']+2048))]
        windows=[dict(kind=k,start=s,stop=t,score=screen(a[s:t],b[s:t])) for k,s,t in intervals];passed=whole['passed'] and all(w['score']['passed'] for w in windows);rows.append(provenance|dict(passed=passed,whole=whole,windows=windows,candidate_sha256=sha256(out),schedule_sha256=sha256(path)));print('PASS' if passed else 'FAIL',c['name'],flush=True)
    if args.stage!='discovery' and not args.regression:
        prediction=json.loads(args.prediction.read_text());require(prediction['source_sha256']==binding and prediction['renderer_sha256']==binary and prediction['cases']==recipe(args.stage),'Frozen prediction differs');require(all(row['candidate_sha256']==prediction['outputs_sha256'][row['case']] for row in rows),'Predicted output differs')
    require(binding==source_hashes() and binary==sha256(args.renderer),'Candidate changed');save_json(root/'comparison.json',dict(kind='rmx220-release-'+args.stage+'-comparison',stage=args.stage,role='development_regression' if args.regression or args.stage=='discovery' else 'frozen_fresh_prediction',prediction_sha256=sha256(args.prediction) if args.stage!='discovery' else None,passed=all(r['passed'] for r in rows),cases=rows,source_sha256=binding,renderer_sha256=binary,acceptance=ACCEPTANCE,scope='Original default48k/120BPM, three Release types; fixed32/32, unchanged1% per-channel whole/segment/edge gates. No fit, wrapper, other profile/rate/tempo or hardware qualification.'));return 0 if all(r['passed'] for r in rows) else 1


def predict(args):
    require(args.stage!='discovery','Predictions are fresh only')
    root=new_directory(args.output);binding=source_hashes();binary=sha256(args.renderer);outputs={};inputs={}
    for name,x in waves(args.stage).items():
        path=root/(name+'.wav');write_wav(path,48000,x.ravel());inputs[name]=sha256(path)
    for c in recipe(args.stage):
        path=root/(c['name']+'.tsv');path.write_text(schedule(c));out=root/(c['name']+'.wav');run([args.renderer,root/(c['source']+'.wav'),out,path]);outputs[c['name']]=sha256(out)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Prediction source changed')
    save_json(root/'prediction.json',dict(kind='rmx220-release-frozen-fresh-prediction',created_utc=datetime.now(timezone.utc).isoformat(),cases=recipe(args.stage),source_sha256=binding,renderer_sha256=binary,inputs_sha256=inputs,outputs_sha256=outputs,acceptance=ACCEPTANCE))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ['capture','compare','predict']:
        q=s.add_parser(name);q.add_argument('--stage',choices=['discovery','fresh','fresh-v2'],default='discovery')
        if name!='predict':
            for key in ['session','host']:q.add_argument('--'+key,type=Path,required=True)
        if name=='capture':
            q.add_argument('--plugin',type=Path,required=True);q.add_argument('--renderer',type=Path)
        else:
            for key in ['renderer','output']:q.add_argument('--'+key,type=Path,required=True)
        if name!='predict':q.add_argument('--prediction',type=Path)
        if name=='compare':q.add_argument('--regression',action='store_true')
    a=p.parse_args();raise SystemExit(globals()[a.command](a))


if __name__=='__main__':main()
