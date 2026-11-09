"""Select completion of the remaining local startup cells only after native, topology and reference checks."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-startup-remaining-native-03'
    previous=STAGING/'two-board-fabrication-status-49/status.json'
    capture=STAGING/'two-board-power-routing-inputs-2172-startup-remaining-03/capture.json'
    survey=STAGING/'two-board-startup-connectivity-survey-06/inventory.json'
    cells=STAGING/'two-board-startup-cell-survey-04/inventory.json'
    aux=STAGING/'two-board-aux-distribution-survey-02/inventory.json'
    names=['review.json','startup-cell-routing.json','startup-cell-review.json','startup-cell-reference-review.json',
           'plots/native-plots.json','plots/preview-render.json','plots/west-startup-render.json',
           'plots/east-startup-render.json','plots/visual-review.json']
    paths=[previous,capture,survey,cells,aux,STAGING/'two-board-startup-remaining-plan-06/plan.json',
           STAGING/'two-board-signal-routed-native-03/review.json',*[power/n for n in names]]
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
    native,route,audit,refs=[json.loads((power/n).read_text()) for n in names[:4]]
    visual=json.loads((power/'plots/visual-review.json').read_text())
    inv=json.loads(survey.read_text());cellinv=json.loads(cells.read_text());auxinv=json.loads(aux.read_text())
    assert native['opens']==audit['new_opens']==cap['native_uncapped_opens']==2172
    assert native['geometry_findings']==native['schematic_parity_findings']==audit['ERC_errors']==0
    assert audit['ERC_warnings']==2 and audit['all_other_native_groups_preserved'] and audit['all_other_objects_preserved']
    assert audit['closed_connections']==len(audit['declared_native_group_merges'])==27
    assert len(audit['quiet_returns'])==7 and all(q['contacts_preserved'] and q['owned_graph_connected'] and q['star_only_main_return'] for q in audit['quiet_returns'])
    assert all(refs[k] for k in ['retained_reference_complete','new_reference_complete','prior_startup_reference_complete',
        'digital_own_quiet_reference_preserved','all_eleven_supply_planes_unchanged','all_seven_quiet_network_fields_unchanged','unanchored_fragments_unchanged','rejected_trial_regressions_repaired'])
    assert len(refs['new_non_ground_paths'])==18 and len(refs['prior_startup_paths'])==9
    assert all(x['uncovered_mm2']<1e-6 for x in refs['retained_reference_cases']+refs['new_non_ground_paths']+refs['prior_startup_paths'])
    assert route['added_tracks']==69 and route['added_vias']==20 and len(route['retired_objects'])==112
    assert len(route['moves'])==5 and len(route['edited_zone_outlines'])==1 and len(route['refilled_existing_zones'])==4
    assert cap['footprints_captured']==1101 and len(cap['objects'])==7215 and len(cap['all_groups'])==2910 and len(cap['zones'])==47
    assert sum(o['kind']=='PCB_TRACK' for o in cap['objects'])==3012 and sum(o['kind']=='PCB_VIA' for o in cap['objects'])==482
    assert audit['retained_part_count']==1086 and audit['retained_pin_entries']==3420
    assert visual['total_directly_inspected_views']==13 and not visual['additional_visual_findings']
    assert (inv['selected_net_count'],inv['open_selected_net_count'],inv['selected_missing_joins'])==(91,32,58)
    assert cellinv['local_bypass_and_both_returns_complete']==[f'E_U{i}' for i in range(18,29)]
    assert not any(c['IC_supply_connected_to_aux_regulator'] for c in cellinv['cells'])
    assert auxinv['source_connected_IC_supply_pins']==8 and auxinv['unconnected_IC_supply_pins']==73
    assert abs(auxinv['nominal_capacitance_F']-28.5e-6)<1e-12 and not auxinv['actual_current_bound_established']
    status={k:v for k,v in prior.items() if not k.startswith('power_') and k not in ['source_sha256','native_checks']}
    docs=[power/'README.md',survey.parent/'README.md',cells.parent/'README.md',aux.parent/'README.md']
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,*docs]},
        revision='TBP50',previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP49 is the historical baseline. The remaining eight U18–U28 local bypass/ground cells and U19 supply-pin tie close 27 connections; auxiliary source distribution remains unfinished.',
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2172,power_footprints=1101,power_electrical_parts=1086,power_schematic_pin_entries=3420,power_mapped_pad_instances=3481,
        power_copper_segments=3012,power_copper_vias=482,power_filled_zones=47,power_native_connection_groups=2910,
        power_connections_closed_this_pass=27,power_added_tracks_this_pass=69,power_retired_tracks_this_pass=112,
        power_added_vias_this_pass=20,power_retired_vias_this_pass=0,power_added_zones_this_pass=0,
        power_moved_footprints_this_pass=5,power_changed_pad_instances_this_pass=10,power_changed_component_values_this_pass=0,power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=43,power_refilled_existing_zones=4,power_edited_existing_zone_outlines=1,
        power_geometry_errors=0,power_parity_errors=0,power_ERC_errors=0,power_ERC_warnings=2,
        power_native_group_merges=audit['declared_native_group_merges'],power_all_other_native_groups_preserved=True,
        power_previous_full_width_adjacent_ground_reference_cases_preserved=len(refs['retained_reference_cases']),
        power_new_non_ground_route_paths=18,power_new_non_ground_reference_complete=True,
        power_retained_quiet_returns=prior['power_retained_quiet_returns'],power_quiet_return_geometry_unchanged=True,power_quiet_return_topology_preserved=True,
        power_own_quiet_reference_preserved=True,power_digital_own_quiet_reference_complete=True,
        power_reference_review=str((power/'startup-cell-reference-review.json').relative_to(REPO)),
        power_connectivity_review=str((power/'startup-cell-review.json').relative_to(REPO)),
        power_supply_plane_review=str((power/'startup-cell-reference-review.json').relative_to(REPO)),
        power_legacy_reference_paths_repaired_this_pass=0,power_legacy_incomplete_reference_paths_preserved=0,
        power_prior_startup_repaired_reference_paths_preserved=True,power_all_supply_planes_unchanged=True,
        power_supply_contacts_and_region_counts_preserved=True,power_loaded_current_timing_noise_thermal_qualified=False,
        power_inlet_resistance_model_scope='TBP35 historical copper only; current fills and via sharing are not modeled.',
        power_visual_evidence_scope='Thirteen directly inspected views: ten local copper/ground details, both surface overviews and the six-inner-layer contact sheet.',
        power_startup_connectivity_survey=str(survey.relative_to(REPO)),
        power_startup_connectivity_survey_scope='Current candidate native connectivity; excludes supply and ground distribution.',
        power_startup_cell_survey=str(cells.relative_to(REPO)),
        power_local_bypass_ground_cells_completed_this_pass=audit['local_bypass_ground_cells'],
        power_local_bypass_ground_cells_complete=cellinv['local_bypass_and_both_returns_complete'],
        power_surveyed_startup_cells_connected_to_aux_source=0,power_aux_source_distribution_complete=False,
        power_aux_distribution_inventory=str(aux.relative_to(REPO)),power_aux_source_connected_IC_supply_pins=8,power_aux_unconnected_IC_supply_pins=73,
        power_aux_nominal_capacitance_F=auxinv['nominal_capacitance_F'],power_aux_current_bound_established=False,power_aux_installed_thermal_path_qualified=False,
        power_surveyed_startup_nets=91,power_open_surveyed_startup_nets=32,power_surveyed_startup_missing_joins=58,
        power_routing_complete=False,power_startup_complete=False,fabrication_released=False,goal_complete=False)
    status['next_required_design_work'][0]='Reconcile AUX load/startup/thermal limits and complete its source distribution, the 58 surveyed startup joins across 32 nets, and startup/fault behavior verification; preserve repaired references'
    out=STAGING/'two-board-fabrication-status-50';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(revision='TBP50',bindings=bindings,reference_cases=len(refs['retained_reference_cases']),power_opens=2172,signal_opens=251,fabrication_released=False)))


if __name__=='__main__':run()
