#!/usr/bin/env python3
"""Assemble and validate static raw-control Reverb Down research maps."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked, controls, recipe as initial_recipe, residual
from tools.rmx_reverb_controls import recipe as control_recipe
from tools.rmx_reverb_network import holdout_recipe
from tools.rmx_spiral_core import calibration


def delay_curve_audit(cases):
    raw = (32,64,96,128,160,192,224,255)
    training = [c for c in cases if c['main_raw'] in raw]
    x = np.array([c['main_raw'] for c in training])
    y = np.array([np.ravel(c['nominal_delays']) for c in training])
    coefficients = np.polynomial.polynomial.polyfit(x,y,2)
    failures, tested = [], 0
    for c in cases:
        if c['silent_wet'] or c['main_raw'] in raw:
            continue
        predicted = np.floor(np.polynomial.polynomial.polyval(c['main_raw'],coefficients)).astype(int).reshape(5,2)
        actual = np.array(c['delays'])
        tested += 10
        if np.any(predicted != actual):
            failures.append(dict(main_raw=c['main_raw'],predicted=predicted.tolist(),measured=actual.tolist(),
                mismatching_taps=int(np.count_nonzero(predicted-actual))))
    return dict(training_raws=list(raw),coefficients_ascending=coefficients.tolist(),heldout_taps=tested,
        mismatching_taps=sum(c['mismatching_taps'] for c in failures),cases=failures,prospective=False,
        interpretation='A smooth nominal fit does not establish exact integer rounding; measured delay tables are retained.')


def build(args):
    if args.report.exists() or args.header.exists():
        raise ValueError('Report/header must be new')
    calibration(args.calibration)
    main, amount = [json.loads(p.read_text()) for p in (args.main, args.amount)]
    for data, stage in ((main, 'main'), (amount, 'amount')):
        if (data.get('kind') != 'rmx220-reverb-down-control-identification' or data['stage'] != stage
                or data['calibration_sha256'] != sha256(args.calibration)
                or not data['fitting_screen_passed'] or len(data['cases']) != 256):
            raise ValueError('Requires complete passing control identification')
    if not amount['prospective_predictions_passed']:
        raise ValueError('Saved Sub1 feedback-scaling predictions failed')
    if main['neutral_model_sha256'] != amount['neutral_model_sha256']:
        raise ValueError('Control sweeps used different frozen neutral models')
    if [c['main_raw'] for c in main['cases']] != list(range(256)):
        raise ValueError('Main rows are incomplete/unordered')
    if [c['amount_raw'] for c in amount['cases']] != list(range(256)):
        raise ValueError('Sub1 rows are incomplete/unordered')
    neutral = main['cases'][128]
    rows = []
    for case in main['cases']:
        row = {key: (neutral if case['silent_wet'] else case)[key]
               for key in ('delays', 'gain_left', 'gain_right')}
        row |= dict(wet_gain=0 if case['silent_wet'] else case['wet_gain'], dry_gain=case['dry_gain'])
        if (np.any(np.array(row['delays']) < 1) or np.any(np.array(row['delays']) > 48000)
                or np.any(np.array(row['gain_left']) <= 0) or np.any(np.array(row['gain_left']) >= 1)
                or np.any(np.array(row['gain_right']) <= 0) or np.any(np.array(row['gain_right']) >= 1)
                or not 0 <= row['dry_gain'] <= 1.000001 or row['wet_gain'] < 0):
            raise ValueError('Control row violates delay/gain bounds')
        rows.append(row)
    gains = [case['wet_gain'] for case in amount['cases']]
    if not np.isfinite(gains).all() or min(gains) <= 0:
        raise ValueError('Sub1 wet gains must be finite and positive')
    main_correction, amount_correction = [0.]*256, [0.]*256
    interaction_sources = None
    if bool(args.main_long) != bool(args.amount_large):
        raise ValueError('Both interaction sweeps are required together')
    if args.main_long:
        high_amount, large_room = [json.loads(p.read_text()) for p in (args.main_long, args.amount_large)]
        for data, stage in ((high_amount, 'main-long'), (large_room, 'amount-large')):
            if (data.get('kind') != 'rmx220-reverb-down-control-identification' or data['stage'] != stage
                    or data['calibration_sha256'] != sha256(args.calibration)
                    or not data['fitting_screen_passed'] or not data['prospective_predictions_passed']
                    or len(data['cases']) != 256):
                raise ValueError('Interaction identification is incomplete or failed')
        if [c['main_raw'] for c in high_amount['cases']] != list(range(256)):
            raise ValueError('Long-decay Main rows are incomplete/unordered')
        if [c['amount_raw'] for c in large_room['cases']] != list(range(256)):
            raise ValueError('Large-room Sub1 rows are incomplete/unordered')
        for raw, c in enumerate(high_amount['cases']):
            if rows[raw]['wet_gain'] > 0:
                main_correction[raw] = c['wet_gain']/rows[raw]['wet_gain']*gains[128]/gains[255]-1
        if abs(main_correction[255]) < .01:
            raise ValueError('Interaction normalization is not identifiable')
        for raw, c in enumerate(large_room['cases']):
            amount_correction[raw] = (c['wet_gain']/rows[255]['wet_gain']*gains[128]/gains[raw]-1)/main_correction[255]
        factors = 1+np.outer(main_correction, amount_correction)
        if not np.isfinite(factors).all() or factors.min() <= 0:
            raise ValueError('Interaction gives invalid wet levels')
        interaction_sources = dict(main_long_sha256=sha256(args.main_long), amount_large_sha256=sha256(args.amount_large))
    header = '// Own measured static Default Down maps, 48 kHz; gestures/rates/Up remain unproven.\n#pragma once\n#include <array>\n'
    header += 'struct ReverbDownControlRow { std::array<std::array<int,2>,5> delays; std::array<double,5> gainL,gainR; double wetGain,dryGain; };\n'
    header += 'constexpr std::array<ReverbDownControlRow,256> reverbDownControls{{\n'
    def numbers(values):
        return ','.join(format(float(v), '.17g') for v in values)
    for row in rows:
        ds = '{{'+','.join('{{'+','.join(map(str, pair))+'}}' for pair in row['delays'])+'}}'
        header += '{'+ds+',{{'+numbers(row['gain_left'])+'}},{{'+numbers(row['gain_right'])+'}},'
        header += numbers([row['wet_gain'], row['dry_gain']])+'},\n'
    header += '}};\nconstexpr std::array<double,256> reverbDownAmountGain{{'+numbers(gains)+'}};\n'
    header += 'constexpr std::array<double,256> reverbDownMainCorrection{{'+numbers(main_correction)+'}};\n'
    header += 'constexpr std::array<double,256> reverbDownAmountCorrection{{'+numbers(amount_correction)+'}};\n'
    args.header.parent.mkdir(parents=True, exist_ok=True)
    with args.header.open('x') as f:
        f.write(header)
    save_json(args.report, dict(kind='rmx220-reverb-down-static-control-model', sample_rate=48000,
        full_reverb_match=False, physical_hardware=False, main_rows=rows, amount_gains=gains,
        calibration_sha256=sha256(args.calibration), main_identification_sha256=sha256(args.main),
        amount_identification_sha256=sha256(args.amount), builder_sha256=sha256(Path(__file__)),
        header_sha256=sha256(args.header),
        quadratic_delay_audit=delay_curve_audit(main['cases']),
        interaction_rank=2 if interaction_sources else 1, interaction_sources=interaction_sources,
        main_correction=main_correction, amount_correction=amount_correction,
        proposed_wet_level_combination='main_wet_gain[Main] * amount_gain[Sub1] / amount_gain[128] * (1 + main_correction[Main] * amount_correction[Sub1])',
        proposed_feedback_combination='main_feedback_gain[Main] ** (nominal_decay(128) / nominal_decay(Sub1))',
        nominal_decay_formula='1 + 49 * (max(0, Sub1_raw - 3) / 252)^3',
        scope='Static integer raw controls 0..255, factory Down, 48 kHz and 120 BPM.',
        limitations=['Separate sweeps do not establish the proposed Main/Sub1 combination; fresh mixed cases are required.',
            'No moving controls, fractional raw settings, other rates/profiles, Up, listening or hardware equivalence claim.']))
    print('Built static control candidate; mixed-control validation remains required')


def mixed_recipe(variant='mixed'):
    if variant not in ('mixed', 'mixed-v2'):
        raise ValueError('Unknown mixed-control recipe')
    second = variant == 'mixed-v2'
    rng = np.random.default_rng(0x2F19E00 if second else 0xF19E00)
    x = np.zeros((384000, 2))
    t = np.arange(48000)/48000
    x[48000:144000] = rng.normal(0, .021, (96000, 2))
    f = (87,1421,173,4591) if second else (127,3517,191,6011)
    x[144000:192000] = .023*np.column_stack((np.sin(2*np.pi*f[0]*t)+np.sin(2*np.pi*f[1]*t),
                                            np.cos(2*np.pi*f[2]*t)+np.sin(2*np.pi*f[3]*t)))
    for index in range(8):
        start = 192000+index*12000
        u = np.arange(12000)/48000
        x[start:start+12000, 0] = .13*np.sin(2*np.pi*(51+5*index)*u)*np.exp(-u*31)
        x[start:start+12000, 1] = rng.normal(0, .034, 12000)*np.exp(-u*39)
    pulse = np.zeros((384000, 2))
    pulse[61913 if second else 57129, 0], pulse[251363 if second else 273161, 1] = .031, -.026
    if second:
        pairs = [(m, a) for m in (35,91,163,221) for a in (37,107,171,229)]
        pairs += [(0,0),(3,0),(4,3),(4,253),(7,4),(7,252),(143,229),(128,98),
                  (129,1),(129,254),(131,2),(131,5),(254,1),(254,2),(254,5),(254,254)]
    else:
        pairs = [(m, a) for m in (49,113,177,237) for a in (49,113,177,237)]
        pairs += [(0,255),(3,255),(4,0),(4,255),(8,3),(8,4),(127,96),(128,97),
                  (129,0),(129,255),(130,3),(130,4),(255,0),(255,3),(255,4),(255,255)]
    cases = []
    for source_index, source in enumerate(('probe', 'late')):
        for index, (main, amount) in enumerate(pairs):
            cutoff = ((61,139,223,251) if second else (0,77,173,241))[(index+source_index)%4]
            if second and main == 143:
                cutoff = 61
            cases.append(dict(name=f'down-{source}-main-{main}-amount-{amount}-cutoff-{cutoff}',
                source=source, direction='down', main=main, amount=amount, cutoff=cutoff,
                tail=90 if amount >= 177 else 18))
    return {'probe':x, 'late':pulse}, cases


def model_checked(path, calibration_path):
    model = json.loads(path.read_text())
    if (model.get('kind') != 'rmx220-reverb-down-static-control-model'
            or model['calibration_sha256'] != sha256(calibration_path)):
        raise ValueError('Wrong static-control model/calibration')
    return model


def capture(args):
    calibration(args.calibration)
    model_checked(args.model, args.calibration)
    model_hash = sha256(args.model)
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    variant = args.recipe
    waves, cases = mixed_recipe(variant)
    for name, source in waves.items():
        write_wav(root/(name+'.wav'), 48000, source.ravel())
    for case in cases:
        parameters = []
        for name, value in controls(case).items():
            matches = [p for p in inventory['parameters'] if p['name'] == name]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous control: '+name)
            parameters.append({k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value})
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference',
            expected_plugin=IDENTITY, sample_rate=48000, bpm=120, tail_seconds=case['tail'],
            parameters=parameters, events=[])
        save_json(root/(case['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/(case['source']+'.wav'),
             root/(case['name']+'.json'), root/case['name'], 128])
        case['receipt_sha256'] = sha256(root/case['name']/'receipt.json')
        print(case['name'], flush=True)
    if model_hash != sha256(args.model):
        raise ValueError('Frozen model changed during capture')
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-down-mixed-holdouts', cases=cases,
        recipe=variant, capture_script_sha256=sha256(Path(__file__)), prospective_model_sha256=model_hash))


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves, cases = mixed_recipe(args.recipe)
    rows = [checked(args.session, c, waves[c['source']])[3] for c in cases]
    save_json(args.report, dict(kind='rmx220-reverb-down-mixed-recipe-verification', passed=True,
        cases=rows, script_sha256=sha256(Path(__file__)),
        scope='Exact samples, controls, rate/extent and hashes only.'))
    print('Verified', len(rows), 'fresh mixed-control captures')


def compare(args):
    calibration(args.calibration)
    model = model_checked(args.model, args.calibration)
    repo = Path(__file__).resolve().parents[1]
    header = repo/'include/rmx/ReverbDownCalibration.h'
    if model['header_sha256'] != sha256(header):
        raise ValueError('Current control header differs from the declared model')
    for stage, directory in args.session:
        if stage in ('mixed', 'mixed-v2'):
            manifest = json.loads((Path(directory)/'matrix.json').read_text())
            if manifest.get('prospective_model_sha256') != sha256(args.model):
                raise ValueError('Mixed holdout does not bind this frozen model')
    root = new_directory(args.output)
    results, skipped = [], []
    for stage, directory in args.session:
        session = Path(directory)
        if stage in ('main', 'amount', 'main-long', 'amount-large'):
            source, cases = control_recipe(stage)
            waves = {'source': source}
        elif stage in ('initial', 'timing', 'filters', 'long-tail'):
            waves, cases = initial_recipe(stage)
        elif stage == 'neutral-holdout':
            waves, cases = holdout_recipe()
        elif stage in ('mixed', 'mixed-v2', 'mixed-development'):
            waves, cases = mixed_recipe('mixed' if stage == 'mixed-development' else stage)
        else:
            raise ValueError('Unknown capture stage: '+stage)
        for case in cases:
            if case['direction'] != 'down':
                skipped.append(dict(stage=stage,case=case['name'],reason='Up remains outside the Down candidate'))
                continue
            receipt, audio, source, provenance = checked(session, case, waves[case['source']])
            output = root/(stage+'-'+case['name']+'.wav')
            run([args.renderer, receipt['input_path'], output, case['main'], case['amount'], case['cutoff'], case['tail']])
            rate, candidate = float_wav(output)
            if rate != 48000 or len(candidate) != len(audio)+32:
                raise ValueError('Renderer extent/rate differs')
            candidate = candidate[:len(audio)].astype(float)
            dry_gain = model['main_rows'][case['main']]['dry_gain']
            wet_a, wet_b = residual(audio, source, dry_gain), residual(candidate, source, dry_gain)
            item = dict(**provenance,stage=stage,main_raw=case['main'],amount_raw=case['amount'],cutoff_raw=case['cutoff'],
                dry_subtraction_gain_fixed_from_main_sweep=dry_gain,whole=screen(audio,candidate),wet=screen(wet_a,wet_b),
                post_input_tail=screen(audio[len(source):],candidate[len(source):]),candidate_sha256=sha256(output))
            results.append(item)
            print('PASS' if all(item[k]['passed'] for k in ('whole','wet','post_input_tail')) else 'FAIL',stage,case['name'],flush=True)
    if not results:
        raise ValueError('No eligible Down cases')
    passed = all(x[k]['passed'] for x in results for k in ('whole','wet','post_input_tail'))
    paths = [Path(__file__),repo/'tools/rmx_reverb_controls.py',repo/'research/audio/experiments/reverb_down_neutral_probe.cpp',
             repo/'research/audio/experiments/ReverbDownNeutralCalibration.h',repo/'include/rmx/ReverbDownCalibration.h']
    save_json(root/'comparison.json',dict(kind='rmx220-reverb-down-static-control-autonomous-comparison',passed=passed,
        full_reverb_match=False,physical_hardware=False,sample_rate=48000,reference_identity=IDENTITY,
        cases=results,out_of_scope=skipped,model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),
        renderer_sha256=sha256(args.renderer),source_sha256={str(p.resolve().relative_to(repo)):sha256(p) for p in paths},
        acceptance=dict(relative_rms_error_limit=.01,silent_channel_absolute_rms_limit=1e-8,reference_channel_energy_floor=1e-20,
            reference_offset_frames=32,gain_fit=False,wet_alignment_search=False),
        scope='Static integer raw controls, Default Down, 48 kHz/120 BPM, input silence before excitation.',
        limitations=['Includes separate control-calibration sweeps; prospective mixed cases are identified by their stage.',
            'No fractional raw controls, gestures, other profiles/rates, Up, listening or hardware equivalence claim.']))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    p = commands.add_parser('build')
    for key in ('main','amount','calibration','report','header'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--main-long',type=Path)
    p.add_argument('--amount-large',type=Path)
    p = commands.add_parser('capture')
    for key in ('host','plugin','session','model','calibration'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--recipe',choices=('mixed','mixed-v2'),default='mixed')
    p = commands.add_parser('verify')
    for key in ('session','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--recipe',choices=('mixed','mixed-v2'),default='mixed')
    p = commands.add_parser('compare')
    for key in ('model','calibration','renderer','output'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--session',nargs=2,action='append',metavar=('STAGE','DIRECTORY'),required=True)
    args = parser.parse_args()
    result = {'build':build,'capture':capture,'verify':verify,'compare':compare}[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__ == '__main__':
    main()
