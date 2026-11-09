"""The additive LED construction must reject changes to retained circuitry."""
import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.digital_led_sink_checkpoint import additive_delta

ROOT = Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'


class LEDCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = read_sexpr((ROOT/'digital-xlat-bridge-native-01/digital_core.kicad_pcb').read_text())
        cls.after = read_sexpr((ROOT/'digital-post-xlat-bridges-routes-01/digital_core.kicad_pcb').read_text())
        cls.recipe = json.loads((ROOT/'digital-post-xlat-bridges-routes-01/construction.json').read_text())

    def test_actual_led49_addition_preserves_original_geometry(self):
        additive_delta(self.before, self.after, self.recipe)

    def test_existing_power_feed_cannot_be_narrowed(self):
        board = copy.deepcopy(self.after)
        track = next(n for n in children(board, 'segment') if first(n, 'uuid')[1] == 'aed69f03-b0cd-5897-804d-23e6631f3816')
        first(track, 'width')[1] = .2
        with self.assertRaises(AssertionError):
            additive_delta(self.before, board, self.recipe)

    def test_new_led_copper_cannot_be_reassigned_to_power(self):
        board = copy.deepcopy(self.after)
        track = next(n for n in children(board, 'segment') if first(n, 'net')[1] == '/LED/LED_49')
        first(track, 'net')[1] = '5V_DIG'
        with self.assertRaises(AssertionError):
            additive_delta(self.before, board, self.recipe)

    def test_smaller_new_drill_cannot_bypass_spacing_requirements(self):
        board = copy.deepcopy(self.after)
        via = next(n for n in children(board, 'via') if first(n, 'net')[1] == '/LED/LED_49')
        first(via, 'drill')[1] = .2
        with self.assertRaises(AssertionError):
            additive_delta(self.before, board, self.recipe)


if __name__ == '__main__':
    unittest.main()
