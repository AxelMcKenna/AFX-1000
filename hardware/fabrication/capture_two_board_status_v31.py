"""Select the independently reviewed fast-overvoltage and AUX-feed checkpoint."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

def run():
    power=STAGING/'two-board-power-fast-ov-native-03'
    previous=STAGING/'two-board-fabrication-status-30/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','fast-ov-routing.json','fast-ov-audit.json','fast-ov-plane-review.json','fast-ov-return-load-review.json','rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/detail-render.json','plots/visual-review.json']],
             STAGING/'two-board-power-routing-inputs-2383-fast-ov/capture.json',STAGING/'two-board-power-fast-ov-filled-03/local-plane-fill.json',STAGING/'two-board-aux-load-review-01/review.json',STAGING/'two-board-aux-load-review-01/verification.json',STAGING/'two-board-signal-routed-native-03/review.json']
    count=0
    for report in reports:
        d=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in d.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name);count+=1
    a,n,pl,rr,v=[json.loads((power/f).read_text()) for f in ['fast-ov-audit.json','review.json','fast-ov-plane-review.json','fast-ov-return-load-review.json','plots/visual-review.json']]
    assert a['old_opens']==2405 and a['new_opens']==n['opens']==2383 and a['connections_closed']==22
    assert a['all_previous_connection_groups_preserved']==pl['all_previous_connection_groups_preserved']==3143
    assert a['components']==1086 and a['footprints']==1101 and a['tracks']==2448 and a['vias']==234 and a['zones']==14
    assert a['moved_footprints']==10 and a['changed_pad_instances']==24 and a['flipped_footprints']==0
    for k in ['unchanged_existing_pin_net_map','new_capacitor_matches_retained_C401_package','all_existing_values_and_package_identifiers_unchanged','all_retained_tracks_vias_and_unmoved_pads_unchanged','all_native_zone_declarations_and_fill_provenance_verified','all_native_instance_paths_canonical','fast_OV_locally_connected','VIN_AUX_feed_connected']:assert a[k],k
    assert a['geometry_errors']==a['parity_errors']==a['ERC_errors']==0 and a['ERC_warnings']==2
    assert pl['all_fourteen_native_planes_contiguous'] and pl['AUX_input_output_returns_separate_after_GND_land_cut']
    assert pl['unchanged_existing_native_zones']==8 and not pl['new_routes_with_reference_gaps']
    assert len(pl['adjacent_In6_back_route_coverage'])==16 and len(pl['new_route_reference_coverage'])==22
    assert rr['all_new_routes_screened']==35 and rr['remaining_reference_design_review_required']
    assert rr['AUX_rail_terminals']==230 and rr['AUX_IC_supply_pins']==81
    assert not v['complete_delta_audit_pending'] and len(v['inspected_views'])==11
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_parts=1086,power_footprints=1101,power_schematic_pin_entries=3420,power_mapped_pad_instances=3481,
        power_opens=2383,power_copper_segments=2448,power_copper_vias=234,power_connections_closed_this_pass=22,
        power_moved_footprints_this_pass=10,power_flipped_footprints_this_pass=0,power_replaced_footprints_this_pass=0,power_added_components_this_pass=[a['added_component']],power_added_schematic_pins_this_pass=2,
        power_changed_pad_instances_this_pass=24,power_added_pad_instances_this_pass=2,power_all_component_poses_preserved=False,
        power_component_pose_exception='Ten existing fast-OV footprints move without flips. C114 is added as a dedicated same-face comparator bypass using C401 package and MPN. Existing values and pin/net assignments remain unchanged.',
        power_retained_copper_geometry_exception='Twenty-four moved pads, two new capacitor pads, 58 new tracks, 15 new vias and six refilled regions. In1/In6 U101 reference outlines expand; eight prior fills remain exact.',
        power_all_retained_tracks_vias_unchanged=True,power_all_other_copper_objects_unchanged=True,power_previous_native_connection_groups_preserved=3143,
        power_all_vias_screened=234,power_minimum_all_via_drill_to_SMD_mm=a['all_via_minimum_drill_to_SMD_mm'],power_local_filled_planes=14,
        power_local_plane_contacts_preserved=False,power_local_plane_contact_change='Fast-OV and C102 ground joins connect to U101 return; all previous groups and AUX split-return topology remain intact.',
        power_input_control_ground_plane_checks=[q for q in pl['plane_contacts'] if q['uuid'] in ['a147ef12-37f5-562e-9340-6c74b3790186','d41ab58e-16e9-5d76-8b14-dc335aff8371','78fadc71-5bdb-5968-8ca8-0e3b4b40722f']],
        power_AUX_ground_plane_checks=[q for q in pl['plane_contacts'] if q['uuid'] in ['d0572a8e-b95d-5c59-9a7c-1d3514a507b4','94ece1a2-cfec-59cf-ba79-c618ed566f57','bc76c316-2c04-5ecb-85b7-3e5f80b26bf1','dfd01f0a-edcf-55b7-aecb-2d44a419b9b3']],
        power_fast_OV_routing_audit=str((power/'fast-ov-audit.json').relative_to(REPO)),power_fast_OV_plane_review=str((power/'fast-ov-plane-review.json').relative_to(REPO)),power_fast_OV_return_load_review=str((power/'fast-ov-return-load-review.json').relative_to(REPO)),
        power_input_fast_OV_monitor_connected=True,power_input_fast_OV_loaded_response_qualified=False,power_fast_OV_reference_design_review_complete=False,
        power_AUX_upstream_VIN_source_connected=True,power_AUX_VIN_connection_scope='Local Q101 drain/U101 input to U102 input network; external input-cable feed and full current return still incomplete.',
        power_AUX_rail_terminals=230,power_AUX_direct_nominal_capacitance_F=rr['AUX_total_direct_nominal_capacitance_F'],power_AUX_load_derating_startup_and_thermal_qualified=False,
        power_duplicate_paths_removed_this_pass=0,power_local_fast_OV_visually_reviewed=True,fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Complete external input-cable feed and full system current return; local VIN-to-AUX and fast-OV circuit are connected',
        'Resolve the recorded fast-OV output/gate/RUN and supply-reference gaps; qualify actual cutoff response, threshold/hysteresis and capacitor derating',
        'Reconcile AUX effective capacitance and loaded startup with the added C114 bypass; current direct nominal total is 28.5uF',
        *[q for q in status['next_required_design_work'] if not q.startswith(('Complete input-cable feed','Complete upstream VIN source'))]]
    out=STAGING/'two-board-fabrication-status-31';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2383,signal_opens=251,connections_closed=22,fabrication_released=False)))

if __name__=='__main__':run()
