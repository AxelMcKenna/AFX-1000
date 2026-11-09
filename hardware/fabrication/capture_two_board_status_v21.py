"""Adopt the native-checked U20 enable routing without claiming electrical release."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-u20-enable-native-01'
    previous = STAGING / 'two-board-fabrication-status-20/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'u20-enable-routing.json', 'u20-enable-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2469-u20-enable/capture.json',
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
    a = json.loads((power / 'u20-enable-audit.json').read_text())
    native = json.loads((power / 'review.json').read_text())
    assert a['new_opens'] == native['opens'] == 2469 and a['connections_closed'] == 3
    assert a['old_opens'] - a['new_opens'] == 3
    assert a['unchanged_complete_pin_net_map'] and a['all_old_copper_objects_unchanged']
    assert a['all_component_poses_values_and_packages_unchanged'] and a['existing_local_U23_planes_unchanged']
    assert a['all_previous_native_connection_groups_preserved'] == 3210
    assert a['geometry_findings'] == a['parity_findings'] == a['erc_errors'] == 0
    assert a['added_segments'] == 8 and a['added_vias'] == 3 and a['vias_screened'] == 167
    assert a['enable_connected'] and a['enable_pulldown_ground_connected'] and a['shared_ready_feed_preserved']
    assert a['quiet_return_to_PGND_pending'] and not a['full_enable_electrical_qualification']
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2469, power_copper_segments=2240, power_copper_vias=167,
        power_connections_closed_this_pass=3, power_moved_footprints_this_pass=0,
        power_replaced_footprints_this_pass=0, power_changed_pad_instances_this_pass=0,
        power_retired_schematic_pins_this_pass=0, power_retired_terminal_opens_this_pass=0,
        power_all_component_poses_preserved=True,
        power_all_retained_copper_objects_unchanged=True, power_all_retained_copper_geometry_unchanged=True,
        power_all_retained_tracks_vias_unchanged=True, power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3210,
        power_previous_native_connection_groups_retired=0,
        power_all_vias_screened=167,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_U20_enable_connected=True, power_U20_enable_pulldown_ground_connected=True,
        power_U20_enable_full_electrical_qualified=False,
        power_U20_enable_reference_plane_complete=False,
        power_U20_enable_route_sections=6, power_U20_enable_added_tracks=8,
        power_U20_enable_added_vias=3, power_U20_enable_shared_READY_feed_preserved=True,
        power_U20_quiet_to_PGND_pending=True,
        power_U20_placement_remaining_scope='Bulk input and quiet/force returns; AUX remains unregrouped',
        power_existing_U23_planes_unchanged=True,
        power_copper_all_layers_visually_reviewed=True, power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete U20 bulk input topology and quiet/force return, sense and enable reference planes',
        *[s for s in status['next_required_design_work'] if not s.startswith('Complete U20 bulk input')]]
    out = STAGING / 'two-board-fabrication-status-21'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2469, signal_opens=251,
                          physical_connections_added=3, fabrication_released=False)))


if __name__ == '__main__':
    run()
