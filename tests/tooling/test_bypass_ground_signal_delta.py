import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta
from hardware.fabrication.audit_bypass_ground_signal_delta import verify_delta, LED, CODEC, GROUND_TRACK, GROUND_VIA

ROOT = Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'


class BypassGroundSignalDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = read_sexpr((ROOT/'digital-blank-codec-native-01/digital_core.kicad_pcb').read_text())
        cls.after = read_sexpr((ROOT/'digital-bypass-ground-signal-repair-03/digital_core.kicad_pcb').read_text())
        cls.recipe = json.loads((ROOT/'digital-bypass-ground-signal-repair-03/construction.json').read_text())

    def check_rejected(self, board, recipe=None):
        recipe = copy.deepcopy(self.recipe) if recipe is None else recipe
        recipe['geometry_delta'] = geometry_delta(self.before, board)
        with self.assertRaises(AssertionError):
            verify_delta(self.before, board, recipe)

    def test_exact_three_signal_thermal_repair_passes(self):
        verify_delta(self.before, self.after, self.recipe)

    def test_undisclosed_power_feed_change_fails(self):
        board = copy.deepcopy(self.after)
        track = next(n for n in children(board,'segment') if first(n,'uuid')[1] == 'aed69f03-b0cd-5897-804d-23e6631f3816')
        first(track,'width')[1] = .8
        self.check_rejected(board)

    def test_pad_reassignment_fails(self):
        board = copy.deepcopy(self.after)
        pad = next(p for f in children(board,'footprint') for p in children(f,'pad') if children(p,'net') and first(p,'net')[-1] == CODEC)
        first(pad,'net')[-1] = LED
        self.check_rejected(board)

    def test_new_led_copper_cannot_be_reassigned_to_codec(self):
        board = copy.deepcopy(self.after)
        track = next(n for n in children(board,'segment') if first(n,'net')[1] == LED)
        first(track,'net')[1] = CODEC
        self.check_rejected(board)

    def test_smaller_via_drill_fails(self):
        board = copy.deepcopy(self.after)
        via = next(n for n in children(board,'via') if first(n,'uuid')[1] in self.recipe['geometry_delta']['via']['added'])
        first(via,'drill')[1] = .25
        self.check_rejected(board)

    def test_missing_codec_repair_path_evidence_fails(self):
        recipe = copy.deepcopy(self.recipe)
        next(r for r in recipe['routes'] if r['net'] == CODEC)['runs'].pop()
        self.check_rejected(copy.deepcopy(self.after), recipe)


    def test_narrower_thermal_branch_fails(self):
        board=copy.deepcopy(self.after)
        track=next(n for n in children(board,'segment') if first(n,'uuid')[1]==GROUND_TRACK)
        first(track,'width')[1]=.2
        self.check_rejected(board)

    def test_smaller_relocated_thermal_drill_fails(self):
        board=copy.deepcopy(self.after)
        via=next(n for n in children(board,'via') if first(n,'uuid')[1]==GROUND_VIA)
        first(via,'drill')[1]=.25
        self.check_rejected(board)

    def test_undeclared_thermal_branch_endpoint_fails(self):
        board=copy.deepcopy(self.after)
        track=next(n for n in children(board,'segment') if first(n,'uuid')[1]==GROUND_TRACK)
        first(track,'start')[1]=97.0
        self.check_rejected(board)

if __name__ == '__main__':
    unittest.main()
