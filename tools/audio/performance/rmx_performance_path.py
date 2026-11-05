#!/usr/bin/env python3
"""Bounded drum/Scene/Isolator/Release interaction checks against Original2.2.0."""
import argparse,json,tempfile,subprocess
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from tools.audio.drums import rmx_drum_combos as combo
from tools.audio.drums import rmx_drum_gestures as gesture
from tools.audio.drums import rmx_drum_performance_audit as audit
from tools.audio.noise.rmx_noise_stream import RenderSpace
from tools.audio.drums.rmx_drums_fx import source_hashes
from tools.audio.common.rmx_factory_match import IDENTITY
from tools.audio.common.reference_audio import save_json,sha256,write_wav
from tools.audio.noise.noise_statistics import float_wav
from tools.audio.filters.rmx_filter_match import screen

FRAMES=480000
ISO=['IsolatorButton','CutAddButton','TransRollButton','GateDriveButton']
RELEASE=['BackSpinSwitch','EchoSwitch','VinylBrakeSwitc']
SCENE=combo.EFFECTS
RAW={'V':'SceneVolume','B':'Sub1Volume','C':'Sub2Volume','U':'IsoLowVolume','W':'IsoMidVolume','Y':'IsoHiVolume','e':'ReleaseLever'}


def bindings():
    return source_hashes()|{n:sha256(Path(n)) for n in ['tools/audio/performance/rmx_performance_path.py','tools/probes/performance_path_probe.cpp','tools/audio/drums/rmx_drum_combos.py','tools/audio/drums/rmx_drum_gestures.py','tools/audio/drums/rmx_drum_performance.py','tools/audio/drums/rmx_drum_performance_audit.py','tools/hosts/audio_plugin_render.cpp','tools/hosts/audio_plugin_host.h','tools/hosts/legacy_vst2_host.h']}


def recipe(stage):
    if stage not in ['discovery','fresh','fresh2','fresh3']:raise ValueError('Unknown stage')
    seed={'discovery':0x50415448,'fresh':0x50415449,'fresh2':0x5041544a,'fresh3':0x5041544b}[stage];rng=np.random.default_rng(seed);rows=[];effects=list(SCENE)
    for family in ['scene','isolate','release','switch','tempo','route']:
        for i,effect in enumerate(effects):
            if stage=='discovery' and i not in [0,4,8]:continue
            shift=int(rng.integers(11,1500)) if stage!='discovery' else 0
            events=[(1,'X',153)]
            for at,pads in [(48079,(0,3)),(77113,(1,)),(96113,(3,)),(128193,(2,)),(144217,(0,)),(192241,(0,1,2,3)),(240337,(1,3)),(288371,(0,2)),(360517,(0,3))]:combo.press(events,at+shift,*pads)
            if i%2:events += [(31,'O',1),(432701+shift,'O',0)]
            else:events += [(96173+shift,'T',1),(120191+shift,'F',1),(168191+shift,'T',0),(192273+shift,'X',204),(288419+shift,'F',0)]
            c=combo.make_case(family,i,events,main=[95,151,73,155,95,123,83,95,93][i],amount=97,cutoff=0 if effect in [0,5,6,7] else 131,effect=effect,enabled=1,level=107,pitch=128,block=[31,127,509,1021,4093,67][i%6])
            c.update(name=f'path-{stage}-{family}-{i:02d}',frames=FRAMES,isolate_mode=0,isolate_enabled=0,low=128,mid=128,high=128,release_type=i%3,source='silent',stage=stage)
            extra=[]
            if family=='scene':extra=[(173113,'V',181),(216173,'B',139),(264239,'V',73),(312373,'B',97),(384601,'V',117)]
            if family=='isolate':
                c.update(isolate_mode=i%3+1,isolate_enabled=1)
                extra=[(108157,'U',64),(144239,'W',191),(192301,'Y',43),(240337,'U',223),(288419,'W',128),(336491,'Y',211),(384601,'U',128)]
            if family=='release':extra=[(168191,'e',85),(192301,'e',170),(216373,'e',255),(288419,'e',0)]
            if family=='switch':extra=[(168191,'N',effects[(i+3)%9]),(288419,'N',effect),(336491,'E',0),(384601,'E',1)]
            if family=='tempo':
                c['automatic']=1
                c['changes'] += [dict(frame=f,type='Z',value=0,bpm=b,beat=beat,seconds=seconds,playing=True) for f,b,beat,seconds in [(0,120,0,0),(192000,137,8,4),(336000,91,14.85,7)]]
            if family=='route':
                c.update(route=i%3,source='external',isolate_enabled=1,isolate_mode=i%3+1)
                extra=[(144239,'S',(i+1)%3),(240337,'U',83),(288419,'S',(i+2)%3),(384601,'S',i%3)]
            c['changes'] += [dict(frame=f+shift,type=k,value=v) for f,k,v in extra]
            c['changes'].sort(key=lambda e:e['frame']);c['hits']=[e['frame'] for e in c['changes'] if e['type']=='H']
            if stage!='discovery':
                c['block']=[43,131,257,1021,4096,79][i%6]
                c['level']=[89,117,137][i%3];c['pitch']=[117,128,139][i%3]
            rows.append(c)
    return rows


