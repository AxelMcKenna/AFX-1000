"""Adopt verified U23 sense/configuration and relocated-buffer bypass routes."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-buck-control-native-02'
    previous=STAGING/'two-board-fabrication-status-14/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','buck-control-routing.json','buck-control-audit.json','rejected-source-net-status.json',
             'plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']],
             STAGING/'two-board-power-routing-inputs-2518-buck-control/capture.json',
             STAGING/'two-board-signal-routed-native-03/review.json']
    count=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    audit=json.loads((power/'buck-control-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert audit['new_opens']==native['opens']==2518 and audit['connections_closed']==7
    assert audit['all_old_copper_objects_unchanged'] and audit['unchanged_complete_pin_net_map']
    assert audit['configuration_returns_use_existing_quiet_AGND_group'] and audit['minimum_projected_sense_to_SW_BOOT_copper_gap_mm']>=1
    assert audit['geometry_findings']==audit['parity_findings']==audit['erc_errors']==0
    assert audit['added_segments']==21 and audit['added_vias']==8 and audit['vias_screened']==138
    status=json.loads(previous.read_text())
    for k in ['power_visual_evidence_reused_from_identical_geometry','power_model_only_external_obligations_removed']:
        status.pop(k,None)
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2518,
        power_copper_segments=2154,power_copper_vias=138,power_connections_closed_this_pass=7,
        power_moved_footprints_this_pass=2,power_replaced_footprints_this_pass=0,power_changed_pad_instances_this_pass=4,
        power_schematic_pin_net_changes_this_pass=0,power_retained_track_net_changes_this_pass=0,
        power_remaining_pin_net_map_unchanged=True,power_all_retained_copper_objects_unchanged=True,
        power_all_retained_copper_geometry_unchanged=True,power_all_component_poses_preserved=False,
        power_previous_native_connection_groups_preserved=3263,power_all_vias_screened=138,
        power_minimum_all_via_drill_to_SMD_mm=audit['minimum_all_via_drill_to_SMD_mm'],
        power_U23_output_bank_connected_to_inductor_and_PGND=True,
        power_U23_output_bank_route_sections=16,power_U23_output_bank_added_tracks=17,power_U23_output_bank_added_vias=6,
        power_U23_output_sense_connected=True,power_U23_configuration_connected=True,power_N_U28_local_bypass_connected=True,
        power_U23_minimum_projected_sense_to_switching_copper_mm=1.15,power_U23_quiet_AGND_to_PGND_pending=True,power_buck_U23_power_loop_qualified=False,
        power_copper_all_layers_visually_reviewed=True,power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False,goal_complete=False)
    old=status['next_required_design_work']
    status['next_required_design_work']=[
        'Complete U23 enable, input/source bypass, PGND/AGND/reference planes and current/thermal return paths',
        *[s for s in old if not s.startswith(('Route U23 output sense','Route N_U28/N_C67 local bypass'))]]
    out=STAGING/'two-board-fabrication-status-15';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2518,signal_opens=251,physical_connections_added=7,fabrication_released=False)))

if __name__=='__main__':run()
