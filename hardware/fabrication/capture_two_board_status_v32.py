"""Select the audited fast-OV return-reference revision without claiming release."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha


def run():
    power=STAGING/'two-board-power-fast-ov-return-native-02'
    previous=STAGING/'two-board-fabrication-status-31/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','fast-ov-return-routing.json','fast-ov-return-audit.json','fast-ov-return-plane-review.json','rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/detail-render.json','plots/visual-review.json']],
        STAGING/'two-board-power-routing-inputs-2383-fast-ov-return-02/capture.json',STAGING/'two-board-power-fast-ov-return-filled-02/local-plane-fill.json',STAGING/'two-board-power-fast-ov-native-03/fast-ov-return-load-review.json',STAGING/'two-board-signal-routed-native-03/review.json']
    count=0
    for report in reports:
        d=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in d.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    audit,native,planes,visual=[json.loads((power/n).read_text()) for n in ['fast-ov-return-audit.json','review.json','fast-ov-return-plane-review.json','plots/visual-review.json']]
    assert audit['old_opens']==audit['new_opens']==native['opens']==2383 and audit['connections_closed']==0
    assert audit['all_previous_connection_groups_preserved']==planes['all_previous_connection_groups_preserved']==3121
    assert (audit['components'],audit['footprints'],audit['tracks'],audit['vias'],audit['zones'])==(1086,1101,2444,234,14)
    assert (audit['moved_footprints'],audit['changed_pad_instances'],audit['flipped_footprints'])==(2,5,0)
    assert (audit['retired_tracks'],audit['retired_vias'],audit['added_tracks'],audit['added_vias'])==(20,3,16,3)
    for k in ['unchanged_existing_pin_net_map','no_added_or_removed_components','all_existing_values_and_package_identifiers_unchanged','all_retained_tracks_vias_and_unmoved_pads_unchanged','all_native_zone_declarations_and_fill_provenance_verified','all_native_instance_paths_canonical','fast_OV_locally_connected','VIN_AUX_feed_connected']:assert audit[k],k
    assert audit['geometry_errors']==audit['parity_errors']==audit['ERC_errors']==0 and audit['ERC_warnings']==2
    assert planes['all_fourteen_native_planes_contiguous'] and planes['AUX_input_output_returns_separate_after_GND_land_cut'] and planes['net_tie_pads_remain_isolated']
    assert planes['unchanged_existing_native_zones']==9 and not planes['new_routes_with_reference_gaps']
    assert len(planes['adjacent_In6_back_route_coverage'])==16 and len(planes['new_route_reference_coverage'])==33
    assert all(q['best_uncovered_mm2']==0 for q in planes['new_route_reference_coverage'])
    assert all(q['uncovered_mm2']==0 for q in planes['AUX_feedback_and_trim_reference_coverage'])
    assert not visual['complete_delta_audit_pending'] and len(visual['inspected_views'])==11
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2383,power_copper_segments=2444,power_copper_vias=234,power_connections_closed_this_pass=0,
        power_moved_footprints_this_pass=2,power_flipped_footprints_this_pass=0,power_replaced_footprints_this_pass=0,power_added_components_this_pass=[],power_added_schematic_pins_this_pass=0,
        power_changed_pad_instances_this_pass=5,power_added_pad_instances_this_pass=0,power_all_component_poses_preserved=False,
        power_component_pose_exception='Q103 moves and rotates 180 degrees; G_NT1 shifts for spacing. Five pads move, with no flips, package/value changes or schematic changes.',
        power_retained_copper_geometry_exception='Five moved pads; 20 tracks and 3 vias retired; 16 tracks and 3 vias added; five refilled regions. Four ground-reference outlines change; nine prior fills remain exact.',
        power_all_retained_tracks_vias_unchanged=True,power_all_other_copper_objects_unchanged=True,power_previous_native_connection_groups_preserved=3121,
        power_all_vias_screened=234,power_minimum_all_via_drill_to_SMD_mm=audit['all_via_minimum_drill_to_SMD_mm'],power_local_filled_planes=14,
        power_local_plane_contacts_preserved=False,power_local_plane_contact_change='Q103 source and R120 return use replacement vias. U101 reference regions extend and AUX reference outlines receive notches. All prior connection groups and AUX split-return topology remain intact.',
        power_input_control_ground_plane_checks=[q for q in planes['plane_contacts'] if q['uuid'] in ['a147ef12-37f5-562e-9340-6c74b3790186','d41ab58e-16e9-5d76-8b14-dc335aff8371','78fadc71-5bdb-5968-8ca8-0e3b4b40722f']],
        power_AUX_ground_plane_checks=[q for q in planes['plane_contacts'] if q['uuid'] in ['d0572a8e-b95d-5c59-9a7c-1d3514a507b4','94ece1a2-cfec-59cf-ba79-c618ed566f57','bc76c316-2c04-5ecb-85b7-3e5f80b26bf1','dfd01f0a-edcf-55b7-aecb-2d44a419b9b3']],
        power_fast_OV_routing_audit=str((power/'fast-ov-return-audit.json').relative_to(REPO)),power_fast_OV_plane_review=str((power/'fast-ov-return-plane-review.json').relative_to(REPO)),
        power_fast_OV_return_load_review=str((STAGING/'two-board-power-fast-ov-native-03/fast-ov-return-load-review.json').relative_to(REPO)),
        power_fast_OV_return_load_review_scope='Historical TBP31 route-gap evidence and unchanged AUX load census; TBP32 plane review supersedes the route-gap screen.',
        power_fast_OV_reference_geometry_passed=True,power_fast_OV_route_sections_with_adjacent_ground=33,power_fast_OV_reference_design_review_complete=False,
        power_input_fast_OV_loaded_response_qualified=False,power_AUX_load_derating_startup_and_thermal_qualified=False,
        power_duplicate_paths_removed_this_pass=0,power_local_fast_OV_visually_reviewed=True,fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Qualify fast-OV cutoff response, threshold/hysteresis, capacitor derating and loop/reference electrical behavior; all 33 current route projections now have adjacent ground coverage',
        *[q for q in status['next_required_design_work'] if not q.startswith('Resolve the recorded fast-OV')]]
    out=STAGING/'two-board-fabrication-status-32';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2383,signal_opens=251,fast_OV_reference_sections=33,connections_closed=0,fabrication_released=False)))

if __name__=='__main__':run()
