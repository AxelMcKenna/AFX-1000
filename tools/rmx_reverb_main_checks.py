#!/usr/bin/env python3
"""Check Main geometry against measured static data and frozen-candidate guards."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.noise_statistics import float_wav
from tools.rmx_factory_match import new_directory, run
from tools.rmx_reverb_motion import capture


def check(args):
    root=new_directory(args.output)
    model=json.loads(args.model.read_text())
    prediction=json.loads(args.prediction.read_text())
    f=np.float32
    raw=np.arange(4,256,dtype=np.float32)
    p=((raw-f(3))*f(1/252))*f(99)+f(1)
    q=p*f(.02306)+f(1.01)
    scale=(q*q)*f(.171)+f(.2)
    bases=np.array([[1032,1146],[1060,1856],[1145,1961],[1916,1115],[1992,1190]],dtype=np.float32)
    predicted=(scale[:,None,None]*bases).astype(int)
    measured=np.array([row['delays'] for row in model['main_rows'][4:]])
    if not np.array_equal(predicted,measured):
        raise ValueError('Nominal room expression misses measured integer delays')
    # A neighboring one-frame change must fail this independent static oracle.
    changed=predicted.copy();changed[143-4,1,0]+=1
    if np.array_equal(changed,measured):
        raise ValueError('One-frame geometry negative control is inconclusive')

    rejected=[]
    for field in ('kind','cases','source_files_sha256','model_sha256','renderer_sha256','calibration_sha256','candidate_config'):
        bad=copy.deepcopy(prediction)
        if field=='cases':bad[field][0]['main']+=1
        elif field=='source_files_sha256':bad[field][next(iter(bad[field]))]='0'*64
        elif field=='candidate_config':bad[field]['control_quantum']=1
        else:bad[field]='modified'
        path=root/(field+'.json');save_json(path,bad)
        try:
            capture(argparse.Namespace(stage=prediction['stage'],session=root/('forbidden-'+field),
                prediction=path,calibration=args.calibration))
        except ValueError as error:
            if 'Prediction recipe/model/source/renderer/calibration differs' not in str(error):raise
            if (root/('forbidden-'+field)).exists():raise ValueError('Rejected capture created session')
            rejected.append(field)
        else:raise ValueError('Modified prediction accepted: '+field)

    native=[]
    variants=[dict(quantum=1),dict(quantum=128),dict(ramp=160),dict(decay=.05),
              dict(gate='inlet'),dict(position='pre'),dict(gain='write'),dict(level='send')]
    for i,variant in enumerate(variants):
        v=dict(quantum=32,ramp=0,decay=0,gate='faded',position='post',gain='read',level='output')|variant
        output,dry=root/f'invalid-{i}.wav',root/f'invalid-{i}-dry.wav'
        try:
            run([args.renderer,args.bypass/'bypass-input.wav',output,args.bypass/'bypass.tsv',v['gate'],
                 v['position'],v['gain'],v['quantum'],dry,v['level'],v['ramp'],'adaptive',v['decay']])
        except RuntimeError:
            if output.exists() or dry.exists():raise ValueError('Rejected mode wrote audio')
            native.append(variant)
        else:raise ValueError('Invalid native mode accepted')

    old=json.loads(args.previous.read_text())
    current=[json.loads(p.read_text()) for p in args.comparison]
    cases={row['case']:row for report in current for row in report['cases']}
    if any(row['passed'] and not cases[row['case']]['passed'] for row in old['cases']):
        raise ValueError('A previously passing case regressed')
    timing=None
    if args.pre_activation_session is not None:
        name='down-main-holdout-7'
        folder=args.pre_activation_session/name
        receipt=json.loads((folder/'receipt.json').read_text())
        original=float_wav(folder/'audio.wav')[1]
        source=float_wav(Path(receipt['input_path']))[1]
        if sha256(folder/'audio.wav')!=receipt['output_sha256'] or sha256(Path(receipt['input_path']))!=receipt['input_sha256']:
            raise ValueError('Modified pre-activation timing fixture')
        start,stop=24000,26000
        direct=source[start:stop]
        fixed=np.array_equal(original[start+32:stop+32],direct)
        diagnostic=np.array_equal(original[start+31:stop+31],direct)
        if fixed or not diagnostic or cases[name]['passed']:
            raise ValueError('Pre-activation timing diagnostic differs from frozen failure')
        timing=dict(case=name,input_frames=[start,stop],receipt_sha256=sha256(folder/'receipt.json'),
            original_audio_sha256=sha256(folder/'audio.wav'),declared_32_frame_bypass_bit_exact=False,
            diagnostic_31_frame_direct_input_bit_exact=True,acceptance_offset_unchanged=32,
            waveform_case_passed=False,
            scope='Direct-input timing diagnostic before first activation, not wet alignment or waveform acceptance.')
    save_json(root/'verification.json',dict(kind='rmx220-reverb-down-main-checks',passed=True,
        script_sha256=sha256(Path(__file__)),model_sha256=sha256(args.model),prediction_sha256=sha256(args.prediction),
        comparison_sha256=[sha256(p) for p in args.comparison],previous_comparison_sha256=sha256(args.previous),
        static_geometry=dict(raw_main=[4,255],compared_delays=int(measured.size),all_integer_delays_equal=True,
            arithmetic='float32 unfused',one_frame_negative_control_rejected=True,
            inactive_raw_0_to_3_observable=False),rejected_prediction_changes=rejected,
        rejected_native_options=native,no_prior_pass_lost=True,pre_activation_timing_diagnostic=timing,
        counts=dict(total=len(cases),passed=sum(row['passed'] for row in cases.values()),
                    failed=sum(not row['passed'] for row in cases.values())),
        scope='Geometry and binding/option guards. Passing these does not override waveform failures.'))
    print('Verified 2520 static delays, seven prediction guards, eight native guards and no lost pass')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','prediction','calibration','renderer','bypass','previous','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--comparison',type=Path,action='append',required=True)
    p.add_argument('--pre-activation-session',type=Path)
    check(p.parse_args())


if __name__=='__main__':
    main()
