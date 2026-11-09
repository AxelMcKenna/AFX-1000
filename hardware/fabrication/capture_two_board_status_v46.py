"""Select the independently checked digital pulldown and reference repair."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-digital-return-native-03'
    previous=STAGING/'two-board-fabrication-status-45/status.json'
    capture=STAGING/'two-board-power-routing-inputs-2210-digital-return-03/capture.json'
    inventory=STAGING/'two-board-startup-connectivity-survey-01/inventory.json'
    paths=[previous,capture,inventory,
           STAGING/'two-board-power-digital-return-filled-03/local-plane-fill.json',
           STAGING/'two-board-signal-routed-native-03/review.json',
           *[power/n for n in ['review.json','digital-return-routing.json','digital-return-review.json',
                              'digital-return-reference-review.json','plots/native-plots.json',
                              'plots/preview-render.json','plots/r104-local-render.json',
                              'plots/r104-former-render.json','plots/visual-review.json']]]
    bindings=0
    for path in paths:
        data=json.loads(path.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                target=Path(name)
                if not target.is_absolute():
                    target=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/target
                assert sha(target)==digest,(path,name)
                bindings+=1
    cap=json.loads(capture.read_text())
    native,route,audit,refs,visual=[json.loads((power/n).read_text()) for n in [
        'review.json','digital-return-routing.json','digital-return-review.json',
        'digital-return-reference-review.json','plots/visual-review.json']]
    survey=json.loads(inventory.read_text())
    assert native['opens']==audit['new_opens']==cap['native_uncapped_opens']==2210
    assert native['geometry_findings']==native['schematic_parity_findings']==audit['ERC_errors']==0
    assert audit['ERC_warnings']==2 and audit['closed_connections']==1
    assert audit['all_other_native_groups_preserved'] and audit['all_supply_planes_unchanged']
    assert audit['retained_part_count']==1086 and audit['retained_pin_entries']==3420 and audit['moved_pad_count']==2
    assert refs['retained_reference_complete'] and refs['new_reference_complete']
    assert refs['own_quiet_reference_preserved'] and refs['legacy_incomplete_paths_preserved']
    assert len(refs['retained_reference_cases'])==1610 and len(refs['new_non_ground_paths'])==2
    assert all(row['uncovered_mm2']<1e-6 for row in refs['retained_reference_cases']+refs['new_non_ground_paths'])
    assert len(refs['legacy_incomplete_paths'])==12 and len(refs['own_quiet_reference'])==22
    assert all(row['regression_mm2']<1e-6 for row in refs['legacy_incomplete_paths']+refs['own_quiet_reference'])
    assert len(audit['quiet_returns'])==7
    assert all(q['contacts_preserved'] and q['owned_graph_connected'] and q['star_only_main_return'] for q in audit['quiet_returns'])
    assert route['added_tracks']==3 and route['added_vias']==0 and len(route['retired_objects'])==5
    assert len(route['moves'])==1 and len(route['edited_zone_outlines'])==2 and len(route['refilled_existing_zones'])==5
    assert cap['footprints_captured']==1101 and len(cap['objects'])==7202 and len(cap['all_groups'])==2948 and len(cap['zones'])==47
    assert sum(o['kind']=='PCB_TRACK' for o in cap['objects'])==3028 and sum(o['kind']=='PCB_VIA' for o in cap['objects'])==453
    assert visual['total_directly_inspected_views']==14 and not visual['additional_visual_findings']
    assert survey['native_board_opens']==2210 and survey['selected_net_count']==91
    assert survey['open_selected_net_count']==32 and survey['selected_missing_joins']==60
    status={k:v for k,v in json.loads(previous.read_text()).items()
            if not k.startswith('power_') and k not in ['source_sha256','native_checks']}
    status.update(
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,power/'README.md']},
        revision='TBP46',previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP45 is the historical baseline. This revision moves R104, completes its owned quiet return and replaces the adjacent master-enable dogleg. Current metrics replace previous power metrics; earlier circuit analyses remain limited to their snapshots.',
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2210,power_footprints=1101,power_electrical_parts=1086,
        power_schematic_pin_entries=3420,power_mapped_pad_instances=3481,
        power_copper_segments=3028,power_copper_vias=453,power_filled_zones=47,
        power_native_connection_groups=2948,power_connections_closed_this_pass=1,
        power_added_tracks_this_pass=3,power_retired_tracks_this_pass=4,
        power_added_vias_this_pass=0,power_retired_vias_this_pass=1,power_added_zones_this_pass=0,
        power_moved_footprints_this_pass=1,power_changed_pad_instances_this_pass=2,
        power_face_changes_this_pass=0,power_changed_component_values_this_pass=0,
        power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=42,power_changed_existing_zone_fills=5,
        power_edited_existing_zone_outlines=2,
        power_geometry_errors=0,power_parity_errors=0,power_ERC_errors=0,power_ERC_warnings=2,
        power_native_group_merges=[audit['declared_native_join']],power_all_other_native_groups_preserved=True,
        power_previous_full_width_adjacent_ground_reference_cases_preserved=1610,
        power_new_non_ground_route_paths=2,power_new_non_ground_reference_complete=True,
        power_retained_quiet_returns=audit['quiet_returns'],power_own_quiet_reference_preserved=True,
        power_reference_review=str((power/'digital-return-reference-review.json').relative_to(REPO)),
        power_connectivity_review=str((power/'digital-return-review.json').relative_to(REPO)),
        power_legacy_incomplete_reference_paths_preserved=12,
        power_all_supply_planes_unchanged=True,power_loaded_current_timing_noise_thermal_qualified=False,
        power_inlet_resistance_model_scope='TBP35 historical copper only; current fills and via sharing are not modeled.',
        power_visual_evidence_scope='Fourteen directly inspected views: five local, six former-location layers, both surface overviews and the inner-layer contact sheet.',
        power_startup_connectivity_survey=str(inventory.relative_to(REPO)),
        power_surveyed_startup_nets=91,power_open_surveyed_startup_nets=32,power_surveyed_startup_missing_joins=60,
        power_routing_complete=False,power_startup_complete=False,fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Correct the twelve recorded earlier support/PG reference gaps; complete remaining startup joins and functional verification',
        'Complete protected outputs, analog input/source loops, analog/module distribution, force/quiet returns and signal routing',
        'Establish load/startup/fault states, effective capacitance, current sharing, accepted stack/plating, parasitic/noise/timing and thermal limits',
        'Resolve approved ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables',
        'Prepare the reviewed whole-unit prototype bring-up plan and complete applicable release checks']
    output=STAGING/'two-board-fabrication-status-46'
    output.mkdir(exist_ok=False)
    (output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(revision='TBP46',bindings=bindings,power_opens=2210,signal_opens=251,
                         closed_connections=1,retained_reference_cases=1610,new_reference_paths=2,
                         fabrication_released=False)))


if __name__=='__main__':
    run()
