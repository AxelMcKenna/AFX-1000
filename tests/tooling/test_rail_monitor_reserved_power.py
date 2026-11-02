"""Ensure the supply-first E13 experiment preserves the circuit and ground plane."""
import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import native_evidence_errors


class ReservedPower(unittest.TestCase):
    def test_actual_native_supply_network_has_no_opens_or_suppressed_rules(self):
        repo = Path(__file__).resolve().parents[2]
        folder = repo/'hardware/fabrication/staging/rail-monitor-v3-tree-native-01'
        project = folder/'rail_monitor.kicad_pro'
        report = json.loads((folder/'review.json').read_text())
        self.assertEqual(native_evidence_errors(project,report),[])
        self.assertEqual(report['status']['counts']['violations'],0)
        self.assertTrue(report['status']['all_native_rule_checks_enabled'])
        drc = json.loads((folder/'drc.json').read_text())
        for connection in drc['unconnected_items']:
            for item in connection['items']:
                self.assertFalse(any(f'[{net}]' in item['description'] for net in ('/AGND','/V5_REG','/V3V3_IO')))
        original = repo/'hardware/electronics/rail_monitor/generated/netlist.xml'
        old_parts, old_pins = netlist(original)
        parts, pins = netlist(folder/'netlist.xml')
        self.assertEqual(pins,old_pins)
        self.assertEqual(set(parts),set(old_parts))
        for ref in parts:
            for field in ('value','footprint'):
                self.assertEqual(parts[ref].findtext(field),old_parts[ref].findtext(field))

    def test_reservation_does_not_add_signal_tracks_to_ground_or_supply_layers(self):
        repo = Path(__file__).resolve().parents[2]
        base = repo/'hardware/fabrication/staging/rail-monitor-supply-first-native-02/rail_monitor.kicad_pcb'
        final = repo/'hardware/fabrication/staging/rail-monitor-v3-tree-native-01/rail_monitor.kicad_pcb'
        old, new = [read_sexpr(p.read_text()) for p in (base,final)]
        self.assertEqual([sexpr(f) for f in children(old,'footprint')],
                         [sexpr(f) for f in children(new,'footprint')])
        for track in children(new,'segment'):
            layer = first(track,'layer')[1]
            self.assertIn(layer,('F.Cu','B.Cu','In2.Cu'))
            if layer == 'In2.Cu':
                self.assertEqual(first(track,'net')[-1],'/V3V3_IO')
                self.assertGreaterEqual(float(first(track,'width')[1]),.4)
        def authored_ground(tree):
            return [sexpr([v for v in z if not (isinstance(v,list) and v and v[0]=='filled_polygon')])
                    for z in children(tree,'zone') if first(z,'net')[-1]=='/AGND']
        self.assertEqual(authored_ground(old),authored_ground(new))


if __name__ == '__main__':
    unittest.main()
