#!/usr/bin/env python3
"""Replay Up Main state from independently measured endpoints; not waveform acceptance."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256


def replay(cases, trace, *, formula=False, double_feedback=False, block_delay=False):
    def delay(raw):
        if not formula:
            return np.float32(cases[raw]['delays'][1][0])
        v = np.float32(1)-np.float32(max(0, raw-3))*np.float32(1/252)
        return np.float32((np.float32(.3)+np.float32(3)*((v*v)*(v*v)))*np.float32(1060))
    coefficient_type = float if double_feedback else np.float32
    current = delay(128); gain = coefficient_type(cases[128]['gain_left'][1])
    slow = pending = 128; period = 60; blocks = 0; remaining = 0
    delay_errors = []; gain_errors = []; counters = []
    for row in trace:
        if row['network_call'] >= 6001:
            if not blocks and slow != 192:
                desired = 15-min(5, 192-slow); period += -1 if period > desired else 1 if period < desired else 0
                pending = slow+1; blocks = period; remaining = period*32
                target = delay(pending); gain_target = coefficient_type(cases[pending]['gain_left'][1])
                step = np.float32(np.float32(target-current)*np.float32(1/remaining))
                gain_step = coefficient_type(coefficient_type(gain_target-gain)*coefficient_type(1/remaining))
            if remaining:
                if block_delay:
                    current = np.float32(current+np.float32(step*np.float32(32)))
                for _ in range(32):
                    if not block_delay:
                        current = np.float32(current+step)
                    gain = coefficient_type(gain+gain_step); remaining -= 1
                    if not remaining:
                        current = target; gain = gain_target
                blocks -= 1
                if not blocks:
                    slow = pending
        delay_errors.append(abs(float(current)-row['delay']))
        gain_errors.append(abs(float(gain)-row['feedback']))
        counters.append(row['main'] == slow and row['pending_main'] == pending and row['period'] == period and row['ramp_blocks'] == blocks)
    return dict(observed_blocks=len(trace), delay_exact_blocks=sum(e == 0 for e in delay_errors),
        feedback_exact_blocks=sum(e == 0 for e in gain_errors), counters_exact_blocks=sum(counters),
        maximum_delay_error_frames=max(delay_errors), maximum_feedback_error=max(gain_errors),
        all_exact=all(e == 0 for e in delay_errors+gain_errors) and all(counters))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('geometry', 'observations', 'trace', 'report'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); geometry = json.loads(args.geometry.read_text()); observations = json.loads(args.observations.read_text())
    if geometry['kind'] != 'rmx220-reverb-up-settled-fractional-scalar-calibration' or not geometry['passed']:
        raise ValueError('Requires verified independent scalar calibration')
    binding = next(c for c in observations['cases'] if c['case'] == 'up-step-main-128-192')
    if observations['kind'] != 'rmx220-reverb-up-motion-clock-observations' or not binding['debugger_audio_byte_identical'] or binding['scalar_log_sha256'] != sha256(args.trace):
        raise ValueError('Wrong independently verified motion trace')
    trace = [json.loads(line) for line in args.trace.read_text().splitlines()]
    if [r['network_call'] for r in trace] != list(range(5800, 10000)):
        raise ValueError('Incomplete original state trace')
    cases = geometry['cases']
    if [c['main_raw'] for c in cases] != list(range(256)):
        raise ValueError('Incomplete static endpoints')
    positive = replay(cases, trace)
    negatives = dict(nominal_fractional_curve=replay(cases, trace, formula=True),
                     double_feedback_updates=replay(cases, trace, double_feedback=True),
                     one_delay_update_per_block=replay(cases, trace, block_delay=True))
    if not positive['all_exact'] or any(value['all_exact'] for value in negatives.values()):
        raise ValueError('Measured replay fails or a negative control is not distinguished')
    save_json(args.report, dict(kind='rmx220-reverb-up-motion-scalar-replay', passed=True,
        script_sha256=sha256(Path(__file__)), geometry_sha256=sha256(args.geometry), observation_sha256=sha256(args.observations),
        trace_sha256=sha256(args.trace), measured_endpoint_replay=positive, rejected_alternatives=negatives,
        scope='One left-comb delay/feedback scalar and shared Main counters over the 4200 observed blocks of Main128-to-192 at Sub1-128. Static endpoints come from a separate ascending sweep. Exact scalar equality is a component check, not full audio or fresh waveform validation.'))
    print('Exact Main delay/feedback/counter replay for', positive['observed_blocks'], 'observed blocks; three alternatives differ')


if __name__ == '__main__':
    main()