def control_case(c):
    ignored=set('EVBCIJKUWYNSGe')
    return c|dict(name=c['name']+'-control',enabled=0,isolate_enabled=0,changes=[e for e in c['changes'] if e['type'] not in ignored])


def stimulus(c):
    if c['source']=='silent':return np.zeros((FRAMES,2),dtype='<f4')
    t=np.arange(FRAMES)/48000;seed={'discovery':0x50494e50,'fresh':0x50494e51,'fresh2':0x50494e52,'fresh3':0x50494e53}[c['stage']]
    x=np.random.default_rng(seed).normal(0,.003,(FRAMES,2));x+=np.column_stack((.006*np.sin(2*np.pi*(83*t+17*t*t)),.005*np.cos(2*np.pi*(1197*t+31*t*t))))
    x[144000:168000]=0;x[360000:]*=.25
    return x.astype('<f4')


def schedule(c):
    base=c|dict(changes=[e for e in c['changes'] if e['type'] in 'HRTXFLPQAOMDEVBCZ'])
    lines=gesture.schedule(base).splitlines();lines[0]='RMX_DRUM_PERFORMANCE 4'
    line=' '.join(map(str,[c['isolate_mode'],c['route'],c['isolate_enabled'],c['low'],c['mid'],c['high'],c['release_type']]))
    events=[]
    for e in c['changes']:
        if e['type']=='Z':events.append(f"{e['frame']} Z {e['bpm']} {e['beat']} {e['seconds']} {int(e['playing'])}")
        else:events.append(f"{e['frame']} {e['type']} {e['value']}")
    return '\n'.join(lines[:5]+[line]+events)+'\n'


def plan_for(c,inventory):
    special=set('IJKUWYNSGe')
    base=c|dict(family='fx',changes=[e for e in c['changes'] if e['type'] not in special])
    plan=gesture.original_plan(base,inventory,Path('.'))
    def setting(name,value):
        p=next(p for p in inventory['parameters'] if p['name']==name)
        return {k:p[k] for k in ['name','id','index']}|dict(value=value)
    values={name:0 for name in ISO+RELEASE};values[ISO[c['isolate_mode']]]=c['isolate_enabled'];values[RELEASE[c['release_type']]]=1
    values.update(IsoLowVolume=c['low']/255,IsoMidVolume=c['mid']/255,IsoHiVolume=c['high']/255)
    values.update({SCENE[c['effect']]:c['enabled']})
    plan['parameters']=[p|dict(value=values.pop(p['name'])) if p['name'] in values else p for p in plan['parameters']]
    plan['parameters'] += [setting(n,v) for n,v in values.items()]
    for e in c['changes']:
        k=e['type'];v=e['value'];pairs=[]
        if k in RAW and k in special:pairs=[(RAW[k],v/255)]
        elif k=='I':pairs=[(ISO[c['isolate_mode']],v)]
        elif k=='J':pairs=[(ISO[v],1)]
        elif k=='N':pairs=[(SCENE[v],1)]
        elif k=='G':pairs=[(RELEASE[v],1)]
        elif k in ['K','S']:pairs=[('InputButton',int(v in [0,2])),('XpadButton',int(v in [1,2]))]
        plan['events'] += [setting(n,x)|dict(frame=e['frame'],type='parameter') for n,x in pairs]
    plan['events'].sort(key=lambda e:e['frame']);return plan


