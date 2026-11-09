"""Adopt AUX return, feedback-reference and thermal copper with explicit limits."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-aux-ground-native-02'
    previous = STAGING / 'two-board-fabrication-status-24/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'aux-ground-routing.json', 'aux-ground-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2447-aux-ground-02/capture.json',
        STAGING / 'two-board-power-aux-ground-filled-02/local-plane-fill.json',
        STAGING / 'two-board-signal-routed-native-03/review.json',
        STAGING / 'two-board-power-buck-enable-native-01/enable-dc-screen.json',
        STAGING / 'two-board-input-capacitor-review-01/review.json']
    count = 0
    for report in reports:
        data = json.loads(report.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in data.get(field, {}).items():
                p = Path(name)
                if not p.is_absolute():
                    p = (REPO if name.startswith(('hardware/', 'tests/')) else report.parent) / p
                assert p.is_file() and sha(p) == h, (report, name)
                count += 1
    a=json.loads((power/'aux-ground-audit.json').read_text())
    native=json.loads((power/'review.json').read_text())
    assert a['old_opens']==a['new_opens']==native['opens']==2447
    assert a['connections_closed']==0 and a['added_segments']==a['added_vias']==a['new_zones']==4
    assert a['unchanged_complete_pin_net_map'] and a['all_component_poses_values_packages_unchanged']
    assert a['all_old_copper_objects_unchanged'] and a['three_previous_authored_zones_and_native_fills_unchanged']
    assert a['all_previous_native_connection_groups_preserved']==3185
    assert a['all_U20_direct_ground_via_contacts_preserved']==12
    assert a['U20_sense_projection_uncovered_area_mm2']==a['FB_projection_uncovered_area_mm2']==0
    assert a['input_output_returns_join_only_through_GND_pin_land']
    assert a['multilayer_pin_land_cut_disconnected_input_and_output'] and a['no_other_circuit_ground_pad_joined']
    assert a['thermal_vias_outside_SMD_lands'] and a['vias_screened']==190
    assert len(a['zone_unfracture_geometric_fidelity'])==8
    assert a['geometry_findings']==a['parity_findings']==a['erc_errors']==0
    status=json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md',
            STAGING/'two-board-aux-unfracture-review-01/README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2447,power_copper_segments=2293,power_copper_vias=190,
        power_connections_closed_this_pass=0,power_moved_footprints_this_pass=0,
        power_flipped_footprints_this_pass=0,power_replaced_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=0,power_all_component_poses_preserved=True,
        power_all_retained_copper_objects_unchanged=True,power_all_retained_copper_geometry_unchanged=False,
        power_retained_copper_geometry_exception='U20 In1 ground edge recessed; all prior ordinary copper and the other three earlier zones/fills unchanged',
        power_all_retained_tracks_vias_unchanged=True,power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3185,
        power_all_vias_screened=190,power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_local_filled_planes=8,power_whole_board_planes_complete=False,
        power_existing_U23_planes_unchanged=True,power_U20_planes_and_U23_VIN_plane_unchanged=False,
        power_U23_planes_and_U20_VIN_plane_unchanged=True,
        power_local_plane_contacts_preserved=True,power_local_plane_contact_change=None,
        power_U20_ground_plane_area_mm2=a['U20_ground_area_after_mm2'],
        power_U20_ground_recess_for_AUX_reference_mm2=a['U20_native_ground_removed_area_mm2'],
        power_U20_all_direct_ground_via_contacts_preserved=12,
        power_AUX_ground_routing_audit=str((power/'aux-ground-audit.json').relative_to(REPO)),
        power_AUX_input_output_ground_regions_and_thermal_vias_complete=True,
        power_AUX_input_output_returns_join_at_GND_pin=True,
        power_AUX_FB_reference_projection_complete_except_own_via_antipads=True,
        power_AUX_ground_plane_checks=a['local_plane_checks'],
        power_AUX_thermal_via_count=4,power_AUX_actual_thermal_resistance_qualified=False,
        power_AUX_source_output_distribution_and_PG_connected=False,
        power_AUX_load_derating_startup_and_thermal_qualified=False,
        power_zone_capture_geometric_fidelity_verified=True,
        power_copper_all_layers_visually_reviewed=True,power_local_AUX_detail_visually_reviewed=True,
        fabrication_released=False,goal_complete=False)
    for row in status['power_U20_local_plane_checks']:
        if row['layer']=='In1.Cu':
            row['area_mm2']=a['U20_ground_area_after_mm2']
            row['area_updated_after_AUX_reference_recess']=True
    status['next_required_design_work']=[
        'Connect AUX source/output distribution and power-good without bypassing the split ground-return topology',
        *[q for q in status['next_required_design_work'] if not q.startswith('Complete AUX input/output ground regions')]]
    out=STAGING/'two-board-fabrication-status-25';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2447,signal_opens=251,new_ground_regions=4,new_thermal_vias=4,fabrication_released=False)))


if __name__=='__main__':run()
