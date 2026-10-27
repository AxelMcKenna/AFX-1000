#!/usr/bin/env python3
"""Build and validate static Up raw-control maps with prospective mixed fixtures."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256,write_wav
from tools.noise_statistics import float_wav
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked,controls,recipe as original_recipe
from tools.rmx_reverb_up import recipe as neutral_recipe
from tools.rmx_reverb_up_controls import recipe as control_recipe
from tools.rmx_spiral_core import calibration


def room_audit(cases):
    bases=np.array([[1032,1146],[1060,1856],[1145,1961],[1916,1115],[1992,1190]],dtype=np.float32)
    failures=[];tested=0
    for c in cases:
        if c['silent_wet']:continue
        raw=c['main_raw'];v=np.float32(1)-np.float32(max(0,raw-3))*np.float32(1/252)
        scale=np.float32(.3)+np.float32(3)*((v*v)*(v*v));predicted=(scale*bases).astype(int)
        tested+=10;actual=np.array(c['delays'])
        if np.any(actual!=predicted):failures.append(dict(raw=raw,predicted=predicted.tolist(),measured=actual.tolist(),mismatching_taps=int(np.count_nonzero(actual-predicted))))
    return dict(formula='float32 scale = 0.3 + 3*(1-max(0,raw-3)/252)^4, unfused scalar operations; integer taps truncate scale*bases',
        observation_positions=[32,64,96,128,160,192,224,255],compared_taps=tested,mismatching_taps=sum(c['mismatching_taps'] for c in failures),cases=failures,
        prospective=False,interpretation='The formula was suggested by eight earlier recordings while dense capture was underway. Exact measured integer rows remain authoritative.')


def build(args):
    if args.report.exists() or args.header.exists():raise ValueError('Model/header must be new')
    calibration(args.calibration);main,amount=[json.loads(p.read_text()) for p in (args.main,args.amount)];neutral=json.loads(args.neutral.read_text())
    for data,stage,key in [(main,'main','main_raw'),(amount,'amount','amount_raw')]:
        if (data.get('kind')!='rmx220-reverb-up-control-identification' or data['stage']!=stage or not data['fitting_screen_passed']
                or data['calibration_sha256']!=sha256(args.calibration) or data['neutral_model_sha256']!=sha256(args.neutral)
                or [c[key] for c in data['cases']]!=list(range(256))):raise ValueError('Incomplete or failed Up identification')
    validation=None
    if not amount['prospective_predictions_passed']:
        if args.feedback_validation is None or not amount.get('retrospective_reference_scaling_passed'):raise ValueError('Saved Sub1 forecasts failed; require retained failures plus a separately validated corrected reference')
        validation=json.loads(args.feedback_validation.read_text())
        if (validation.get('kind')!='rmx220-reverb-up-feedback-arithmetic-validation' or not validation['passed'] or len(validation['cases'])!=8
                or validation['reference_sha256']!=sha256(args.neutral) or validation['calibration_sha256']!=sha256(args.calibration)
                or validation['fixed_gain_error_limit']!=2e-6 or not all(c['passed'] for c in validation['cases'])):raise ValueError('Corrected-reference prospective validation differs')
    if neutral['kind'] not in ('rmx220-reverb-up-neutral-network-identification','rmx220-reverb-up-control-reference') or neutral['calibration_sha256']!=sha256(args.calibration):raise ValueError('Wrong neutral model')
    neutral_row=dict(delays=neutral['delays'],gain_left=neutral['gain_left'],gain_right=neutral['gain_right'],
        input_a=neutral['input_filter']['denominator'],wet_gain=neutral['wet_gain'])
    rows=[]
    for c in main['cases']:
        row=dict(neutral_row) if c['silent_wet'] or c['main_raw']==128 else {k:c[k] for k in ('delays','gain_left','gain_right','input_a','wet_gain')}
        if c['silent_wet']:row['wet_gain']=0
        if abs(c['dry_gain']-1)>1e-8:raise ValueError('Up dry gain differs from unity')
        if (np.any(np.array(row['delays'])<=0) or np.any(np.array(row['delays'])>48000)
                or np.any(np.array(row['gain_left'])<=0) or np.any(np.array(row['gain_left'])>=1)
                or np.any(np.array(row['gain_right'])<=0) or np.any(np.array(row['gain_right'])>=1)
                or np.any(abs(np.roots(row['input_a']))>=1) or row['wet_gain']<0):raise ValueError('Invalid static Up row')
        rows.append(row)
    gains=[c['wet_gain'] for c in amount['cases']]
    if not np.isfinite(gains).all() or min(gains)<=0:raise ValueError('Invalid Sub1 gains')
    input_coefficient_deviation=float(max(np.max(abs(np.array(c['input_a'])-np.array(amount['cases'][128]['input_a']))) for c in amount['cases']))
    main_correction,amount_correction=[0.]*256,[0.]*256;interaction_sources=None
    if bool(args.main_long)!=bool(args.amount_large):raise ValueError('Both interaction sweeps are required')
    if args.main_long:
        high,large=[json.loads(p.read_text()) for p in (args.main_long,args.amount_large)]
        for data,stage,key in [(high,'main-long','main_raw'),(large,'amount-large','amount_raw')]:
            if (data.get('kind')!='rmx220-reverb-up-control-identification' or data['stage']!=stage or not data['fitting_screen_passed']
                    or not data['prospective_predictions_passed'] or data['calibration_sha256']!=sha256(args.calibration)
                    or [c[key] for c in data['cases']]!=list(range(256))):raise ValueError('Incomplete/failed interaction sweep')
        for raw,c in enumerate(high['cases']):
            if rows[raw]['wet_gain']>0:main_correction[raw]=c['wet_gain']/rows[raw]['wet_gain']*gains[128]/gains[255]-1
        if abs(main_correction[255])<.01:raise ValueError('Interaction scale is not identifiable')
        for raw,c in enumerate(large['cases']):amount_correction[raw]=(c['wet_gain']/rows[255]['wet_gain']*gains[128]/gains[raw]-1)/main_correction[255]
        factors=1+np.outer(main_correction,amount_correction)
        if not np.isfinite(factors).all() or factors.min()<=0:raise ValueError('Nonpositive interaction gain')
        interaction_sources=dict(main_long_sha256=sha256(args.main_long),amount_large_sha256=sha256(args.amount_large))
    def numbers(values):return ','.join(format(float(v),'.17g') for v in values)
    header='// Own measured static Default Up maps, 48 kHz. Motion/rates/hardware remain unproven.\n#pragma once\n#include <array>\n'
    header+='struct ReverbUpControlRow {std::array<std::array<int,2>,5> delays;std::array<double,5> gainL,gainR;std::array<double,2> inputA;double wetGain;};\n'
    header+='constexpr std::array<ReverbUpControlRow,256> reverbUpControls{{\n'
    for r in rows:
        ds='{{'+','.join('{{'+','.join(map(str,p))+'}}' for p in r['delays'])+'}}'
        header+='{'+ds+',{{'+numbers(r['gain_left'])+'}},{{'+numbers(r['gain_right'])+'}},{{'+numbers(r['input_a'][1:])+'}},'+numbers([r['wet_gain']])+'},\n'
    header+='}};\n'
    feedback=neutral.get('feedback_filter')
    if feedback is None:
        pole=(1-np.tan(np.pi*25/48000))/(1+np.tan(np.pi*25/48000));feedback=dict(b=[(1+pole)/2,-(1+pole)/2],a=[1,-pole])
    header+='constexpr std::array<double,3> reverbUpFeedback{{'+numbers([*feedback['b'],feedback['a'][1]])+'}};\n'
    for label,values in [('AmountGain',gains),('MainCorrection',main_correction),('AmountCorrection',amount_correction)]:header+='constexpr std::array<double,256> reverbUp'+label+'{{'+numbers(values)+'}};\n'
    args.header.parent.mkdir(parents=True,exist_ok=True)
    with args.header.open('x') as f:f.write(header)
    save_json(args.report,dict(kind='rmx220-reverb-up-static-control-model',sample_rate=48000,full_reverb_match=False,physical_hardware=False,
        main_rows=rows,amount_gains=gains,main_correction=main_correction,amount_correction=amount_correction,interaction_rank=2 if interaction_sources else 1,
        feedback_filter=feedback,corrected_feedback_validation_sha256=sha256(args.feedback_validation) if validation else None,
        original_sub1_forecasts_passed=amount['prospective_predictions_passed'],
        interaction_sources=interaction_sources,calibration_sha256=sha256(args.calibration),neutral_model_sha256=sha256(args.neutral),
        main_identification_sha256=sha256(args.main),amount_identification_sha256=sha256(args.amount),builder_sha256=sha256(Path(__file__)),header_sha256=sha256(args.header),
        room_formula_audit=room_audit(main['cases']),sub1_input_coefficient_maximum_deviation=input_coefficient_deviation,
        proposed_feedback_combination='main_feedback_gain[Main] ** (nominal_decay(128)/nominal_decay(Sub1)); nominal_decay = 1+49*(max(0,raw-3)/252)^3',
        proposed_wet_gain_combination='MainGain[Main] * Sub1Gain[Sub1]/Sub1Gain[128] * (1+MainCorrection[Main]*Sub1Correction[Sub1])',
        scope='Static integer raw controls, factory Up, stereo 48 kHz/120 BPM. Main0..3 geometry uses a placeholder only when static wet gain is zero.',
        limitations=['Sweeps are coefficient identification, not independent complete waveform validation. Fresh mixed-control programs are required.',
            'No motion/startup, profiles/rates/tempos, production integration, overload, listening or hardware claim.']))
    print('Built static Up maps; fresh mixed-control validation remains required')


def mixed_recipe(variant):
    if variant not in ('mixed','mixed-v2'):raise ValueError('Unknown mixed Up variant')
    second=variant=='mixed-v2';rng=np.random.default_rng(0x7A1A21 if second else 0x7A1A20)
    program=np.zeros((408000,2));t=np.arange(336000)/48000
    program[48000:384000]=rng.normal(0,.018,(336000,2))+.008*np.column_stack((np.sin(2*np.pi*(263*t+41*t*t)),np.cos(2*np.pi*2017*t)))
    program[168000:240000]=0
    pulse=np.zeros_like(program);pulse[61517 if second else 58313,0]=.029;pulse[249389 if second else 271337,1]=-.025
    pairs=[(m,a) for m in ((41,105,171,231) if second else (25,73,149,219)) for a in ((29,91,163,227) if second else (41,103,181,239))]
    pairs+=([(1,0),(2,255),(5,3),(5,253),(7,4),(7,252),(127,229),(128,98),(129,1),(129,254),(131,2),(131,5),(254,1),(254,2),(254,5),(254,254)] if second else
        [(0,0),(3,255),(4,0),(4,255),(8,3),(8,4),(104,97),(128,98),(129,0),(129,255),(130,3),(130,4),(255,0),(255,3),(255,4),(255,255)])
    cases=[]
    for si,source in enumerate(('program','pulses')):
        for i,(main,amount) in enumerate(pairs):
            cutoff=((37,119,211,249) if second else (0,83,179,243))[(i+si)%4]
            cases.append(dict(name=f'up-{source}-main-{main}-amount-{amount}-cutoff-{cutoff}',source=source,direction='up',main=main,amount=amount,cutoff=cutoff,tail=90 if amount>=177 else 18))
    return dict(program=program,pulses=pulse),cases


def paths():
    repo=Path(__file__).resolve().parents[1]
    return [Path(__file__),repo/'tools/rmx_reverb_up_controls.py',repo/'tools/rmx_reverb_controls.py',repo/'tools/rmx_reverb_up.py',
        repo/'research/audio/experiments/reverb_up_neutral_probe.cpp',repo/'research/audio/experiments/ReverbUpControlCalibration.h',repo/'research/audio/experiments/ReverbUpNeutralCalibration.h',
        repo/'src/core/Wav.cpp',repo/'include/rmx/Wav.h',repo/'include/rmx/Dsp.h',repo/'CMakeLists.txt']


def hashes():
    repo=Path(__file__).resolve().parents[1];return {str(p.relative_to(repo)):sha256(p) for p in paths()}


def model_checked(args):
    calibration(args.calibration);model=json.loads(args.model.read_text());header=Path(__file__).resolve().parents[1]/'research/audio/experiments/ReverbUpControlCalibration.h'
    if model.get('kind')!='rmx220-reverb-up-static-control-model' or model['calibration_sha256']!=sha256(args.calibration) or model['header_sha256']!=sha256(header):raise ValueError('Wrong static Up model/header/calibration')
    return model


def payload(variant):
    waves,cases=mixed_recipe(variant)
    return dict(kind='rmx220-reverb-up-mixed-predictions',variant=variant,cases=cases,source_sha256=hashes(),
        samples_sha256={s:hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for s,x in waves.items()})


def predict(args):
    model_checked(args)
    save_json(args.report,payload(args.recipe)|dict(model_path=str(args.model.resolve()),model_sha256=sha256(args.model),renderer_path=str(args.renderer.resolve()),renderer_sha256=sha256(args.renderer),calibration_sha256=sha256(args.calibration),
        expected='All 64 complete renders pass unchanged whole/wet/post-input-tail per-channel RMS limit .01, energy floor1e-20 and silent-channel absolute RMS1e-8, reference offset32/candidate0, no gain fit or wet alignment search.'))


def capture(args):
    model_checked(args);prediction=json.loads(args.prediction.read_text());model_hash=sha256(args.model);renderer_hash=sha256(Path(prediction['renderer_path']))
    if any(prediction.get(k)!=v for k,v in payload(args.recipe).items()) or prediction['model_sha256']!=model_hash or prediction['calibration_sha256']!=sha256(args.calibration) or prediction['renderer_sha256']!=renderer_hash:raise ValueError('Frozen mixed prediction differs')
    root=new_directory(args.session);(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):raise ValueError('Requires original RMX-1000 2.2.0')
    waves,cases=mixed_recipe(args.recipe)
    for s,x in waves.items():write_wav(root/(s+'.wav'),48000,x.ravel())
    for c in cases:
        settings=[]
        for name,value in controls(c).items():
            found=[p for p in inventory['parameters'] if p['name']==name]
            if len(found)!=1:raise ValueError('Ambiguous/missing original control '+name)
            settings.append({k:found[0][k] for k in ('index','id','name')}|dict(value=value))
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,sample_rate=48000,bpm=120,tail_seconds=c['tail'],parameters=settings,events=[])
        save_json(root/(c['name']+'.json'),plan);run([args.host,'render',args.plugin,root/(c['source']+'.wav'),root/(c['name']+'.json'),root/c['name'],128])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print(c['name'],flush=True)
    if sha256(args.model)!=model_hash or sha256(Path(prediction['renderer_path']))!=renderer_hash or any(prediction.get(k)!=v for k,v in payload(args.recipe).items()):raise ValueError('Frozen candidate changed during capture')
    save_json(root/'matrix.json',dict(kind='rmx220-reverb-up-mixed-captures',recipe=args.recipe,cases=cases,prediction_sha256=sha256(args.prediction),model_sha256=model_hash))


def session_recipe(stage):
    if stage in ('main','amount','main-long','amount-large'):
        x,cases=control_recipe(stage);return dict(source=x),cases
    if stage in ('mixed','mixed-v2'):return mixed_recipe(stage)
    if stage=='neutral-holdout':return neutral_recipe('holdout')
    if stage in ('initial','filters','timing','long-tail'):
        waves,cases=original_recipe(stage);return waves,[c for c in cases if c['direction']=='up']
    raise ValueError('Unknown Up session stage')


def compare(args):
    model_checked(args);root=new_directory(args.output);rows=[]
    for stage,directory in args.session:
        waves,cases=session_recipe(stage)
        for c in cases:
            receipt,a,x,provenance=checked(directory,c,waves[c['source']]);output=root/(stage+'-'+c['name']+'.wav')
            run([args.renderer,receipt['input_path'],output,c['main'],c['amount'],c['cutoff'],c['tail']]);rate,b=float_wav(output)
            if rate!=48000 or len(b)!=len(a)+32:raise ValueError('Candidate extent/rate differs')
            b=b[:len(a)].astype(float);dry=np.zeros_like(a);dry[:min(len(a),len(x))]=x[:len(a)]
            row=provenance|dict(stage=stage,candidate_sha256=sha256(output),whole=screen(a,b),wet=screen(a-dry,b-dry),post_input_tail=screen(a[len(x):],b[len(x):]))
            row['passed']=all(row[k]['passed'] for k in ('whole','wet','post_input_tail'));rows.append(row)
            print('PASS' if row['passed'] else 'FAIL',stage,c['name'],flush=True)
    if not rows:raise ValueError('No Up comparisons')
    passed=all(r['passed'] for r in rows)
    save_json(root/'comparison.json',dict(kind='rmx220-reverb-up-static-control-comparison',passed=passed,full_reverb_match=False,physical_hardware=False,
        model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),renderer_sha256=sha256(args.renderer),source_sha256=hashes(),cases=rows,
        acceptance=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,reference_offset_frames=32,candidate_offset_frames=0,gain_fit=False,wet_alignment_search=False),
        limitations=['Control sweeps calibrate coefficients; all prior fixtures are regressions. Fresh prediction-bound mixed programs are separate evidence.',
            'Static integer controls at factory Up/48 kHz/120 BPM with a silent pre-roll; no motion/startup, production, rate/profile/tempo, overload, listening or hardware claim.']))
    return 0 if passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
    q=commands.add_parser('build')
    for name in ('main','amount','neutral','calibration','report','header'):q.add_argument('--'+name,type=Path,required=True)
    q.add_argument('--main-long',type=Path);q.add_argument('--amount-large',type=Path);q.add_argument('--feedback-validation',type=Path)
    for command in ('predict','capture','compare'):
        q=commands.add_parser(command)
        for name in ('model','calibration'):q.add_argument('--'+name,type=Path,required=True)
        if command in ('predict','compare'):q.add_argument('--renderer',type=Path,required=True)
        if command in ('predict','capture'):q.add_argument('--recipe',choices=('mixed','mixed-v2'),default='mixed')
        if command=='predict':q.add_argument('--report',type=Path,required=True)
        if command=='capture':
            for name in ('host','plugin','prediction','session'):q.add_argument('--'+name,type=Path,required=True)
        if command=='compare':q.add_argument('--session',nargs=2,action='append',required=True);q.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.command=='compare':args.session=[(s,Path(d)) for s,d in args.session]
    result=globals()[args.command](args)
    if result is not None:raise SystemExit(result)


if __name__=='__main__':main()
