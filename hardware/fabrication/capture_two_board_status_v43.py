"""Select the independently reviewed U30/U34/U41 startup-routing checkpoint."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-startup-completion-native-06'
    previous = STAGING / 'two-board-fabrication-status-42/status.json'
    capture = STAGING / 'two-board-power-routing-inputs-2267-startup-completion-06/capture.json'
    reports = [previous, capture,
        STAGING / 'two-board-startup-completion-plan-06/manifest.json',
        STAGING / 'two-board-power-startup-completion-filled-06/local-plane-fill.json',
        STAGING / 'two-board-signal-routed-native-03/review.json',
        *[power / n for n in ['review.json', 'startup-completion-routing.json',
            'startup-completion-review.json', 'retained-startup-completion-reference-review.json',
            'rejected-source-net-status.json', 'plots/native-plots.json',
            'plots/preview-render.json', 'plots/startup-render.json', 'plots/visual-review.json']]]
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
    audit, refs, route, cap, native = [json.loads(p.read_text()) for p in [
        power / 'startup-completion-review.json', power / 'retained-startup-completion-reference-review.json',
        power / 'startup-completion-routing.json', capture, power / 'review.json']]
    assert native['opens'] == audit['new_opens'] == 2267 and audit['closed_connections'] == 27
    assert native['geometry_findings'] == native['schematic_parity_findings'] == 0
    assert audit['all_other_native_groups_preserved'] and len(audit['declared_native_joins']) == 27
    assert audit['moved_pad_count'] == 30 and audit['retained_part_count'] == 1086 and audit['retained_pin_entries'] == 3420
    assert len(audit['prior_reference_coverage']) == 486 and len(audit['own_quiet_reference_preservation']) == 22
    assert len(audit['quiet_returns']) == 4 and audit['source_plane_contacts_preserved'] == 20
    assert audit['new_logic_fully_referenced_sections'] == len(audit['new_logic_reference']) == 70
    assert audit['source_plane_change_mm2'] == audit['source_plane_unexplained_change_mm2'] == 0
    assert audit['geometry_errors'] == audit['parity_errors'] == audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    assert refs['retained_support_fully_referenced_sections'] == 24 and len(refs['retained_support_reference']) == 28
    assert refs['new_startup_fully_referenced_sections'] == 7 and len(refs['new_startup_reference']) == 15
    assert len(refs['fast_OV_reference']) == 33
    assert len(cap['objects']) == 6964 and len(cap['all_groups']) == 3005 and cap['footprints_captured'] == 1101
    assert sum(o['kind'] == 'PCB_TRACK' for o in cap['objects']) == 2857
    assert sum(o['kind'] == 'PCB_VIA' for o in cap['objects']) == 386 and len(cap['zones']) == 39
    assert route['added_tracks'] == 178 and route['added_vias'] == 49 and len(route['retired_objects']) == 16
    assert len(route['moves']) == 6 and not route['circuit_changes'] and not route['deferred']
    assert len(route['joins']) == 23 and len(route['edited_zone_outlines']) == 4 and len(route['refilled_existing_zones']) == 9
    visual = json.loads((power / 'plots/visual-review.json').read_text())
    assert len(visual['changed_views_directly_inspected']) == 11 and not visual['additional_visual_findings']
    status = json.loads(previous.read_text())
    for key in ['power_previous_native_connection_groups_preserved', 'power_digital_source_matches_isolated_reroute_control',
                'power_digital_source_native_remeshing_outside_via_neighborhoods_mm2']:
        status.pop(key, None)
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP42 remains applicable except the six declared IC/bypass moves, retired startup copper, new interconnects and four extended main-ground outlines. TBP43 independently verifies 27 net new joins, all other connectivity and 486 retained complete reference cases.',
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2267, power_copper_segments=2857, power_copper_vias=386,
        power_filled_zones=39, power_native_connection_groups=3005,
        power_connections_closed_this_pass=27, power_added_tracks_this_pass=178,
        power_retired_tracks_this_pass=14, power_retired_vias_this_pass=2,
        power_added_vias_this_pass=49, power_added_zones_this_pass=0,
        power_native_group_merges=audit['declared_native_joins'], power_native_connection_partition_unchanged=False,
        power_all_other_native_groups_preserved=True,
        power_moved_footprints_this_pass=6, power_changed_pad_instances_this_pass=30,
        power_complete_footprints_unchanged=1095, power_complete_footprint_geometries_unchanged=1095,
        power_changed_component_values_this_pass=0, power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=30, power_changed_existing_zone_fills=9,
        power_edited_existing_zone_outlines=4, power_existing_zone_layer_changes=0, power_zone_priority_changes=[],
        power_previous_full_width_adjacent_ground_reference_cases_preserved=486,
        power_fast_OV_current_reference_coverage=refs['fast_OV_reference'],
        power_digital_startup_review=str((power / 'startup-completion-review.json').relative_to(REPO)),
        power_digital_reference_review=str((power / 'retained-startup-completion-reference-review.json').relative_to(REPO)),
        power_digital_source_plane_contacts_preserved=20, power_digital_source_plane_unchanged_this_pass=True,
        power_digital_source_unexplained_change_mm2=0,
        power_digital_eFuse_quiet_islands=audit['quiet_returns'],
        power_digital_reference_complete_route_sections=24, power_digital_reference_screened_route_sections=28,
        power_digital_reference_residuals=[r for r in refs['retained_support_reference'] if min(r['adjacent_uncovered_mm2'].values()) >= 1e-6],
        power_digital_own_quiet_reference_screen=audit['own_quiet_reference_preservation'],
        power_digital_cell_full_new_route_reference_complete=False, power_digital_cell_current_thermal_transient_qualified=False,
        power_startup_fully_referenced_sections=70, power_startup_reference_screened_sections=70,
        power_startup_reference_scope='TBP43 U30/U34/U41 fanouts, supplies/bypasses and targeted receiver/enable/PG interconnects, with same-net via-antipad exclusions. Earlier support/PG/EN gaps, ALL_RAILS_ALLOW, pull-up AUX ends and the complete startup chain remain unfinished.',
        power_startup_full_reference_complete=True, power_startup_complete=False,
        power_startup_reference_details=audit['new_logic_reference'],
        power_retained_TBP40_startup_reference_complete_sections=7, power_retained_TBP40_startup_reference_screened_sections=15,
        power_digital_source_plane_area_mm2=refs['source_plane_area_mm2'],
        power_digital_source_In5_reference_uncovered_mm2=refs['source_In5_uncovered_mm2'],
        power_digital_source_In5_reference_covered_fraction=1-refs['source_In5_uncovered_mm2']/refs['source_In5_screen_area_mm2'],
        power_digital_source_reference_full_area_coverage=False,
        power_visual_evidence_scope='Eleven current TBP43 views directly inspected: front/back overview, six-inner overview and all eight startup detail layers.',
        power_inlet_resistance_model_scope='TBP35 historical conditional screen; subsequent copper, refills and current sharing are not modeled.',
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete U29 ALL_RAILS_ALLOW, remaining startup gate/receiver paths, PG pull-up AUX ends and pulldown returns',
        'Complete retained support and PG/EN ground-reference coverage while preserving quiet-return owners',
        'Complete digital eFuse protected outputs/thermal copper, analog regulator outputs, module supplies, force/quiet returns and signal routing',
        'Establish load/startup/fault states, effective capacitance, current sharing, accepted stack/plating and thermal limits',
        'Resolve ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables',
        'Prepare the reviewed prototype bring-up plan and complete applicable release checks']
    out = STAGING / 'two-board-fabrication-status-43'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2267, signal_opens=251,
                         closed_connections=27, new_logic_fully_referenced_sections=70,
                         fabrication_released=False)))

if __name__ == '__main__':
    run()
