"""Noise statistics retain their gates without keeping large audio files."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tools.noise_statistics import measure, measure_powers, powers, stereo_correlation
from tools.rmx_noise_stream import RenderSpace
from tools.rmx_noise_user import check_readbacks
from tools.rmx_noise_user import xml


class NoiseStreamTests(unittest.TestCase):
    def test_verified_trajectory_pairing_preserves_ratio_and_rejects_wrong_gain(self):
        from tools.noise_reference_trajectory_statistics import measure
        common=np.exp(np.sin(np.arange(60))*2)
        total=np.repeat(common[:,None],2,axis=1)
        reference=dict(bands=np.repeat(total[:,None,:]/30,30,axis=1),total=total)
        small=reference|dict(bands=reference['bands']*10**(.02/10),total=total*10**(.02/10))
        result=measure(reference,small)
        self.assertEqual(result['verdict'],'pass')
        np.testing.assert_allclose(result['whole_level_ratio_db'],[.02,.02],atol=1e-12)
        wrong=reference|dict(bands=reference['bands']*10**.3,total=total*10**.3)
        self.assertEqual(measure(reference,wrong)['verdict'],'different')

    def test_random_profiles_allow_independent_exposures_and_reject_gain_error(self):
        from tools.noise_random_statistics import measure
        levels=np.broadcast_to(np.asarray([1.,2.,4.,8.])[None,:,None],(30,4,2)).copy()
        reference=dict(bands=np.repeat(levels[:,:,None,:]/6,6,axis=2),total=levels,exposure=np.full((30,4),100))
        different_exposure=reference|dict(exposure=np.full((30,4),150))
        self.assertEqual(measure(reference,different_exposure)['verdict'],'pass')
        self.assertEqual(measure(reference,different_exposure|dict(bands=reference['bands']*2,total=levels*2))['verdict'],'different')
        with self.assertRaisesRegex(ValueError,'exposure'):
            measure(reference,different_exposure|dict(exposure=np.zeros((30,4))))

    def test_sidechain_dry_subtraction_detects_one_sample_misalignment(self):
        from tools.rmx_noise_sidechain_controls import stimulus
        from tools.rmx_noise_sidechain_stream import residual
        from tools.reference_audio import write_wav
        pattern=stimulus('asymmetric');dry=np.tile(pattern,(2,1))
        with tempfile.TemporaryDirectory() as directory:
            for delay in [32,31]:
                shifted=np.zeros_like(dry);shifted[delay:]=dry[:-delay]
                path=Path(directory)/f'dry-{delay}.wav';write_wav(path,48000,shifted.reshape(-1))
                error=np.max(np.abs(residual(path,pattern)))
                if delay==32:self.assertEqual(error,0)
                else:self.assertGreater(error,.1)

    def test_motion_screen_rejects_wrong_gain_and_inverted_control_profile(self):
        from tools.noise_motion_statistics import measure
        levels=np.broadcast_to(np.asarray([1.,2.,4.,8.])[None,:,None],(30,4,2)).copy()
        bands=np.repeat(levels[:,:,None,:]/6,6,axis=2)
        reference=dict(bands=bands,total=levels,exposure=np.full((30,4),100))
        self.assertEqual(measure(reference,reference)['verdict'],'pass')
        for changed in [reference|dict(bands=bands*2,total=levels*2),reference|dict(bands=bands[:,::-1],total=levels[:,::-1])]:
            self.assertEqual(measure(reference,changed)['verdict'],'different')
        with self.assertRaisesRegex(ValueError,'exposure'):
            measure(reference,reference|dict(exposure=np.zeros((30,4))))

    def test_user_noise_width_order_and_required_scene_fields(self):
        import xml.etree.ElementTree as ET
        for width, original in enumerate([1, 0, 2]):
            root = ET.fromstring(xml(dict(width=width, minimum=1, maximum=2)))
            self.assertEqual(root.findtext('SceneFx/Lock'), '0')
            self.assertEqual(root.findtext('SceneFx/Noise/CenterFilterTypeCb'), str(original))
            self.assertEqual(len(root.find('SceneFx/Noise')), 6)

    def test_power_summaries_reproduce_waveform_screen(self):
        a = np.random.default_rng(73).normal(0, .1, (40*800, 2))
        b = a * .5
        x, tx = powers(a, 800); y, ty = powers(b, 800)
        expected = measure(a, b, 800)
        self.assertEqual(expected, measure_powers(x, tx, y, ty, 800, stereo_correlation(a), stereo_correlation(b)))
        self.assertEqual(expected['verdict'], 'different')

    def test_invalid_or_silent_summaries_are_rejected(self):
        bands = np.ones((20, 30, 2)); total = np.ones((20, 2))
        for changed, levels in [(bands[:-1], total), (bands*float('nan'), total), (bands, total*0)]:
            with self.subTest(shape=changed.shape), self.assertRaises(ValueError):
                measure_powers(changed, levels, bands, total, 48000, 0, 0)

    def test_host_double_request_and_serialized_float_readback(self):
        value = 81/255
        request = dict(name='SceneVolume', id='27', index=27, value=value)
        expected = dict(parameters=[request], events=[])
        log = [dict(name='SceneVolume', id='27', index=27, frame=-1,
                    requested_value=.317647058823529, immediate_readback=.317647069692612)]
        after = dict(parameters=[dict(name='SceneVolume', value=.317647069692612)])
        check_readbacks(expected, log, after)
        for key in ['requested_value', 'immediate_readback']:
            bad = [log[0] | {key: value+.001}]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'readback'):
                check_readbacks(expected, bad, after)

    def test_render_space_detects_budget_overrun_and_cleans_up(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='rmx-budget-test-') as temporary:
            root = Path(temporary); space = RenderSpace(root)
            with patch('tools.rmx_noise_stream.BUDGET', 16):
                with self.assertRaisesRegex(ValueError, 'budget'):
                    space.run([sys.executable, '-c', 'from pathlib import Path; Path(__import__("sys").argv[1]).write_bytes(b"x"*32)', str(root/'output')])
            self.assertEqual(space.peak, 32)
        self.assertFalse(root.exists())


if __name__ == '__main__': unittest.main()
