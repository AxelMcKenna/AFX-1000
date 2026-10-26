#!/usr/bin/env python3
"""Identify and independently check factory Up at Main128/Sub1-128/48 kHz."""
import argparse
import datetime
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked,controls,recipe as static_recipe,residual
from tools.rmx_reverb_network import allpass,biquad,first_peaks,global_filter,refine
from tools.rmx_spiral_core import calibration


def recipe(stage):
    if stage in ('initial','filters'):
        waves,cases=static_recipe(stage)
        return waves,[c for c in cases if c['direction']=='up' and c['main']==128 and c['amount']==128]
    if stage!='holdout':raise ValueError('Unknown Up stage')
    x=np.zeros((408000,2));rng=np.random.default_rng(0x7EAB1027)
    t=np.arange(336000)/48000
    x[48000:384000]=rng.normal(0,.019,(336000,2))+.009*np.column_stack((np.sin(2*np.pi*(197*t+37*t*t)),np.cos(2*np.pi*1723*t)))
    x[168000:240000]=0
    pulses=np.zeros((312000,2));locations=[52117,96203,144277,192307,240337,288359]
    pulses[locations]=np.random.default_rng(0x7EAB1028).uniform(-.027,.027,(len(locations),2))
    waves=dict(up_program=x,up_pulses=pulses)
    cases=[dict(name=f'up-{source}-cutoff-{raw}',source=source,direction='up',main=128,amount=128,cutoff=raw,tail=18)
           for source in waves for raw in (19,111,203,247)]
    return waves,cases


def paths():
    repo=Path(__file__).resolve().parents[1]
    return [Path(__file__),repo/'tools/rmx_reverb_network.py',repo/'tools/rmx_reverb_characterize.py',
        repo/'research/audio/experiments/reverb_up_neutral_probe.cpp',repo/'research/audio/experiments/ReverbUpNeutralCalibration.h',
        repo/'src/core/Wav.cpp',repo/'include/rmx/Wav.h',repo/'include/rmx/Dsp.h',repo/'CMakeLists.txt']


def source_hashes():
    repo=Path(__file__).resolve().parents[1]
    return {str(p.relative_to(repo)):sha256(p) for p in paths()}


