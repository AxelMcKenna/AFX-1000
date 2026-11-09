"""Adopt verified U23 bulk input connections and bounded local planes."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-buck-input-native-01'
    previous=STAGING/'two-board-fabrication-status-15/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','buck-input-routing.json','buck-input-audit.json','rejected-source-net-status.json',
             'plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']],
             STAGING/'two-board-power-routing-inputs-2511-buck-input/capture.json',
             STAGING/'two-board-signal-routed-native-03/review.json',
             STAGING/'two-board-power-buck-input-filled-01/local-plane-fill.json']
    count=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    audit=json.loads((power/'buck-input-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert audit['new_opens']==native['opens']==2511 and audit['connections_closed']==7
    assert audit['all_old_copper_objects_unchanged'] and audit['unchanged_complete_pin_net_map']
    assert audit['sense_trace_projection_covered_by_In1_except_own_via_antipads']
    assert len(audit['local_plane_checks'])==2 and all(z['single_contiguous_filled_polygon'] and z['connected_new_vias']==6 for z in audit['local_plane_checks'])
    assert audit['geometry_findings']==audit['parity_findings']==audit['erc_errors']==0
    assert audit['added_segments']==15 and audit['added_vias']==12 and audit['vias_screened']==150
    status=json.loads(previous.read_text())
    for k in ['power_visual_evidence_reused_from_identical_geometry','power_model_only_external_obligations_removed']:
        status.pop(k,None)
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2511,
        power_copper_segments=2169,power_copper_vias=150,power_connections_closed_this_pass=7,
        power_moved_footprints_this_pass=3,power_replaced_footprints_this_pass=0,power_changed_pad_instances_this_pass=6,
        power_schematic_pin_net_changes_this_pass=0,power_retained_track_net_changes_this_pass=0,
        power_remaining_pin_net_map_unchanged=True,power_all_retained_copper_objects_unchanged=True,
        power_all_retained_copper_geometry_unchanged=True,power_all_component_poses_preserved=False,
        power_previous_native_connection_groups_preserved=3256,power_all_vias_screened=150,
        power_minimum_all_via_drill_to_SMD_mm=audit['minimum_all_via_drill_to_SMD_mm'],
        power_U23_output_bank_connected_to_inductor_and_PGND=True,
        power_U23_output_bank_route_sections=16,power_U23_output_bank_added_tracks=17,power_U23_output_bank_added_vias=6,
        power_U23_output_sense_connected=True,power_U23_configuration_connected=True,power_N_U28_local_bypass_connected=True,
        power_U23_minimum_projected_sense_to_switching_copper_mm=1.15,power_U23_quiet_AGND_to_PGND_pending=False,power_buck_U23_power_loop_qualified=False,
        power_copper_all_layers_visually_reviewed=True,power_local_buck_detail_visually_reviewed=False,
        power_local_filled_planes=2,power_whole_board_planes_complete=False,
        power_U23_local_input_connected=True,power_U23_input_connected_to_source=False,power_U23_enable_connected=False,
        fabrication_released=False,goal_complete=False)
    old=status['next_required_design_work']
    status['next_required_design_work']=[
        'Complete U23 enable and wider source feed; verify local current/thermal returns and complete board-wide distribution and planes',
        *[s for s in old if not s.startswith(('Complete U23 enable, input/source bypass','Route U23 output sense','Route N_U28/N_C67 local bypass'))]]
    out=STAGING/'two-board-fabrication-status-16';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2511,signal_opens=251,physical_connections_added=7,fabrication_released=False)))

if __name__=='__main__':run()
