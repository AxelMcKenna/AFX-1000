"""Adopt the checked input eFuse controls without claiming fabrication release."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-input-controls-native-02'
    previous=STAGING/'two-board-fabrication-status-26/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','input-controls-routing.json','input-controls-audit.json',
        'rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json',
        'plots/detail-render.json','plots/visual-review.json']],
        STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json',
        STAGING/'two-board-power-input-controls-filled-02/local-plane-fill.json',
        STAGING/'two-board-aux-load-review-01/review.json',
        STAGING/'two-board-aux-load-review-01/verification.json',
        STAGING/'two-board-signal-routed-native-03/review.json']
    count=0
    for report in reports:
        d=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in d.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    a=json.loads((power/'input-controls-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert a['new_opens']==native['opens']==2440 and a['old_opens']==2445 and a['connections_closed']==5
    assert a['all_previous_native_connection_groups_preserved']==3183
    for key in ['unchanged_complete_pin_net_map','all_old_tracks_vias_unchanged','all_unmoved_pads_unchanged',
        'all_values_packages_and_sides_preserved','all_eight_authored_zones_and_native_fills_unchanged',
        'AUX_group_and_return_topology_preserved','local_ground_has_only_four_intended_pads']:assert a[key],key
    assert a['geometry_findings']==a['parity_findings']==a['erc_errors']==0 and a['erc_warnings']==2
    assert a['full_control_trace_reference_uncovered_mm2']==0
    assert a['tracks']==2313 and a['vias']==194 and a['zones']==10
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2440,power_copper_segments=2313,power_copper_vias=194,
        power_connections_closed_this_pass=5,power_moved_footprints_this_pass=2,
        power_flipped_footprints_this_pass=0,power_replaced_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=4,power_all_component_poses_preserved=False,
        power_component_pose_exception='C105 and R107 move on the front beside U101; four pads move. Values, land patterns, sides and pin/net assignments are unchanged.',
        power_all_retained_copper_objects_unchanged=False,power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='Only four pads on C105/R107 move. All old tracks, vias, other pads and eight existing zone outlines/fills remain exact.',
        power_all_retained_tracks_vias_unchanged=True,power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3183,
        power_all_vias_screened=194,power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_local_filled_planes=10,power_whole_board_planes_complete=False,
        power_local_plane_contacts_preserved=True,power_local_plane_contact_change=None,
        power_input_controls_routing_audit=str((power/'input-controls-audit.json').relative_to(REPO)),
        power_input_ILIM_and_dVdT_locally_connected=True,
        power_input_GND_EP_and_control_passive_returns_locally_connected=True,
        power_input_control_reference_projection_complete=True,
        power_input_control_ground_plane_checks=a['local_plane_checks'],
        power_input_force_routing_complete=False,power_input_protection_startup_and_thermal_qualified=False,
        power_exact_input_control_passive_MPN_and_tolerances_qualified=False,
        power_zone_capture_geometric_fidelity_verified=True,
        power_copper_all_layers_visually_reviewed=True,power_local_input_controls_visually_reviewed=True,
        fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Complete the input source/blocking-FET loop, bypass capacitors, voltage-threshold dividers, high-current paths and final system ground return; local ILIM/dVdT controls and references are now connected',
        *status['next_required_design_work']]
    out=STAGING/'two-board-fabrication-status-27';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2440,signal_opens=251,connections_closed=5,fabrication_released=False)))

if __name__=='__main__':run()
