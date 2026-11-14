"""Bind TBP67 native, independent topology, supply-delta and visual evidence."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    folder = STAGING / 'two-board-power-monitor-return-planes-native-01'
    target = folder / 'final-review.json'
    assert not target.exists()
    paths = [folder / 'review.json', folder / 'monitor-return-planes-review.json',
             STAGING / 'two-board-monitor-inlet-via-comparison-01/review.json',
             STAGING / 'two-board-power-routing-inputs-monitor-return-planes-01/capture.json',
             STAGING / 'two-board-control-return-survey-after-08/survey.json',
             folder / 'plots/visual-review.json', folder / 'plots/native-plots.json',
             folder / 'plots/monitor2-render.json', folder / 'plots/west2-render.json']
    data = [json.loads(p.read_text()) for p in paths]
    cached = {}
    bindings = 0
    for path, report in zip(paths, data):
        for key in ['source_sha256', 'artifact_sha256']:
            for name, digest in report.get(key, {}).items():
                source = Path(name)
                if not source.is_absolute():
                    source = (REPO if name.startswith(('hardware/', 'tests/')) or name == 'uv.lock' else path.parent) / source
                if source not in cached:
                    cached[source] = sha(source)
                assert cached[source] == digest, (path, name)
                bindings += 1
    native, audit, supply, capture, controls, visual, *_ = data
    assert native['opens'] == audit['new_opens'] == capture['native_uncapped_opens'] == 2037
    assert native['geometry_findings'] == native['schematic_parity_findings'] == audit['ERC_errors'] == 0
    assert audit['ERC_warnings'] == 2 and audit['closed_connections'] == 5
    assert audit['all_other_native_groups_preserved']
    assert audit['all_original_objects_placements_and_schematic_nets_preserved']
    assert audit['quiet_network_fields_preserved'] == 7 and audit['nine_supply_planes_unchanged']
    assert len(audit['retained_reference_checks']) == 2401
    assert len(audit['new_reference_checks']) == 4 and len(audit['plane_stitches']) == 15
    assert supply['numerical_refinement_within_2_percent'] and supply['native_contacts_identical']
    assert supply['nine_other_supply_fields_exact']
    assert {r['uuid'] for r in supply['supply_deltas']} == {r['uuid'] for r in audit['supply_plane_deltas']}
    assert controls['unreferenced_existing_tracks'] == 4 and controls['new_unreferenced_tracks'] == 0
    assert visual['inspection_complete'] and len(visual['views_inspected']) == 9
    # Independent native pad-group check against every SN74 ground in netlist.
    tree = ET.parse(folder / 'netlist.xml')
    values = {c.attrib['ref']: c.findtext('value') for c in tree.findall('./components/comp')}
    nodes = [p.attrib for n in tree.findall('./nets/net') if n.attrib['name'] == 'PWR_AGND'
             for p in n.findall('node') if values[p.attrib['ref']].startswith('SN74')
             and p.attrib.get('pintype') == 'power_in' and p.attrib.get('pinfunction', '').startswith('GND')]
    pads = {(o['ref'], o['pin']): o for o in capture['objects'] if o['kind'] == 'PAD'}
    main = pads['P_C103', '2']['group']
    assert len(nodes) == 75 and all(pads[n['ref'], n['pin']]['group'] == main for n in nodes)
    sources = [Path(__file__), folder / 'netlist.xml', *paths]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  working_candidate='two-board-power-monitor-return-planes-native-01', revision='TBP67',
                  verified_direct_bindings=bindings, power_opens=2037, closed_connections=5,
                  surveyed_SN74_ground_pins=75, disconnected_surveyed_SN74_ground_pins=0,
                  retained_reference_checks=2401, quiet_networks_preserved=7,
                  remaining_control_connector_reference_gaps=4,
                  paired_input_sheet_resistance_relative_increase=supply['paired_comparisons'][2]['paired_resistance_relative_change'],
                  scope='Verified additive ground-routing working candidate. Input-sheet comparison is conditional and excludes via barrels and installed thermal/load behavior.',
                  supply_comparison_completed=True, supply_current_and_thermal_rating_qualified=False,
                  complete_routing=False, fabrication_released=False, goal_complete=False)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__':
    run()
