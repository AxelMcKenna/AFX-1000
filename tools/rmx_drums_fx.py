#!/usr/bin/env python3
"""Original-reference discovery for factory drums through deterministic Scene FX."""
import argparse
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


def source():
    x=np.zeros((FRAMES,2));t=np.arange(264000)/48000
    x[24000:288000]=np.random.default_rng(0x44524658).normal(0,.004,(len(t),2))
    x[24000:288000]+=.006*np.column_stack((np.sin(2*np.pi*(173*t+23*t*t)),np.cos(2*np.pi*1327*t)))
    return x.astype('<f4')


def recipe():
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
    paths=[Path('tools/rmx_drums_fx.py'),Path('tools/drums_fx_probe.cpp'),Path('CMakeLists.txt')]
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
    root=new_directory(args.session);binding=source_hashes();inventory=json.loads(run([args.host,'inventory',args.plugin]))
    require(all(inventory[k]==v for k,v in IDENTITY.items()),'Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json',inventory);write_wav(root/'program.wav',48000,source().ravel());rows=[]
    for c in recipe():
        path=root/(c['name']+'.json');save_json(path,plan_for(c,inventory))
        run([args.host,'render',args.plugin,root/'program.wav',path,root/c['name'],c['block']])
        rows.append(c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json')));print('Captured',c['name'],flush=True)
    require(binding==source_hashes(),'Capture sources changed')
    save_json(root/'matrix.json',dict(kind='rmx220-drums-fx-discovery',cases=rows,source_sha256=binding,
              scope='Discovery:128 original programs, seven deterministic Scene effects, four source routes, factory drums at48k/120BPM. No candidate prediction or accuracy claim.'))
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
    require(rate==source_rate==48000 and a.shape==x.shape==(FRAMES,2) and np.array_equal(x,source()),'Original waveform extent/input differs')
    return a,dict(case=c['name'],receipt_sha256=sha256(folder/'receipt.json'),output_sha256=receipt['output_sha256'],input_sha256=receipt['input_sha256'],plan_sha256=receipt['plan_sha256'])


def compare(args):
    root=new_directory(args.output);binding=source_hashes();binary=sha256(args.renderer);rows=[];baselines={}
    for c in recipe():
        original,provenance=checked(args,c);path=root/(c['name']+'.tsv');save=root/(c['name']+'.wav');path.write_text(schedule(c))
        run([args.renderer,args.session/'program.wav',save,path]);rate,candidate=float_wav(save)
        require(rate==48000 and candidate.shape==original.shape,'Candidate extent/rate differs');a=original[32:].astype(float);b=candidate[32:].astype(float)
        if not c['enabled']:baselines[c['baseline']]=(a,b)
        da,db=baselines[c['baseline']];wa,wb=a-da,b-db
        row=provenance|dict(effect=c['effect'],route=c['route'],enabled=c['enabled'],candidate_sha256=sha256(save),schedule_sha256=sha256(path),
                           whole=screen(a,b),wet=screen(wa,wb),tail=screen(a[288000:],b[288000:]),windows=[])
        for at in [24000,*c['hits']]:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                row['windows'].append(dict(frame=at,kind=kind,start=left,stop=right,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
        row['passed']=all(row[k]['passed'] for k in ('whole','wet','tail')) and all(w[k]['passed'] for w in row['windows'] for k in ('whole','wet'))
        rows.append(row);print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Candidate changed')
    save_json(root/'comparison.json',dict(kind='rmx220-drums-fx-discovery-comparison',passed=all(r['passed'] for r in rows),cases=rows,
        acceptance=ACCEPTANCE,source_sha256=binding,renderer_sha256=binary,full_drum_match=False,physical_hardware=False,
        scope='128 discovery regressions: mixed stereo input and four factory drums, seven deterministic Scene effects, all four source routes, static controls at48k/120BPM. Whole/wet/tail and attack/body/decay screens; wet subtracts the matching independently captured FX-off baseline. No gain/alignment fit, no fresh prediction or broad FX accuracy claim.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('capture','compare'):
        p=commands.add_parser(name)
        for key in ('host','session',*(['plugin'] if name=='capture' else ['renderer','output'])):p.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
