"""Failure-path tests against the delivered native routing evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from hardware.cad.signal_completion.review_routes import audit, retained_board_check
from hardware.electronics.common.sexpr import first, read_sexpr, sexpr

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / 'routes-01'
NATIVE = HERE / 'native-routes-01'


class NativeEvidenceRegression(unittest.TestCase):
    def run_changed_report(self, change):
        report = json.loads((NATIVE / 'native-review.json').read_text())
        change(report)
        with tempfile.TemporaryDirectory(prefix='signal-negative-') as directory:
            folder = Path(directory)
            (folder / 'native-review.json').write_text(json.dumps(report))
            (folder / 'signal_main.kicad_pcb').symlink_to(NATIVE / 'signal_main.kicad_pcb')
            audit(CANDIDATE, folder, folder / 'review.json')

    def test_complete_native_checkpoint_passes(self):
        with tempfile.TemporaryDirectory(prefix='signal-positive-', dir=HERE) as directory:
            output = Path(directory) / 'review.json'
            audit(CANDIDATE, NATIVE, output)
            self.assertTrue(json.loads(output.read_text())['accepted_routing_checkpoint'])

    def test_changed_global_stack_fails(self):
        path = NATIVE / 'signal_main.kicad_pcb'
        manifest = json.loads((CANDIDATE / 'routing.json').read_text())
        expected = {uid for row in manifest['routes'] for uid in row['segment_uuids']}
        board = read_sexpr(path.read_text())
        first(first(board, 'general'), 'thickness')[1] = 9.9
        with tempfile.TemporaryDirectory(prefix='signal-global-') as directory:
            changed = Path(directory) / path.name
            changed.write_text(sexpr(board))
            with self.assertRaisesRegex(AssertionError, 'Board-global settings changed'):
                retained_board_check(HERE.parent / 'two_board_sensor_05/signal_dac/native-r148/signal_main.kicad_pcb', changed, expected)

    def test_duplicate_copper_uuid_fails(self):
        def change(report):
            report['added_copper'].append(copy.deepcopy(report['added_copper'][0]))
        with self.assertRaisesRegex(AssertionError, 'Duplicate native added-copper UUID'):
            self.run_changed_report(change)

    def test_missing_reference_fails(self):
        with self.assertRaisesRegex(AssertionError, 'unreferenced introduced copper'):
            self.run_changed_report(lambda report: report.update(reference_fields=[]))

    def test_changed_fill_fails(self):
        with self.assertRaises(AssertionError):
            self.run_changed_report(lambda report: report.update(changed_filled_zone_uuids=['unexpected-zone']))

    def test_unexpected_opens_fail(self):
        with self.assertRaises(AssertionError):
            self.run_changed_report(lambda report: report.update(native_opens=163))

    def test_wrong_net_added_copper_fails(self):
        def change(report):
            report['added_copper'][0]['net'] = '/wrong-net'
        with self.assertRaises(AssertionError):
            self.run_changed_report(change)

    def test_extra_added_copper_fails(self):
        def change(report):
            extra = copy.deepcopy(report['added_copper'][0])
            extra['uuid'] = 'unapproved-segment'
            report['added_copper'].append(extra)
        with self.assertRaises(AssertionError):
            self.run_changed_report(change)


if __name__ == '__main__':
    unittest.main()
