"""Adopt checked U20 input/return planes and the back-side bulk-capacitor move."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-u20-input-native-01'
    previous = STAGING / 'two-board-fabrication-status-21/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'u20-input-routing.json', 'u20-input-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2462-u20-input/capture.json',
        STAGING / 'two-board-power-u20-input-filled-01/local-plane-fill.json',
        STAGING / 'two-board-signal-routed-native-03/review.json',
        STAGING / 'two-board-power-buck-enable-native-01/enable-dc-screen.json',
        STAGING / 'two-board-input-capacitor-review-01/review.json']
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
    a = json.loads((power / 'u20-input-audit.json').read_text())
    native = json.loads((power / 'review.json').read_text())
    assert a['new_opens'] == native['opens'] == 2462 and a['connections_closed'] == 7
    assert a['old_opens'] - a['new_opens'] == 7
    assert a['unchanged_complete_pin_net_map'] and a['all_old_tracks_vias_unchanged']
    assert a['all_other_copper_objects_unchanged'] and a['existing_U23_zones_and_fill_unchanged']
    assert a['all_previous_native_connection_groups_preserved'] == 3207
    assert a['geometry_findings'] == a['parity_findings'] == a['erc_errors'] == 0
    assert a['added_segments'] == 16 and a['added_vias'] == 13 and a['vias_screened'] == 180
    assert a['moved_footprints'] == a['flipped_footprints'] == 1 and a['changed_native_pad_instances'] == 2
    assert a['quiet_return_to_PGND_connected'] and a['configuration_return_enters_force_plane_only_near_BP5']
    assert a['sense_trace_projection_covered_by_In1_except_own_via_antipads']
    assert a['sense_projection_uncovered_area_mm2'] == 0
    assert len(a['local_plane_checks']) == 2 and all(p['single_contiguous_filled_polygon'] for p in a['local_plane_checks'])
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2462, power_copper_segments=2256, power_copper_vias=180,
        power_connections_closed_this_pass=7, power_moved_footprints_this_pass=1,
        power_flipped_footprints_this_pass=1,
        power_replaced_footprints_this_pass=0, power_changed_pad_instances_this_pass=2,
        power_retired_schematic_pins_this_pass=0, power_retired_terminal_opens_this_pass=0,
        power_all_component_poses_preserved=False,
        power_all_retained_copper_objects_unchanged=False, power_all_retained_copper_geometry_unchanged=False,
        power_all_retained_tracks_vias_unchanged=True, power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3207,
        power_previous_native_connection_groups_retired=0,
        power_all_vias_screened=180,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_local_filled_planes=4, power_whole_board_planes_complete=False,
        power_U20_input_route_sections=16, power_U20_input_added_tracks=16,
        power_U20_input_added_vias=13, power_U20_local_plane_checks=a['local_plane_checks'],
        power_U20_bulk_capacitor_move='C204: front (185,132) at 90deg to back (173,132) at 0deg; identical C205 package template',
        power_U20_local_input_output_quiet_return_connectivity_complete=True,
        power_U20_configuration_enable_and_feedback_top_complete=True,
        power_U20_effective_input_capacitance_qualified=False,
        power_U20_quiet_to_PGND_pending=False,
        power_U20_quiet_return_enters_plane_near_BP5=True,
        power_U20_sense_reference_plane_complete=True,
        power_U20_sense_reference_scope='Geometric coverage of 0.2mm trace projection except its own via clearances; field impedance/noise unqualified',
        power_U20_enable_reference_plane_complete=False,
        power_U20_placement_remaining_scope='Local U20 cell routed; wider distribution/current/thermal/derating and enable reference remain; AUX still unregrouped',
        power_existing_U23_planes_unchanged=True,
        power_copper_all_layers_visually_reviewed=True, power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Connect and qualify wider U20 input/output/force-return distribution and enable reference environment',
        'Review U23 quiet-return topology against the same near-BP5 force-plane entry criterion',
        *[s for s in status['next_required_design_work'] if not s.startswith('Complete U20 bulk input')]]
    out = STAGING / 'two-board-fabrication-status-22'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2462, signal_opens=251,
                          physical_connections_added=7, fabrication_released=False)))


if __name__ == '__main__':
    run()
