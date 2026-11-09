"""Adopt the checked enable reroute with explicit MODE copper replacement."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

def run():
    power=STAGING/'two-board-power-buck-enable-native-01';previous=STAGING/'two-board-fabrication-status-16/status.json'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','buck-enable-routing.json','buck-enable-audit.json','enable-dc-screen.json','rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/detail-render.json','plots/visual-review.json']],STAGING/'two-board-power-routing-inputs-2508-buck-enable/capture.json',STAGING/'two-board-power-buck-enable-filled-01/local-plane-fill.json',STAGING/'two-board-signal-routed-native-03/review.json']
    count=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    a=json.loads((power/'buck-enable-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert a['new_opens']==native['opens']==2508 and a['connections_closed']==3
    assert a['all_other_copper_objects_unchanged'] and a['unchanged_complete_pin_net_map'] and a['sense_trace_projection_coverage_preserved']
    assert a['geometry_findings']==a['parity_findings']==a['erc_errors']==0
    assert a['added_segments']==11 and a['added_vias']==2 and a['vias_screened']==151
    assert len(a['local_plane_checks'])==2 and all(z['single_contiguous_filled_polygon'] and z['unexplained_fill_change_mm2']<1e-5 for z in a['local_plane_checks'])
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2508,
        power_copper_segments=2177,power_copper_vias=151,power_connections_closed_this_pass=3,
        power_moved_footprints_this_pass=1,power_replaced_footprints_this_pass=0,power_changed_pad_instances_this_pass=2,
        power_schematic_pin_net_changes_this_pass=0,power_retained_track_net_changes_this_pass=0,
        power_all_retained_copper_objects_unchanged=False,power_all_retained_copper_geometry_unchanged=False,
        power_intentionally_replaced_MODE_tracks=3,power_intentionally_replaced_MODE_vias=1,power_all_other_copper_objects_unchanged=True,
        power_previous_native_connection_groups_preserved=3249,power_all_vias_screened=151,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_U23_enable_connected=True,power_U23_enable_full_electrical_qualified=False,
        power_U23_enable_DC_scenario_screen_pass=True,power_U23_enable_DC_allocations_guaranteed=False,
        power_local_filled_planes=2,power_local_plane_contacts_preserved=True,power_sense_reference_projection_preserved=True,
        power_copper_all_layers_visually_reviewed=True,power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Connect wider U23 source feed and complete board-wide distribution/planes; verify local current/thermal returns',
        'Qualify shared POWER_READY enable levels, EN sourcing bounds, loaded AUX, resistor drift and partial-power/timing behavior',
        *[s for s in status['next_required_design_work'] if not s.startswith('Complete U23 enable and wider source feed')]]
    out=STAGING/'two-board-fabrication-status-17';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2508,signal_opens=251,physical_connections_added=3,fabrication_released=False)))

if __name__=='__main__':run()
