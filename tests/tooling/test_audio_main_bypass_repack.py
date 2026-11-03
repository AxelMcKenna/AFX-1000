"""Bypass relocation must preserve physical geometry, receiving and native endpoints."""
import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_bypass_repack as audit


class BypassRepack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / 'audio_core.kicad_pcb').read_text())
        cls.saved_record = json.loads((audit.OUT / 'distribution-construction.json').read_text())
        cls.capture = json.loads((audit.DRAFT / 'escaped-native-inputs.json').read_text())
        cls.witness = json.loads((audit.OUT / 'terminal-connectivity-review.json').read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.record = copy.deepcopy(self.saved_record)

    def verify_controls(self):
        record = dict(self.record, added_segments=[r for r in self.record['control_additions'] if r['kind']=='segment'],
                      added_vias=[r for r in self.record['control_additions'] if r['kind']=='via'],
                      trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01,
                      allowed_control_nets=sorted(audit.TARGETS), signal_layers=list(audit.LAYERS))
        return audit.verify_control_delta(self.board, record, self.capture)

    def test_complete_source_bound_handoff_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / 'routing-handoff.json').read_text()))

    def test_unrelated_analog_copper_cannot_be_removed(self):
        self.board.remove(children(self.board, 'segment')[0])
        with self.assertRaisesRegex(AssertionError, 'Parent analog/power'):
            self.verify_controls()

    def test_smaller_control_width_in_board_and_receipt_is_rejected(self):
        row = next(r for r in self.record['control_additions'] if r['kind']=='segment')
        node = next(n for n in children(self.board, 'segment') if first(n, 'uuid')[1]==row['uuid'])
        first(node, 'width')[1] = row['width_mm'] = .16
        with self.assertRaisesRegex(AssertionError, 'Control width changed'):
            self.verify_controls()

    def test_larger_drill_in_board_and_receipt_is_rejected(self):
        row = next(r for r in self.record['control_additions'] if r['kind']=='via')
        node = next(n for n in children(self.board, 'via') if first(n, 'uuid')[1]==row['uuid'])
        first(node, 'drill')[1] = row['drill_mm'] = .4
        with self.assertRaisesRegex(AssertionError, 'Control drill changed'):
            self.verify_controls()

    def test_island_cannot_merge_with_itself(self):
        self.record['routes'][0]['source_groups'][1] = self.record['routes'][0]['source_groups'][0]
        with self.assertRaisesRegex(AssertionError, 'False control island merge'):
            self.verify_controls()

    def test_longer_comparison_cannot_be_presented_as_electrically_qualified(self):
        row = next(r for r in self.record['routes'] if r['net']=='/BYPASS/INPUT_ENABLE')
        row['timing_loading_return_noise_and_EMC_qualified'] = True
        with self.assertRaises(AssertionError):
            self.verify_controls()

    def test_full_route_length_limit_cannot_be_expanded(self):
        row = next(r for r in self.record['routes'] if r['net']=='/BYPASS/INPUT_ENABLE')
        row['maximum_escape_inclusive_length_mm'] = 60
        with self.assertRaises(AssertionError):
            audit.verify_full_budgets(self.record)

    def test_unused_temporary_drill_cannot_be_retained(self):
        self.record['retired_unused_reserved_via_uuids'].pop()
        with self.assertRaises(AssertionError):
            audit.verify_full_budgets(self.record)

    def test_new_native_witness_cannot_omit_a_pad(self):
        witness = copy.deepcopy(self.witness)
        witness['new_route_witnesses'][0]['contacts'].pop()
        with self.assertRaisesRegex(AssertionError, 'complete native pad witnesses'):
            audit.verify_terminals(witness, self.record, self.capture)

    def test_previously_connected_ground_cannot_be_lost(self):
        witness = copy.deepcopy(self.witness)
        witness['ground_pads'][0]['native_connected_to_input_ground'] = False
        with self.assertRaisesRegex(AssertionError, 'Ground terminal lost'):
            audit.verify_terminals(witness, self.record, self.capture)

    def test_unauthorized_pose_change_is_rejected(self):
        prepared = read_sexpr((audit.DRAFT / 'prepared-input.kicad_pcb').read_text())
        record = json.loads((audit.DRAFT / 'preparation-record.json').read_text())
        plan = json.loads((audit.DRAFT / 'plan.json').read_text())
        first(audit.fps(prepared)['U107'], 'at')[1] = 25
        with self.assertRaisesRegex(AssertionError, 'Undeclared pose'):
            audit.verify_preparation(prepared, record, plan)

    def test_supply_trunk_cannot_be_narrowed_in_board_and_receipt(self):
        before = read_sexpr((audit.DRAFT / 'prepared-input.kicad_pcb').read_text())
        after = read_sexpr((audit.DRAFT / 'powered-input.kicad_pcb').read_text())
        rows = json.loads((audit.DRAFT / 'power-construction.json').read_text())['additions']
        row = next(r for r in rows if r['kind']=='segment' and r['purpose']=='supervisor_power_trunk')
        node = next(n for n in children(after, 'segment') if first(n, 'uuid')[1]==row['uuid'])
        first(node, 'width')[1] = row['width_mm'] = .2
        with self.assertRaises(AssertionError):
            audit.verify_added_phase(before, after, rows, 'power')

    def test_unrelated_power_copper_cannot_be_pruned(self):
        old = read_sexpr((audit.ROOT / 'staging/audio-main-bypass-repack-03/distribution-input.kicad_pcb').read_text())
        already = set(self.record['native_identified_abandoned_tail_uuids'])
        replacement = next(n for n in children(old, 'segment') if first(n, 'uuid')[1] not in already and first(n, 'layer')[1]=='In2.Cu')
        row = next(n for n in self.record['native_identified_abandoned_tail_nodes'] if first(n, 'uuid')[1] not in audit.TAILS)
        previous = str(first(row, 'uuid')[1])
        row[:] = replacement
        self.record['native_identified_abandoned_tail_uuids'].remove(previous)
        self.record['native_identified_abandoned_tail_uuids'].append(str(first(row, 'uuid')[1]))
        with self.assertRaises(AssertionError):
            audit.verify_tail_chains(self.record, self.capture)


if __name__ == '__main__':
    unittest.main()
