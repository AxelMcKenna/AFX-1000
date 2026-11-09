"""Adopt the independently checked blocking-FET and output-routing revision."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-input-source-native-03'
    previous=STAGING/'two-board-fabrication-status-27/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','input-source-routing.json','input-source-audit.json','input-source-plane-review.json',
        'rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json',
        'plots/detail-render.json','plots/visual-review.json']],
        STAGING/'two-board-power-routing-inputs-2427-input-source/capture.json',
        STAGING/'two-board-power-input-source-filled-03/local-plane-fill.json',
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
    a=json.loads((power/'input-source-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    planes=json.loads((power/'input-source-plane-review.json').read_text())
    assert a['new_opens']==native['opens']==2427 and a['old_opens']==2440 and a['connections_closed']==13
    assert a['all_previous_connection_groups_preserved']==planes['all_previous_connection_groups_preserved']==3178
    for key in ['unchanged_complete_pin_net_map','all_values_and_package_identifiers_unchanged',
        'back_C104_matches_retained_C102_package','all_retained_tracks_vias_and_unmoved_pads_unchanged',
        'all_native_zone_declarations_and_fill_provenance_verified','all_native_instance_paths_canonical']:assert a[key],key
    assert a['geometry_errors']==a['parity_errors']==a['ERC_errors']==0 and a['ERC_warnings']==2
    assert planes['all_thirteen_native_planes_contiguous'] and planes['AUX_input_output_returns_separate_after_GND_land_cut']
    assert planes['full_control_reference_uncovered_mm2']==planes['bulk_output_trace_reference_uncovered_mm2_excluding_own_antipads']==0
    assert a['tracks']==2334 and a['vias']==200 and a['zones']==13 and a['unchanged_existing_zones']==7
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2427,power_copper_segments=2334,power_copper_vias=200,
        power_connections_closed_this_pass=13,power_moved_footprints_this_pass=5,
        power_flipped_footprints_this_pass=1,power_replaced_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=27,power_all_component_poses_preserved=False,
        power_component_pose_exception='Q101/Q102/C103/G_NT1 move on the front; C104 moves to the back using the identical C102 package template. Values, package identifiers and logical pin/net mapping stay unchanged.',
        power_all_retained_copper_objects_unchanged=False,power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='27 moved pad instances, three explicitly retired/replaced PG tracks and three refilled ground regions. All retained tracks/vias, unmoved pads and seven earlier zone outlines/fills are exact.',
        power_all_retained_tracks_vias_unchanged=True,power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3178,
        power_all_vias_screened=200,power_minimum_all_via_drill_to_SMD_mm=a['all_via_minimum_drill_to_SMD_mm'],
        power_local_filled_planes=13,power_whole_board_planes_complete=False,
        power_local_plane_contacts_preserved=False,
        power_local_plane_contact_change='Expanded U101 In1 ground now directly connects C103 ground and the new C104 ground via. Original local ground contacts and AUX topology remain intact.',
        power_input_source_routing_audit=str((power/'input-source-audit.json').relative_to(REPO)),
        power_input_source_plane_review=str((power/'input-source-plane-review.json').relative_to(REPO)),
        power_input_blocking_gate_driver_and_local_pulldown_connected=True,
        power_input_Q101_drain_to_both_U101_IN_pins_connected=True,
        power_input_U101_OUT_pins_and_output_capacitors_connected=True,
        power_input_output_capacitor_returns_connected=True,
        power_input_bulk_output_trace_reference_complete_except_own_antipads=True,
        power_input_gate_driver_reference_environment_complete=False,
        power_input_control_ground_plane_checks=[q for q in planes['plane_contacts'] if q['uuid'] in ['a147ef12-37f5-562e-9340-6c74b3790186','d41ab58e-16e9-5d76-8b14-dc335aff8371']],
        power_AUX_ground_plane_checks=[q for q in planes['plane_contacts'] if q['uuid'] in ['d0572a8e-b95d-5c59-9a7c-1d3514a507b4','94ece1a2-cfec-59cf-ba79-c618ed566f57','bc76c316-2c04-5ecb-85b7-3e5f80b26bf1','dfd01f0a-edcf-55b7-aecb-2d44a419b9b3']],
        power_input_force_routing_complete=False,power_input_protection_startup_and_thermal_qualified=False,
        power_input_current_capacity_and_transients_qualified=False,
        power_input_bypass_and_voltage_thresholds_complete=False,
        power_native_instance_paths_canonical=True,power_duplicate_paths_removed_this_pass=24955,
        power_zone_capture_geometric_fidelity_verified=True,
        power_copper_all_layers_visually_reviewed=True,power_local_input_source_visually_reviewed=True,
        fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Resolve the input IN_SYS bypass placement/loop, voltage-threshold dividers, input-cable feed, VIN link to AUX and system return; local blocking-FET/pulldown and output-capacitor paths are now connected',
        'Qualify actual stack/current/thermal and source transient limits, including the 2mm output bus, bulk-capacitor loop and gate/driver reference environment',
        *[q for q in status['next_required_design_work'] if not q.startswith('Complete the input source/blocking-FET loop')]]
    out=STAGING/'two-board-fabrication-status-28';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2427,signal_opens=251,connections_closed=13,fabrication_released=False)))

if __name__=='__main__':run()
