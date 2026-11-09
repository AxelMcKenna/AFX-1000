"""Adopt the checked U20 output bank without claiming full power qualification."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-u20-output-native-02'
    previous = STAGING / 'two-board-fabrication-status-18/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'u20-output-routing.json', 'u20-output-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2478-u20-output/capture.json',
        STAGING / 'two-board-signal-routed-native-03/review.json']
    count = 0
    for report in reports:
        data = json.loads(report.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in data.get(field, {}).items():
                p = Path(name)
                if not p.is_absolute():
                    p = (REPO if name.startswith(('hardware/', 'tests/')) else report.parent) / p
                assert p.is_file() and sha(p) == h, (report, name)
                count += 1
    a = json.loads((power / 'u20-output-audit.json').read_text())
    native = json.loads((power / 'review.json').read_text())
    assert a['new_opens'] == native['opens'] == 2478 and a['connections_closed'] == 8
    assert a['old_opens'] - a['new_opens'] == 8
    assert a['unchanged_complete_pin_net_map'] and a['all_old_copper_objects_unchanged']
    assert a['all_component_poses_values_and_packages_unchanged'] and a['existing_local_U23_planes_unchanged']
    assert a['all_previous_native_connection_groups_preserved'] == 3224
    assert a['geometry_findings'] == a['parity_findings'] == a['erc_errors'] == 0
    assert a['added_segments'] == 17 and a['added_vias'] == 6 and a['vias_screened'] == 157
    assert a['output_bank_connected_to_inductor'] and a['output_bank_connected_to_regulator_PGND']
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2478, power_copper_segments=2216, power_copper_vias=157,
        power_connections_closed_this_pass=8, power_moved_footprints_this_pass=0,
        power_replaced_footprints_this_pass=0, power_changed_pad_instances_this_pass=0,
        power_retired_schematic_pins_this_pass=0, power_retired_terminal_opens_this_pass=0,
        power_all_component_poses_preserved=True,
        power_all_retained_copper_objects_unchanged=True, power_all_retained_copper_geometry_unchanged=True,
        power_all_retained_tracks_vias_unchanged=True, power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3224,
        power_previous_native_connection_groups_retired=0,
        power_all_vias_screened=157,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_U20_output_bank_connected_to_inductor_and_PGND=True,
        power_U20_output_bank_route_sections=16, power_U20_output_bank_added_tracks=17,
        power_U20_output_bank_added_vias=6,
        power_U20_output_bank_current_thermal_stability_qualified=False,
        power_U20_effective_input_capacitance_qualified=False,
        power_U20_placement_remaining_scope='Bulk input/quiet return and feedback/enable access; AUX remains unregrouped',
        power_existing_U23_planes_unchanged=True,
        power_copper_all_layers_visually_reviewed=True, power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete U20 bulk input, FSEL/MODE/enable, feedback top/sense and quiet/force return planes',
        'Reconcile exact input MPN/derating to at least 2uF effective near each VIN/PGND side; the old 1uF allocation alone is insufficient',
        *[s for s in status['next_required_design_work'] if not s.startswith('Complete U20 bulk input/output')]]
    out = STAGING / 'two-board-fabrication-status-19'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2478, signal_opens=251,
                          physical_connections_added=8, fabrication_released=False)))


if __name__ == '__main__':
    run()
