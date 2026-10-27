#!/usr/bin/env python3
"""Test corrected Up feedback arithmetic with new prediction-bound impulse captures."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_reverb_characterize import checked,controls
from tools.rmx_reverb_controls import nominal_decay
from tools.rmx_reverb_up_controls import neutral_checked,setup,fit_case,recipe as sweep_recipe


def refine_reference(args):
    neutral=neutral_checked(args.neutral,args.calibration);observation=json.loads(args.observation.read_text())
    if observation.get('kind')!='rmx220-reverb-up-feedback-arithmetic-observation' or not observation['debugger_audio_byte_identical']:raise ValueError('Requires verified read-only coefficient observation')
    feedback=observation['feedback_filter']
    if feedback['b'][0]!=-feedback['b'][1] or not 0<feedback['b'][0]<1 or not -1<feedback['a'][1]<0:raise ValueError('Invalid observed high-pass')
    x,cases=sweep_recipe('main');c=cases[128];_,audio,source,provenance=checked(args.session,c,x)
    detector,frequency=setup(feedback);result=fit_case(audio,source,c,neutral,detector,frequency)
    if not result['stable'] or result['damped_frequency_relative_error']>1e-4:raise ValueError('Revised reference fitting failed')
    save_json(args.report,dict(kind='rmx220-reverb-up-control-reference',calibration_sha256=sha256(args.calibration),
        neutral_model_sha256=sha256(args.neutral),coefficient_observation_sha256=sha256(args.observation),feedback_filter=feedback,
        source=provenance,delays=result['delays'],gain_left=result['gain_left'],gain_right=result['gain_right'],
        input_filter=dict(numerator=[1,0,-1],denominator=result['input_a']),wet_gain=result['wet_gain'],
        damped_frequency_relative_error=result['damped_frequency_relative_error'],script_sha256=sha256(Path(__file__)),
        scope='Refit of the Main128/Sub1-128 calibration only with observed feedback coefficients. This reference is not a new prospective waveform pass.'))


def recipe():
    x=np.zeros((120000,2));x[72013,0]=-.019
    cases=[dict(name=f'up-feedback-{raw}',source='source',direction='up',main=128,amount=raw,cutoff=0,tail=3,impulse_frame=72013) for raw in (0,5,31,83,131,179,227,253)]
    return x,cases


def payload(reference):
    x,cases=recipe();repo=Path(__file__).resolve().parents[1]
    files=[Path(__file__),repo/'tools/rmx_reverb_up_controls.py',repo/'tools/rmx_reverb_controls.py',repo/'tools/rmx_reverb_characterize.py',repo/'tools/rmx_reverb_network.py']
    predictions=[dict(case=c['name'],left=[g**(nominal_decay(128)/nominal_decay(c['amount'])) for g in reference['gain_left']],right=[g**(nominal_decay(128)/nominal_decay(c['amount'])) for g in reference['gain_right']]) for c in cases]
    return dict(kind='rmx220-reverb-up-feedback-arithmetic-predictions',cases=cases,predictions=predictions,
        source_sha256={str(p.relative_to(repo)):sha256(p) for p in files},samples_sha256=hashlib.sha256(x.astype('<f4').tobytes()).hexdigest(),
        maximum_absolute_gain_error=2e-6,reference_sha256=sha256(Path(reference['_path'])))


def reference_checked(args):
    r=neutral_checked(args.reference,args.calibration)
    if r['kind']!='rmx220-reverb-up-control-reference':raise ValueError('Requires revised control reference')
    r['_path']=str(args.reference);return r


def predict(args):
    r=reference_checked(args)
    save_json(args.report,payload(r)|dict(reference_path=str(args.reference.resolve()),calibration_sha256=sha256(args.calibration),
        expected='All eight fresh signed/shifted impulse captures fit the corrected static network and every saved feedback-gain forecast meets the unchanged absolute 2e-6 limit.'))


def bound(args):
    r=reference_checked(args);prediction=json.loads(args.prediction.read_text())
    if any(prediction.get(k)!=v for k,v in payload(r).items()) or prediction['calibration_sha256']!=sha256(args.calibration):raise ValueError('Frozen feedback prediction differs')
    return r,prediction


def capture(args):
    _,prediction=bound(args);root=new_directory(args.session);(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):raise ValueError('Requires original RMX-1000 2.2.0')
    x,cases=recipe();write_wav(root/'source.wav',48000,x.ravel())
    for c in cases:
        settings=[]
        for name,value in controls(c).items():
            match=[p for p in inventory['parameters'] if p['name']==name]
            if len(match)!=1:raise ValueError('Ambiguous/missing original parameter '+name)
            settings.append({k:match[0][k] for k in ('index','id','name')}|dict(value=value))
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,sample_rate=48000,bpm=120,tail_seconds=c['tail'],parameters=settings,events=[])
        save_json(root/(c['name']+'.json'),plan);run([args.host,'render',args.plugin,root/'source.wav',root/(c['name']+'.json'),root/c['name'],128])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print(c['name'],flush=True)
    bound(args)
    save_json(root/'matrix.json',dict(kind='rmx220-reverb-up-feedback-arithmetic-captures',cases=cases,prediction_sha256=sha256(args.prediction)))


def validate(args):
    r,prediction=bound(args);manifest=json.loads((args.session/'matrix.json').read_text())
    if manifest['prediction_sha256']!=sha256(args.prediction) or sha256(args.session/'predictions.json')!=sha256(args.prediction):raise ValueError('Fresh session prediction differs')
    x,cases=recipe();detector,frequency=setup(r['feedback_filter']);rows=[]
    for c,forecast in zip(cases,prediction['predictions']):
        _,audio,source,provenance=checked(args.session,c,x);folder=args.session/c['name'];receipt=json.loads((folder/'receipt.json').read_text())
        plan=json.loads((folder/'plan.json').read_text());log=json.loads((folder/'parameter-log.json').read_text())['entries']
        for filename,field in [('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
            if sha256(folder/filename)!=receipt[field]:raise ValueError('Modified auxiliary capture')
        if len(log)!=len(plan['parameters']):raise ValueError('Unexpected parameter events')
        for requested,actual in zip(plan['parameters'],log):
            if actual['frame']!=-1 or any(actual[k]!=requested[k] for k in ('index','id','name')) or abs(actual['immediate_readback']-float(np.float32(requested['value'])))>1e-14:raise ValueError('Immediate readback differs')
        final={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
        if any(abs(final[p['name']]-float(np.float32(p['value'])))>1e-14 for p in plan['parameters']):raise ValueError('Final readback differs')
        result=fit_case(audio,source,c,r,detector,frequency);error=float(max(abs(np.array(result['gain_left'])-forecast['left']).max(),abs(np.array(result['gain_right'])-forecast['right']).max()))
        passed=result['stable'] and result['damped_frequency_relative_error']<=1e-4 and error<=prediction['maximum_absolute_gain_error']
        rows.append(provenance|dict(amount=c['amount'],fitted=result,maximum_absolute_gain_error=error,passed=passed,readbacks_verified=True));print('PASS' if passed else 'FAIL',c['name'],error,flush=True)
    passed=all(c['passed'] for c in rows)
    save_json(args.report,dict(kind='rmx220-reverb-up-feedback-arithmetic-validation',passed=passed,reference_sha256=sha256(args.reference),
        prediction_sha256=sha256(args.prediction),calibration_sha256=sha256(args.calibration),script_sha256=sha256(Path(__file__)),cases=rows,
        fixed_gain_error_limit=2e-6,scope='Eight new signed/shifted impulse captures after revised reference/prediction freeze. Coefficient-law validation only; independent full mixed-program waveform validation remains required.'))
    return 0 if passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
    q=commands.add_parser('refine-reference')
    for name in ('neutral','observation','calibration','session','report'):q.add_argument('--'+name,type=Path,required=True)
    for command in ('predict','capture','validate'):
        q=commands.add_parser(command)
        for name in ('reference','calibration'):q.add_argument('--'+name,type=Path,required=True)
        if command in ('predict','validate'):q.add_argument('--report',type=Path,required=True)
        if command in ('capture','validate'):q.add_argument('--session',type=Path,required=True);q.add_argument('--prediction',type=Path,required=True)
        if command=='capture':q.add_argument('--host',type=Path,required=True);q.add_argument('--plugin',type=Path,required=True)
    args=p.parse_args();result={'refine-reference':refine_reference,'predict':predict,'capture':capture,'validate':validate}[args.command](args)
    if result is not None:raise SystemExit(result)


if __name__=='__main__':main()
