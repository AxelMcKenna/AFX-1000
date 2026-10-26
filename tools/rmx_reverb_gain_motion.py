#!/usr/bin/env python3
"""Diagnostic Sub1 feedback/return-gain separation. Fitted gains are not acceptance."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import new_directory, run
from tools.rmx_reverb_motion import checked, recipe
from tools.rmx_spiral_core import calibration


def analyze(args):
    calibration(args.calibration)
    model=json.loads(args.model.read_text())
    header=Path(__file__).resolve().parents[1]/'research/audio/experiments/ReverbDownControlCalibration.h'
    if (model['kind']!='rmx220-reverb-down-static-control-model'
            or model['header_sha256']!=sha256(header)
            or model['calibration_sha256']!=sha256(args.calibration)):
        raise ValueError('Static model/header/calibration differs')
    root=new_directory(args.output)
    waves,cases=recipe('steps')
    rows=[]
    for c in cases:
        if not c['name'].startswith('down-step-amount-'):
            continue
        audio,source,provenance=checked(args.session,c,waves[c['source']])
        receipt=json.loads((args.session/c['name']/'receipt.json').read_text())
        schedule=root/(c['name']+'.tsv')
        schedule.write_text('RMX_REVERB_MOTION 1\n'+f'initial 128 {c["amount"]} 0 1\n'
            +f'tail {c["tail"]}\n'+''.join(f'event {e["frame"]} amount {e["value"]}\n' for e in c['events']))
        start=(c['events'][0]['frame']+31)//32*32
        end=start+192000
        if len(audio)<end:
            raise ValueError('Insufficient post-event extent')
        dry=np.zeros_like(audio)
        dry[32:32+len(source)]=source
        observed=audio[start:end]-dry[start:end]
        raw=np.arange(start,end)
        progress=(raw-start)//32+1
        initial,target=c['amount'],c['events'][0]['value']
        amount=initial+np.sign(target-initial)*np.minimum(progress,abs(target-initial))
        gain=model['main_rows'][128]['wet_gain']*np.asarray(model['amount_gains'])[amount]/model['amount_gains'][128]
        gain*=1+model['main_correction'][128]*np.asarray(model['amount_correction'])[amount]
        for step in args.decay_step:
            prefix=c['name']+'-'+str(step)
            output,trace=root/(prefix+'.wav'),root/(prefix+'-dry.wav')
            run([args.renderer,receipt['input_path'],output,schedule,'inlet','post',args.feedback_position,32,trace,
                 'output',0,'levels',step])
            candidate=float_wav(output)[1].astype(float)
            direct=float_wav(trace)[1].astype(float)
            if len(candidate)!=len(audio) or not np.array_equal(direct,dry.astype(np.float32)):
                raise ValueError('Candidate extent/direct contribution differs')
            unit=(candidate[start:end]-direct[start:end])/gain[:,None]
            u,y=unit.reshape(-1,32,2),observed.reshape(-1,32,2)
            energy=np.sum(u*u,axis=(1,2))
            fitted=np.sum(u*y,axis=(1,2))/np.maximum(energy,1e-30)
            residual=y-u*fitted[:,None,None]
            error=np.sqrt(np.sum(residual*residual,axis=(0,1))/np.sum(y*y,axis=(0,1)))
            samples=[]
            for seconds in (0,.1,.25,.5,.75,1,1.25,1.5,1.75,2,2.5,3,3.5):
                idx=round(seconds*1500)
                samples.append(dict(after_boundary_seconds=seconds,fitted_gain=float(fitted[idx])))
            array=root/(prefix+'-diagnostic.npz')
            np.savez_compressed(array,frame=start+np.arange(len(fitted))*32,fitted_gain=fitted,
                                shape_error_energy=np.sum(residual*residual,axis=(1,2)),reference_energy=np.sum(y*y,axis=(1,2)))
            rows.append(provenance|dict(decay_step_per_32_frames=step,feedback_position=args.feedback_position,
                diagnostic_shape_relative_rms_error=error.tolist(),gain_samples=samples,
                negative_fitted_gain_blocks=int(np.sum(fitted<0)),unit_renderer_output_sha256=sha256(output),
                dry_trace_sha256=sha256(trace),diagnostic_arrays_sha256=sha256(array)))
            print(c['name'],step,'diagnostic shape',error,flush=True)
    save_json(root/'diagnostic.json',dict(kind='rmx220-reverb-down-feedback-gain-motion-diagnostic',cases=rows,
        model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),renderer_sha256=sha256(args.renderer),
        identifier_sha256=sha256(Path(__file__)),full_reverb_match=False,physical_hardware=False,
        acceptance_pass=False,gain_fit=True,gain_fit_frames=32,reference_offset_frames=32,candidate_offset_frames=32,
        limitations=['Fitted return gain diagnoses state error; it cannot be used as a waveform-acceptance result.',
            'Observed dry is fixed independently by Main128 and enabled button, without a dry gain fit.',
            'Only nominal decay slew and read/write placement are varied; source filters and delay realization remain hypotheses.']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('session','model','calibration','renderer','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--decay-step',type=float,action='append',required=True)
    p.add_argument('--feedback-position',choices=('read','write'),default='read')
    analyze(p.parse_args())


if __name__=='__main__':
    main()
