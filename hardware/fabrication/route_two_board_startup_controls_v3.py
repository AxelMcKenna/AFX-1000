"""Author startup controls while preserving the input supply planes."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
import hardware.fabrication.route_two_board_startup_controls as build


def run():
    build.PLAN=STAGING/'two-board-startup-control-plan-05/plan.json'
    build.OUT=STAGING/'two-board-power-startup-controls-03'
    build.run()
    path=build.OUT/'startup-control-routing.json';r=json.loads(path.read_text())
    r['source_sha256'][str(Path(__file__).relative_to(REPO))]=sha(Path(__file__))
    path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':run()
