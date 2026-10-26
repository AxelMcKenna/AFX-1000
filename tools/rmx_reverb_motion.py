#!/usr/bin/env python3
"""Capture Reverb Down state changes; timing diagnostics are not full fidelity."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import controls
from tools.rmx_spiral_core import calibration

STAGES = ('button', 'steps', 'ramps', 'blocks')
CAPTURE_STAGES = (*STAGES,'cutoff-holdout','state-probes')
NAMES = {'main':'SceneVolume','amount':'Sub1Volume','cutoff':'Sub2Volume','enabled':'ReverbDownButto'}


def recipe(stage):
    rng = np.random.default_rng(0x2C170)
    t = np.arange(288000)/48000
    continuous = np.zeros((384000,2))
    continuous[48000:336000] = rng.normal(0,.022,(288000,2))
    continuous[48000:336000] += .018*np.column_stack((np.sin(2*np.pi*233*t)+np.sin(2*np.pi*1000*t),
                                                    np.sin(2*np.pi*711*t)+np.cos(2*np.pi*2651*t)))
    burst = continuous.copy()
    burst[144000:240000] = 0
    tones = np.zeros_like(continuous)
    tones[48000:336000] = .025*np.column_stack((np.sin(2*np.pi*233*t)+np.sin(2*np.pi*1000*t),
                                              np.sin(2*np.pi*711*t)+np.cos(2*np.pi*2651*t)))
    pulses = np.zeros_like(continuous)
    pulses[48000,0],pulses[144000,1],pulses[300000,0] = .02,-.017,.013
    waves = dict(continuous=continuous,burst=burst,tones=tones,pulses=pulses)
    cases = []
    event_frame = 192037

    def add(name,source='burst',main=128,amount=128,cutoff=0,enabled=1,events=None,block=128,tail=None,baseline=None):
        events = events or []
        high = max([amount]+[e['value'] for e in events if e['control']=='amount'])
        cases.append(dict(name='down-'+name,source=source,direction='down',main=main,amount=amount,cutoff=cutoff,
            enabled=enabled,events=events,block=block,tail=tail if tail is not None else (90 if high>=224 else 18),baseline=baseline))

    if stage == 'button':
        for main in (128,255):
            for source in ('burst','continuous'):
                base=f'down-baseline-{source}-{main}'
                add(f'baseline-{source}-{main}',source,main)
                add(f'off-on-{source}-{main}',source,main,events=[dict(frame=event_frame,control='enabled',value=0),
                    dict(frame=288073,control='enabled',value=1)],baseline=base)
            for source in ('continuous','pulses'):
                add(f'initial-off-{source}-{main}',source,main,enabled=0,
                    events=[dict(frame=event_frame,control='enabled',value=1),dict(frame=336091,control='enabled',value=0)])
    elif stage == 'steps':
        transitions = [('main',a,b) for a,b in ((128,192),(192,128),(64,224),(224,64),(128,0),(0,128),(143,144))]
        transitions += [('amount',a,b) for a,b in ((64,224),(224,64),(128,255),(255,0))]
        transitions += [('cutoff',a,b) for a,b in ((0,192),(192,0),(77,241),(241,77))]
        for control,start,end in transitions:
            values=dict(main=128,amount=128,cutoff=0)
            values[control]=start
            source='continuous' if control=='main' and (start,end) in ((128,192),(192,128)) else 'burst'
            add(f'step-{control}-{start}-{end}',source,**values,events=[dict(frame=event_frame,control=control,value=end)])
        add('step-combined-forward','continuous',events=[dict(frame=event_frame,control=k,value=v)
            for k,v in (('main',177),('amount',229),('cutoff',139))])
        add('step-combined-reverse','burst',main=177,amount=229,cutoff=139,events=[dict(frame=event_frame,control=k,value=v)
            for k,v in (('main',128),('amount',128),('cutoff',0))])
    elif stage == 'ramps':
        for control,low,high in (('main',32,224),('amount',32,224),('cutoff',0,255)):
            for start,end in ((low,high),(high,low)):
                values=dict(main=128,amount=128,cutoff=0)
                values[control]=start
                events=[dict(frame=144013+i*1500,control=control,value=int(raw))
                        for i,raw in enumerate(np.rint(np.linspace(start,end,64)).astype(int))]
                add(f'ramp-{control}-{start}-{end}','tones',**values,events=events)
    elif stage == 'blocks':
        for block in (32,256):
            for control in ('main','cutoff'):
                add(f'step-{control}-block-{block}','continuous' if control=='main' else 'burst',block=block,
                    events=[dict(frame=event_frame,control=control,value=192)],
                    baseline=f'steps/down-step-{control}-128-192' if control=='main' else 'steps/down-step-cutoff-0-192')
            add(f'off-on-block-{block}','continuous',main=255,block=block,
                events=[dict(frame=event_frame,control='enabled',value=0),dict(frame=288073,control='enabled',value=1)],
                baseline='button/down-off-on-continuous-255')
    elif stage == 'state-probes':
        dry=np.zeros_like(continuous)
        dry[event_frame-128:event_frame+256]=np.random.default_rng(0xD029).normal(0,.02,(384,2))
        late=np.zeros_like(continuous);late[event_frame+48000]=[.02,0]
        waves=dict(dry=dry,late=late)
        for start,end in ((128,192),(192,128),(255,0),(0,255),(143,144),(144,143)):
            add(f'dry-main-{start}-{end}','dry',main=start,
                events=[dict(frame=event_frame,control='main',value=end)])
        for main in (128,255):
            for offset in (64,4096,12000):
                name=f'on-pulse-{offset}'
                pulse=np.zeros_like(continuous);pulse[event_frame+offset]=[.02,0]
                waves[name]=pulse
                add(f'initial-off-{main}-pulse-{offset}',name,main=main,enabled=0,
                    events=[dict(frame=event_frame,control='enabled',value=1)])
        for main in (0,128,192):
            add(f'settled-main-baseline-{main}','late',main=main)
        for start,end in ((0,128),(128,0),(128,192),(192,128)):
            add(f'settled-main-{start}-{end}','late',main=start,
                events=[dict(frame=event_frame,control='main',value=end)],
                baseline=f'down-settled-main-baseline-{end}')
        for amount in (0,64,224,255):
            add(f'settled-amount-baseline-{amount}','late',amount=amount)
        for start,end in ((64,224),(224,64),(128,255),(255,0)):
            add(f'settled-amount-{start}-{end}','late',amount=start,
                events=[dict(frame=event_frame,control='amount',value=end)],
                baseline=f'down-settled-amount-baseline-{end}')
    elif stage == 'cutoff-holdout':
        fresh=np.zeros((288000,2))
        fresh[24000:264000]=np.random.default_rng(0xC039A7).normal(0,.019,(240000,2))
        t=np.arange(240000)/48000
        fresh[24000:264000]+=.012*np.column_stack((np.sin(2*np.pi*(173*t+180*t*t)),
                                                  np.cos(2*np.pi*1831*t)+np.sin(2*np.pi*61*t)))
        gap=fresh.copy();gap[96000:192000]=0
        pulses=np.zeros_like(fresh)
        pulses[[24000,96007,120111,192019,240017]]=[[.025,0],[0,-.017],[.013,.009],[-.019,.021],[.01,0]]
        waves=dict(fresh=fresh,gap=gap,pulses=pulses)
        specs=[(47,83,5,'fresh',32,[(120013,255),(121249,0),(144017,91)]),
            (203,221,180,'fresh',256,[(96013,64),(96109,90),(144071,250)]),
            (129,161,1,'fresh',128,[(72001,4),(72045,5),(120013,3)]),
            (255,37,254,'fresh',32,[(96013,255),(96077,250),(144031,0)]),
            (64,224,96,'pulses',256,[(48049,97),(48095,95),(192019,201)]),
            (176,0,223,'gap',128,[(144019,9),(145111,201),(192071,0)]),
            (128,128,0,'fresh',256,[(96013,192),(96111,224),(96143,223),(144197,77)]),
            (143,255,241,'pulses',32,[(96013,1),(120013,241),(192013,255)])]
        for i,(main,amount,cutoff,source,block,events) in enumerate(specs):
            add(f'cutoff-holdout-{i}',source,main,amount,cutoff,block=block,
                events=[dict(frame=frame,control='cutoff',value=value) for frame,value in events])
    else:
        raise ValueError('Unknown motion stage')
    if stage in ('steps','ramps'):
        # A separately rendered original baseline for every initial state/source.
        baselines={}
        for c in cases:
            key=tuple(c[k] for k in ('source','main','amount','cutoff','enabled'))
            if key not in baselines:
                name='down-baseline-'+str(len(baselines))
                baselines[key]=c|dict(name=name,events=[],baseline=None)
            baselines[key]['tail']=max(baselines[key]['tail'],c['tail'])
            c['baseline']=baselines[key]['name']
        cases=[*baselines.values(),*cases]
    return waves,cases


def parameters(case):
    return controls(case)|{'ReverbDownButto':case['enabled']}


def event_values(case):
    return [dict(frame=e['frame'],name=NAMES[e['control']],value=e['value'] if e['control']=='enabled' else e['value']/255)
            for e in case['events']]


def prediction_payload(stage):
    waves,cases=recipe(stage)
    repo=Path(__file__).resolve().parents[1]
    paths=[Path(__file__),repo/'research/audio/experiments/reverb_down_motion_probe.cpp',
           repo/'research/audio/experiments/ReverbDownControlCalibration.h']
    return dict(stage=stage,cases=cases,source_files_sha256={str(p.relative_to(repo)):sha256(p) for p in paths},
        source_samples_sha256={name:hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for name,x in waves.items()})


def predict(args):
    calibration(args.calibration)
    payload=prediction_payload('cutoff-holdout')
    save_json(args.report,dict(kind='rmx220-reverb-down-cutoff-motion-predictions',**payload,
        model_path=str(args.model.resolve()),model_sha256=sha256(args.model),
        renderer_path=str(args.renderer.resolve()),renderer_sha256=sha256(args.renderer),
        calibration_sha256=sha256(args.calibration),candidate_config=dict(gate='inlet',cutoff_position='post',
            gain_position='read',control_quantum=32,candidate_latency=32,level_position='send',
            coefficient_ramp_frames=0,ramp_components='all',decay_step_per_32_frames=0),
        expected='All eight complete renders pass whole/wet/tail and every event window at relative RMS <=0.01.',
        scope='Only Sub2 moves; Main/Sub1 stay fixed and the effect starts enabled.'))


def capture(args):
    calibration(args.calibration)
    if args.stage=='cutoff-holdout':
        if args.prediction is None:
            raise ValueError('Fresh cutoff capture requires frozen prospective predictions')
        prediction=json.loads(args.prediction.read_text())
        if (prediction.get('kind')!='rmx220-reverb-down-cutoff-motion-predictions'
                or any(prediction.get(k)!=v for k,v in prediction_payload(args.stage).items())
                or prediction['calibration_sha256']!=sha256(args.calibration)
                or any(sha256(Path(prediction[k+'_path']))!=prediction[k+'_sha256'] for k in ('model','renderer'))):
            raise ValueError('Prediction recipe/model/source/renderer/calibration differs')
    elif args.prediction is not None:
        raise ValueError('Predictions apply only to fresh cutoff stage')
    root=new_directory(args.session)
    inventory=json.loads(run([args.host,'inventory',args.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json',inventory)
    def setting(name,value):
        matches=[p for p in inventory['parameters'] if p['name']==name]
        if len(matches)!=1:
            raise ValueError('Missing or ambiguous control: '+name)
        return {k:matches[0][k] for k in ('index','id','name')}|{'value':value}
    waves,cases=recipe(args.stage)
    for name,x in waves.items():
        write_wav(root/(name+'.wav'),48000,x.ravel())
    for c in cases:
        events=[setting(e['name'],e['value'])|dict(frame=e['frame'],type='parameter') for e in event_values(c)]
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,
            sample_rate=48000,bpm=120,tail_seconds=c['tail'],parameters=[setting(k,v) for k,v in parameters(c).items()],events=events)
        save_json(root/(c['name']+'.json'),plan)
        run([args.host,'render',args.plugin,root/(c['source']+'.wav'),root/(c['name']+'.json'),root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json')
        print(c['name'],flush=True)
    save_json(root/'matrix.json',dict(kind='rmx220-reverb-down-motion-captures',stage=args.stage,cases=cases,
        calibration_sha256=sha256(args.calibration),capture_script_sha256=sha256(Path(__file__)),
        prediction_sha256=sha256(args.prediction) if args.prediction else None))


def checked(session,case,source):
    folder=session/case['name']
    receipt=json.loads((folder/'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role']!='reference'
            or any(receipt['plugin'][k]!=v for k,v in IDENTITY.items())):
        raise ValueError('Wrong reference: '+str(folder))
    for path,key in ((folder/'audio.wav','output_sha256'),(folder/'plan.json','plan_sha256'),(Path(receipt['input_path']),'input_sha256')):
        if sha256(path)!=receipt[key]:
            raise ValueError('Modified capture: '+str(path))
    plan=json.loads((folder/'plan.json').read_text())
    actual={p['name']:p['value'] for p in plan['parameters']}
    events=[{k:e[k] for k in ('frame','name','value')} for e in plan['events']]
    if (actual!=parameters(case) or events!=event_values(case) or any(e['type']!='parameter' for e in plan['events'])
            or plan['sample_rate']!=48000 or plan['bpm']!=120 or plan['tail_seconds']!=case['tail']
            or receipt['maximum_block_size']!=case['block']):
        raise ValueError('Outside exact motion recipe: '+str(folder))
    rate,audio=float_wav(folder/'audio.wav')
    input_rate,x=float_wav(Path(receipt['input_path']))
    if (rate!=48000 or input_rate!=rate or not np.array_equal(x,source.astype(np.float32))
            or len(audio)!=len(x)+case['tail']*48000):
        raise ValueError('Motion sample/rate/extent differs')
    manifest=json.loads((session/'matrix.json').read_text())
    stored=next(c for c in manifest['cases'] if c['name']==case['name'])
    if stored['receipt_sha256']!=sha256(folder/'receipt.json'):
        raise ValueError('Receipt differs from manifest')
    provenance=dict(case=case['name'],receipt_sha256=sha256(folder/'receipt.json'),input_sha256=receipt['input_sha256'],
        output_sha256=receipt['output_sha256'],plan_sha256=receipt['plan_sha256'])
    return audio.astype(float),x,provenance


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves,cases=recipe(args.stage)
    rows=[checked(args.session,c,waves[c['source']])[2] for c in cases]
    save_json(args.report,dict(kind='rmx220-reverb-down-motion-recipe-verification',stage=args.stage,passed=True,cases=rows,
        script_sha256=sha256(Path(__file__)),scope='Exact samples, controls/events, host block, extent and provenance only.'))
    print('Verified',len(rows),args.stage,'recipes')


def analyze(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    findings={}
    for stage in STAGES:
        session=getattr(args,stage)
        waves,cases=recipe(stage)
        records={c['name']:checked(session,c,waves[c['source']]) for c in cases}
        rows=[]
        for c in cases:
            audio,x,provenance=records[c['name']]
            row=provenance|dict(events=c['events'],block=c['block'],initial=parameters(c))
            if c['baseline']:
                if '/' in c['baseline']:
                    other,name=c['baseline'].split('/',1)
                    ow,oc=recipe(other)
                    baseline=next(b for b in oc if b['name']==name)
                    before,_,baseprov=checked(getattr(args,other),baseline,ow[baseline['source']])
                else:
                    before,_,baseprov=records[c['baseline']]
                length=min(len(audio),len(before))
                changed=np.flatnonzero(np.any(audio[:length]!=before[:length],axis=1))
                row['baseline']=baseprov
                row['baseline_comparison_overlap_frames']=length
                row['baseline_total_frames']=len(before)
                row['bit_exact_to_baseline']=bool(not len(changed))
                row['first_different_output_frame']=int(changed[0]) if len(changed) else None
                row['first_different_frame_after_bypass_offset']=int(changed[0])-32 if len(changed) else None
                if c['events'] and len(changed):
                    row['difference_relative_to_first_event_after_bypass_offset']=int(changed[0])-32-c['events'][0]['frame']
                row['post_input_tail_vs_baseline']=screen(before[len(x):length],audio[len(x):length])
                if c['events']:
                    at=c['events'][0]['frame']
                    row['event_windows']=[]
                    for offset in (-.1,0,.02,.1,.5,1,2):
                        start=int(at+offset*48000)+32
                        end=min(length,start+4800)
                        if start>=0 and end>start:
                            row['event_windows'].append(dict(offset_seconds=offset,comparison=screen(before[start:end],audio[start:end])))
            else:
                if not c['enabled'] and c['events']:
                    stop=c['events'][0]['frame']
                    row['initial_off_prefix_vs_direct_input']=screen(x[:stop],audio[32:32+stop])
            rows.append(row)
        findings[stage]=rows
    save_json(args.report,dict(kind='rmx220-reverb-down-motion-characterization',sample_rate=48000,
        reference_identity=IDENTITY,full_reverb_match=False,physical_hardware=False,
        calibration_sha256=sha256(args.calibration),identifier_sha256=sha256(Path(__file__)),findings=findings,
        limitations=['Original-versus-original state/timing diagnostics, not clone validation.',
            'Parameter timing is reported both in raw output and after the fixed bypass offset; no wet alignment is fitted.']))
    print('Recorded original motion/state diagnostics')


def compare(args):
    calibration(args.calibration)
    model=json.loads(args.model.read_text())
    repo=Path(__file__).resolve().parents[1]
    header=repo/'research/audio/experiments/ReverbDownControlCalibration.h'
    if (model.get('kind')!='rmx220-reverb-down-static-control-model'
            or model['calibration_sha256']!=sha256(args.calibration) or model['header_sha256']!=sha256(header)):
        raise ValueError('Model/calibration/control header differs')
    root=new_directory(args.output)
    rows=[]
    for stage,directory in args.session:
        waves,cases=recipe(stage)
        for c in cases:
            if args.case and c['name'] not in args.case:
                continue
            audio,source,provenance=checked(Path(directory),c,waves[c['source']])
            receipt=json.loads((Path(directory)/c['name']/'receipt.json').read_text())
            prefix=stage+'-'+c['name']
            schedule,output,dry_trace=root/(prefix+'.tsv'),root/(prefix+'.wav'),root/(prefix+'-dry.wav')
            schedule.write_text('RMX_REVERB_MOTION 1\n'
                +f'initial {c["main"]} {c["amount"]} {c["cutoff"]} {c["enabled"]}\n'
                +f'tail {c["tail"]}\n'
                +''.join(f'event {e["frame"]} {e["control"]} {e["value"]}\n' for e in c['events']))
            command=[args.renderer,receipt['input_path'],output,schedule,args.gate,args.cutoff_position,
                     args.gain_position,args.quantum,dry_trace]
            if args.level_position is not None or args.coefficient_ramp is not None or args.ramp_components is not None or args.decay_slew is not None:
                command.append(args.level_position or 'send')
            if args.coefficient_ramp is not None or args.ramp_components is not None or args.decay_slew is not None:
                command.append(args.coefficient_ramp or 0)
            if args.ramp_components is not None or args.decay_slew is not None:
                command.append(args.ramp_components or 'all')
            if args.decay_slew is not None:
                command.append(args.decay_slew)
            run(command)
            rate,candidate=float_wav(output)
            dry_rate,dry=float_wav(dry_trace)
            if rate!=48000 or dry_rate!=rate or len(candidate)!=len(audio) or len(dry)!=len(audio):
                raise ValueError('Motion renderer extent/rate differs')
            extent=len(audio)-32
            a=audio[32:]
            b=candidate[args.candidate_latency:args.candidate_latency+extent].astype(float)
            dry=dry[args.candidate_latency:args.candidate_latency+extent].astype(float)
            wet_a,wet_b=a-dry,b-dry
            row=provenance|dict(stage=stage,whole=screen(a,b),wet=screen(wet_a,wet_b),
                post_input_tail=screen(a[len(source):],b[len(source):]),
                candidate_sha256=sha256(output),dry_trace_sha256=sha256(dry_trace),schedule_sha256=sha256(schedule),
                event_windows=[])
            for frame in sorted({e['frame'] for e in c['events']}):
                start,end=max(0,frame-64),min(len(a),frame+4096)
                row['event_windows'].append(dict(frame=frame,whole=screen(a[start:end],b[start:end]),
                    wet=screen(wet_a[start:end],wet_b[start:end])))
            rows.append(row)
            passed=all(row[k]['passed'] for k in ('whole','wet','post_input_tail'))
            passed=passed and all(w[k]['passed'] for w in row['event_windows'] for k in ('whole','wet'))
            row['passed']=passed
            print('PASS' if passed else 'FAIL',stage,c['name'],flush=True)
    if not rows:
        raise ValueError('No motion cases')
    passed=all(c['passed'] for c in rows)
    paths=[Path(__file__),repo/'research/audio/experiments/reverb_down_motion_probe.cpp',header]
    save_json(root/'comparison.json',dict(kind='diagnostic-reverb-down-motion-prototype-comparison',passed=passed,
        full_reverb_match=False,physical_hardware=False,sample_rate=48000,reference_identity=IDENTITY,
        model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),renderer_sha256=sha256(args.renderer),
        candidate_config=dict(gate=args.gate,cutoff_position=args.cutoff_position,gain_position=args.gain_position,control_quantum=args.quantum,candidate_latency=args.candidate_latency,level_position=args.level_position or 'send',coefficient_ramp_frames=args.coefficient_ramp or 0,ramp_components=args.ramp_components or 'all',decay_step_per_32_frames=args.decay_slew or 0),
        source_sha256={str(p.resolve().relative_to(repo)):sha256(p) for p in paths},cases=rows,
        acceptance=dict(relative_rms_error_limit=.01,silent_channel_absolute_rms_limit=1e-8,
            reference_channel_energy_floor=1e-20,reference_offset_frames=32,candidate_offset_frames=args.candidate_latency,gain_fit=False,wet_alignment_search=False),
        limitations=['Discovery recipes characterize state handling; fresh independent dynamic validation is still required.',
            'Wet subtraction uses the candidate-predicted dry trace on both sides, without a reference gain fit.',
            'Whole/wet event windows and the separate post-input tail prevent long quiet intervals or dry output from masking errors.']))
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for command in ('capture','verify'):
        p=commands.add_parser(command)
        p.add_argument('--stage',choices=CAPTURE_STAGES,required=True)
        p.add_argument('--session',type=Path,required=True)
        if command=='capture':
            p.add_argument('--prediction',type=Path)
            for name in ('host','plugin','calibration'):
                p.add_argument('--'+name,type=Path,required=True)
        else:
            p.add_argument('--report',type=Path,required=True)
    p=commands.add_parser('predict-cutoff')
    for name in ('model','calibration','renderer','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('analyze')
    for name in (*STAGES,'calibration','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('compare')
    for name in ('model','calibration','renderer','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--session',nargs=2,action='append',required=True,metavar=('STAGE','DIRECTORY'))
    p.add_argument('--gate',choices=('inlet','output','inlet-output','reset'),default='inlet')
    p.add_argument('--cutoff-position',choices=('pre','comb','post'),default='post')
    p.add_argument('--gain-position',choices=('read','write'),default='read')
    p.add_argument('--level-position',choices=('send','output','main-send','amount-send'))
    p.add_argument('--coefficient-ramp',type=int,help='Exploratory linear feedback/level coefficient ramp, 0..200000 frames')
    p.add_argument('--ramp-components',choices=('all','levels','feedback','staged'))
    p.add_argument('--decay-slew',type=float,help='Exploratory nominal T60 step per 32 frames; requires levels-only ramp')
    p.add_argument('--case',action='append',help='Exact recipe name; repeat to select diagnostic cases')
    p.add_argument('--candidate-latency',type=int,choices=(0,32),default=32)
    p.add_argument('--quantum',type=int,choices=(1,32,128),default=32)
    args=parser.parse_args()
    result={'capture':capture,'verify':verify,'analyze':analyze,'compare':compare,'predict-cutoff':predict}[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__=='__main__':
    main()
