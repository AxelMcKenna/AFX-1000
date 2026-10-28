#!/usr/bin/env python3
"""Capture and compare original Release effects with fixed latency and raw gates."""
import argparse
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


def waves():
    t=np.arange(FRAMES)/48000
    tone=np.column_stack((.12*np.sin(2*np.pi*997*t),.08*np.cos(2*np.pi*1283*t)))
    chirp=np.column_stack((.09*np.sin(2*np.pi*(97*t+83*t*t)),.07*np.cos(2*np.pi*(187*t+131*t*t))))
    program=np.random.default_rng(0x72656c30).normal(0,.025,(FRAMES,2))+np.column_stack((.05*np.sin(2*np.pi*79*t),.04*np.sin(2*np.pi*1141*t)))
    pulses=np.zeros_like(tone);at=[9600,48061,95993,96097,120239,144301,168359,192421,216487,239999,240241,264301,288373,312437]
    pulses[at]=np.random.default_rng(0x72656c31).uniform(-.2,.2,(len(at),2))
    return {k:v.astype('<f4') for k,v in dict(tone=tone,chirp=chirp,program=program,pulses=pulses).items()}


def recipe():
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


def capture(args):
    binding=source_hashes();root=new_directory(args.session);inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original');save_json(root/'inventory.json',inventory)
    for name,x in waves().items():write_wav(root/(name+'.wav'),48000,x.ravel())
    rows=[]
    for c in recipe():
        path=root/(c['name']+'.json');save_json(path,plan_for(c,inventory));run([args.host,'render',args.plugin,root/(c['source']+'.wav'),path,root/c['name'],c['block']]);rows.append(c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json')));print('CAPTURED',c['name'],flush=True)
    require(binding==source_hashes(),'Capture source changed');save_json(root/'matrix.json',dict(kind='rmx220-release-discovery',cases=rows,source_sha256=binding));return 0


def original(args,c):
    folder=args.session/c['name'];r=json.loads((folder/'receipt.json').read_text());inventory=json.loads((args.session/'inventory.json').read_text());plan=plan_for(c,inventory)
    require(r['complete'] and r['role']=='reference' and r['sample_rate']==48000 and r['frames']==FRAMES and r['maximum_block_size']==c['block'] and r['host_sha256']==sha256(args.host) and all(r['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong original capture')
    require(json.loads((folder/'plan.json').read_text())==plan,'Original plan differs')
    for name,key in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==r[key],'Original artifact changed')
    source=args.session/(c['source']+'.wav');require(sha256(source)==sha256(Path(r['input_path']))==r['input_sha256'],'Original source changed')
    rate,x=float_wav(source);require(rate==48000 and np.array_equal(x,waves()[c['source']]),'Source samples differ')
    for b in r['plugin']['binary_files']:require(sha256(Path(r['plugin']['bundle'])/b['path'])==b['sha256'],'Original binary changed')
    requests=[p|dict(frame=-1) for p in plan['parameters']]+plan['events'];log=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(log)==len(requests),'Control log differs');final={}
    for req,actual in zip(requests,log):
        expected=float(np.float32(req['value']));require(all(req[k]==actual[k] for k in ['name','id','index','frame']) and float(np.float32(actual['requested_value']))==expected and abs(actual['immediate_readback']-expected)<=1e-14,'Requested/readback control differs');final[req['name']]=expected
    after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-14 for k,v in final.items()),'Final controls differ')
    stored=next(row for row in json.loads((args.session/'matrix.json').read_text())['cases'] if row['name']==c['name']);require(stored==c|dict(receipt_sha256=sha256(folder/'receipt.json')),'Matrix differs')
    rate,a=float_wav(folder/'audio.wav');require(rate==48000 and a.shape==(FRAMES,2),'Original extent differs')
    return a,dict(case=c['name'],receipt_sha256=sha256(folder/'receipt.json'),output_sha256=r['output_sha256'],input_sha256=r['input_sha256'],plan_sha256=r['plan_sha256'])


def compare(args):
    binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    for c in recipe():
        a,provenance=original(args,c);path=root/(c['name']+'.tsv');path.write_text(schedule(c));out=root/(c['name']+'.wav');run([args.renderer,args.session/(c['source']+'.wav'),out,path]);rate,b=float_wav(out);require(rate==48000 and a.shape==b.shape,'Candidate extent differs');a,b=a[32:],b[32:];whole=screen(a,b);intervals=[('pre-control',256,96000),('active',96079,240173),('return',240173,FRAMES-32)]
        for e in c['changes']:intervals += [('edge',e['frame'],e['frame']+2048)]
        windows=[dict(kind=k,start=s,stop=t,score=screen(a[s:t],b[s:t])) for k,s,t in intervals];passed=whole['passed'] and all(w['score']['passed'] for w in windows);rows.append(provenance|dict(passed=passed,whole=whole,windows=windows,candidate_sha256=sha256(out),schedule_sha256=sha256(path)));print('PASS' if passed else 'FAIL',c['name'],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Candidate changed');save_json(root/'comparison.json',dict(kind='rmx220-release-development-comparison',passed=all(r['passed'] for r in rows),cases=rows,source_sha256=binding,renderer_sha256=binary,acceptance=ACCEPTANCE,scope='Discovery only: original default48k/120BPM, three Release types/lever positions, fixed32/32, unchanged1% per-channel whole/active/edge/return gates. No fit, wrapper or hardware qualification.'));return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ['capture','compare']:
        q=s.add_parser(name)
        for key in ['session','host']:q.add_argument('--'+key,type=Path,required=True)
        if name=='capture':q.add_argument('--plugin',type=Path,required=True)
        else:
            for key in ['renderer','output']:q.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();raise SystemExit(globals()[a.command](a))


if __name__=='__main__':main()
