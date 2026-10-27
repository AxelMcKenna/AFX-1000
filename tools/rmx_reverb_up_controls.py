#!/usr/bin/env python3
"""Measure factory Up's static integer control maps; no complete-device claim."""
import argparse
import datetime
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_reverb_characterize import checked,controls
from tools.rmx_reverb_network import allpass,biquad,first_peaks
from tools.rmx_reverb_controls import nominal_decay,refine
from tools.rmx_spiral_core import calibration


def recipe(stage):
    x=np.zeros((96000,2));x[48000,0]=.02
    if stage not in ('main','amount','main-long','amount-large'):raise ValueError('Unknown Up control stage')
    cases=[]
    for raw in range(256):
        main=raw if stage in ('main','main-long') else (255 if stage=='amount-large' else 128)
        amount=raw if stage in ('amount','amount-large') else (255 if stage=='main-long' else 128)
        cases.append(dict(name=f'up-{stage}-{raw}',source='source',direction='up',main=main,amount=amount,cutoff=0,tail=3))
    return x,cases


def neutral_checked(path,calibration_path):
    calibration(calibration_path);n=json.loads(path.read_text())
    if n.get('kind')!='rmx220-reverb-up-neutral-network-identification' or n['calibration_sha256']!=sha256(calibration_path):raise ValueError('Wrong neutral Up model/calibration')
    return n


def capture(args):
    neutral=neutral_checked(args.neutral,args.calibration);neutral_hash=sha256(args.neutral)
    static=None
    if args.stage in ('main-long','amount-large'):
        if args.static_model is None:raise ValueError('Interaction sweeps require a frozen static Up model')
        static=json.loads(args.static_model.read_text())
        if static.get('kind')!='rmx220-reverb-up-static-control-model' or static['calibration_sha256']!=sha256(args.calibration):raise ValueError('Wrong static Up model/calibration')
    static_hash=sha256(args.static_model) if static else None
    root=new_directory(args.session);x,cases=recipe(args.stage)
    inventory=json.loads(run([args.host,'inventory',args.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):raise ValueError('Requires original RMX-1000 2.2.0')
    write_wav(root/'source.wav',48000,x.ravel())
    if args.stage!='main':
        predictions=[]
        for c in cases:
            base=static['main_rows'][c['main']] if static else neutral
            exponent=nominal_decay(128)/nominal_decay(c['amount'])
            predictions.append(dict(case=c['name'],main=c['main'],amount=c['amount'],
                assessable=base.get('wet_gain',1)!=0,left=[g**exponent for g in base['gain_left']],right=[g**exponent for g in base['gain_right']]))
        save_json(root/'predictions.json',dict(kind='rmx220-reverb-up-sub1-feedback-predictions',
            created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),neutral_model_sha256=neutral_hash,
            static_model_sha256=static_hash,maximum_absolute_gain_error=2e-6,
            formula='gain(Main,Sub1) = gain(Main,128) ** (nominal_decay(128)/nominal_decay(Sub1)); nominal_decay = 1+49*(max(0,raw-3)/252)^3',predictions=predictions))
    for c in cases:
        settings=[]
        for name,value in controls(c).items():
            matches=[p for p in inventory['parameters'] if p['name']==name]
            if len(matches)!=1:raise ValueError('Missing/ambiguous original parameter '+name)
            settings.append({k:matches[0][k] for k in ('index','id','name')}|dict(value=value))
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,
            sample_rate=48000,bpm=120,tail_seconds=c['tail'],parameters=settings,events=[])
        save_json(root/(c['name']+'.json'),plan)
        run([args.host,'render',args.plugin,root/'source.wav',root/(c['name']+'.json'),root/c['name'],128])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print(c['name'],flush=True)
    if sha256(args.neutral)!=neutral_hash or (static and sha256(args.static_model)!=static_hash):raise ValueError('Frozen model changed during capture')
    save_json(root/'matrix.json',dict(kind='rmx220-reverb-up-control-captures',stage=args.stage,cases=cases,
        neutral_model_sha256=neutral_hash,static_model_sha256=static_hash,capture_script_sha256=sha256(Path(__file__)),
        predictions_sha256=sha256(root/'predictions.json') if args.stage!='main' else None))


def verify(args):
    x,cases=recipe(args.stage)
    rows=[checked(args.session,c,x)[3] for c in cases]
    save_json(args.report,dict(kind='rmx220-reverb-up-control-recipe-verification',passed=True,stage=args.stage,cases=rows,
        script_sha256=sha256(Path(__file__)),scope='Exact input, controls, extent/rate and capture hashes only.'))


