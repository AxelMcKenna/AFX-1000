"""Bind the inlet-cable retirement and independently checked U23 regrouping."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-buck-cell-native-01'
    previous=STAGING/'two-board-fabrication-status-10/status.json'
    reports=[power/n for n in ['review.json','circuit-audit.json','buck-cell-change.json','buck-cell-audit.json',
                              'plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']]
    reports.extend([previous,STAGING/'two-board-power-routing-inputs-2551-buck-cell/capture.json',
                    STAGING/'two-board-buck-cell-survey-01/survey.json',STAGING/'two-board-buck-cell-survey-02/survey.json',
                    STAGING/'two-board-signal-routed-native-03/review.json'])
    bindings=0
    for report in reports:
        d=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in d.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                bindings+=1
    audit=json.loads((power/'buck-cell-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert audit['new_opens']==native['opens']==2551
    assert audit['retained_components']==native['placed_electrical_parts']==1088
    assert audit['retained_footprints']==1103 and native['mapped_pad_instances']==3485
    assert audit['unchanged_remaining_pin_net_map'] and audit['retained_native_connection_groups_preserved']==3287
    assert audit['moved_footprints']==10 and audit['moved_native_pad_instances']==48
    assert audit['geometry_findings']==audit['schematic_parity_findings']==audit['erc_errors']==0
    assert audit['via_drill_SMD_checks']==124
    status=json.loads(previous.read_text())
    # Keep historical measurements in their bound checkpoint, not as fresh
    # measurements of this board after terminal retirement and pad relocation.
    for key in ['power_interface_pin_pairs','power_restored_source_connection_groups',
                'power_layer_detour_control_routes_this_pass','power_via_repair_parent_groups_preserved',
                'power_new_vias_rechecked_against_final_geometry','power_new_route_mount_reserves_checked',
                'power_minimum_all_via_hole_to_hole_mm','power_minimum_all_via_to_foreign_polygon_mm',
                'power_remaining_opens_on_originally_rejected_source_nets']:
        status.pop(key,None)
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2551,power_parts=1088,power_footprints=1103,power_schematic_pin_entries=3424,power_mapped_pad_instances=3485,
        power_copper_segments=2094,power_copper_vias=124,power_connections_closed_this_pass=0,
        power_retired_internal_cable_connectors=['I_J2','P_J101'],power_retired_connector_terminal_opens=3,
        power_retired_inlet_leaf_tracks=3,power_original_integration_pin_pairs=49,power_retained_interface_header_pin_pairs=47,
        power_all_component_poses_preserved=False,power_moved_critical_cell_footprints=10,
        power_moved_native_pad_instances=48,power_remaining_pin_net_map_unchanged=True,
        power_previous_native_connection_groups_preserved=3287,power_all_retained_copper_objects_unchanged=True,
        power_buck_U23_local_cell_regrouped=True,power_buck_U23_power_loop_qualified=False,
        power_U20_and_AUX_local_placement_requires_repair=True,
        power_all_vias_screened=124,power_remaining_via_drills_in_SMD_lands=0,
        power_minimum_all_via_drill_to_SMD_mm=audit['minimum_via_drill_to_SMD_mm'],
        power_moved_courtyard_context_findings=0,power_moved_courtyard_gap_mm=.3,
        power_copper_all_layers_visually_reviewed=True,fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Optimize U23 feedback/BP5/AGND placement and route its short input, boot, switching, output and return paths',
        'Regroup U20, AUX and other critical cells; remove additional internal connectors only after verifying every terminal role',
        'Verify effective buck input/output capacitance after voltage/temperature/tolerance derating',
        *status['next_required_design_work']]
    out=STAGING/'two-board-fabrication-status-11';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=bindings,power_opens=2551,power_parts=1088,signal_opens=251,fabrication_released=False)))


if __name__=='__main__':run()