def verify(root,c,plan,host,plugin):
    folder=root/'original';receipt=json.loads((folder/'receipt.json').read_text())
    if not receipt['complete'] or receipt['role']!='reference' or receipt['host_sha256']!=sha256(host) or any(receipt['plugin'][k]!=v for k,v in IDENTITY.items()):raise ValueError('Wrong/incomplete Original')
    if receipt['sample_rate']!=48000 or receipt['frames']!=FRAMES or receipt['maximum_block_size']!=c['block'] or json.loads((folder/'plan.json').read_text())!=plan:raise ValueError('Original plan/extent differs')
    for name,key in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        if sha256(folder/name)!=receipt[key]:raise ValueError('Original auxiliary changed')
    if receipt['input_sha256']!=sha256(root/'input.wav'):raise ValueError('Input changed')
    for member in receipt['plugin']['binary_files']:
        if sha256(plugin/member['path'])!=member['sha256']:raise ValueError('Original binary changed')
    requests=[p|dict(frame=-1) for p in plan['parameters']]+[e for e in plan['events'] if e['type']=='parameter'];log=json.loads((folder/'parameter-log.json').read_text())['entries']
    if len(requests)!=len(log):raise ValueError('Parameter extent differs')
    for req,actual in zip(requests,log,strict=True):
        expected=np.float32(req['value'])
        if req['name']=='ReleaseLever':expected=np.float32(int(expected*np.float32(3))/3)
        if any(req[k]!=actual[k] for k in ['frame','name','id','index']) or np.float32(actual['requested_value'])!=np.float32(req['value']) or abs(actual['immediate_readback']-float(expected))>1e-14:raise ValueError('Immediate readback differs: '+str((req,actual)))
    transport=[e for e in plan['events'] if e['type']=='transport']
    if transport:
        if not receipt.get('explicit_transport') or sha256(folder/'transport-log.json')!=receipt['transport_log_sha256'] or json.loads((folder/'transport-log.json').read_text())!=dict(kind='explicit-transport-event-log',entries=transport):raise ValueError('Transport delivery differs')
    return receipt


def windows(c):
    length=FRAMES-32
    return [(0,length,'complete')]+[(f,min(f+48000,length),'second') for f in range(0,length,48000)]+[(max(0,e['frame']-64),min(length,e['frame']+2048),'event') for e in c['changes'] if e['frame']<length]


def scores(x,y,ws):
    rows=[]
    for start,stop,kind in ws:
        a=x[start:stop].astype(float);b=y[start:stop].astype(float);s=screen(a,b);ind=audit.independent(a,b)
        if s['passed']!=ind['passed']:raise ValueError('Independent gate differs')
        for v,w in zip(s['channels'],ind['channels'],strict=True):
            for k in ['relative_rms_error','absolute_error_rms']:
                if v[k] is not None and not np.isclose(v[k],w[k],rtol=1e-12,atol=1e-10):raise ValueError('Independent score differs')
        n=len(a);energy=np.einsum('ij,ij->j',a,a);error=np.einsum('ij,ij->j',b-a,b-a)
        rows.append(dict(start=start,stop=stop,kind=kind,score=s,reference_energy=energy.tolist(),error_energy=error.tolist(),samples=n))
    return rows


