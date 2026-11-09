"""Select the reviewed inlet-corridor geometry without asserting fab readiness."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING/'two-board-power-inlet-corridor-native-02'
    signal = STAGING/'two-board-signal-routed-native-03'
    previous = STAGING/'two-board-fabrication-status-32/status.json'
    reports = [previous, signal/'review.json', *[power/n for n in [
        'review.json', 'circuit-audit.json', 'inlet-corridor-routing.json',
        'inlet-corridor-review.json', 'rejected-source-net-status.json',
        'plots/native-plots.json', 'plots/preview-render.json', 'plots/detail-render.json',
        'plots/mount-render.json', 'plots/entry-render.json', 'plots/visual-review.json']],
        STAGING/'two-board-power-routing-inputs-2374-inlet-corridor-02/capture.json',
        STAGING/'two-board-power-inlet-corridor-filled-02/local-plane-fill.json']
    count = 0
    for p in reports:
        d = json.loads(p.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in d.get(field, {}).items():
                q = Path(name)
                if not q.is_absolute():
                    q = (REPO if name.startswith(('hardware/', 'tests/')) else p.parent)/q
                assert sha(q) == h, (p, name)
                count += 1
    old = json.loads(previous.read_text())
    audit, native, visual, sig = [json.loads(p.read_text()) for p in [
        power/'inlet-corridor-review.json', power/'review.json',
        power/'plots/visual-review.json', signal/'review.json']]
    assert audit['new_opens'] == native['opens'] == 2374 and sig['uncapped_open_connections'] == 251
    assert audit['old_opens'] == old['power_opens'] == 2383 and audit['connections_closed'] == 9
    assert audit['all_prior_connection_groups_preserved'] == 3121
    assert audit['complete_footprints_unchanged'] == 1101 and audit['pin_net_map_unchanged']
    assert audit['total_tracks'] == 2444 and audit['total_vias'] == 250
    assert audit['geometry_errors'] == audit['parity_errors'] == audit['ERC_errors'] == 0
    assert audit['ERC_warnings'] == 2 and len(audit['fast_OV_reference_coverage']) == 33
    assert audit['AUX_ground_group_and_local_copper_unchanged'] and audit['G_NT1_isolated']
    assert len(visual['inspected_views']) == 20 and not visual['complete_delta_audit_pending']
    assert all(abs(z['H_NEW2_cross_section_total_mm']-5.56) < 1e-6
               for z in audit['new_zones'] if z['layer'].startswith('In'))
    sources = [Path(__file__), *reports, power/'README.md']
    status = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='Historical circuit and design evidence; current geometry is described by this revision and its direct reports.',
        verified_direct_source_and_artifact_bindings=count,
        signal_project=str((signal/'signal_main.kicad_pro').relative_to(REPO)), signal_opens=251,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)), power_opens=2374,
        power_geometry_findings=0, power_schematic_parity_findings=0, power_ERC_errors=0, power_ERC_warnings=2,
        power_parts=1086, power_footprints=1101, power_schematic_pin_entries=3420, power_mapped_pad_instances=3481,
        power_copper_segments=2444, power_copper_vias=250, power_filled_zones=19,
        power_connections_closed_this_pass=9, power_added_vias_this_pass=16, power_added_zones_this_pass=5,
        power_previous_native_connection_groups_preserved=3121, power_complete_footprints_unchanged=1101,
        power_moved_footprints_this_pass=0, power_schematic_pin_net_changes_this_pass=0,
        power_retired_tracks_this_pass=0, power_retired_vias_this_pass=0,
        power_unchanged_existing_zone_fills=11, power_changed_existing_zone_fills=3,
        power_native_group_merges=audit['new_group_merges'],
        power_inlet_geometry_review=str((power/'inlet-corridor-review.json').relative_to(REPO)),
        power_inlet_feed_connected=True, power_inlet_return_connected=True,
        power_input_TVS_connected=False, power_inlet_full_current_thermal_transient_qualified=False,
        power_inlet_H_NEW2_total_width_per_layer_mm=5.56,
        power_inlet_minimum_nominal_hole_edge_gap_mm=min(z['minimum_nominal_drill_edge_gap_mm'] for z in audit['new_zones']),
        power_inlet_In5_fill_pieces=2, power_inlet_all_new_filled_pieces_connected_to_intended_group=True,
        power_source_bank_contact_vias=5, power_all_vias_screened=250,
        power_minimum_all_via_drill_to_SMD_mm=audit['all_via_minimum_drill_to_SMD_mm'],
        power_fast_OV_route_sections_with_adjacent_ground=33, power_fast_OV_reference_geometry_passed=True,
        power_fast_OV_electrical_response_qualified=False, power_AUX_ground_group_and_local_copper_preserved=True,
        power_AUX_load_derating_startup_and_thermal_qualified=False, power_G_NT1_connected=False,
        power_copper_all_layers_visually_reviewed=True, power_full_system_return_qualified=False,
        power_complete_circuit=False, stack_accepted=False, full_installed_fit_verified=False,
        next_required_design_work=[
            'Connect and qualify the input TVS and its surge return; its two pads remain isolated',
            'Qualify inlet feed/return current sharing, voltage drop and thermal margin, including fuse, jack-to-fuse neck, both transition banks and mounting-hole sections',
            'Complete full system current returns and remaining distribution; G_NT1 remains isolated',
            *[q for q in old['next_required_design_work'] if not q.startswith('Complete external input-cable feed')]],
        other_open_release_requirements=old['other_open_release_requirements'],
        fabrication_released=False, goal_complete=False)
    out = STAGING/'two-board-fabrication-status-33'; out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(dict(bindings=count, power_opens=2374, signal_opens=251,
                         connections_closed=9, fabrication_released=False)))


if __name__ == '__main__':
    run()
