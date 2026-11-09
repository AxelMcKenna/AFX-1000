"""Select the independently checked analog control and quiet-return checkpoint."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

def run():
    power=STAGING/'two-board-power-analog-cells-native-03'
    previous=STAGING/'two-board-fabrication-status-44/status.json'
    capture=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json'
    paths=[previous,capture,STAGING/'two-board-analog-cell-plan-06/geometry-review.json',
           STAGING/'two-board-power-analog-cells-filled-03/local-plane-fill.json',
           STAGING/'two-board-signal-routed-native-03/review.json',
           *[power/n for n in ['review.json','analog-cell-routing.json','analog-connectivity-review.json',
               'analog-reference-review.json','analog-supply-plane-review.json','plots/native-plots.json',
               'plots/preview-render.json','plots/analog-complete-render.json','plots/analog-retirement-render.json',
               'plots/analog-visual-review.json','plots/visual-review.json']]]
    bindings=0
    for path in paths:
        d=json.loads(path.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,h in d.get(key,{}).items():
                q=Path(name)
                if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/q
                assert sha(q)==h,(path,name)
                bindings+=1
    cap=json.loads(capture.read_text())
    native,route,audit,refs,supply,visual=[json.loads((power/n).read_text()) for n in ['review.json','analog-cell-routing.json','analog-connectivity-review.json','analog-reference-review.json','analog-supply-plane-review.json','plots/visual-review.json']]
    assert native['opens']==audit['new_opens']==cap['native_uncapped_opens']==2211
    assert native['geometry_findings']==native['schematic_parity_findings']==audit['ERC_errors']==0 and audit['ERC_warnings']==2
    assert audit['all_other_native_groups_preserved'] and audit['closed_connections']==len(audit['declared_native_joins'])==26
    assert audit['retained_part_count']==1086 and audit['retained_pin_entries']==3420 and audit['moved_pad_count']==24
    assert refs['retained_reference_complete'] and refs['new_reference_complete'] and refs['own_quiet_reference_complete']
    assert len(refs['retained_reference_cases'])==1567 and len(refs['new_non_ground_paths'])==26
    assert all(x['uncovered_mm2']<1e-6 for x in refs['retained_reference_cases']+refs['new_non_ground_paths'])
    assert len(audit['new_quiet_returns'])==3 and len(audit['retained_digital_quiet_returns'])==4
    assert all(q['owned_graph_connected'] and q['star_only_main_return'] for q in audit['new_quiet_returns'])
    assert all(q['contacts_preserved'] and q['star_only_main_return'] for q in audit['retained_digital_quiet_returns'])
    assert route['added_tracks']==73 and route['added_vias']==27 and len(route['new_zones'])==8 and len(route['retired_objects'])==91
    assert len(route['moves'])==12 and not route['circuit_changes'] and len(route['edited_zone_outlines'])==6 and len(route['refilled_existing_zones'])==8
    assert cap['footprints_captured']==1101 and len(cap['objects'])==7204 and len(cap['all_groups'])==2949 and len(cap['zones'])==47
    assert sum(o['kind']=='PCB_TRACK' for o in cap['objects'])==3029 and sum(o['kind']=='PCB_VIA' for o in cap['objects'])==454
    assert supply['all_supply_contacts_preserved'] and supply['all_supply_region_counts_preserved'] and supply['supply_outlines_unchanged']
    assert len(supply['supply_planes'])==11 and supply['changed_supply_plane_count']==2
    before=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text())
    supplynets={z['net'] for z in supply['supply_planes']}
    assert not any(o['uuid'] in route['retired_objects'] and o['net'] in supplynets for o in before['objects'])
    assert visual['total_directly_inspected_views']==16 and not visual['additional_visual_findings']
    status={k:v for k,v in json.loads(previous.read_text()).items() if not k.startswith('power_') and k not in ['source_sha256','native_checks']}
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,power/'README.md']},
        revision='TBP45',previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP44 is the historical baseline. This revision moves twelve analog passives, replaces declared control copper and creates eight quiet fields. Current metrics below replace prior power metrics; earlier circuit analyses remain scoped to their recorded snapshots.',
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2211,
        power_footprints=1101,power_electrical_parts=1086,power_schematic_pin_entries=3420,power_mapped_pad_instances=3481,
        power_copper_segments=3029,power_copper_vias=454,power_filled_zones=47,power_native_connection_groups=2949,
        power_connections_closed_this_pass=26,power_added_tracks_this_pass=73,power_retired_tracks_this_pass=83,
        power_added_vias_this_pass=27,power_retired_vias_this_pass=8,power_added_zones_this_pass=8,
        power_moved_footprints_this_pass=12,power_changed_pad_instances_this_pass=24,power_face_changes_this_pass=3,
        power_changed_component_values_this_pass=0,power_schematic_pin_net_changes_this_pass=0,
        power_unchanged_existing_zone_fills=31,power_changed_existing_zone_fills=8,power_edited_existing_zone_outlines=6,
        power_geometry_errors=0,power_parity_errors=0,power_ERC_errors=0,power_ERC_warnings=2,
        power_native_group_merges=audit['declared_native_joins'],power_all_other_native_groups_preserved=True,
        power_previous_full_width_adjacent_ground_reference_cases_preserved=1567,
        power_new_non_ground_route_paths=26,power_new_non_ground_reference_complete=True,
        power_new_analog_quiet_returns=audit['new_quiet_returns'],power_retained_digital_quiet_returns=audit['retained_digital_quiet_returns'],
        power_analog_own_quiet_reference_complete=True,power_analog_reference_review=str((power/'analog-reference-review.json').relative_to(REPO)),
        power_connectivity_review=str((power/'analog-connectivity-review.json').relative_to(REPO)),
        power_supply_plane_review=str((power/'analog-supply-plane-review.json').relative_to(REPO)),
        power_supply_contacts_and_region_counts_preserved=True,power_inlet_supply_fill_changed=True,
        power_loaded_current_timing_noise_thermal_qualified=False,power_inlet_resistance_model_scope='TBP35 historical copper only; current fills and via sharing are not modeled.',
        power_visual_evidence_scope='Sixteen inspected views: five analog details, eight wider changed-route views, both surface overviews and the inner-layer overview sheet.',
        power_routing_complete=False,power_startup_complete=False,fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Complete remaining digital pulldown returns (including R104), earlier support/PG reference gaps and full startup verification',
        'Complete protected outputs, analog input/source loops, analog/module distribution, force/quiet returns and signal routing',
        'Establish load/startup/fault states, effective capacitance, current sharing, accepted stack/plating, parasitic/noise/timing and thermal limits',
        'Resolve approved ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables',
        'Prepare the reviewed whole-unit prototype bring-up plan and complete applicable release checks']
    out=STAGING/'two-board-fabrication-status-45';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(revision='TBP45',bindings=bindings,power_opens=2211,signal_opens=251,closed_connections=26,retained_reference_cases=1567,new_reference_paths=26,fabrication_released=False)))
if __name__=='__main__':run()
