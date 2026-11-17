"""Verify the completed right-input/relay connection in the native checkpoint."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from hardware.cad.signal_completion.verify_selected import selected_pcb

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


class BypassNativeConnectivity(unittest.TestCase):
    def test_selection_cannot_redirect_gate_to_another_board(self):
        selection = json.loads((ROOT / 'hardware/cad/assembly_workflow/current.json').read_text())
        redirected = copy.deepcopy(selection)
        redirected['boards']['signal'] = str(Path(selection['boards']['signal']).with_name('different.kicad_pcb'))
        with self.assertRaisesRegex(AssertionError, 'not the board checked'):
            selected_pcb(redirected)

    def test_receiving_pads_share_native_group(self):
        capture = HERE / 'capture-routes-03/capture.json'
        record = json.loads((HERE / 'integration-review-02.json').read_text())
        self.assertEqual(hashlib.sha256(capture.read_bytes()).hexdigest(), record['source_sha256'][str(capture.relative_to(ROOT))])
        data = json.loads(capture.read_text())
        for name, expected in data['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        wanted = {('A_J607', '3'), ('A_K601', '7'), ('A_K602', '5')}
        pads = [o for o in data['objects'] if (o.get('ref'), o.get('pin')) in wanted]
        self.assertEqual(len(pads), 3)
        self.assertEqual({o['net'] for o in pads}, {'/A_BYPASS/IN_R'})
        self.assertEqual(len({o['group'] for o in pads}), 1)
        self.assertIsNotNone(pads[0]['group'])
        self.assertEqual(data['native_uncapped_opens'], 143)
        self.assertEqual(data['independent_sum_of_pad_cluster_gaps'], 143)


if __name__ == '__main__':
    unittest.main()
