#!/usr/bin/env python3
"""Predict button-gate impulse scaling from a fixed 160-sample fade."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_filter_match import screen
from tools.rmx_reverb_motion import checked, recipe
from tools.rmx_spiral_core import calibration


def analyze(args):
    calibration(args.calibration)
    manifest=json.loads((args.session/'matrix.json').read_text())
    if manifest['calibration_sha256']!=sha256(args.calibration):
        raise ValueError('Button probes use a different calibration')
    waves,cases=recipe('button-probes')
    records={}
    rows=[]
    event=192037
    boundary=(event+31)//32*32
    for case in cases:
        audio,source,provenance=checked(args.session,case,waves[case['source']])
        pulse=int(np.flatnonzero(np.any(source!=0,axis=1))[0])
        dry=np.zeros_like(audio)
        dry[32:32+len(source)]=source
        wet=audio-dry
        if case['baseline']:
            baseline=records[case['baseline']]
            turning_on='gate-on-' in case['name']
            gain=np.float32(0 if turning_on else 1)
            step=np.float32(1/160)*(1 if turning_on else -1)
            for _ in range(max(0,pulse-boundary+1)):
                gain=np.float32(np.clip(gain+step,0,1))
            predicted=baseline*float(gain)
            result=screen(wet,predicted)
            first=pulse+32+1033
            observed=float(wet[first,0]/baseline[first,0])
            rows.append(provenance|dict(pulse_input_frame=pulse,control_boundary_frame=boundary,
                predicted_gate_gain=float(gain),observed_first_arrival_ratio=observed,
                absolute_gain_error=abs(observed-float(gain)),whole_wet_prediction=result,
                expected_silent_wet=bool(gain==0)))
        else:
            records[case['name']]=wet
    passed=all(r['whole_wet_prediction']['passed'] and r['absolute_gain_error']<=2e-6 for r in rows)
    save_json(args.report,dict(kind='rmx220-reverb-down-button-gate-component-prediction',passed=passed,
        calibration_sha256=sha256(args.calibration),identifier_sha256=sha256(Path(__file__)),
        reference_offset_frames=32,gate_fade_samples=160,gate_gain_tolerance=2e-6,gain_fit=False,
        capture_cases=18,predicted_motion_cases=12,expected_silent_motion_cases=sum(r['expected_silent_wet'] for r in rows),
        cases=rows,full_reverb_match=False,physical_hardware=False,
        limitations=['Original impulse baselines are scaled by the predicted gate value to check this component.',
            'This component check does not replace autonomous candidate waveform validation.',
            'Only neutral Main/Sub1/Sub2 and active-before-toggle gate probes enter this record.']))
    print('PASS' if passed else 'FAIL','12 fixed-gate predictions from 18 verified original probes')
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('session','calibration','report'):
        parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(analyze(parser.parse_args()))


if __name__=='__main__':
    main()
