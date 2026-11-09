"""Author the startup access repair without the obsolete rail-allow via."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
import hardware.fabrication.route_two_board_startup_access as build


def run():
    build.PLAN=STAGING/'two-board-startup-access-plan-03/plan.json'
    build.OUT=STAGING/'two-board-power-startup-access-02'
    build.run()
    path=build.OUT/'startup-access-routing.json'
    r=json.loads(path.read_text())
    r['source_sha256'][str(Path(__file__).relative_to(REPO))]=sha(Path(__file__))
    path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':
    run()
