"""Bind control detours, inherited via repairs and reconciled source-net work."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-routed-native-08'
    detours=STAGING/'two-board-power-routed-native-07'
    signal=STAGING/'two-board-signal-routed-native-03'
    previous=STAGING/'two-board-fabrication-status-09/status.json'
    reports=[power/n for n in ['review.json','circuit-audit.json','via-repair.json','via-repair-audit.json',
        'plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']]
    reports.extend(detours/n for n in ['review.json','via-routing.json','additive-audit.json',
        'retained-via-clearance.json','rejected-source-net-status.json'])
    reports.extend([STAGING/'two-board-power-routing-inputs-2554/capture.json',
        STAGING/'two-board-power-routing-inputs-2554-via-repair/capture.json',
        signal/'review.json',signal/'copper-retention-v2.json',previous])
    bindings=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(str(report),name)
                bindings+=1
    native=json.loads((power/'review.json').read_text());repair=json.loads((power/'via-repair-audit.json').read_text())
    routing=json.loads((detours/'additive-audit.json').read_text())
    rejected=json.loads((detours/'rejected-source-net-status.json').read_text())
    assert native['opens']==repair['new_opens']==repair['old_opens']==routing['new_opens']==2554
    assert routing['old_opens']==2572 and routing['verified_routes']==18
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    assert repair['relocated_vias']==10 and repair['all_vias_screened']==124 and repair['remaining_via_drills_in_SMD_lands']==0
    assert repair['copper_counts']=={'PCB_TRACK':2097,'PCB_VIA':124}
    assert rejected['now_fully_connected']==8 and rejected['still_incomplete']==44
    status=json.loads(previous.read_text())
    for k in ['power_opposite_face_control_routes_this_pass','power_surface_control_branches_this_pass',
        'power_minimum_new_via_drill_to_SMD_mm','power_minimum_new_via_hole_to_hole_mm','power_minimum_new_via_to_foreign_copper_mm']:
        status.pop(k,None)
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md',detours/'README.md']},
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2554,
        power_copper_segments=2097,power_copper_vias=124,power_connections_closed_this_pass=18,
        power_local_control_routes_verified=99,power_layer_detour_control_routes_this_pass=18,
        power_previous_native_connection_groups_preserved=3308,power_via_repair_parent_groups_preserved=3290,
        power_new_route_mount_reserves_checked=15,power_all_component_poses_preserved=True,
        power_new_vias_rechecked_against_final_geometry=36,power_inherited_vias_relocated=10,
        power_all_vias_screened=124,power_remaining_via_drills_in_SMD_lands=0,
        power_minimum_all_via_drill_to_SMD_mm=repair['minimum_drill_to_SMD_mm'],
        power_minimum_all_via_hole_to_hole_mm=repair['minimum_hole_to_hole_mm'],
        power_minimum_all_via_to_foreign_polygon_mm=repair['minimum_via_to_foreign_polygon_mm'],
        power_originally_rejected_source_nets=52,power_formerly_rejected_source_nets_now_connected=8,
        power_rejected_source_nets_requiring_route_repair=44,power_remaining_opens_on_originally_rejected_source_nets=82,
        power_copper_all_layers_visually_reviewed=True,power_planes_restored=False,
        fabrication_released=False,goal_complete=False)
    out=STAGING/'two-board-fabrication-status-10';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(verified_bindings=bindings,power_opens=2554,signal_opens=251,via_in_SMD_count=0,fabrication_released=False)))


if __name__=='__main__':run()
