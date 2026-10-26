#!/usr/bin/env python3
"""Audit motion provenance, fixed bypass latency, guards and sanitizer renders."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import new_directory, run
from tools.rmx_reverb_motion import checked, prediction_payload, recipe
from tools.rmx_spiral_core import calibration


def audit(args):
    calibration(args.calibration)
    root = new_directory(args.output)
    prediction = json.loads(args.prediction.read_text())
    if (any(prediction.get(k) != v for k, v in prediction_payload('cutoff-holdout').items())
            or prediction['model_sha256'] != sha256(args.model)
            or prediction['renderer_sha256'] != sha256(args.renderer)
            or prediction['calibration_sha256'] != sha256(args.calibration)):
        raise ValueError('Frozen prospective model/recipe/source/renderer/calibration differs')
    comparisons = [json.loads(p.read_text()) for p in args.comparison]
    records = {}
    for path, report in zip(args.comparison, comparisons):
        if (report['candidate_config'] != prediction['candidate_config']
                or report['renderer_sha256'] != sha256(args.renderer)
                or report['model_sha256'] != sha256(args.model)
                or report['calibration_sha256'] != sha256(args.calibration)):
            raise ValueError('Comparison does not use frozen candidate')
        for row in report['cases']:
            key = (row['stage'], row['case'])
            if key in records:
                raise ValueError('Duplicate comparison case')
            records[key] = (path.parent, row)
    verified, bypass, seen = [], [], set()
    host_hashes = set()
    guard_fixture = None
    for stage, directory in args.session:
        waves, cases = recipe(stage)
        for case in cases:
            audio, source, provenance = checked(directory, case, waves[case['source']])
            key = (stage, case['name'])
            seen.add(key)
            folder = directory / case['name']
            receipt = json.loads((folder / 'receipt.json').read_text())
            plan = json.loads((folder / 'plan.json').read_text())
            for name, field in (('state-before.bin', 'initial_state_sha256'),
                                ('state-after.bin', 'final_state_sha256'),
                                ('parameter-log.json', 'parameter_log_sha256'),
                                ('inventory-after.json', 'final_inventory_sha256')):
                if sha256(folder / name) != receipt[field]:
                    raise ValueError('Modified capture auxiliary file: ' + str(folder / name))
            log = json.loads((folder / 'parameter-log.json').read_text())['entries']
            expected = [p | dict(frame=-1) for p in plan['parameters']] + plan['events']
            if len(log) != len(expected):
                raise ValueError('Parameter log extent differs')
            for actual, requested in zip(log, expected):
                if (any(actual[k] != requested[k] for k in ('frame', 'index', 'id', 'name'))
                        or np.float32(actual['requested_value']) != np.float32(requested['value'])
                        or abs(actual['immediate_readback'] - float(np.float32(requested['value']))) > 1e-14):
                    raise ValueError('Applied parameter/readback differs: ' + str(folder) + '/' + requested['name'])
            final = {p['name']: p['value'] for p in json.loads((folder / 'inventory-after.json').read_text())['parameters']}
            target = {p['name']: p['value'] for p in expected}
            if any(abs(final[k] - float(np.float32(v))) > 1e-14 for k, v in target.items()):
                raise ValueError('Final control readback differs')
            parent, result = records[key]
            if any(result[k] != v for k, v in provenance.items()):
                raise ValueError('Comparison provenance differs')
            output = parent / (stage + '-' + case['name'] + '.wav')
            if sha256(output) != result['candidate_sha256']:
                raise ValueError('Candidate render changed')
            if not case['enabled']:
                stop = case['events'][0]['frame']
                candidate = float_wav(output)[1]
                a, b = audio[32:32+stop], candidate[32:32+stop]
                if not np.array_equal(a, source[:stop]) or not np.array_equal(b, source[:stop]):
                    raise ValueError('Fixed bypass latency fails independent initially-off prefix')
                bypass.append(dict(stage=stage, case=case['name'], frames=stop,
                    reference_offset=32, candidate_offset=32, both_bit_exact=True))
            verified.append(provenance | dict(stage=stage, parameter_log_sha256=receipt['parameter_log_sha256'],
                final_inventory_sha256=receipt['final_inventory_sha256'], applied_controls_verified=True))
            host_hashes.add(receipt['host_sha256'])
            if stage == 'steps' and case['name'] == 'down-step-main-128-192':
                guard_fixture = (directory, case, waves[case['source']])
    if seen != set(records) or len(host_hashes) != 1:
        raise ValueError('Comparison/session coverage or reference host differs')

    # A short full-bypass render proves the candidate offset without a wet search.
    x = np.random.default_rng(0x8A11).normal(0, .02, (2048, 2)).astype(np.float32)
    input_file, schedule = root / 'bypass-input.wav', root / 'bypass.tsv'
    write_wav(input_file, 48000, x.ravel())
    schedule.write_text('RMX_REVERB_MOTION 1\ninitial 128 128 0 0\ntail 0.03\n')
    output, dry = root / 'bypass.wav', root / 'bypass-dry.wav'
    run([args.renderer, input_file, output, schedule, 'inlet', 'post', 'read', 32, dry])
    y = float_wav(output)[1]
    expected = np.zeros_like(y)
    expected[32:32+len(x)] = x
    if not np.array_equal(y, expected) or not np.array_equal(float_wav(dry)[1], expected):
        raise ValueError('Candidate bypass is not exactly delayed by 32 frames')
    rejected_offsets = [n for n in (0, 31, 33) if not np.array_equal(y[n:n+len(x)], x)]
    if rejected_offsets != [0, 31, 33]:
        raise ValueError('Bypass offset negative control is inconclusive')

    guards = []
    if guard_fixture is None:
        raise ValueError('Audit requires the Main128-to-192 step guard fixture')
    directory, case, source = guard_fixture
    for field in ('main', 'amount', 'cutoff', 'block', 'tail', 'events', 'source-samples'):
        changed, signal = copy.deepcopy(case), source
        if field == 'events':
            changed['events'][0]['frame'] += 1
        elif field == 'source-samples':
            signal = source.copy()
            signal[1, 0] = .01
        else:
            changed[field] += 1
        try:
            checked(directory, changed, signal)
        except ValueError:
            guards.append(field)
        else:
            raise ValueError('Capture guard accepted changed ' + field)

    sanitized = []
    for key in (('steps', 'down-step-main-0-128'), ('cutoff-holdout', 'down-cutoff-holdout-0')):
        parent, result = records[key]
        prefix = key[0] + '-' + key[1]
        plan = parent / (prefix + '.tsv')
        directory = dict(args.session)[key[0]]
        receipt = json.loads((directory / key[1] / 'receipt.json').read_text())
        out, trace = root / (prefix + '-asan.wav'), root / (prefix + '-asan-dry.wav')
        run([args.sanitized, receipt['input_path'], out, plan, 'inlet', 'post', 'read', 32, trace])
        if sha256(out) != result['candidate_sha256'] or sha256(trace) != result['dry_trace_sha256']:
            raise ValueError('Sanitized and optimized renders differ')
        sanitized.append(dict(stage=key[0], case=key[1], bit_exact=True, output_sha256=sha256(out)))
    save_json(root / 'verification.json', dict(kind='rmx220-reverb-down-motion-audit', passed=True,
        prediction_sha256=sha256(args.prediction), model_sha256=sha256(args.model),
        renderer_sha256=sha256(args.renderer), sanitized_renderer_sha256=sha256(args.sanitized),
        script_sha256=sha256(Path(__file__)), comparisons_sha256=[sha256(p) for p in args.comparison],
        capture_cases=verified, host_sha256=next(iter(host_hashes)), initially_off_bypass_prefixes=bypass,
        full_candidate_bypass=dict(frames=len(y), bit_exact=True, offset=32,
            rejected_offsets=rejected_offsets, input_sha256=sha256(input_file), output_sha256=sha256(output)),
        rejected_capture_changes=guards, sanitized_renders=sanitized,
        limitations=['The linked WAV library was not rebuilt with sanitizers.',
            'Provenance, bypass and sanitizer checks do not turn failing motion cases into passes.']))
    print('Audited', len(verified), 'captures, four bypass prefixes, seven guards and two sanitizer renders')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', nargs=2, action='append', required=True, type=Path)
    parser.add_argument('--comparison', type=Path, action='append', required=True)
    for name in ('prediction', 'model', 'calibration', 'renderer', 'sanitized', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.session = [(str(stage), directory) for stage, directory in args.session]
    audit(args)


if __name__ == '__main__':
    main()
