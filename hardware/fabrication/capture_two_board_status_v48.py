"""Select the coordinated startup-reference repair after native and independent reviews."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-startup-references-native-04'
    previous=STAGING/'two-board-fabrication-status-47/status.json'
    capture=STAGING/'two-board-power-routing-inputs-2210-startup-references-04/capture.json'
    names=['review.json','startup-reference-routing.json','startup-reference-review.json','startup-reference-coverage.json','startup-supply-plane-review.json','plots/native-plots.json','plots/preview-render.json','plots/startup-local-render.json','plots/visual-review.json']
    paths=[previous,capture,STAGING/'two-board-startup-connectivity-survey-01/inventory.json',STAGING/'two-board-startup-reference-plan-01/reference-plan.json',STAGING/'two-board-signal-routed-native-03/review.json',*[power/n for n in names]]
    bindings=0
    for path in paths:
        data=json.loads(path.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/p
                assert sha(p)==digest,(path,name)
                bindings+=1
    prior=json.loads(previous.read_text());cap=json.loads(capture.read_text())
    native,route,audit,refs,supply=[json.loads((power/n).read_text()) for n in names[:5]]
    visual=json.loads((power/'plots/visual-review.json').read_text())
    assert native['opens']==audit['new_opens']==cap['native_uncapped_opens']==2210
    assert native['geometry_findings']==native['schematic_parity_findings']==audit['ERC_errors']==0
    assert audit['ERC_warnings']==2 and audit['all_native_groups_preserved'] and audit['all_other_objects_preserved']
    assert len(audit['quiet_returns'])==7 and all(q['contacts_preserved'] and q['owned_graph_connected'] and q['star_only_main_return'] for q in audit['quiet_returns'])
    assert all(refs[k] for k in ['retained_reference_complete','new_reference_complete','startup_references_complete','digital_own_quiet_reference_complete'])
    assert len(refs['retained_reference_cases'])==1611 and len(refs['new_non_ground_paths'])==9
    assert len(refs['startup_paths'])==8 and len(refs['digital_own_quiet_paths'])==22
    assert all(x['uncovered_mm2']<1e-6 for x in refs['retained_reference_cases']+refs['new_non_ground_paths']+refs['digital_own_quiet_paths'])
    assert all(x['after_uncovered_mm2']<1e-6 for x in refs['startup_paths'])
    assert len(refs['retained_trace_new_transition_contacts'])==1
    transition=refs['retained_trace_new_transition_contacts'][0]
    assert transition['track_uuid']=='baef8b7c-e5fe-5e7f-9264-2fb0867d5533' and transition['copper_overlap_mm2']>.1 and transition['clearance_exclusion_radius_mm']==.515
    assert len(supply['supply_planes'])==11 and all(supply[k] for k in ['all_supply_contacts_preserved','all_supply_region_counts_preserved','supply_outlines_unchanged'])
    assert route['added_tracks']==25 and route['added_vias']==5 and len(route['retired_objects'])==20
    assert len(route['edited_zone_outlines'])==7 and len(route['refilled_existing_zones'])==16
    assert cap['footprints_captured']==1101 and len(cap['objects'])==7215 and len(cap['all_groups'])==2948 and len(cap['zones'])==47
    assert sum(o['kind']=='PCB_TRACK' for o in cap['objects'])==3039 and sum(o['kind']=='PCB_VIA' for o in cap['objects'])==455
    assert audit['retained_part_count']==1086 and audit['retained_pin_entries']==3420
    assert visual['total_directly_inspected_views']==9 and not visual['additional_visual_findings']
    status={k:v for k,v in prior.items() if not k.startswith('power_') and k not in ['source_sha256','native_checks']}
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,power/'README.md']},
        revision='TBP48',previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP47 is the historical baseline. Coordinated PG0, PG1 and U33 reroutes and adjacent ground extensions repair all eight recorded startup-reference gaps; every native connection group and all seven quiet-ground topologies are preserved.',
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2210,power_footprints=1101,power_electrical_parts=1086,power_schematic_pin_entries=3420,power_mapped_pad_instances=3481,
        power_copper_segments=3039,power_copper_vias=455,power_filled_zones=47,power_native_connection_groups=2948,
        power_connections_closed_this_pass=0,power_added_tracks_this_pass=25,power_retired_tracks_this_pass=17,
        power_added_vias_this_pass=5,power_retired_vias_this_pass=3,power_added_zones_this_pass=0,
        power_moved_footprints_this_pass=0,power_changed_pad_instances_this_pass=0,power_changed_component_values_this_pass=0,power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=31,power_refilled_existing_zones=16,power_edited_existing_zone_outlines=7,
        power_geometry_errors=0,power_parity_errors=0,power_ERC_errors=0,power_ERC_warnings=2,
        power_native_group_merges=[],power_all_other_native_groups_preserved=True,
        power_previous_full_width_adjacent_ground_reference_cases_preserved=1611,power_new_non_ground_route_paths=9,power_new_non_ground_reference_complete=True,
        power_retained_quiet_returns=prior['power_retained_quiet_returns'],power_quiet_return_geometry_unchanged=False,power_quiet_return_topology_preserved=True,
        power_own_quiet_reference_preserved=True,power_digital_own_quiet_reference_complete=True,
        power_reference_review=str((power/'startup-reference-coverage.json').relative_to(REPO)),
        power_connectivity_review=str((power/'startup-reference-review.json').relative_to(REPO)),
        power_supply_plane_review=str((power/'startup-supply-plane-review.json').relative_to(REPO)),
        power_legacy_reference_paths_repaired_this_pass=8,power_legacy_incomplete_reference_paths_preserved=0,
        power_all_supply_planes_unchanged=False,power_supply_contacts_and_region_counts_preserved=True,
        power_loaded_current_timing_noise_thermal_qualified=False,
        power_inlet_resistance_model_scope='TBP35 historical copper only; current fills and via sharing are not modeled.',
        power_visual_evidence_scope='Nine directly inspected views: six local copper/ground details, both surface overviews and the six-inner-layer contact sheet.',
        power_startup_connectivity_survey=prior['power_startup_connectivity_survey'],
        power_startup_connectivity_survey_scope='TBP46 survey remains applicable because every native connection group and pad position is preserved.',
        power_surveyed_startup_nets=91,power_open_surveyed_startup_nets=32,power_surveyed_startup_missing_joins=60,
        power_routing_complete=False,power_startup_complete=False,fabrication_released=False,goal_complete=False)
    status['next_required_design_work'][0]='Complete the 60 remaining surveyed startup joins across 32 nets and verify startup/fault behavior; preserve the repaired references'
    out=STAGING/'two-board-fabrication-status-48';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(revision='TBP48',bindings=bindings,repaired_startup_reference_paths=8,power_opens=2210,signal_opens=251,fabrication_released=False)))


if __name__=='__main__':run()
