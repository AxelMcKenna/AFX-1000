"""Invalid wire handoffs must fail before a candidate can be staged."""
import copy
import unittest
from hardware.cad.assembly_workflow.stage_panel_inputs import validate


class PanelStagingContracts(unittest.TestCase):
    def setUp(self):
        self.parts = {'existing_wire': {}}
        self.old = [{'source': 'J1:1', 'target': 'switch1:1', 'net': '/CONTROL_1'}]
        edge = {'source': 'J1:2', 'target': 'switch2:1', 'net': '/CONTROL_2'}
        self.inventory = copy.deepcopy(self.old + [edge])
        self.reg = {'requires_roles': ['existing_wire'], 'components': [{'id': 'new_wire', 'role': 'receiving'}],
                    'candidate_inventory_edges': [edge]}

    def test_valid_additive_edge(self):
        ids, edges = validate(self.reg, self.parts, self.old, self.inventory)
        self.assertEqual(ids, ['new_wire'])
        self.assertEqual(len(edges), 2)

    def test_wrong_net_rejected(self):
        self.reg['candidate_inventory_edges'][0]['net'] = '/OTHER'
        with self.assertRaisesRegex(AssertionError, 'Wrong electrical net'):
            validate(self.reg, self.parts, self.old, self.inventory)

    def test_unknown_terminal_rejected(self):
        self.reg['candidate_inventory_edges'][0]['target'] = 'switch2:2'
        with self.assertRaisesRegex(AssertionError, 'Unknown inventory edge'):
            validate(self.reg, self.parts, self.old, self.inventory)

    def test_duplicate_edge_rejected(self):
        self.reg['candidate_inventory_edges'] = copy.deepcopy(self.old)
        with self.assertRaisesRegex(AssertionError, 'already selected'):
            validate(self.reg, self.parts, self.old, self.inventory)

    def test_replacement_requires_separate_review(self):
        self.reg['components'][0]['replaces_component'] = 'holder'
        with self.assertRaisesRegex(AssertionError, 'Only additive'):
            validate(self.reg, self.parts, self.old, self.inventory)

    def test_missing_dependency_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Missing required'):
            validate(self.reg, {}, self.old, self.inventory)

    def test_existing_role_rejected(self):
        self.reg['components'][0]['id'] = 'existing_wire'
        with self.assertRaisesRegex(AssertionError, 'Duplicate component'):
            validate(self.reg, self.parts, self.old, self.inventory)


if __name__ == '__main__':
    unittest.main()
