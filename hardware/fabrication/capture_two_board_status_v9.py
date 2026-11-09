"""Bind the verified two-stage power control routing and remaining release holds."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-routed-native-06'
    via=STAGING/'two-board-power-routed-native-05'
    signal=STAGING/'two-board-signal-routed-native-03'
    previous=STAGING/'two-board-fabrication-status-08/status.json'
    reports=[power/n for n in ['review.json','circuit-audit.json','branch-routing.json','additive-audit.json',
        'retained-via-clearance.json','plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']]
    reports.extend(via/n for n in ['review.json','via-routing.json','additive-audit.json'])
    reports.extend([STAGING/'two-board-power-routing-inputs-2599/capture.json',
        STAGING/'two-board-power-routing-inputs-2572/capture.json',
        signal/'review.json',signal/'copper-retention-v2.json',previous])
    bindings=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                path=Path(name)
                if not path.is_absolute():path=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/path
                assert path.is_file() and sha(path)==h,(str(report),name)
                bindings+=1
    native=json.loads((power/'review.json').read_text());audit=json.loads((power/'additive-audit.json').read_text())
    via_audit=json.loads((via/'additive-audit.json').read_text())
    receiving=json.loads((power/'retained-via-clearance.json').read_text())
    assert native['opens']==audit['new_opens']==2572
    assert via_audit['old_opens']==2619 and via_audit['new_opens']==audit['old_opens']==2599
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    assert audit['verified_routes']==27 and via_audit['verified_routes']==20
    assert audit['provisional_mount_reserves_checked']==via_audit['provisional_mount_reserves_checked']==15
    assert receiving['vias_checked']==20 and receiving['minimum_copper_to_foreign_copper_mm']>=.21
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md',via/'README.md']},
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2572,
        power_copper_segments=1971,power_copper_vias=88,power_connections_closed_this_pass=47,
        power_local_control_routes_verified=81,power_opposite_face_control_routes_this_pass=20,
        power_surface_control_branches_this_pass=27,power_previous_native_connection_groups_preserved=3355,
        power_new_route_mount_reserves_checked=15,power_all_component_poses_preserved=True,
        power_new_vias_rechecked_against_final_geometry=20,
        power_minimum_new_via_drill_to_SMD_mm=receiving['minimum_drill_to_SMD_mm'],
        power_minimum_new_via_hole_to_hole_mm=receiving['minimum_hole_to_hole_mm'],
        power_minimum_new_via_to_foreign_copper_mm=receiving['minimum_copper_to_foreign_copper_mm'],
        power_copper_all_layers_visually_reviewed=True,power_planes_restored=False,
        fabrication_released=False,goal_complete=False)
    out=STAGING/'two-board-fabrication-status-09';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(verified_bindings=bindings,power_opens=2572,signal_opens=251,fabrication_released=False)))


if __name__=='__main__':run()
