"""Adopt the checked AUX PG/input-capacitor routes without claiming release."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-aux-pg-native-01'
    previous=STAGING/'two-board-fabrication-status-25/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','aux-pg-routing.json','aux-pg-audit.json',
        'rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json',
        'plots/detail-render.json','plots/visual-review.json']],
        STAGING/'two-board-power-routing-inputs-2445-aux-pg/capture.json',
        STAGING/'two-board-power-aux-pg-filled-01/local-plane-fill.json',
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
    a=json.loads((power/'aux-pg-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert a['new_opens']==native['opens']==2445 and a['old_opens']==2447 and a['connections_closed']==2
    assert a['all_previous_connection_groups_preserved']==3185
    for key in ['unchanged_complete_pin_net_map','all_component_poses_values_and_lands_unchanged',
        'E_U42_datasheet_corrected_in_PCB_schematic_embedded_and_local_library',
        'all_retained_ordinary_copper_unchanged','all_authored_zone_settings_and_outlines_unchanged',
        'U20_and_U23_zones_and_contacts_unchanged','input_output_returns_separate_after_multilayer_GND_land_cut',
        'AUX_ground_group_has_only_original_seven_pads']:assert a[key],key
    assert a['geometry_errors']==a['parity_errors']==a['ERC_errors']==0 and a['ERC_warnings']==2
    assert a['full_FB_trace_projection_uncovered_mm2']==0 and a['unchanged_native_zone_fills']==5
    assert a['tracks']==2300 and a['vias']==192 and a['zones']==8
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2445,power_copper_segments=2300,power_copper_vias=192,
        power_connections_closed_this_pass=2,power_moved_footprints_this_pass=0,
        power_flipped_footprints_this_pass=0,power_replaced_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=0,power_all_component_poses_preserved=True,
        power_all_retained_copper_objects_unchanged=True,power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='Three AUX native ground fills change around the FB via relocation and new PG route. Three FB tracks and one FB via are explicitly retired/replaced; all other ordinary copper and five fills are unchanged.',
        power_all_retained_tracks_vias_unchanged=True,power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3185,
        power_all_vias_screened=192,power_minimum_all_via_drill_to_SMD_mm=a['all_via_minimum_drill_to_SMD_mm'],
        power_local_filled_planes=8,power_whole_board_planes_complete=False,
        power_existing_U23_planes_unchanged=True,power_U20_planes_and_U23_VIN_plane_unchanged=True,
        power_U23_planes_and_U20_VIN_plane_unchanged=True,power_local_plane_contacts_preserved=True,
        power_local_plane_contact_change=None,
        power_AUX_PG_routing_audit=str((power/'aux-pg-audit.json').relative_to(REPO)),
        power_AUX_input_output_ground_regions_and_thermal_vias_complete=True,
        power_AUX_input_output_returns_join_at_GND_pin=True,
        power_AUX_FB_reference_projection_complete_except_own_via_antipads=True,
        power_AUX_ground_plane_checks=a['local_plane_checks'],
        power_AUX_FB_via_relocated_mm={'from':[190.6,133.6],'to':[190.3,133.4]},
        power_AUX_PG_connected_to_input_eFuse_SHDN=True,
        power_AUX_input_C102_connected_to_regulator_input_cell=True,
        power_AUX_upstream_VIN_source_connected=False,power_complete_RUN_net_connected=False,
        power_AUX_source_output_distribution_and_PG_connected=False,
        power_AUX_load_derating_startup_and_thermal_qualified=False,
        power_AUX_load_review=str((STAGING/'two-board-aux-load-review-01/review.json').relative_to(REPO)),
        power_E_U42_stale_datasheet_metadata_corrected=True,
        power_zone_capture_geometric_fidelity_verified=True,
        power_copper_all_layers_visually_reviewed=True,power_local_AUX_detail_visually_reviewed=True,
        fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Complete upstream VIN source, AUX output distribution and full RUN net with applicable return references; local PG-to-SHDN and input-capacitor joins are now native connected',
        'Reconcile current E/P/N state loads against AX03; resolve actual effective capacitance, startup and installed regulator thermal margin',
        *[q for q in status['next_required_design_work'] if not q.startswith(('Connect AUX source/output distribution','Verify full AUX load'))]]
    out=STAGING/'two-board-fabrication-status-26';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2445,signal_opens=251,connections_closed=2,fabrication_released=False)))

if __name__=='__main__':run()
