"""Find surface startup joins after the independently checked access repair."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
import hardware.fabrication.plan_two_board_startup_controls as planner


def run():
    base = STAGING/'two-board-power-startup-access-native-02'
    audit_path = base/'startup-access-review.json'
    audit = json.loads(audit_path.read_text())
    assert audit['all_native_groups_preserved'] and audit['all_eleven_supply_planes_unchanged']
    assert len(audit['verified_launch_corridors']) == 21
    for name, h in audit['source_sha256'].items():
        assert sha(REPO/name) == h, name
    planner.BASE = base
    planner.CAP = STAGING/'two-board-power-routing-inputs-startup-access-02/capture.json'
    planner.OUT = STAGING/'two-board-startup-control-plan-06'
    planner.run()
    path = planner.OUT/'plan.json'
    result = json.loads(path.read_text())
    for source in [Path(__file__), audit_path]:
        result['source_sha256'][str(source.relative_to(REPO))] = sha(source)
    result['joins'] = [dict(net=r['net'], source_groups=r['source_groups']) for r in result['routes']]
    result['vias'] = []
    path.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    run()
