#!/usr/bin/env python3
"""Audit static Up maps, complete recordings, frozen forecasts and implementation guards."""
import argparse
import copy
import json
from pathlib import Path
import shlex

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked
from tools.rmx_reverb_up_model import capture, hashes, model_checked, payload, session_recipe
from tools.rmx_reverb_up_feedback import validate as validate_feedback

ACCEPTANCE = dict(relative_rms_error_limit=.01, reference_channel_energy_floor=1e-20,
                  silent_channel_absolute_rms_limit=1e-8, reference_offset_frames=32,
                  candidate_offset_frames=0, gain_fit=False, wet_alignment_search=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def auxiliary(folder, receipt):
    plan = json.loads((folder/'plan.json').read_text())
    for name, field in [('state-before.bin', 'initial_state_sha256'), ('state-after.bin', 'final_state_sha256'),
                        ('parameter-log.json', 'parameter_log_sha256'), ('inventory-after.json', 'final_inventory_sha256')]:
        require(sha256(folder/name) == receipt[field], 'Modified auxiliary capture: '+str(folder/name))
    log = json.loads((folder/'parameter-log.json').read_text())['entries']
    require(len(log) == len(plan['parameters']), 'Unexpected static parameter events')
    for requested, actual in zip(plan['parameters'], log):
        require(actual['frame'] == -1 and all(actual[k] == requested[k] for k in ('index', 'id', 'name'))
                and np.float32(actual['requested_value']) == np.float32(requested['value'])
                and abs(actual['immediate_readback']-float(np.float32(requested['value']))) <= 1e-14,
                'Immediate parameter readback differs')
    final = {p['name']: p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
    require(all(abs(final[p['name']]-float(np.float32(p['value']))) <= 1e-14 for p in plan['parameters']),
            'Final parameter readback differs')


def instrumented(args):
    build = args.sanitized_build.resolve(); repo = Path(__file__).resolve().parents[1]
    manifest = build/'compile_commands.json'; entries = json.loads(manifest.read_text())
    require(args.sanitized.resolve() == build/'rmx_reverb_up_probe', 'Unexpected sanitizer target')
    result = {}; newest = 0
    for name in ('research/audio/experiments/reverb_up_neutral_probe.cpp', 'src/core/Wav.cpp'):
        matches = [e for e in entries if Path(e['file']).resolve() == repo/name]
        matches = [e for e in matches if 'RMX_REVERB_UP_ONE_FRAME_NEGATIVE_CONTROL' not in e.get('command', ' '.join(e.get('arguments', [])))]
        require(len(matches) == 1, 'Missing or ambiguous sanitizer compile entry')
        entry = matches[0]; command = entry.get('arguments') or shlex.split(entry['command'])
        flags = {s for item in command if item.startswith('-fsanitize=') for s in item.split('=', 1)[1].split(',')}
        require({'address', 'undefined'} <= flags and '-fno-omit-frame-pointer' in command, 'Missing sanitizer flags')
        obj = Path(entry['directory'])/command[command.index('-o')+1]
        dependencies = [repo/name]
        if name.endswith('_probe.cpp'):
            dependencies += [repo/'research/audio/experiments'/n for n in ('ReverbUpControlCalibration.h', 'ReverbUpNeutralCalibration.h')]
        require(obj.stat().st_mtime_ns >= max(p.stat().st_mtime_ns for p in dependencies), 'Stale instrumented object')
        newest = max(newest, obj.stat().st_mtime_ns)
        result[name] = dict(command=command, dependencies_sha256={str(p.relative_to(repo)): sha256(p) for p in dependencies}, object_sha256=sha256(obj))
    require(args.sanitized.stat().st_mtime_ns >= newest, 'Stale sanitizer binary')
    return dict(compile_commands_sha256=sha256(manifest), instrumented_sources=result,
                renderer_sha256=sha256(args.sanitized))


def audit(args):
    model = model_checked(args); root = new_directory(args.output)
    prediction = json.loads(args.prediction.read_text()); variant = prediction['variant']; current_hashes = hashes()
    require(all(prediction.get(k) == v for k, v in payload(variant).items())
            and prediction['model_sha256'] == sha256(args.model)
            and prediction['calibration_sha256'] == sha256(args.calibration)
            and prediction['renderer_sha256'] == sha256(args.renderer), 'Frozen current candidate differs')
    records = {}
    for path in args.comparison:
        report = json.loads(path.read_text())
        require(report['kind'] == 'rmx220-reverb-up-static-control-comparison' and report['passed']
                and report['acceptance'] == ACCEPTANCE and report['model_sha256'] == sha256(args.model)
                and report['renderer_sha256'] == sha256(args.renderer) and report['source_sha256'] == current_hashes
                and report['calibration_sha256'] == sha256(args.calibration), 'Comparison binding or acceptance differs')
        for row in report['cases']:
            key = row['stage'], row['case']
            require(key not in records and row['passed'], 'Duplicate or failed comparison')
            records[key] = path.parent, row
    seen = set(); verified = []; direct = []; hosts = set(); plugin_files = None; plugin_bundle = None
    fixtures = {}; prior = dict(args.prior_prediction or [])
    for stage, directory in args.session:
        if stage in ('mixed', 'mixed-v2'):
            bound = args.prediction if stage == variant else prior.get(stage)
            require(bound is not None, 'Missing historical mixed prediction')
            historical = json.loads(bound.read_text()); manifest = json.loads((directory/'matrix.json').read_text())
            # Historical candidates retain their own frozen hashes; they are regressions for this candidate.
            recipe_payload = payload(stage)
            require(all(historical[k] == recipe_payload[k] for k in ('kind', 'variant', 'cases', 'samples_sha256'))
                    and manifest['prediction_sha256'] == sha256(bound)
                    and sha256(directory/'predictions.json') == sha256(bound)
                    and manifest['model_sha256'] == historical['model_sha256'], 'Mixed capture freeze differs')
        waves, cases = session_recipe(stage)
        for c in cases:
            receipt, a, x, provenance = checked(directory, c, waves[c['source']]); folder = directory/c['name']
            auxiliary(folder, receipt); key = stage, c['name']; require(key not in seen, 'Duplicate session case'); seen.add(key)
            parent, row = records[key]
            require(all(row[k] == v for k, v in provenance.items()), 'Comparison provenance differs')
            output = parent/(stage+'-'+c['name']+'.wav'); rate, raw_b = float_wav(output)
            require(rate == 48000 and len(raw_b) == len(a)+32 and sha256(output) == row['candidate_sha256'], 'Candidate WAV differs')
            b = raw_b[:len(a)].astype(float); dry = np.zeros_like(a); dry[:min(len(a), len(x))] = x[:len(a)]
            screens = dict(whole=screen(a, b), wet=screen(a-dry, b-dry), post_input_tail=screen(a[len(x):], b[len(x):]))
            require(all(value == row[k] and value['passed'] for k, value in screens.items()), 'Recomputed waveform screen differs')
            nonzero = np.flatnonzero(np.any(x != 0, axis=1))
            if len(nonzero):
                start = int(nonzero[0]); stop = min(start+128, len(x))
                bits = [v[start:stop].astype(np.float32).view(np.uint32) for v in (a, b, x)]
                require(np.array_equal(bits[0], bits[2]) and np.array_equal(bits[1], bits[2]), 'Direct-only prefix differs')
                direct.append(dict(stage=stage, case=c['name'], start=start, frames=stop-start, original_candidate_input_bit_exact=True))
            else:
                require(not np.any(a) and not np.any(b), 'Silent input produces audio')
            if (stage == 'main' and c['main'] == 104) or (stage == variant and 'fresh' not in fixtures):
                fixtures['main104' if stage == 'main' else 'fresh'] = directory, c, waves[c['source']], output
            hosts.add(receipt['host_sha256'])
            if plugin_files is None:
                plugin_files = receipt['plugin']['binary_files']; plugin_bundle = Path(receipt['plugin']['bundle'])
            require(receipt['plugin']['binary_files'] == plugin_files, 'Original plug-in binary members differ')
            verified.append(provenance | dict(stage=stage, auxiliary_hashes_verified=True, applied_controls_verified=True, waveform_screens_recomputed=True))
        print('Audited', stage, len(cases), flush=True)
    require(seen == set(records) and len(hosts) == 1 and set(fixtures) == {'main104', 'fresh'}, 'Coverage or host differs')
    for member in plugin_files:
        member_path = plugin_bundle/member['path']
        require(member_path.stat().st_size == member['bytes'] and sha256(member_path) == member['sha256'], 'Installed original changed')
    reference = json.loads(args.reference.read_text()); observation = json.loads(args.observation.read_text())
    require(model['neutral_model_sha256'] == sha256(args.reference)
            and reference['coefficient_observation_sha256'] == sha256(args.observation)
            and model['feedback_filter'] == reference['feedback_filter'] == observation['feedback_filter']
            and observation['debugger_audio_byte_identical']
            and any(m['sha256'] == observation['original_binary_sha256'] for m in plugin_files), 'Feedback observation/reference differs')
    original_folder = dict(args.session)['main']/'up-main-128'
    original_receipt = json.loads((original_folder/'receipt.json').read_text())
    debugger_receipt = json.loads((args.debugger_capture/'receipt.json').read_text())
    require(sha256(original_folder/'receipt.json') == observation['original_receipt_sha256']
            and sha256(args.debugger_capture/'receipt.json') == observation['debugger_receipt_sha256']
            and sha256(original_folder/'audio.wav') == sha256(args.debugger_capture/'audio.wav') == observation['original_audio_sha256']
            and all(original_receipt[k] == debugger_receipt[k] for k in ('input_sha256', 'plan_sha256', 'output_sha256', 'host_sha256'))
            and debugger_receipt['plugin']['binary_files'] == plugin_files
            and sha256(args.debugger_script) == observation['read_only_scalar_script_sha256']
            and sha256(args.debugger_log) == observation['scalar_log_sha256'], 'Debugger capture/log provenance differs')
    auxiliary(args.debugger_capture, debugger_receipt)
    validation_path = root/'feedback-validation.json'
    require(validate_feedback(argparse.Namespace(reference=args.reference, calibration=args.calibration, prediction=args.feedback_prediction,
                                                session=args.feedback_session, report=validation_path)) == 0, 'Fresh coefficient forecasts fail')
    feedback_validation = json.loads(args.feedback_validation.read_text())
    require(model['corrected_feedback_validation_sha256'] == sha256(args.feedback_validation)
            and feedback_validation['cases'] == json.loads(validation_path.read_text())['cases'], 'Recorded coefficient validation differs')
    directory, c, signal, valid_output = fixtures['main104']; recipe_guards = []
    for field in ('main', 'amount', 'cutoff', 'tail', 'source-samples'):
        changed = copy.deepcopy(c); source = signal
        if field == 'source-samples':
            source = signal.copy(); source[1, 0] = .01
        else:
            changed[field] += 1
        try:
            checked(directory, changed, source)
        except ValueError:
            recipe_guards.append(field)
        else:
            raise ValueError('Changed recipe accepted: '+field)
    prediction_guards = []
    for field in ('kind', 'variant', 'cases', 'source_sha256', 'samples_sha256', 'model_sha256', 'renderer_sha256', 'calibration_sha256'):
        bad = copy.deepcopy(prediction)
        if field == 'cases':
            bad[field][0]['main'] += 1
        elif field in ('source_sha256', 'samples_sha256'):
            bad[field][next(iter(bad[field]))] = '0'*64
        else:
            bad[field] = 'modified'
        path = root/(field+'.json'); save_json(path, bad); forbidden = root/('forbidden-'+field)
        try:
            capture(argparse.Namespace(model=args.model, calibration=args.calibration, recipe=variant, prediction=path, session=forbidden))
        except ValueError as error:
            require(str(error) == 'Frozen mixed prediction differs' and not forbidden.exists(), 'Prediction guard did not reject before capture')
            prediction_guards.append(field)
        else:
            raise ValueError('Changed prediction accepted')
    wrong_model = json.loads(args.model.read_text()); wrong_model['header_sha256'] = '0'*64
    bad_model = root/'bad-model.json'; save_json(bad_model, wrong_model)
    try:
        model_checked(argparse.Namespace(model=bad_model, calibration=args.calibration))
    except ValueError:
        prediction_guards.append('model-header-binding')
    else:
        raise ValueError('Changed model/header binding accepted')
    input_path = Path(json.loads((directory/c['name']/'receipt.json').read_text())['input_path'])
    wrong_rate = root/'wrong-rate.wav'; nonfinite = root/'nonfinite.wav'
    write_wav(wrong_rate, 44100, [0, 0]*1024); write_wav(nonfinite, 48000, [float('nan'), 0]*1024)
    requests = []
    for index, label in enumerate(('main', 'amount', 'cutoff')):
        for name, value in [('negative', -1), ('overflow', 256), ('fraction', .5), ('nan', 'nan')]:
            values = [128, 128, 0, 1]; values[index] = value
            requests.append((label+'-'+name, input_path, values))
    requests += [('suffix', input_path, ['128x', 128, 0, 1]), ('tail-negative', input_path, [128, 128, 0, -1]),
                 ('tail-overflow', input_path, [128, 128, 0, 121]), ('rate', wrong_rate, [128, 128, 0, 1]),
                 ('argument-count', input_path, [128, 128, 0])]
    rejected = []
    for name, source, values in requests:
        output = root/(name+'.wav')
        try:
            run([args.renderer, source, output, *values])
        except RuntimeError:
            require(not output.exists(), 'Rejected request wrote audio'); rejected.append(name)
        else:
            raise ValueError('Invalid request accepted: '+name)
    sentinel = root/'existing.wav'; sentinel.write_bytes(b'preserve-existing-output')
    try:
        run([args.renderer, input_path, sentinel, 128, 128, 0, 1])
    except RuntimeError:
        require(sentinel.read_bytes() == b'preserve-existing-output', 'Existing output changed'); rejected.append('existing-output')
    else:
        raise ValueError('Existing output accepted')
    sanitized_input = root/'nonfinite-sanitized.wav'; run([args.renderer, nonfinite, sanitized_input, 128, 128, 0, 1])
    rate, audio = float_wav(sanitized_input)
    require(rate == 48000 and len(audio) == 49024 and not np.any(audio), 'NaN-to-zero WAV policy differs')
    # Change a network delay, not comparison alignment: Main104 is the measured quartic exception.
    receipt, a, x, provenance = checked(directory, c, signal); wrong_output = root/'one-frame-negative.wav'
    run([args.negative_renderer, input_path, wrong_output, c['main'], c['amount'], c['cutoff'], c['tail']])
    b = float_wav(wrong_output)[1][:len(a)].astype(float); dry = np.zeros_like(a); dry[:len(x)] = x
    negative = dict(whole=screen(a, b), wet=screen(a-dry, b-dry))
    require(not negative['whole']['passed'] and not negative['wet']['passed']
            and model['main_rows'][104]['delays'][4][0] == 1368, 'One-frame network error not rejected')
    instrumentation = instrumented(args); sanitized = []
    for label, (directory, c, _, valid_output) in fixtures.items():
        receipt = json.loads((directory/c['name']/'receipt.json').read_text()); output = root/(label+'-asan.wav')
        run([args.sanitized, receipt['input_path'], output, c['main'], c['amount'], c['cutoff'], c['tail']])
        require(sha256(output) == sha256(valid_output), 'Optimized/sanitized output differs')
        sanitized.append(dict(case=c['name'], output_sha256=sha256(output), byte_exact=True))
    save_json(root/'verification.json', dict(kind='rmx220-reverb-up-static-control-audit', passed=True,
        script_sha256=sha256(Path(__file__)), model_sha256=sha256(args.model), prediction_sha256=sha256(args.prediction),
        renderer_sha256=sha256(args.renderer), source_sha256=current_hashes, acceptance=ACCEPTANCE,
        comparison_sha256=[sha256(p) for p in args.comparison], reference_host_sha256=next(iter(hosts)), plugin_binary_files=plugin_files,
        captures=verified, direct_only_prefixes=direct, feedback_validation_sha256=sha256(validation_path),
        feedback_observation_sha256=sha256(args.observation), debugger_original_audio_byte_identical=True,
        debugger_log_and_script_hashes_verified=True, rejected_recipe_changes=recipe_guards,
        rejected_prediction_changes=prediction_guards, rejected_native_inputs=rejected,
        nonfinite_wav_policy=dict(nonfinite_samples_replaced_with_zero=True, output_sha256=sha256(sanitized_input)),
        network_negative_control=dict(main_raw=104, measured_delay=1368, changed_delay=1367,
            renderer_sha256=sha256(args.negative_renderer), output_sha256=sha256(wrong_output), **negative),
        sanitizer=instrumentation, sanitized_renders=sanitized,
        limitations=['Static integer factory Up at 48 kHz/120 BPM with silent pre-roll. No live Engine, motion/startup, other rates/profiles/tempos, overload, listening or hardware claim.',
                    'Sanitizers cover the stated two renders; offline whole-WAV buffers allocate. This is not callback/MCU deadline qualification.',
                    'Prior mixed failures remain bound to their historical candidate and become regressions here.']))
    print('Audited', len(verified), 'captures,', len(direct), 'direct prefixes, guards and sanitizer parity', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'calibration', 'prediction', 'renderer', 'negative-renderer', 'sanitized', 'sanitized-build',
                 'reference', 'observation', 'debugger-capture', 'debugger-script', 'debugger-log',
                 'feedback-prediction', 'feedback-session', 'feedback-validation', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--session', nargs=2, action='append', required=True)
    parser.add_argument('--comparison', type=Path, action='append', required=True)
    parser.add_argument('--prior-prediction', nargs=2, action='append')
    args = parser.parse_args(); args.session = [(s, Path(d)) for s, d in args.session]
    args.prior_prediction = [(s, Path(p)) for s, p in (args.prior_prediction or [])]
    audit(args)


if __name__ == '__main__':
    main()
