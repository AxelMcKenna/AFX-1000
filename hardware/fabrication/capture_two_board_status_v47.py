"""Select four checked support-reference repairs with unchanged native topology."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha


def run():
    power=STAGING/'two-board-power-support-references-native-01'
    previous=STAGING/'two-board-fabrication-status-46/status.json'
    capture=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'
    paths=[previous,capture,STAGING/'two-board-startup-connectivity-survey-01/inventory.json',
           STAGING/'two-board-startup-reference-plan-01/reference-plan.json',
           STAGING/'two-board-signal-routed-native-03/review.json',
           *[power/n for n in ['review.json','support-reference-routing.json','support-reference-review.json',
                              'support-reference-coverage.json','plots/native-plots.json','plots/preview-render.json',
                              'plots/support-local-render.json','plots/visual-review.json']]]
    bindings=0
    for path in paths:
        data=json.loads(path.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                target=Path(name)
                if not target.is_absolute():target=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/target
                assert sha(target)==digest,(path,name)
                bindings+=1
    cap=json.loads(capture.read_text());prior=json.loads(previous.read_text())
    native,route,audit,refs,visual=[json.loads((power/n).read_text()) for n in [
        'review.json','support-reference-routing.json','support-reference-review.json',
        'support-reference-coverage.json','plots/visual-review.json']]
    assert native['opens']==audit['new_opens']==cap['native_uncapped_opens']==2210
    assert native['geometry_findings']==native['schematic_parity_findings']==audit['ERC_errors']==0 and audit['ERC_warnings']==2
    assert audit['all_native_groups_preserved'] and audit['all_other_objects_preserved']
    assert audit['all_zones_and_fills_unchanged'] and audit['all_supply_planes_unchanged'] and audit['quiet_return_geometry_unchanged']
    assert audit['retained_part_count']==1086 and audit['retained_pin_entries']==3420
    assert refs['retained_reference_complete'] and refs['new_reference_complete'] and refs['own_quiet_reference_complete']
    assert refs['own_quiet_reference_preserved'] and refs['legacy_incomplete_paths_preserved']
    assert len(refs['new_non_ground_paths'])==4 and len(refs['own_quiet_reference'])==22
    assert refs['legacy_paths_repaired']==4 and refs['remaining_legacy_reference_gaps']==8
    assert all(x['uncovered_mm2']<1e-6 for x in refs['retained_reference_cases']+refs['new_non_ground_paths'])
    assert all(x['after_uncovered_mm2']<1e-6 for x in refs['own_quiet_reference'])
    assert route['added_tracks']==9 and route['retired_tracks']==6 and route['added_vias']==route['modified_zones']==route['moved_footprints']==0
    assert cap['footprints_captured']==1101 and len(cap['objects'])==7205 and len(cap['all_groups'])==2948 and len(cap['zones'])==47
    assert sum(o['kind']=='PCB_TRACK' for o in cap['objects'])==3031 and sum(o['kind']=='PCB_VIA' for o in cap['objects'])==453
    assert visual['total_directly_inspected_views']==8 and not visual['additional_visual_findings']
    status={k:v for k,v in prior.items() if not k.startswith('power_') and k not in ['source_sha256','native_checks']}
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,power/'README.md']},
        revision='TBP47',previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP46 is the historical baseline. This revision replaces six surface segments with nine to repair four support-reference gaps. All components, vias, zones, fills and native connection groups are unchanged.',
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2210,power_footprints=1101,power_electrical_parts=1086,power_schematic_pin_entries=3420,
        power_mapped_pad_instances=3481,power_copper_segments=3031,power_copper_vias=453,power_filled_zones=47,
        power_native_connection_groups=2948,power_connections_closed_this_pass=0,
        power_added_tracks_this_pass=9,power_retired_tracks_this_pass=6,
        power_added_vias_this_pass=0,power_retired_vias_this_pass=0,power_added_zones_this_pass=0,
        power_moved_footprints_this_pass=0,power_changed_pad_instances_this_pass=0,power_face_changes_this_pass=0,
        power_changed_component_values_this_pass=0,power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=47,power_changed_existing_zone_fills=0,power_edited_existing_zone_outlines=0,
        power_geometry_errors=0,power_parity_errors=0,power_ERC_errors=0,power_ERC_warnings=2,
        power_native_group_merges=[],power_all_other_native_groups_preserved=True,
        power_previous_full_width_adjacent_ground_reference_cases_preserved=len(refs['retained_reference_cases']),
        power_new_non_ground_route_paths=4,power_new_non_ground_reference_complete=True,
        power_retained_quiet_returns=prior['power_retained_quiet_returns'],power_quiet_return_geometry_unchanged=True,
        power_own_quiet_reference_preserved=True,power_digital_own_quiet_reference_complete=True,
        power_reference_review=str((power/'support-reference-coverage.json').relative_to(REPO)),
        power_remaining_reference_plan='hardware/fabrication/staging/two-board-startup-reference-plan-01/reference-plan.json',
        power_connectivity_review=str((power/'support-reference-review.json').relative_to(REPO)),
        power_legacy_reference_paths_repaired_this_pass=4,power_legacy_incomplete_reference_paths_preserved=8,
        power_all_supply_planes_unchanged=True,power_loaded_current_timing_noise_thermal_qualified=False,
        power_inlet_resistance_model_scope='TBP35 historical copper only; current fills and via sharing are not modeled.',
        power_visual_evidence_scope='Eight directly inspected views: five complete changed-route details, both surface overviews and the inner-layer contact sheet.',
        power_startup_connectivity_survey=prior['power_startup_connectivity_survey'],
        power_startup_connectivity_survey_scope='TBP46 native group survey remains applicable because all native groups and pad positions are preserved.',
        power_surveyed_startup_nets=91,power_open_surveyed_startup_nets=32,power_surveyed_startup_missing_joins=60,
        power_routing_complete=False,power_startup_complete=False,fabrication_released=False,goal_complete=False)
    status['next_required_design_work'][0]='Correct the eight remaining startup reference gaps; complete remaining startup joins and functional verification'
    output=STAGING/'two-board-fabrication-status-47';output.mkdir(exist_ok=False)
    (output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(revision='TBP47',bindings=bindings,power_opens=2210,signal_opens=251,
        retained_reference_cases=len(refs['retained_reference_cases']),new_reference_paths=4,
        repaired_reference_paths=4,remaining_legacy_reference_gaps=8,fabrication_released=False)))


if __name__=='__main__':run()
