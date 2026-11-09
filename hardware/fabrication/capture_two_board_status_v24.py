"""Adopt the native-checked AUX cell without claiming complete power design."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-aux-local-native-01'
    previous = STAGING / 'two-board-fabrication-status-23/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'aux-local-routing.json', 'aux-local-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2447-aux-local/capture.json',
        STAGING / 'two-board-power-aux-local-filled-01/local-plane-fill.json',
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
    a = json.loads((power / 'aux-local-audit.json').read_text())
    native = json.loads((power / 'review.json').read_text())
    assert a['old_opens'] == 2462 and a['new_opens'] == native['opens'] == 2447 and a['connections_closed'] == 15
    assert a['unchanged_complete_pin_net_map'] and a['all_old_tracks_vias_unchanged']
    assert a['all_unmoved_pads_unchanged'] and a['all_values_packages_and_sides_preserved']
    assert a['all_four_authored_zones_and_native_fills_unchanged']
    assert a['all_previous_native_connection_groups_preserved'] == 3200
    assert a['geometry_findings'] == a['parity_findings'] == a['erc_errors'] == 0
    assert a['added_segments'] == 32 and a['added_vias'] == 5 and a['vias_screened'] == 186
    assert a['moved_footprints'] == 8 and a['changed_pad_instances'] == 27
    assert a['regulator_and_capacitors_same_front_side']
    assert set(a['verified_terminal_groups']) == {'input-and-enable','output','ground','delay','feedback','trim'}
    assert a['PG_and_NC_not_routed']
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2447, power_copper_segments=2289, power_copper_vias=186,
        power_connections_closed_this_pass=15, power_moved_footprints_this_pass=8,
        power_flipped_footprints_this_pass=0, power_replaced_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=27, power_retired_schematic_pins_this_pass=0,
        power_retired_terminal_opens_this_pass=0, power_all_component_poses_preserved=False,
        power_all_retained_copper_objects_unchanged=False, power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='Eight AUX footprints moved/rotated; all old tracks, vias, unmoved pads and four zones/fills unchanged',
        power_all_retained_tracks_vias_unchanged=True, power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3200,
        power_previous_native_connection_groups_retired=0, power_all_vias_screened=186,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_local_filled_planes=4, power_whole_board_planes_complete=False,
        power_existing_U23_planes_unchanged=True, power_U20_planes_and_U23_VIN_plane_unchanged=True,
        power_local_plane_contacts_preserved=True, power_local_plane_contact_change=None,
        power_U20_and_AUX_local_placement_requires_repair=False,
        power_U20_placement_remaining_scope='Local U20 cell routed; wider distribution/current/thermal/derating and enable reference remain',
        power_AUX_placement_candidate_native_validation_pending=False,
        power_AUX_placement_candidate_implemented=True,
        power_AUX_placement_revision='Eight moved footprints; R108 and R130 revised from the original seven-move survey',
        power_AUX_local_routing_audit=str((power/'aux-local-audit.json').relative_to(REPO)),
        power_AUX_local_capacitor_feedback_enable_connected=True,
        power_AUX_local_route_sections=20, power_AUX_local_added_tracks=32,
        power_AUX_local_added_vias=5, power_AUX_local_connections_closed=15,
        power_AUX_input_output_ground_regions_and_thermal_vias_complete=False,
        power_AUX_source_output_distribution_and_PG_connected=False,
        power_AUX_load_derating_startup_and_thermal_qualified=False,
        power_copper_all_layers_visually_reviewed=True, power_local_AUX_detail_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete AUX input/output ground regions, thermal vias and feedback shielding, then source/output distribution and power-good routing',
        'Verify full AUX load, derated effective capacitance, regulator dissipation, startup and shared enable behavior',
        'Regroup remaining source/protection critical circuits; audit every terminal before further internal-port removal',
        *[s for s in status['next_required_design_work'] if not s.startswith(('Implement and natively validate the screened AUX cell', 'Regroup AUX and remaining critical circuits'))]]
    out = STAGING / 'two-board-fabrication-status-24'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2447, signal_opens=251,
                          physical_connections_added=15, fabrication_released=False)))


if __name__ == '__main__':
    run()
