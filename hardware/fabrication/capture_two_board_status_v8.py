"""Record the checked mounting-aware local power routes and current release holds."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-routed-native-04'
    signal=STAGING/'two-board-signal-routed-native-03'
    previous=STAGING/'two-board-fabrication-status-07/status.json'
    reports=[power/n for n in ['review.json','circuit-audit.json','local-routing.json','additive-audit.json',
        'plots/native-plots.json','plots/visual-review.json']]
    reports.extend([STAGING/'two-board-power-routing-inputs-2619/capture.json',
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
    assert native['opens']==audit['new_opens']==2619
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    assert audit['verified_routes']==34 and audit['provisional_mount_reserves_checked']==15
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2619,
        power_copper_segments=1765,power_copper_vias=68,power_connections_closed_this_pass=34,
        power_local_control_routes_verified=34,power_previous_native_connection_groups_preserved=3389,
        power_new_route_mount_reserves_checked=15,power_all_component_poses_preserved=True,
        power_copper_all_layers_visually_reviewed=True,power_planes_restored=False,
        fabrication_released=False,goal_complete=False)
    out=STAGING/'two-board-fabrication-status-08';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(verified_bindings=bindings,power_opens=2619,signal_opens=251,fabrication_released=False)))


if __name__=='__main__':run()
