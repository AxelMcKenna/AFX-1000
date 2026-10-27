#!/usr/bin/env python3
"""Original-reference discovery for factory drums through deterministic Scene FX."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import DRUMS, parameters, require
from tools.rmx_drums_engine import original_plan
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen

EFFECTS={0:'BpfEchoButton',1:'EchoButton',4:'ReverbUpButton',5:'HpfEchoButton',6:'LpfEchoButton',7:'CrushEchoButton',9:'ReverbDownButto'}
ACCEPTANCE=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,
                reference_offset_frames=32,candidate_offset_frames=32,gain_fit=False,alignment_search=False)
FRAMES=28*48000


def source(stage='discovery'):
    if stage=='fresh-v4':
        t=np.arange(FRAMES)/48000;x=np.zeros((FRAMES,2))
        x[:288000]=np.random.default_rng(0x4452465C).normal(0,.0048,(288000,2))
        x[:288000]+=.0052*np.column_stack((np.sin(2*np.pi*(379*t[:288000]+53*t[:288000]**2)),np.cos(2*np.pi*2713*t[:288000])))
        x[151000:221000]=0;x[[0,11,31,101,197,433,911,1783]] += [-.011,.015]
        return x.astype('<f4')
    if stage=='fresh-v3':
        t=np.arange(FRAMES)/48000;x=np.zeros((FRAMES,2))
        x[:288000]=np.random.default_rng(0x4452465B).normal(0,.0045,(288000,2))
        x[:288000]+=.0055*np.column_stack((np.sin(2*np.pi*(293*t[:288000]+47*t[:288000]**2)),np.cos(2*np.pi*2531*t[:288000])))
        x[156000:228000]=0;x[[0,5,23,97,193,421,887,1723]] += [.012,-.014]
        return x.astype('<f4')
    if stage=='fresh-v2':
        t=np.arange(FRAMES)/48000;x=np.zeros((FRAMES,2))
        x[:288000]=np.random.default_rng(0x4452465A).normal(0,.005,(288000,2))
        x[:288000]+=.005*np.column_stack((np.sin(2*np.pi*(431*t[:288000]+37*t[:288000]**2)),np.cos(2*np.pi*1877*t[:288000])))
        x[168000:216000]=0;x[[0,3,17,79,163,347,769,1543]] += [-.013,.010]
        return x.astype('<f4')
    if stage=='fresh':
        t=np.arange(FRAMES)/48000;x=np.zeros((FRAMES,2))
        x[:288000]=np.random.default_rng(0x44524659).normal(0,.006,(288000,2))
        x[:288000]+=.004*np.column_stack((np.sin(2*np.pi*(317*t[:288000]+41*t[:288000]**2)),np.cos(2*np.pi*2179*t[:288000])))
        x[144000:192000]=0;x[[0,7,19,53,103,241,491,977]] += [.011,-.009]
        return x.astype('<f4')
    x=np.zeros((FRAMES,2));t=np.arange(264000)/48000
    x[24000:288000]=np.random.default_rng(0x44524658).normal(0,.004,(len(t),2))
    x[24000:288000]+=.006*np.column_stack((np.sin(2*np.pi*(173*t+23*t*t)),np.cos(2*np.pi*1327*t)))
    return x.astype('<f4')


def recipe(stage='discovery'):
    if stage=='fresh-v4':
        rows=[];specs=[(effect,route,None) for effect in EFFECTS if effect!=7 for route in (1,2)]
        specs += [(7,route,main) for main in (15,30,65,93) for route in range(4)]
        for i,(effect,route,main) in enumerate(specs):
            name=f'drum-fx-fresh4-{i}-effect{effect}-route{route}';baseline=name+'-dry';first=[5,13,17,31][i%4]
            events=[(first,pad) for pad in range(4)]+[(89,3),(137,1),(229,0),(317,2),(419,3),(631,1),(48127,1),(48127,2),(96203,0),(96203,3)]+[(240307,pad) for pad in range(4)]
            c=dict(name=name,drum='kick',pads=[pad for at,pad in events],hits=[at for at,pad in events],
                   level=[0,7,97,249][(i+route)%4],pitch=[7,83,153,247][(i*3+route)%4],
                   block=[17,41,61,107,277,541,1571,3137][(i+route*2)%8],effect=effect,enabled=1,route=route,
                   main=[23,59,137,229][i%4] if main is None else main,amount=[31,87,143,191][(i+route)%4],
                   cutoff=[23,109,183,239][i%4] if effect in (1,4,9) else 0,baseline=baseline)
            rows.extend([c|dict(name=baseline,effect=1,enabled=0),c])
        return rows
    if stage=='fresh-v3':
        rows=[];specs=[(effect,route,None) for effect in EFFECTS if effect!=7 for route in (1,2)]
        specs += [(7,route,main) for main in (31,47,63,101) for route in range(4)]
        for i,(effect,route,main) in enumerate(specs):
            name=f'drum-fx-fresh3-{i}-effect{effect}-route{route}';baseline=name+'-dry';first=[3,7,19,29][i%4]
            events=[(first,pad) for pad in range(4)]+[(83,0),(127,3),(211,2),(307,1),(401,0),(613,2),(48103,0),(48103,3),(96179,1),(96179,2)]+[(240271,pad) for pad in range(4)]
            c=dict(name=name,drum='kick',pads=[pad for at,pad in events],hits=[at for at,pad in events],
                   level=[0,5,101,251][(i+route)%4],pitch=[3,79,149,243][(i*3+route)%4],
                   block=[19,39,59,109,271,529,1567,3121][(i+route*2)%8],effect=effect,enabled=1,route=route,
                   main=[19,53,133,227][i%4] if main is None else main,amount=[29,83,141,189][(i+route)%4],
                   cutoff=[19,107,181,233][i%4] if effect in (1,4,9) else 0,baseline=baseline)
            rows.extend([c|dict(name=baseline,effect=1,enabled=0),c])
        return rows
    if stage=='fresh-v2':
        rows=[]
        for i,effect in enumerate(EFFECTS):
            for route in range(4):
                name=f'drum-fx-fresh2-effect{effect}-route{route}';baseline=name+'-dry';first=[2,5,11,23][(i+route)%4]
                events=[(first,pad) for pad in range(4)]+[(61,3),(101,2),(167,1),(223,0),(367,3),(509,1),(48089,0),(48089,1),(96161,2),(96161,3)]+[(240223,pad) for pad in range(4)]
                c=dict(name=name,drum='kick',pads=[pad for at,pad in events],hits=[at for at,pad in events],
                       level=[0,19,109,241][(i+route*3)%4],pitch=[11,87,169,239][(i*3+route)%4],
                       block=[13,27,49,113,269,523,1561,3109][(i*3+route*2)%8],effect=effect,enabled=1,route=route,
                       main=[0,7,63,219][(i+route)%4],amount=[37,101,149,177][(i+route*3)%4],
                       cutoff=[13,97,173,229][(i+route)%4] if effect in (1,4,9) else 0,baseline=baseline)
                rows.extend([c|dict(name=baseline,effect=1,enabled=0),c])
        return rows
    if stage=='fresh':
        rows=[]
        for i,effect in enumerate(EFFECTS):
            for route in range(4):
                name=f'drum-fx-fresh-effect{effect}-route{route}';baseline=name+'-dry'
                events=[(1,pad) for pad in range(4)]+[(69,0),(87,1),(141,2),(179,3),(48073,0),(48073,2),(96139,1),(96139,3)]+[(240173,pad) for pad in range(4)]
                c=dict(name=name,drum='kick',pads=[pad for at,pad in events],hits=[at for at,pad in events],
                       level=[0,71,183,255][(i+route)%4],pitch=[29,104,151,227][(i+route*3)%4],
                       block=[11,23,43,127,263,521,1549,3089][(i+route*2)%8],effect=effect,enabled=1,route=route,
                       main=[57,119,201,247][(i+route)%4],amount=[23,89,157,181][(i*3+route)%4],
                       cutoff=[3,81,149,237][(i+route)%4] if effect in (1,4,9) else 0,baseline=baseline)
                rows.extend([c|dict(name=baseline,effect=1,enabled=0),c])
        return rows
    rows=[]
    for pad,drum in enumerate(DRUMS):
        for route in range(4):
            baseline=f'drum-fx-{drum}-route{route}-dry'
            for effect in [None,*EFFECTS]:
                rows.append(dict(name=baseline if effect is None else f'drum-fx-{drum}-route{route}-effect{effect}',
                    drum=drum,pads=[pad]*3,hits=[48000,96037,192079],level=128,pitch=128,block=128,
                    effect=1 if effect is None else effect,enabled=int(effect is not None),route=route,
                    main=128,amount=64,cutoff=64 if effect in (1,4,9) else 0,baseline=baseline))
    return rows


def source_hashes():
    paths=[Path('tools/rmx_drums_fx.py'),Path('tools/drums_fx_probe.cpp'),Path('CMakeLists.txt'),Path('research/audio/experiments/SharedDrumFX.h')]
    paths += [Path('tools')/name for name in ('rmx_drums.py','rmx_drums_engine.py','rmx_factory_match.py','rmx_filter_match.py','reference_audio.py','noise_statistics.py')]
    paths += sorted(Path('include/rmx').rglob('*.h'))+sorted(Path('src/core').rglob('*.cpp'))
    return {str(p):sha256(p) for p in paths}


def plan_for(c,inventory):
    plan=original_plan(c,inventory);values=parameters(c)
    values.update(InputButton=int(c['route'] in (0,2)),XpadButton=int(c['route'] in (1,2)),
                  SceneVolume=c['main']/255,Sub1Volume=c['amount']/255,Sub2Volume=c['cutoff']/255)
    values[EFFECTS[c['effect']]]=c['enabled']
    def setting(name,value):
        matches=[p for p in inventory['parameters'] if p['name']==name];require(len(matches)==1,'Ambiguous parameter: '+name)
        return {k:matches[0][k] for k in ('index','id','name')}|dict(value=value)
    plan['parameters']=[setting(k,v) for k,v in values.items()]
    return plan


def schedule(c):
    return ('RMX_DRUM_FX 1\n'+' '.join(str(c[k]) for k in ('effect','route','main','amount','cutoff','enabled','level','pitch','block'))+'\n'
            +''.join(f'{at} {pad}\n' for at,pad in zip(c['hits'],c['pads'])))


def capture(args):
    if args.stage!='discovery':frozen(args)
    root=new_directory(args.session);binding=source_hashes();inventory=json.loads(run([args.host,'inventory',args.plugin]))
    require(all(inventory[k]==v for k,v in IDENTITY.items()),'Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json',inventory);write_wav(root/'program.wav',48000,source(args.stage).ravel());rows=[]
    if args.stage!='discovery':(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    for c in recipe(args.stage):
        path=root/(c['name']+'.json');save_json(path,plan_for(c,inventory))
        run([args.host,'render',args.plugin,root/'program.wav',path,root/c['name'],c['block']])
        rows.append(c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json')));print('Captured',c['name'],flush=True)
    require(binding==source_hashes(),'Capture sources changed')
    if args.stage!='discovery':frozen(args)
    save_json(root/'matrix.json',dict(kind='rmx220-drums-fx-captures',stage=args.stage,cases=rows,source_sha256=binding,
              prediction_sha256=sha256(args.prediction) if args.stage!='discovery' else None,
              scope='Factory drums and seven deterministic Scene effects, four source routes,48k/120BPM. Discovery128; fresh56 (28 FX-on plus28 independent FX-off baselines).'))
    return 0


def checked(args,c):
    inventory=json.loads((args.session/'inventory.json').read_text());folder=args.session/c['name'];receipt=json.loads((folder/'receipt.json').read_text());plan=plan_for(c,inventory)
    require(receipt['complete'] and receipt['role']=='reference' and all(receipt['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong original')
    require(receipt['host_sha256']==sha256(args.host) and receipt['maximum_block_size']==c['block'] and receipt['sample_rate']==48000
            and receipt['frames']==FRAMES and receipt['reported_latency_frames']==0,'Original host/timing differs')
    require(json.loads((folder/'plan.json').read_text())==plan and sha256(args.session/(c['name']+'.json'))==receipt['plan_sha256'],'Original recipe differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(folder/name)==receipt[field],'Modified original artifact')
    require(sha256(args.session/'program.wav')==sha256(Path(receipt['input_path']))==receipt['input_sha256'],'Original input differs')
    for binary in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/binary['path'])==binary['sha256'],'Original binary differs')
    log=json.loads((folder/'parameter-log.json').read_text())['entries'];requests=[p|dict(frame=-1) for p in plan['parameters']]+plan['events']
    require(len(log)==len(requests),'Original parameter log length differs');final={}
    for req,actual in zip(requests,log):
        value=float(np.float32(req['value']))
        require(all(req[k]==actual[k] for k in ('frame','name','index','id')) and float(np.float32(actual['requested_value']))==value
                and abs(actual['immediate_readback']-value)<=1e-14,'Original parameter readback differs: '+req['name'])
        final[req['name']]=value
    after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
    require(all(abs(after[k]-v)<=1e-14 for k,v in final.items()),'Original final controls differ')
    manifest=json.loads((args.session/'matrix.json').read_text());stored=next(r for r in manifest['cases'] if r['name']==c['name'])
    require(stored==c|dict(receipt_sha256=sha256(folder/'receipt.json')),'Original matrix differs')
    rate,a=float_wav(folder/'audio.wav');source_rate,x=float_wav(args.session/'program.wav')
    require(rate==source_rate==48000 and a.shape==x.shape==(FRAMES,2) and np.array_equal(x,source(args.stage)),'Original waveform extent/input differs')
    return a,dict(case=c['name'],receipt_sha256=sha256(folder/'receipt.json'),output_sha256=receipt['output_sha256'],input_sha256=receipt['input_sha256'],plan_sha256=receipt['plan_sha256'])


def compare(args):
    if args.stage!='discovery':
        if args.regression:
            old=json.loads(args.prediction.read_text());expected=payload(args)
            require(all(old[k]==expected[k] for k in ('kind','cases','source_samples_sha256','acceptance')),'Former capture recipe/gates differ')
        else:frozen(args)
        manifest=json.loads((args.session/'matrix.json').read_text())
        require(manifest['prediction_sha256']==sha256(args.prediction)==sha256(args.session/'predictions.json'),'Fresh prediction copy differs')
    root=new_directory(args.output);binding=source_hashes();binary=sha256(args.renderer);rows=[];baselines={}
    for c in recipe(args.stage):
        original,provenance=checked(args,c);path=root/(c['name']+'.tsv');save=root/(c['name']+'.wav');path.write_text(schedule(c))
        run([args.renderer,args.session/'program.wav',save,path]);rate,candidate=float_wav(save)
        require(rate==48000 and candidate.shape==original.shape,'Candidate extent/rate differs');a=original[32:].astype(float);b=candidate[32:].astype(float)
        if not c['enabled']:baselines[c['baseline']]=(a,b)
        da,db=baselines[c['baseline']];wa,wb=a-da,b-db
        row=provenance|dict(effect=c['effect'],route=c['route'],enabled=c['enabled'],candidate_sha256=sha256(save),schedule_sha256=sha256(path),
                           whole=screen(a,b),wet=screen(wa,wb),tail=screen(a[288000:],b[288000:]),windows=[])
        for at in [24000 if args.stage=='discovery' else 0,*c['hits']]:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                row['windows'].append(dict(frame=at,kind=kind,start=left,stop=right,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
        row['passed']=all(row[k]['passed'] for k in ('whole','wet','tail')) and all(w[k]['passed'] for w in row['windows'] for k in ('whole','wet'))
        rows.append(row);print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Candidate changed')
    if args.stage!='discovery' and not args.regression:frozen(args)
    save_json(root/'comparison.json',dict(kind='rmx220-drums-fx-discovery-comparison',passed=all(r['passed'] for r in rows),cases=rows,
        stage=args.stage,role=('former_prediction_regression' if args.regression else 'fresh_prediction_bound') if args.stage!='discovery' else 'development_regression',prediction_sha256=sha256(args.prediction) if args.stage!='discovery' else None,
        acceptance=ACCEPTANCE,source_sha256=binding,renderer_sha256=binary,backend=args.backend,live_engine=args.backend=='engine',full_drum_match=False,physical_hardware=False,
        scope='Mixed stereo input and four factory drums, seven deterministic Scene effects, static controls at48k/120BPM. Discovery and first two fresh campaigns cover all four source routes per effect; fresh-v3/v4 focus16 Crush cases across four routes and12 other-effect cases on X-Pad/both routes. Whole/wet/tail and attack/body/decay screens; wet subtracts the independently captured FX-off baseline. Discovery128; fresh campaigns56 each (28 FX-on plus28 independent FX-off baselines). Fixed32/32; no gain/alignment fit or broad FX accuracy claim.'))
    return 0 if all(r['passed'] for r in rows) else 1


def payload(args):
    stage=getattr(args,'stage','fresh')
    return dict(kind='rmx220-drums-fx-shared-prediction',cases=recipe(stage),source_sha256=source_hashes(),renderer_sha256=sha256(args.renderer),
                source_samples_sha256=hashlib.sha256(source(stage).tobytes()).hexdigest(),acceptance=ACCEPTANCE,
                expected='All56 fresh programs pass every per-channel1% whole/wet/tail and attack/body/decay screen. Fixed32/32; no gain or alignment fit.',
                scope='Shared-clock research adapter, not live Engine. Seven deterministic Scene effects, factory48k/default profiles, static controls. Fresh-v3/v4 focus16 Crush cases across four routes and12 other-effect cases on X-Pad/both routes; earlier fresh campaigns use four routes per effect. New raw level/pitch, irregular callbacks, cold input and simultaneous/staggered drums. No automation, custom profiles/rates, Isolator/Release, DAW or physical hardware qualification.')


def predict(args):
    require(args.stage!='discovery','Only fresh campaigns accept predictions');save_json(args.report,payload(args));return 0


def frozen(args):
    require(args.prediction is not None and json.loads(args.prediction.read_text())==payload(args),'Frozen shared-clock drum/FX prediction differs')


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('capture','compare','predict'):
        p=commands.add_parser(name);p.add_argument('--stage',choices=['discovery','fresh','fresh-v2','fresh-v3','fresh-v4'],default='discovery')
        keys=['renderer','report'] if name=='predict' else ['host','session',*(['plugin'] if name=='capture' else ['renderer','output'])]
        for key in keys:p.add_argument('--'+key,type=Path,required=True)
        if name!='predict':p.add_argument('--prediction',type=Path)
        if name=='capture':p.add_argument('--renderer',type=Path)
        if name=='compare':p.add_argument('--backend',choices=['engine','shared'],default='engine')
        if name=='compare':p.add_argument('--regression',action='store_true',help='Treat a formerly frozen fresh campaign as regression data; preserve its recipe/gates, not its old candidate identity.')
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
