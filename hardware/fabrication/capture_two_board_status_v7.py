"""Record the first clean power-copper checkpoint and remaining release work."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-routed-native-02'
    signal=STAGING/'two-board-signal-routed-native-03'
    previous=STAGING/'two-board-fabrication-status-06/status.json'
    reports=[power/'review.json',power/'circuit-audit.json',power/'copper-restoration.json',
        power/'copper-audit.json',power/'plots/native-plots.json',power/'plots/visual-review.json',
        STAGING/'two-board-module-protection-followup-01/review.json',
        signal/'review.json',signal/'copper-retention-v2.json',previous]
    bindings=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                path=Path(name)
                if not path.is_absolute():path=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/path
                assert path.is_file() and sha(path)==h,(str(report),name)
                bindings+=1
    native=json.loads((power/'review.json').read_text());audit=json.loads((power/'copper-audit.json').read_text())
    assert native['opens']==audit['new_opens']==2653
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    assert audit['fully_connected_restored_terminal_sets']==audit['restored_source_nets']==50
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2653,
        power_copper_segments=1689,power_copper_vias=68,power_restored_source_connection_groups=50,
        power_connections_closed_this_pass=56,power_all_component_poses_preserved=True,
        power_copper_all_layers_visually_reviewed=True,power_planes_restored=False,
        power_rejected_source_nets_requiring_route_repair=52,fabrication_released=False,goal_complete=False)
    status['next_required_design_work'].append('Repair rejected source routes to current track/drill/clearance rules; route remaining power and signal nets with verified returns')
    out=STAGING/'two-board-fabrication-status-07';assert not out.exists();out.mkdir()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(verified_bindings=bindings,power_opens=2653,signal_opens=251,fabrication_released=False)))


if __name__=='__main__':run()
