"""Adopt U23 quiet-return correction and a screened, unimplemented AUX candidate."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-u23-quiet-native-01'
    previous = STAGING / 'two-board-fabrication-status-22/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'u23-quiet-routing.json', 'u23-quiet-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2462-u23-quiet/capture.json',
        STAGING / 'two-board-power-u23-quiet-filled-01/local-plane-fill.json',
        STAGING / 'two-board-signal-routed-native-03/review.json',
        STAGING / 'two-board-power-buck-enable-native-01/enable-dc-screen.json',
        STAGING / 'two-board-input-capacitor-review-01/review.json',
        STAGING / 'two-board-aux-cell-survey-01/survey.json']
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
    a = json.loads((power / 'u23-quiet-audit.json').read_text())
    native = json.loads((power / 'review.json').read_text())
    assert a['old_opens'] == a['new_opens'] == native['opens'] == 2462 and a['connections_closed'] == 0
    assert a['unchanged_complete_pin_net_map'] and a['all_old_copper_objects_unchanged']
    assert a['all_component_poses_values_and_packages_unchanged']
    assert a['other_three_authored_zones_and_native_fills_unchanged']
    assert a['all_previous_native_connection_groups_preserved'] == 3200
    assert a['geometry_findings'] == a['parity_findings'] == a['erc_errors'] == 0
    assert a['added_segments'] == a['added_vias'] == 1 and a['vias_screened'] == 181
    assert a['remote_MODE_return_still_connected'] and a['configuration_return_enters_force_plane_only_near_BP5']
    assert a['sense_trace_projection_covered_except_own_via_antipads'] and a['sense_projection_uncovered_area_mm2'] == 0
    assert a['old_direct_ground_via_contacts'] == a['new_direct_ground_via_contacts'] == 12
    aux=json.loads(reports[-1].read_text())
    assert aux['candidate_only'] and aux['moved_footprints']==7 and not aux['physical_board_modified']
    assert aux['copper_courtyard_body_support_height_screen_pass']
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2462, power_copper_segments=2257, power_copper_vias=181,
        power_connections_closed_this_pass=0, power_moved_footprints_this_pass=0,
        power_flipped_footprints_this_pass=0,
        power_replaced_footprints_this_pass=0, power_changed_pad_instances_this_pass=0,
        power_retired_schematic_pins_this_pass=0, power_retired_terminal_opens_this_pass=0,
        power_all_component_poses_preserved=True,
        power_all_retained_copper_objects_unchanged=True, power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='U23 In1 ground outline/fill recessed; all ordinary copper objects unchanged',
        power_all_retained_tracks_vias_unchanged=True, power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3200,
        power_previous_native_connection_groups_retired=0,
        power_all_vias_screened=181,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_local_filled_planes=4, power_whole_board_planes_complete=False,
        power_U23_quiet_return_enters_plane_near_BP5=True,
        power_U23_ground_plane_area_mm2=a['new_U23_ground_plane_area_mm2'],
        power_U23_direct_plane_contact_replaced=a['changed_direct_plane_contact_removed'],
        power_U23_remote_MODE_return_connection_preserved=True,
        power_local_plane_contacts_preserved=False,
        power_local_plane_contact_change='Remote MODE direct plane contact removed; existing trace retains connection; added BP5 via contacts plane',
        power_existing_U23_planes_unchanged=False,
        power_U20_planes_and_U23_VIN_plane_unchanged=True,
        power_AUX_placement_candidate=str(reports[-1].relative_to(REPO)),
        power_AUX_placement_candidate_native_validation_pending=True,
        power_AUX_placement_candidate_implemented=False,
        power_copper_all_layers_visually_reviewed=True, power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Implement and natively validate the screened AUX cell, preserving short same-side capacitor paths and controlled return/feedback topology',
        *[s for s in status['next_required_design_work'] if not s.startswith('Review U23 quiet-return topology')]]
    out = STAGING / 'two-board-fabrication-status-23'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2462, signal_opens=251,
                          physical_connections_added=0, fabrication_released=False)))


if __name__ == '__main__':
    run()
