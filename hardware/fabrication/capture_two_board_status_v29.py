"""Adopt the independently checked IN_SYS bypass and PGTH routing revision."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING/'two-board-power-input-bypass-native-03'
    previous = STAGING/'two-board-fabrication-status-28/status.json'
    reports = [previous, *[power/n for n in [
        'review.json', 'circuit-audit.json', 'input-bypass-routing.json',
        'input-bypass-audit.json', 'input-bypass-plane-review.json',
        'rejected-source-net-status.json', 'plots/native-plots.json',
        'plots/preview-render.json', 'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING/'two-board-power-routing-inputs-2420-input-bypass/capture.json',
        STAGING/'two-board-power-input-bypass-filled-03/local-plane-fill.json',
        STAGING/'two-board-aux-load-review-01/review.json',
        STAGING/'two-board-aux-load-review-01/verification.json',
        STAGING/'two-board-signal-routed-native-03/review.json']
    count = 0
    for report in reports:
        d = json.loads(report.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in d.get(field, {}).items():
                p = Path(name)
                if not p.is_absolute(): p = (REPO if name.startswith(('hardware/', 'tests/')) else report.parent)/p
                assert p.is_file() and sha(p) == h, (report, name)
                count += 1
    audit = json.loads((power/'input-bypass-audit.json').read_text())
    native = json.loads((power/'review.json').read_text())
    planes = json.loads((power/'input-bypass-plane-review.json').read_text())
    visual = json.loads((power/'plots/visual-review.json').read_text())
    assert audit['new_opens'] == native['opens'] == 2420 and audit['old_opens'] == 2427 and audit['connections_closed'] == 7
    assert audit['all_previous_connection_groups_preserved'] == planes['all_previous_connection_groups_preserved'] == 3165
    for key in ['unchanged_complete_pin_net_map', 'all_values_and_package_identifiers_unchanged',
        'back_C101_matches_retained_C102_package', 'all_retained_tracks_vias_and_unmoved_pads_unchanged',
        'all_native_zone_declarations_and_fill_provenance_verified', 'all_native_instance_paths_canonical']:
        assert audit[key], key
    assert audit['geometry_errors'] == audit['parity_errors'] == audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    assert planes['all_thirteen_native_planes_contiguous'] and planes['AUX_input_output_returns_separate_after_GND_land_cut']
    assert planes['full_control_reference_uncovered_mm2'] == planes['bulk_output_trace_reference_uncovered_mm2_excluding_own_antipads'] == 0
    assert audit['tracks'] == 2354 and audit['vias'] == 207 and audit['zones'] == 13 and audit['unchanged_existing_zones'] == 7
    assert not visual['complete_delta_audit_pending'] and len(visual['inspected_views']) == 7
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2420, power_copper_segments=2354, power_copper_vias=207,
        power_connections_closed_this_pass=7, power_moved_footprints_this_pass=4,
        power_flipped_footprints_this_pass=1, power_replaced_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=8, power_all_component_poses_preserved=False,
        power_component_pose_exception='C101 moves to the back using the identical C102 package; R106/R110/R111 move on the back. Values, packages and logical pin/net mapping remain unchanged.',
        power_all_retained_copper_objects_unchanged=False, power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='Eight moved pads, five retired/replaced PG tracks, one retired/replaced PG via, and six refilled regions. All retained tracks/vias, unmoved pads, all zone outlines/settings and seven earlier fills remain exact.',
        power_all_retained_tracks_vias_unchanged=True, power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3165,
        power_all_vias_screened=207,
        power_minimum_all_via_drill_to_SMD_mm=audit['all_via_minimum_drill_to_SMD_mm'],
        power_local_plane_contacts_preserved=False,
        power_local_plane_contact_change='Two new ground vias join the local U101 front/In1 return for C101 and R106; previous ground contacts and AUX split-return topology remain intact.',
        power_input_bypass_routing_audit=str((power/'input-bypass-audit.json').relative_to(REPO)),
        power_input_bypass_plane_review=str((power/'input-bypass-plane-review.json').relative_to(REPO)),
        power_input_IN_SYS_bypass_locally_connected=True,
        power_input_IN_SYS_connected_to_Q101_source_bank=True,
        power_input_PGTH_divider_locally_connected=True,
        power_input_UV_OV_dividers_and_clamp_connected=False,
        power_input_bypass_loop_and_final_reference_qualified=False,
        power_input_bypass_and_voltage_thresholds_complete=False,
        power_input_control_ground_plane_checks=[q for q in planes['plane_contacts'] if q['uuid'] in ['a147ef12-37f5-562e-9340-6c74b3790186', 'd41ab58e-16e9-5d76-8b14-dc335aff8371']],
        power_AUX_ground_plane_checks=[q for q in planes['plane_contacts'] if q['uuid'] in ['d0572a8e-b95d-5c59-9a7c-1d3514a507b4', '94ece1a2-cfec-59cf-ba79-c618ed566f57', 'bc76c316-2c04-5ecb-85b7-3e5f80b26bf1', 'dfd01f0a-edcf-55b7-aecb-2d44a419b9b3']],
        power_duplicate_paths_removed_this_pass=0,
        power_local_input_bypass_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete input UV/OV dividers and clamp, input-cable feed, VIN link to AUX and system return; local IN_SYS bypass and PGTH divider are now connected',
        'Qualify complete bypass-loop inductance, final adjacent-layer reference, exact passive MPN/derating and threshold tolerances',
        *[q for q in status['next_required_design_work'] if not q.startswith('Resolve the input IN_SYS bypass')]]
    out = STAGING/'two-board-fabrication-status-29'; out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(dict(bindings=count, power_opens=2420, signal_opens=251, connections_closed=7, fabrication_released=False)))


if __name__ == '__main__': run()
