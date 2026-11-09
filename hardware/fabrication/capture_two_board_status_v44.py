"""Select the independently checked startup-permission routing checkpoint."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-permission-native-04'
    previous = STAGING / 'two-board-fabrication-status-43/status.json'
    capture = STAGING / 'two-board-power-routing-inputs-2237-permission-04/capture.json'
    reports = [previous, capture,
        STAGING / 'two-board-permission-plan-04/manifest.json',
        STAGING / 'two-board-power-permission-filled-04/local-plane-fill.json',
        STAGING / 'two-board-permission-source-diagnostic-02/source-control.json',
        STAGING / 'two-board-signal-routed-native-03/review.json',
        *[power / name for name in ['review.json', 'permission-routing.json',
            'permission-review.json', 'permission-net-review.json',
            'retained-permission-reference-review.json', 'rejected-source-net-status.json',
            'plots/native-plots.json', 'plots/preview-render.json',
            'plots/permission-west-render.json', 'plots/permission-east-render.json',
            'plots/visual-review.json']]]
    count = 0
    for path in reports:
        data = json.loads(path.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, digest in data.get(field, {}).items():
                target = Path(name)
                if not target.is_absolute():
                    target = (REPO if name.startswith(('hardware/', 'tests/')) else path.parent) / target
                assert sha(target) == digest, (path, name)
                count += 1
    audit, refs, route, cap, native, nets = [json.loads(p.read_text()) for p in [
        power / 'permission-review.json', power / 'retained-permission-reference-review.json',
        power / 'permission-routing.json', capture, power / 'review.json', power / 'permission-net-review.json']]
    assert native['opens'] == audit['new_opens'] == 2237 and audit['closed_connections'] == 30
    assert native['geometry_findings'] == native['schematic_parity_findings'] == 0
    assert audit['all_other_native_groups_preserved'] and len(audit['declared_native_joins']) == 30
    assert audit['moved_pad_count'] == 10 and audit['retained_part_count'] == 1086 and audit['retained_pin_entries'] == 3420
    assert len(audit['prior_reference_coverage']) == 1015 and len(audit['own_quiet_reference_preservation']) == 22
    assert len(audit['quiet_returns']) == 4 and audit['source_plane_contacts_preserved'] == 20
    assert audit['new_logic_fully_referenced_sections'] == len(audit['new_logic_reference']) == 72
    assert audit['source_plane_unexplained_change_mm2'] < 1e-6
    assert 1.7122 < audit['source_plane_change_mm2'] < 1.7123
    assert audit['geometry_errors'] == audit['parity_errors'] == audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    assert refs['retained_support_fully_referenced_sections'] == 24 and len(refs['retained_support_reference']) == 28
    assert refs['new_startup_fully_referenced_sections'] == 7 and len(refs['new_startup_reference']) == 15
    assert refs['retained_TBP43_fully_referenced_sections'] == len(refs['retained_TBP43_reference']) == 70
    assert len(refs['fast_OV_reference']) == 33
    assert len(cap['objects']) == 7195 and len(cap['all_groups']) == 2975 and cap['footprints_captured'] == 1101
    assert sum(o['kind'] == 'PCB_TRACK' for o in cap['objects']) == 3039
    assert sum(o['kind'] == 'PCB_VIA' for o in cap['objects']) == 435 and len(cap['zones']) == 39
    assert route['added_tracks'] == 183 and route['added_vias'] == 49
    assert route['retired_objects'] == ['292630b4-8a36-50b7-ba5c-702909f64dda']
    assert len(route['moves']) == 2 and not route['circuit_changes'] and not route['deferred']
    assert len(route['joins']) == 25 and len(route['edited_zone_outlines']) == 4 and len(route['refilled_existing_zones']) == 11
    assert len(nets['complete_control_nets']) == 7 and all(n['whole_net_connected'] for n in nets['complete_control_nets'])
    assert len(nets['pullup_AUX_ends_in_existing_supply_group']) == 7
    visual = json.loads((power / 'plots/visual-review.json').read_text())
    assert len(visual['changed_views_directly_inspected']) == 19 and not visual['additional_visual_findings']
    status = json.loads(previous.read_text())
    # These inherited counts describe an older via screen; do not present them
    # as a board-wide current result after moving parts and adding copper.
    for key in ['power_all_vias_screened', 'power_minimum_all_via_drill_to_SMD_mm']:
        status.pop(key, None)
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP43 remains applicable except the U42/C85 moves, replaced ANA_PG0 segment, new permission/pull-up routes, four main-ground outline extensions and eleven refills. TBP44 verifies 30 net new joins, all other connectivity and 1,015 retained complete reference cases.',
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2237, power_copper_segments=3039, power_copper_vias=435,
        power_filled_zones=39, power_native_connection_groups=2975,
        power_connections_closed_this_pass=30, power_added_tracks_this_pass=183,
        power_retired_tracks_this_pass=1, power_retired_vias_this_pass=0,
        power_added_vias_this_pass=49, power_added_zones_this_pass=0,
        power_native_group_merges=audit['declared_native_joins'], power_native_connection_partition_unchanged=False,
        power_all_other_native_groups_preserved=True,
        power_moved_footprints_this_pass=2, power_changed_pad_instances_this_pass=10,
        power_complete_footprints_unchanged=1099, power_complete_footprint_geometries_unchanged=1099,
        power_changed_component_values_this_pass=0, power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=28, power_changed_existing_zone_fills=11,
        power_edited_existing_zone_outlines=4, power_existing_zone_layer_changes=0, power_zone_priority_changes=[],
        power_previous_full_width_adjacent_ground_reference_cases_preserved=1015,
        power_new_vias_screened=49,
        power_minimum_new_via_drill_to_SMD_mm=audit['minimum_new_via_to_SMD_drill_gap_mm'],
        power_minimum_new_hole_gap_mm=audit['minimum_new_hole_gap_mm'],
        power_fast_OV_current_reference_coverage=refs['fast_OV_reference'],
        power_digital_startup_review=str((power / 'permission-review.json').relative_to(REPO)),
        power_digital_reference_review=str((power / 'retained-permission-reference-review.json').relative_to(REPO)),
        power_permission_net_review=str((power / 'permission-net-review.json').relative_to(REPO)),
        power_complete_permission_control_nets=[n['net'] for n in nets['complete_control_nets']],
        power_PG_pullup_AUX_ends_connected=7,
        power_digital_source_plane_contacts_preserved=20, power_digital_source_plane_unchanged_this_pass=False,
        power_digital_source_plane_change_mm2=audit['source_plane_change_mm2'],
        power_digital_source_unexplained_change_mm2=audit['source_plane_unexplained_change_mm2'],
        power_digital_source_single_via_control=audit['source_single_via_control'],
        power_digital_eFuse_quiet_islands=audit['quiet_returns'],
        power_digital_reference_complete_route_sections=24, power_digital_reference_screened_route_sections=28,
        power_digital_reference_residuals=[r for r in refs['retained_support_reference'] if min(r['adjacent_uncovered_mm2'].values()) >= 1e-6],
        power_digital_own_quiet_reference_screen=audit['own_quiet_reference_preservation'],
        power_digital_cell_full_new_route_reference_complete=False, power_digital_cell_current_thermal_transient_qualified=False,
        power_startup_fully_referenced_sections=72, power_startup_reference_screened_sections=72,
        power_startup_reference_scope='TBP44 U31/U42 permission, follower, PG pull-up AUX and NF header routes, plus the restored ANA_PG0 segment. Same-net via and plated-pad antipads are explicitly excluded. Earlier support/PG/EN gaps, pulldown returns and the complete startup chain remain unfinished.',
        power_startup_full_reference_complete=True, power_startup_complete=False,
        power_startup_reference_details=audit['new_logic_reference'],
        power_retained_TBP43_reference_sections=refs['retained_TBP43_reference'],
        power_retained_TBP40_startup_reference_complete_sections=7, power_retained_TBP40_startup_reference_screened_sections=15,
        power_digital_source_plane_area_mm2=refs['source_plane_area_mm2'],
        power_digital_source_In5_reference_uncovered_mm2=refs['source_In5_uncovered_mm2'],
        power_digital_source_In5_reference_covered_fraction=1-refs['source_In5_uncovered_mm2']/refs['source_In5_screen_area_mm2'],
        power_digital_source_reference_full_area_coverage=False,
        power_visual_evidence_scope='Nineteen current TBP44 views directly inspected: front/back overview, six-inner overview and both eight-layer west/east detail sets covering all edited routes.',
        power_inlet_resistance_model_scope='TBP35 historical conditional screen; subsequent copper, refills and current sharing are not modeled.',
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete analog/digital pulldown returns with reviewed local return ownership; verify the full startup chain',
        'Complete retained support and PG/EN ground-reference coverage while preserving quiet-return owners',
        'Complete digital eFuse protected outputs/thermal copper, analog regulator outputs, module supplies, force/quiet returns and signal routing',
        'Establish load/startup/fault states, effective capacitance, current sharing, accepted stack/plating and thermal limits',
        'Resolve ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables',
        'Prepare the reviewed prototype bring-up plan and complete applicable release checks']
    out = STAGING / 'two-board-fabrication-status-44'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2237, signal_opens=251,
        closed_connections=30, new_logic_fully_referenced_sections=72, fabrication_released=False)))


if __name__ == '__main__':
    run()