def setup():
    size=524288;zd=np.exp(-2j*np.pi*np.arange(size//2+1)/size)
    fixed=biquad(zd,54,True)*biquad(zd,17330,False)
    leading=np.fft.irfft(fixed*(1-zd*zd),n=size)[:8]
    detector=(size,zd,np.column_stack([allpass(zd,ch)*fixed for ch in (0,1)]),leading)
    size=262144;bins=np.arange(16,size//2,16);hz=bins*48000/size;bins=bins[(hz>=60)&(hz<18000)]
    radius=np.exp(-3*np.log(10)/(48000*.75));z=radius*np.exp(-2j*np.pi*bins/size)
    p=(1-np.tan(np.pi*25/48000))/(1+np.tan(np.pi*25/48000));hp=(1+p)/2*(1-z)/(1-p*z)
    return detector,(size,bins,z,radius,hp,np.column_stack([allpass(z,ch) for ch in (0,1)]),biquad(z,54,True)*biquad(z,17330,False))


def fit_case(audio,source,c,neutral,detector,frequency,known=None):
    h=audio[48000:].astype(float)/float(source[48000,0]);dry=float(h[0,0]);h[0,0]=0
    if not np.any(h):return dict(dry_gain=dry,silent_wet=True)
    if known is not None:delays=np.array(known)
    elif c['main']==128:delays=np.array(neutral['delays'])
    else:
        first=int(np.flatnonzero(abs(h[:,0])>abs(h[:,0]).max()*1e-7)[0]);y=h[first:first+8,0]
        amp=abs(y).max();u=y/amp;idx=np.arange(2,8)
        m=np.column_stack([-u[idx-1],-u[idx-2],detector[3][idx]])
        a1,a2,_=np.linalg.lstsq(m,u[idx],rcond=1e-12)[0]
        size,z,fixed,_=detector;input_filter=(1-z*z)/(1+a1*z+a2*z*z)
        transfer=fixed*input_filter[:,None]
        whitened=np.fft.irfft(np.fft.rfft(h,n=size,axis=0)*transfer.conj()/(abs(transfer)**2+1e-10),n=size,axis=0)
        left=np.array(first_peaks(whitened[:,0]));cross=np.array(first_peaks(whitened[:,1]))
        delays=np.column_stack([left,cross[[0,1,3,2,4]]-left])
        if np.any(delays<=0):raise ValueError('Invalid comb delays')
    size,bins,z,radius,hp,diffusers,output_filter=frequency
    observed=np.fft.rfft(h*radius**np.arange(len(h))[:,None],n=size,axis=0)[bins];target=observed/diffusers
    zl=z[:,None]**delays[:,0];periods=z[:,None]**delays.sum(axis=1)
    def network(parameters):
        gl,loop=np.exp(parameters[:5]),np.exp(parameters[5:]);den=1-loop*periods*hp[:,None]**2
        return np.column_stack([np.sum(gl*zl/den,axis=1),np.sum(loop*periods*hp[:,None]/den,axis=1)])
    initial=-3*np.log(10)/(48000*nominal_decay(c['amount']))*np.r_[delays[:,0],delays.sum(axis=1)]
    scale=np.linalg.norm(target[:,0]*network(initial)[:,1])
    def objective(parameters):
        v=network(parameters);e=(target[:,1]*v[:,0]-target[:,0]*v[:,1])/scale
        return np.r_[e.real,e.imag]
    fitted=refine(objective,initial);gl=np.exp(fitted[:5]);gr=np.exp(fitted[5:]-fitted[:5])
    unit=network(fitted)*diffusers*output_filter[:,None]
    design=np.column_stack([(observed*z[:,None]).ravel(),(observed*z[:,None]**2).ravel(),(-(1-z[:,None]**2)*unit).ravel()])
    a1,a2,gain=np.linalg.lstsq(np.r_[design.real,design.imag],np.r_[-observed.real.ravel(),-observed.imag.ravel()],rcond=1e-12)[0]
    predicted=unit*(gain*(1-z*z)/(1+a1*z+a2*z*z))[:,None]
    error=float(np.linalg.norm(predicted-observed)/np.linalg.norm(observed))
    stable=bool(np.all(gl>0) and np.all(gl<1) and np.all(gr>0) and np.all(gr<1) and np.all(abs(np.roots([1,a1,a2]))<1) and gain>0)
    return dict(silent_wet=False,dry_gain=dry,delays=delays.tolist(),gain_left=gl.tolist(),gain_right=gr.tolist(),
        input_a=[1,float(a1),float(a2)],wet_gain=float(gain),stable=stable,damped_frequency_relative_error=error,
        stereo_relation_relative_error=float(np.linalg.norm(objective(fitted))),
        nominal_delays=(-np.log(np.column_stack([gl,gr]))*48000*nominal_decay(c['amount'])/(3*np.log(10))).tolist())


def identify(args):
    if args.report.exists():raise ValueError('Report must be new')
    neutral=neutral_checked(args.neutral,args.calibration);detector,frequency=setup();x,cases=recipe(args.stage)
    static=None
    if args.stage in ('main-long','amount-large'):
        if args.static_model is None:raise ValueError('Interaction fitting requires frozen static model')
        static=json.loads(args.static_model.read_text())
        if static['kind']!='rmx220-reverb-up-static-control-model' or static['calibration_sha256']!=sha256(args.calibration):raise ValueError('Wrong static model')
    predictions=None
    if args.stage!='main':
        predictions=json.loads((args.session/'predictions.json').read_text());manifest=json.loads((args.session/'matrix.json').read_text())
        if (manifest['predictions_sha256']!=sha256(args.session/'predictions.json') or predictions['neutral_model_sha256']!=sha256(args.neutral)
                or (static and predictions['static_model_sha256']!=sha256(args.static_model))):raise ValueError('Saved feedback predictions differ')
    rows=[]
    for c in cases:
        _,audio,source,provenance=checked(args.session,c,x)
        known=static['main_rows'][c['main']]['delays'] if static else None
        result=fit_case(audio,source,c,neutral,detector,frequency,known)
        row=provenance|dict(main_raw=c['main'],amount_raw=c['amount'],**result)
        if predictions is not None:
            forecast=next(p for p in predictions['predictions'] if p['case']==c['name'])
            row['prospective_prediction_assessable']=not result['silent_wet']
            if not result['silent_wet']:
                error=float(max(abs(np.array(result['gain_left'])-forecast['left']).max(),abs(np.array(result['gain_right'])-forecast['right']).max()))
                row['prospective_maximum_absolute_gain_error']=error;row['prospective_prediction_passed']=error<=predictions['maximum_absolute_gain_error']
        rows.append(row);print(c['name'],'silent' if result['silent_wet'] else f'fit {result["damped_frequency_relative_error"]:.3g}',flush=True)
    passed=all(c.get('stable',True) and c.get('damped_frequency_relative_error',0)<=1e-4 for c in rows)
    forecasts_passed=all(c.get('prospective_prediction_passed',True) for c in rows)
    save_json(args.report,dict(kind='rmx220-reverb-up-control-identification',stage=args.stage,fitting_screen_passed=passed,
        prospective_predictions_passed=forecasts_passed,cases=rows,neutral_model_sha256=sha256(args.neutral),
        calibration_sha256=sha256(args.calibration),static_model_sha256=sha256(args.static_model) if static else None,
        script_sha256=sha256(Path(__file__)),identification_weighting_t60_seconds=.75,prospective_predictions=predictions,
        full_reverb_match=False,physical_hardware=False,
        limitations=['Weighted fitting identifies coefficients; autonomous waveform acceptance uses original undamped audio.',
        'Static integer controls, factory Up, 48 kHz/120 BPM only. Main/Sub1 interactions, motion/startup, production integration and hardware remain unproven.']))
    return 0 if passed and forecasts_passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
    for command in ('capture','identify','verify'):
        q=commands.add_parser(command);q.add_argument('--stage',choices=('main','amount','main-long','amount-large'),required=True)
        q.add_argument('--session',type=Path,required=True)
        if command in ('capture','identify'):
            q.add_argument('--neutral',type=Path,required=True);q.add_argument('--calibration',type=Path,required=True);q.add_argument('--static-model',type=Path)
        if command=='capture':q.add_argument('--host',type=Path,required=True);q.add_argument('--plugin',type=Path,required=True)
        else:q.add_argument('--report',type=Path,required=True)
    args=p.parse_args();result=globals()[args.command](args)
    if result is not None:raise SystemExit(result)


if __name__=='__main__':main()