def identify(args):
    if args.report.exists() or args.header.exists():raise ValueError('Report/header must be new')
    calibration(args.calibration)
    waves,cases=recipe('initial');by_name={c['name']:c for c in cases}
    records={s:checked(args.initial,by_name['up-source-'+s],waves[s]) for s in ('left','right')}
    size=2097152;z=np.exp(-2j*np.pi*np.arange(size//2+1)/size)
    # The Down inverse is only an arrival locator. Its input-filter hypothesis
    # is explicitly replaced by the fitted Up bandpass below.
    inverse=np.column_stack([allpass(z,ch)*global_filter(z) for ch in (0,1)])
    arrivals={}
    for side,(_,audio,x,_) in records.items():
        h=residual(audio,x,1)[48000:]/float(x[48000,0 if side=='left' else 1])
        sparse=np.fft.irfft(np.fft.rfft(h,n=size,axis=0)*inverse.conj()/(abs(inverse)**2+1e-10),n=size,axis=0)
        arrivals[side]=[first_peaks(sparse[:,ch]) for ch in (0,1)]
    if arrivals['left'][1]!=arrivals['right'][0]:raise ValueError('Cross arrivals disagree')
    left,right=arrivals['left'][0],arrivals['right'][1]
    matches=[p for p in itertools.permutations(right) if sorted(a+b for a,b in zip(left,p))==arrivals['left'][1]]
    if len(matches)!=1:raise ValueError('Comb pairing is not unique')
    delays=np.column_stack([left,matches[0]])
    nfft=1048576;bins=np.arange(64,nfft//2,32);hz=bins*48000/nfft;bins=bins[(hz>=60)&(hz<18000)]
    z=np.exp(-2j*np.pi*bins/nfft)
    diffusers=np.column_stack([allpass(z,ch) for ch in (0,1)])
    observed={}
    for side,(_,audio,x,_) in records.items():
        h=residual(audio,x,1)[48000:]/float(x[48000,0 if side=='left' else 1])
        observed[side]=np.fft.rfft(h,n=nfft,axis=0)[bins]
    cross_error=float(np.linalg.norm(observed['left'][:,1]*diffusers[:,0]-observed['right'][:,0]*diffusers[:,1])/np.linalg.norm(observed['left'][:,1]))
    if cross_error>2e-6:raise ValueError('Shared diffuser/symmetric network hypothesis fails')
    target=observed['left']/diffusers
    pole=(1-np.tan(np.pi*25/48000))/(1+np.tan(np.pi*25/48000))
    hp=(1+pole)/2*(1-z)/(1-pole*z)
    zl=z[:,None]**delays[:,0];period=z[:,None]**delays.sum(axis=1)
    initial=-3*np.log(10)/(48000*(1+49*(125/252)**3))*np.r_[delays[:,0],delays.sum(axis=1)]
    def network(parameters,filtered):
        gl,loop=np.exp(parameters[:5]),np.exp(parameters[5:])
        f=hp[:,None] if filtered else 1
        denominator=1-loop*period*f*f
        return np.column_stack([np.sum(gl*zl/denominator,axis=1),np.sum(loop*period*f/denominator,axis=1)])
    scale=np.linalg.norm(target[:,0]*network(initial,True)[:,1])
    def objective(parameters,filtered=True):
        m=network(parameters,filtered);error=(target[:,1]*m[:,0]-target[:,0]*m[:,1])/scale
        return np.r_[error.real,error.imag]
    fitted=refine(objective,initial)
    rejected=refine(lambda p:objective(p,False),initial)
    ratio_error=float(np.linalg.norm(objective(fitted)))
    if ratio_error>1e-4:raise ValueError('Filtered feedback topology misses fitting screen')
    gl=np.exp(fitted[:5]);gr=np.exp(fitted[5:]-fitted[:5])
    if np.any(gl>=1) or np.any(gr>=1) or np.any(gr<=0):raise ValueError('Unstable scalar feedback')
    network_only=network(fitted,True)*diffusers*(biquad(z,54,True)*biquad(z,17330,False))[:,None]
    y=observed['left']
    design=np.column_stack([(y*z[:,None]).ravel(),(y*z[:,None]**2).ravel(),(-(1-z[:,None]**2)*network_only).ravel()])
    values=np.linalg.lstsq(np.r_[design.real,design.imag],np.r_[-y.real.ravel(),-y.imag.ravel()],rcond=1e-12)[0]
    a1,a2,gain=map(float,values)
    if np.any(abs(np.roots([1,a1,a2]))>=1) or gain<=0:raise ValueError('Unstable/negative input bandpass')
    prediction=network_only*(gain*(1-z*z)/(1+a1*z+a2*z*z))[:,None]
    frequency_error=float(np.linalg.norm(prediction-y)/np.linalg.norm(y))
    if frequency_error>1e-4:raise ValueError('Combined network/input/output filter fit fails')
    text='// Own I/O identification. Static factory Up Main128/Sub1-128/48 kHz only.\n#pragma once\n#include <array>\n'
    text+='constexpr std::array<std::array<int,2>,5> reverbUpDelays{{'+','.join('{{'+','.join(map(str,p))+'}}' for p in delays.tolist())+'}};\n'
    for label,data in [('GainL',gl),('GainR',gr),('InputA',[a1,a2])]:
        text+=f'constexpr std::array<double,{len(data)}> reverbUp{label}'+ '{'+','.join(format(float(v),'.17g') for v in data)+'};\n'
    text+='constexpr double reverbUpWetGain='+format(gain,'.17g')+';\n'
    args.header.parent.mkdir(parents=True,exist_ok=True)
    with args.header.open('x') as f:f.write(text)
    save_json(args.report,dict(kind='rmx220-reverb-up-neutral-network-identification',sample_rate=48000,reference_identity=IDENTITY,
        full_reverb_match=False,physical_hardware=False,calibration_sha256=sha256(args.calibration),header_sha256=sha256(args.header),
        script_sha256=sha256(Path(__file__)),created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sources={s:r[3] for s,r in records.items()},arrivals=arrivals,delays=delays.tolist(),gain_left=gl.tolist(),gain_right=gr.tolist(),
        input_filter=dict(numerator=[1,0,-1],denominator=[1,a1,a2]),wet_gain=gain,feedback_highpass_hz=25,
        fixed_output_lowpass_hz=17330,variable_output_highpass_endpoints_hz=[54,6310],allpass_delays=[[335,1091],[395,1031]],allpass_gain=.7,
        diffuser_cross_symmetry_relative_error=cross_error,feedback_stereo_ratio_relative_error=ratio_error,combined_frequency_relative_error=frequency_error,
        rejected_unfiltered_feedback_relative_error=float(np.linalg.norm(objective(rejected,False))),
        scope='Static factory Up, Main128/Sub1-128, 48 kHz/120 BPM. Feedback/input coefficients fitted only to left-source recording; right-source delays and diffuser symmetry inform topology.',
        limitations=['Original local binary/control-path inspection suggested Up-only input biquad and feedback high-pass; independent I/O fits determine this model.',
        'The Down inverse locates candidate arrivals only; full Up fitting and waveform checks are separate evidence.',
        'No Main/Sub1 map, motion/startup, other profiles/rates/tempos, overload, listening or hardware equivalence claim.']))
    print('Up network identified; frequency error',frequency_error,'unfiltered feedback rejection',float(np.linalg.norm(objective(rejected,False))))


def model_checked(args):
    calibration(args.calibration);model=json.loads(args.model.read_text())
    header=Path(__file__).resolve().parents[1]/'research/audio/experiments/ReverbUpNeutralCalibration.h'
    if model.get('kind')!='rmx220-reverb-up-neutral-network-identification' or model['header_sha256']!=sha256(header) or model['calibration_sha256']!=sha256(args.calibration):raise ValueError('Model/header/calibration differs')
    return model


def payload():
    waves,cases=recipe('holdout')
    return dict(kind='rmx220-reverb-up-neutral-predictions',cases=cases,source_sha256=source_hashes(),
        samples_sha256={s:hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for s,x in waves.items()})


def predict(args):
    model_checked(args)
    save_json(args.report,payload()|dict(model_path=str(args.model.resolve()),model_sha256=sha256(args.model),
        renderer_path=str(args.renderer.resolve()),renderer_sha256=sha256(args.renderer),calibration_sha256=sha256(args.calibration),
        expected='All eight complete whole/wet/tail per-channel screens <=1% with unchanged energy floor/silent-channel limit, reference offset32 and candidate offset0; no gain fitting or wet alignment search.'))


def capture(args):
    model_checked(args);prediction=json.loads(args.prediction.read_text())
    if any(prediction.get(k)!=v for k,v in payload().items()) or prediction['model_sha256']!=sha256(args.model) or prediction['calibration_sha256']!=sha256(args.calibration) or sha256(Path(prediction['renderer_path']))!=prediction['renderer_sha256']:raise ValueError('Frozen prediction differs')
    root=new_directory(args.session);(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):raise ValueError('Requires original RMX-1000 2.2.0')
    waves,cases=recipe('holdout')
    for name,x in waves.items():write_wav(root/(name+'.wav'),48000,x.ravel())
    for c in cases:
        settings=[]
        for name,value in controls(c).items():
            matches=[p for p in inventory['parameters'] if p['name']==name]
            if len(matches)!=1:raise ValueError('Missing/ambiguous original parameter '+name)
            settings.append({k:matches[0][k] for k in ('index','id','name')}|dict(value=value))
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,
            sample_rate=48000,bpm=120,tail_seconds=c['tail'],parameters=settings,events=[])
        save_json(root/(c['name']+'.json'),plan)
        run([args.host,'render',args.plugin,root/(c['source']+'.wav'),root/(c['name']+'.json'),root/c['name'],128])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print(c['name'],flush=True)
    save_json(root/'matrix.json',dict(kind='rmx220-reverb-up-neutral-holdout-captures',cases=cases,prediction_sha256=sha256(args.prediction)))


def compare(args):
    model_checked(args);root=new_directory(args.output);rows=[]
    for stage,directory in args.session:
        waves,cases=recipe(stage)
        for c in cases:
            _,a,x,provenance=checked(directory,c,waves[c['source']]);output=root/(stage+'-'+c['name']+'.wav')
            run([args.renderer,Path(json.loads((directory/c['name']/'receipt.json').read_text())['input_path']),output,c['cutoff'],c['tail']])
            rate,b=float_wav(output)
            if rate!=48000 or len(b)!=len(a)+32:raise ValueError('Candidate extent/rate differs')
            b=b[:len(a)].astype(float);dry=np.zeros_like(a);dry[:min(len(dry),len(x))]=x[:len(dry)]
            row=provenance|dict(stage=stage,candidate_sha256=sha256(output),whole=screen(a,b),wet=screen(a-dry,b-dry),post_input_tail=screen(a[len(x):],b[len(x):]))
            row['passed']=all(row[k]['passed'] for k in ('whole','wet','post_input_tail'));rows.append(row)
            print('PASS' if row['passed'] else 'FAIL',stage,c['name'],flush=True)
    if not rows:raise ValueError('No Up cases')
    passed=all(r['passed'] for r in rows)
    save_json(root/'comparison.json',dict(kind='rmx220-reverb-up-neutral-autonomous-comparison',passed=passed,full_reverb_match=False,physical_hardware=False,
        model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),renderer_sha256=sha256(args.renderer),source_sha256=source_hashes(),cases=rows,
        acceptance=dict(relative_rms_limit=.01,silent_channel_absolute_rms_limit=1e-8,reference_channel_energy_floor=1e-20,reference_offset_frames=32,candidate_offset_frames=0,gain_fit=False,wet_alignment_search=False),
        scope='Static factory Up Main128/Sub1-128/48 kHz/120 BPM. Initial left/right impulses inform identification; other eligible cases are regressions, and a frozen holdout is independent.',
        limitations=['The candidate generates the complete room independently; only input WAV and declared static controls are supplied.',
        'Duplicate baselines and silence are included in case counts. No Main/Sub1 map, motion/startup, other profiles/rates/tempos, production integration, overload, listening or hardware claim.']))
    return 0 if passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
    q=commands.add_parser('identify')
    for name in ('initial','calibration','report','header'):q.add_argument('--'+name,type=Path,required=True)
    for command in ('predict','capture','compare'):
        q=commands.add_parser(command)
        for name in ('model','calibration'):q.add_argument('--'+name,type=Path,required=True)
        if command in ('predict','compare'):q.add_argument('--renderer',type=Path,required=True)
        if command=='predict':q.add_argument('--report',type=Path,required=True)
        if command=='capture':
            for name in ('host','plugin','prediction','session'):q.add_argument('--'+name,type=Path,required=True)
        if command=='compare':
            q.add_argument('--session',nargs=2,action='append',required=True,metavar=('STAGE','DIRECTORY'))
            q.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.command=='compare':args.session=[(s,Path(d)) for s,d in args.session]
    result=globals()[args.command](args)
    if result is not None:raise SystemExit(result)


if __name__=='__main__':main()
