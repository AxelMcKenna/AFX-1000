"""Replay private scalar observations without retaining audio or vendor code."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_drums import require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scalars', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--modulation', action='store_true', help='Audit five discovery observations; this does not qualify modulation audio')
    parser.add_argument('--gain', action='store_true', help='Audit three high-main gain observations')
    args = parser.parse_args()
    require(not (args.modulation and args.gain), 'Choose one observation group')
    verification = json.loads((args.scalars/'verification.json').read_text())
    require(verification['passed'] and not verification['raw_audio_retained'] and len(verification['cases']) == (5 if args.modulation else 3 if args.gain else 9), 'Incomplete observation campaign')
    rows = []
    for row in verification['cases']:
        case = row['case']; path = args.scalars/(case['name']+'.json')
        require(sha256(path) == row['scalars_sha256'], 'Scalar observation changed')
        record = json.loads(path.read_text())
        require(record['binary_sha256'] == 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced', 'Wrong Original')
        require(record['main'] == case['main'] and (args.gain or case['main'] == 147) and record['sub2'] == case['sub2']
                and record['smoothed_sub2'] == max(0, case['sub2']-3)
                and record['amount'] == case['amount'] and record['customization']['width'] == [1,0,2][case['width']]
                and record['customization']['wave'] == case.get('wave',0)
                and record['customization']['mode'] == (0 if args.modulation else 1) and record['customization']['resonance'] == case['resonance']
                and (args.modulation or record['lfo_edges'] == [0, 0]), 'Unexpected reference controls')
        errors = dict(biquad=0., base_feedback=0., feedback=0.)
        positions = []
        for channel, lfo in enumerate(record['lfo_edges']):
            position = min(255, max(0, record['smoothed_main']+int(np.float32(np.float32(1)-np.float32(lfo))*np.float32(50))))
            positions.append(position)
            ratio, step, base, frequency_step = record['sweep']
            spread = ratio*(step**(position-234) if position >= 234 else 1)
            low = base*frequency_step**(position-4)
            high = low*(spread+.5)/(spread-.5)
            a, b = [math.tan(math.pi*edge/48000) for edge in [low, high]]
            delta, product = b-a, a*b
            inverse = 1/(1+delta+product)
            coefficients = np.asarray([delta*inverse, 0, -delta*inverse, (2*product-2)*inverse, (1-delta+product)*inverse], dtype=np.float32)
            travel = np.float32((position-3)*np.float32(1/252))
            for _ in range(4): travel = np.float32(travel*travel)
            base_feedback = np.float32(.7) if args.modulation else np.float32(np.float32(max(0, case['sub2']-3)*np.float32(1/252))*np.float32([.7, .5, 0][case['resonance']]))
            feedback = np.float32(base_feedback+np.float32(travel*np.float32(.1)))
            errors['biquad'] = max(errors['biquad'], float(np.max(np.abs(coefficients-np.asarray(record['biquads'][channel*5:channel*5+5])))))
            errors['base_feedback'] = max(errors['base_feedback'], abs(float(base_feedback)-record['base_feedback']))
            errors['feedback'] = max(errors['feedback'], abs(float(feedback)-record['feedback'][channel]))
        require(all(error == 0 for error in errors.values()), 'Reconstructed scalar law differs')
        if args.gain:
            base = np.float32(1)+np.float32((case['main']-101)*np.float32(-.00194805197))
            power = base
            for _ in range(7): power = np.float32(power*base)
            target = np.float32(np.float32((case['main']-3)*np.float32(.0055210432))*power)
            errors['main_level'] = max(abs(float(target)-v) for v in record['main_level_targets'])
            require(errors['main_level'] == 0, 'Reconstructed main level differs')
        require(set(row['unchanged_audio_and_auxiliary_sha256']) == {'audio.wav','plan.json','state-before.bin','state-after.bin','parameter-log.json','inventory-after.json'}, 'Missing observation invariance evidence')
        rows.append(dict(case=case, effective_positions=positions, lfo_period=record['lfo_period'], lfo_depth=record['lfo_depth'], lfo_edges=record['lfo_edges'], maximum_absolute_errors=errors, scalar_sha256=sha256(path),
                         observed_and_ordinary_hashes=row['unchanged_audio_and_auxiliary_sha256'], original_receipt_sha256=row['original_receipt_sha256']))
    save_json(args.output, dict(kind='noise-modulation-scalar-discovery' if args.modulation else 'noise-main-level-scalar-replay' if args.gain else 'noise-resonance-scalar-replay', passed=True, cases=rows,
        verification_sha256=sha256(args.scalars/'verification.json'),
        observer_sha256={name:sha256(Path(__file__).with_name(name)) for name in ['noise_coefficients_observer.py','noise_advanced_observer.py']+(['noise_gain_observer.py'] if args.gain else [])},
        auditor_sha256=sha256(Path(__file__)), raw_audio_retained=False,
        scope=('Five modulation waves at main147/Sub2=128; cutoff destination discovery only. No modulation waveform, phase, envelope or audio qualification.' if args.modulation else 'Three high-main level targets and filter/feedback records; no transient or waveform-fidelity claim.' if args.gain else 'Nine steady Original control records at main147, three resonance characters and Sub2=0/128/255. No transient or waveform-fidelity claim.')+' Independent scalar arithmetic; observed/ordinary audio and five auxiliary hashes agree.'))


if __name__ == '__main__': main()
