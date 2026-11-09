"""Select the independently verified startup-logic ground-reference checkpoint."""
import json
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-logic-references-native-02'
    previous = STAGING / 'two-board-fabrication-status-41/status.json'
    capture = STAGING / 'two-board-power-routing-inputs-2294-logic-references-02/capture.json'
    diagnostics = STAGING / 'two-board-logic-reference-refill-diagnostic-01'
    reports = [previous, capture,
               STAGING / 'two-board-logic-reference-plan-02/manifest.json',
               STAGING / 'two-board-power-logic-references-filled-03/local-plane-fill.json',
               STAGING / 'two-board-signal-routed-native-03/review.json',
               *[diagnostics / (n + '.json') for n in [
                   'unchanged_baseline', 'candidate_without_added_zones',
                   'full_candidate', 'source_priority_2', 'reroutes_only']],
               *[power / n for n in [
                   'review.json', 'logic-reference-routing.json',
                   'logic-reference-review.json', 'retained-logic-reference-review.json',
                   'rejected-source-net-status.json', 'plots/native-plots.json',
                   'plots/preview-render.json', 'plots/logic-render.json',
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
    audit = json.loads((power / 'logic-reference-review.json').read_text())
    refs = json.loads((power / 'retained-logic-reference-review.json').read_text())
    route = json.loads((power / 'logic-reference-routing.json').read_text())
    cap = json.loads(capture.read_text())
    native = json.loads((power / 'review.json').read_text())
    assert native['opens'] == 2294 and native['geometry_findings'] == native['schematic_parity_findings'] == 0
    assert audit['new_opens'] == 2294 and audit['closed_connections'] == 0
    assert audit['native_connection_partition_unchanged'] and audit['all_other_native_groups_preserved']
    assert audit['moved_pad_count'] == 0 and audit['retained_part_count'] == 1086 and audit['retained_pin_entries'] == 3420
    assert len(audit['prior_reference_coverage']) == 305 and len(audit['own_quiet_reference_preservation']) == 22
    assert len(audit['quiet_returns']) == 4 and audit['source_plane_contacts_preserved'] == 20
    assert audit['new_logic_fully_referenced_sections'] == len(audit['new_logic_reference']) == 33
    assert audit['source_matches_isolated_reroute_control'] and audit['unexplained_source_plane_change_mm2'] == 0
    assert audit['source_zone_priority_before'] == 0 and audit['source_zone_priority_after'] == 2
    assert audit['geometry_errors'] == audit['parity_errors'] == audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    assert refs['retained_support_fully_referenced_sections'] == 24 and len(refs['retained_support_reference']) == 28
    assert refs['new_startup_fully_referenced_sections'] == 7 and len(refs['new_startup_reference']) == 15
    assert len(refs['fast_OV_reference']) == 33
    assert len(cap['objects']) == 6753 and len(cap['all_groups']) == 3032 and cap['footprints_captured'] == 1101
    assert sum(o['kind'] == 'PCB_TRACK' for o in cap['objects']) == 2693
    assert sum(o['kind'] == 'PCB_VIA' for o in cap['objects']) == 339 and len(cap['zones']) == 39
    assert route['added_tracks'] == 18 and route['added_vias'] == 2 and len(route['retired_objects']) == 9
    assert not route['moved_footprints'] and not route['circuit_changes']
    assert len(route['added_zones']) == 3 and len(route['edited_zone_outlines']) == 2 and len(route['refilled_existing_zones']) == 6
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP41 remains applicable except the explicitly replaced PG1/FOLLOW1 copper, three added reference zones, two extended ground outlines and digital-source priority. TBP42 independently proves unchanged connectivity and full adjacent-ground coverage for all 33 current logic sections.',
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2294, power_copper_segments=2693, power_copper_vias=339,
        power_filled_zones=39, power_native_connection_groups=3032,
        power_connections_closed_this_pass=0, power_added_tracks_this_pass=18,
        power_retired_tracks_this_pass=8, power_retired_vias_this_pass=1,
        power_added_vias_this_pass=2, power_added_zones_this_pass=3,
        power_previous_native_connection_groups_preserved=3032,
        power_native_group_merges=[], power_native_connection_partition_unchanged=True,
        power_moved_footprints_this_pass=0, power_changed_pad_instances_this_pass=0,
        power_complete_footprints_unchanged=1101, power_complete_footprint_geometries_unchanged=1101,
        power_changed_component_values_this_pass=0, power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=30, power_changed_existing_zone_fills=6,
        power_edited_existing_zone_outlines=2, power_existing_zone_layer_changes=0,
        power_zone_priority_changes=route['zone_priority_changes'],
        power_previous_full_width_adjacent_ground_reference_cases_preserved=305,
        power_fast_OV_current_reference_coverage=refs['fast_OV_reference'],
        power_digital_startup_review=str((power / 'logic-reference-review.json').relative_to(REPO)),
        power_digital_reference_review=str((power / 'retained-logic-reference-review.json').relative_to(REPO)),
        power_digital_source_layer='In4.Cu', power_digital_source_previous_layer='In4.Cu',
        power_digital_source_plane_contacts_preserved=20,
        power_digital_source_matches_isolated_reroute_control=True,
        power_digital_source_unexplained_change_mm2=0,
        power_digital_source_native_remeshing_outside_via_neighborhoods_mm2=audit['source_native_remeshing_outside_via_neighborhoods_mm2'],
        power_digital_eFuse_quiet_islands=audit['quiet_returns'],
        power_digital_reference_complete_route_sections=24,
        power_digital_reference_screened_route_sections=28,
        power_digital_reference_residuals=[r for r in refs['retained_support_reference'] if min(r['adjacent_uncovered_mm2'].values()) >= 1e-6],
        power_digital_own_quiet_reference_screen=audit['own_quiet_reference_preservation'],
        power_digital_cell_full_new_route_reference_complete=False,
        power_digital_cell_current_thermal_transient_qualified=False,
        power_startup_fully_referenced_sections=33, power_startup_reference_screened_sections=33,
        power_startup_reference_scope='TBP42 current U29/U40 logic fanout, interconnects and AUX branches, including replaced PG1/FOLLOW1 sections; adjacent-ground projection with recorded same-net via-antipad exclusions only. Earlier support/PG/EN references remain incomplete. Complete startup chain and current/timing/noise qualification remain unfinished.',
        power_startup_full_reference_complete=True, power_startup_complete=False,
        power_startup_reference_details=audit['new_logic_reference'],
        power_retained_TBP40_startup_reference_complete_sections=7,
        power_retained_TBP40_startup_reference_screened_sections=15,
        power_digital_source_plane_area_mm2=refs['source_plane_area_mm2'],
        power_digital_source_In5_reference_uncovered_mm2=refs['source_In5_uncovered_mm2'],
        power_digital_source_In5_reference_covered_fraction=1-refs['source_In5_uncovered_mm2']/refs['source_In5_screen_area_mm2'],
        power_digital_source_reference_full_area_coverage=False,
        power_visual_evidence_scope='Eleven current TBP42 views directly inspected: front/back overview, six-inner overview and all eight 110 mm logic/distribution detail layers.',
        power_inlet_resistance_model_scope='TBP35 historical conditional screen; TBP36–TBP42 copper/refills/layer changes and current sharing are not modeled.',
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete U29 ALL_RAILS_ALLOW and U30/U34/U41 supplies/bypass, remaining gate/receiver paths and PG pull-up AUX ends',
        'Complete retained support and PG/EN ground-reference coverage while preserving all quiet-return owners',
        'Complete digital eFuse protected outputs/thermal copper, analog regulator outputs, remaining module supplies, force/quiet returns and signal routing',
        'Establish actual load/startup/fault states, effective capacitance, current sharing, accepted stack/plating and thermal limits',
        'Resolve ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables',
        'Prepare the reviewed prototype bring-up plan and complete applicable release checks']
    out = STAGING / 'two-board-fabrication-status-42'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2294, signal_opens=251,
                         closed_connections=0, new_logic_fully_referenced_sections=33,
                         fabrication_released=False)))


if __name__ == '__main__':
    run()