def validate(a):
    if a.output.exists():raise ValueError('Choose new report')
    cases=recipe(a.stage)
    if a.family:cases=[c for c in cases if c['family'] in a.family]
    if a.case:cases=[c for c in cases if c['name'] in a.case]
    if not cases:raise ValueError('No cases selected')
    bound=bindings();binary={k:sha256(getattr(a,k)) for k in ['renderer','sanitizer','host']};rows=[];peak=0
    inventory=json.loads(subprocess.check_output([a.host,'inventory',a.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):raise ValueError('Wrong Original')
    for active in cases:
        with tempfile.TemporaryDirectory(prefix='rmx-performance-path-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);write_wav(root/'input.wav',48000,stimulus(active).reshape(-1));data={};case_rows=[]
            for role,c in [('control',control_case(active)),('active',active)]:
                program=root/'program.tsv';program.write_text(schedule(c));out=root/'native.wav';dry=root/'dry.wav'
                space.run([a.renderer,root/'input.wav',out,program,dry]);digest=sha256(out);dry_digest=sha256(dry);rate,y=float_wav(out);out.unlink();dry.unlink();frozen=datetime.now(timezone.utc).isoformat()
                space.run([a.sanitizer,root/'input.wav',out,program,dry],sanitized=True)
                if sha256(out)!=digest or sha256(dry)!=dry_digest:raise ValueError('ASAN differs')
                out.unlink();dry.unlink();plan=plan_for(c,inventory);save_json(root/'plan.json',plan);space.run([a.host,'render',a.plugin,root/'input.wav',root/'plan.json',root/'original',c['block']]);receipt=verify(root,c,plan,a.host,a.plugin)
                if datetime.fromisoformat(frozen)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Prediction followed Original')
                rate,x=float_wav(root/'original/audio.wav')
                if x.shape!=y.shape or x.shape!=(FRAMES,2) or rate!=48000:raise ValueError('Audio extent differs')
                x=x[32:];y=y[32:];data[role]=(x,y);ws=scores(x,y,windows(c));passed=all(w['score']['passed'] for w in ws)
                negatives={name:audit.independent(x,z)['passed'] for name,z in [('gain6db',x*.5),('silence',np.zeros_like(x)),('shift1',np.roll(x,1,axis=0))]}
                if any(negatives.values()):raise ValueError('Whole-output negative passed')
                case_rows.append(dict(case=c,role=role,passed=passed,windows=ws,original_wav_sha256=receipt['output_sha256'],original_receipt_sha256=sha256(root/'original/receipt.json'),plan=plan,prediction_created_utc=frozen,prediction_sha256=digest,schedule_sha256=sha256(program),complete_native_sanitizer_wav_identity=True,complete_sample_bit_identity=bool(np.array_equal(x.view(np.uint32),y.view(np.uint32))),negative_controls_rejected=True))
                import shutil
                shutil.rmtree(root/'original');(root/'plan.json').unlink()
            x,y=data['active'];rx,ry=data['control'];wet=scores(x.astype(float)-rx,y.astype(float)-ry,windows(active));case_rows[1]['effect_difference_windows']=wet;case_rows[1]['whole_output_passed']=case_rows[1]['passed'];case_rows[1]['passed'] &= all(w['score']['passed'] for w in wet) and case_rows[0]['passed'];rows+=case_rows;peak=max(peak,space.peak)
            print('PATH',active['name'],'control',case_rows[0]['passed'],'active',case_rows[1]['passed'],'whole',case_rows[1]['whole_output_passed'],'worst',max(v['relative_rms_error'] or 0 for w in case_rows[1]['windows'] for v in w['score']['channels']),flush=True)
        if root.exists():raise ValueError('Audio retained')
        a.output.with_suffix('.partial.json').write_text(json.dumps(dict(complete=False,cases=rows),separators=(',',':'))+'\n')
    if bound!=bindings() or any(sha256(getattr(a,k))!=v for k,v in binary.items()):raise ValueError('Inputs changed during campaign')
    save_json(a.output,dict(kind='bounded-full-performance-path-reference-checks',verification_passed=True,passed=all(c['passed'] for c in rows),stage=a.stage,cases=rows,source_sha256=bound,binary_sha256=binary,peak_temporary_bytes=peak,raw_audio_retained=False,all_temporary_directories_removed=True,scope='Declared Default48k programs, fixed32/32 offsets, no fitted gain/alignment. Whole/second/event and active-minus-matched-control windows require1%perchannel or1e-8 absolute for silence. Independent numerical audit and negatives checked before raw cleanup. Synthetic external input, not arbitrary music or physical hardware. Failures retained.'))
    a.output.with_suffix('.partial.json').unlink()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['renderer','sanitizer','host','plugin','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--stage',choices=['discovery','fresh','fresh2','fresh3'],default='discovery');p.add_argument('--family',action='append');p.add_argument('--case',action='append');a=p.parse_args();validate(a)


if __name__=='__main__':main()
