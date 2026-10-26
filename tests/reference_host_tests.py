#!/usr/bin/env python3
"""Exercise an offline host with the project plug-in, never as reference parity evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import numpy as np

from tools.reference_audio import read_wav, write_wav


class ReferenceHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host = Path(os.environ['RMX_REFERENCE_HOST']).resolve()
        cls.plugin = Path(os.environ['RMX_REFERENCE_FIXTURE']).resolve()
        result = subprocess.run([str(cls.host), 'inventory', str(cls.plugin)],
                                check=True, capture_output=True, text=True, timeout=60)
        cls.inventory = json.loads(result.stdout)
        if cls.inventory['manufacturer'] != 'Axel McKenna':
            raise RuntimeError('Use the project plug-in as the synthetic test fixture')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='rmx-host-tests-')
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        frames = np.arange(12000)
        samples = np.column_stack((.1 * np.sin(frames * .13), .07 * np.sin(frames * .077)))
        self.input = self.root / 'input.wav'
        write_wav(self.input, 48000, samples.ravel())

    def setting(self, name, value):
        selected = [p for p in self.inventory['parameters'] if p['name'] == name]
        self.assertEqual(len(selected), 1, name)
        return {key: selected[0][key] for key in ('index', 'id', 'name')} | {'value': value}

    def plan(self):
        return {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'host_fixture',
                'expected_plugin': {k: self.inventory[k] for k in ('name', 'manufacturer', 'version')},
                'sample_rate': 48000, 'bpm': 120, 'tail_seconds': 0,
                'parameters': [self.setting('Auto BPM', 0), self.setting('Scene enabled', 0),
                               self.setting('Sampler mute', 1)], 'events': []}

    def render(self, plan, name, block=128, success=True):
        source = self.root / (name + '.json')
        source.write_text(json.dumps(plan))
        destination = self.root / name
        result = subprocess.run([str(self.host), 'render', str(self.plugin), str(self.input),
                                 str(source), str(destination), str(block)],
                                capture_output=True, text=True, timeout=60)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((destination / 'receipt.json').read_text())
            self.assertTrue(receipt['complete'])
            self.assertEqual(receipt['role'], 'host_fixture')
            self.assertEqual(receipt['output_sha256'], hashlib.sha256((destination / 'audio.wav').read_bytes()).hexdigest())
            self.assertEqual(receipt['input_sha256'], hashlib.sha256(self.input.read_bytes()).hexdigest())
            self.assertEqual(receipt['parameter_log_sha256'], hashlib.sha256((destination / 'parameter-log.json').read_bytes()).hexdigest())
            self.assertEqual(receipt['final_inventory_sha256'], hashlib.sha256((destination / 'inventory-after.json').read_bytes()).hexdigest())
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((destination / 'receipt.json').exists())
        return destination, result

    def test_event_timing_is_independent_of_host_blocks(self):
        plan = self.plan()
        default = next(p['value'] for p in self.inventory['parameters'] if p['name'] == 'Output gain')
        plan['events'] = [self.setting('Output gain', 1 / 3) | {'frame': 2003, 'type': 'parameter'},
                          self.setting('Output gain', default) | {'frame': 7001, 'type': 'parameter'}]
        a, _ = self.render(plan, 'block-32', 32)
        b, _ = self.render(plan, 'block-128', 128)
        left = np.asarray(read_wav(a / 'audio.wav')[1]).reshape(-1, 2)
        right = np.asarray(read_wav(b / 'audio.wav')[1]).reshape(-1, 2)
        self.assertEqual(left.shape, (12000, 2))
        np.testing.assert_allclose(left, right, atol=2e-6, rtol=0)
        self.assertLess(np.std(left[4500:6500]), np.std(left[500:1500]) * .4)
        self.assertGreater(np.std(left[10000:11500]), np.std(left[4500:6500]) * 2)
        log = json.loads((a / 'parameter-log.json').read_text())['entries']
        self.assertEqual([entry['frame'] for entry in log if entry['frame'] >= 0], [2003, 7001])
        self.assertAlmostEqual(log[-1]['immediate_readback'], default, places=6)

    def test_wrong_parameter_identity_and_version_are_rejected(self):
        plan = self.plan()
        plan['parameters'][0]['id'] = 'wrong'
        _, result = self.render(plan, 'bad-parameter', success=False)
        self.assertIn('differs from inventory', result.stderr)
        plan = self.plan()
        plan['expected_plugin']['version'] = 'wrong'
        _, result = self.render(plan, 'bad-version', success=False)
        self.assertIn('differs from capture plan', result.stderr)

    def test_out_of_order_events_are_rejected(self):
        plan = self.plan()
        plan['events'] = [self.setting('Output gain', .5) | {'frame': frame, 'type': 'parameter'}
                          for frame in (2000, 1000)]
        _, result = self.render(plan, 'unordered', success=False)
        self.assertIn('Events must be ordered', result.stderr)

    def test_existing_capture_is_preserved(self):
        destination, _ = self.render(self.plan(), 'existing')
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
        result = subprocess.run([str(self.host), 'render', str(self.plugin), str(self.input),
                                 str(self.root / 'existing.json'), str(destination)],
                                capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already exists', result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in destination.iterdir()})

    def test_post_render_dispatch_observes_down_latency_without_changing_audio(self):
        plan=self.plan()
        plan['parameters'] += [self.setting('Scene FX',1),self.setting('Scene source',0),
            self.setting('Scene depth',130/255),self.setting('Scene sub parameter 1',137/255)]
        before,_=self.render(plan,'latency-before')
        plan['post_render_message_pump_ms']=100
        after,_=self.render(plan,'latency-after')
        self.assertEqual((before/'audio.wav').read_bytes(),(after/'audio.wav').read_bytes())
        receipt=json.loads((after/'receipt.json').read_text())
        self.assertEqual(receipt['reported_latency_frames'],32)
        self.assertEqual(receipt['post_render_message_pump_ms'],100)

    def test_invalid_post_render_dispatch_is_rejected_before_capture(self):
        for i,value in enumerate((-1,251,.5,'invalid',True)):
            plan=self.plan();plan['post_render_message_pump_ms']=value
            destination,_=self.render(plan,f'invalid-dispatch-{i}',success=False)
            self.assertFalse(destination.exists())

    def test_nonfinite_input_cannot_produce_a_completed_receipt(self):
        write_wav(self.input, 48000, [float('nan'), 0] * 12000)
        _, result = self.render(self.plan(), 'invalid-audio', success=False)
        self.assertIn('non-finite', result.stderr)

    def test_midi_trigger_is_rendered_at_its_sample_timestamp(self):
        write_wav(self.input, 48000, [0, 0] * 12000)
        plan = self.plan()
        plan['parameters'][-1] = self.setting('Sampler mute', 0)
        plan['parameters'].append(self.setting('Sample source', 0))
        plan['events'] = [{'frame': 1001, 'type': 'midi', 'bytes': [144, 36, 127]},
                          {'frame': 1100, 'type': 'midi', 'bytes': [128, 36, 0]}]
        destination, _ = self.render(plan, 'midi-trigger')
        values = np.asarray(read_wav(destination / 'audio.wav')[1]).reshape(-1, 2)
        self.assertEqual(float(np.max(np.abs(values[:1001]))), 0)
        self.assertGreater(float(np.max(np.abs(values[1001:1100]))), .001)

    def test_auto_follows_host_tempo_and_manual_holds_stored_bpm(self):
        samples = np.zeros((24000, 2))
        samples[4096] = [.125, .0625]
        write_wav(self.input, 48000, samples.ravel())
        for automatic, delay in ((0, 12000), (1, 15984)):
            plan = self.plan()
            plan['bpm'] = 90
            plan['parameters'] = [self.setting(name, value) for name, value in (
                ('Auto BPM', automatic), ('BPM', .4), ('Sampler mute', 1),
                ('Isolate enabled', 0), ('Scene FX', 1/9), ('Scene enabled', 1),
                ('Scene depth', 1), ('Scene sub parameter 1', 128/255),
                ('Scene sub parameter 2', 0))]
            destination, _ = self.render(plan, f'tempo-{automatic}')
            values = np.asarray(read_wav(destination / 'audio.wav')[1]).reshape(-1, 2)
            onset = int(np.flatnonzero(np.abs(values[4097:, 0]) > 1e-7)[0])+4097
            self.assertEqual(onset, 4096+delay)

    def test_truncated_midi_message_is_rejected(self):
        plan = self.plan()
        plan['events'] = [{'frame': 1001, 'type': 'midi', 'bytes': [144, 36]}]
        _, result = self.render(plan, 'invalid-midi', success=False)
        self.assertIn('MIDI byte count', result.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--plugin', required=True)
    args, remainder = parser.parse_known_args()
    os.environ['RMX_REFERENCE_HOST'] = args.host
    os.environ['RMX_REFERENCE_FIXTURE'] = args.plugin
    unittest.main(argv=[__file__, *remainder])
