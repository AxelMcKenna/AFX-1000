"""Native SVG inspection views of the integrated, partly routed signal board."""
import json
import subprocess
import sys
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform == "linux"
    folder = STAGING / "two-board-signal-routed-native-03"
    pcb = folder / "signal_main.kicad_pcb"
    report = json.loads((folder / "review.json").read_text())
    assert sha(pcb) == report["checked_PCB_sha256"]
    assert report["status"]["counts"] == dict(violations=0, unconnected_items=251, schematic_parity=1, erc=0)
    output = folder / "plots"
    output.mkdir(exist_ok=False)
    commands, artifacts = [], []
    for name, layers in [("front","F.Cu,F.Fab,Edge.Cuts"),("back","B.Cu,B.Fab,Edge.Cuts"),
                         *[("inner"+str(i),"In"+str(i)+".Cu,Edge.Cuts") for i in range(1,7)]]:
        target = output / (name + ".svg")
        cmd = ["kicad-cli","pcb","export","svg","--layers",layers,"--page-size-mode","2",
               "--mode-single","--exclude-drawing-sheet","--output",str(target),str(pcb)]
        p = subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        assert p.returncode == 0,(cmd,p.stdout,p.stderr)
        commands.append(cmd)
        artifacts.append(target)
    assert sha(pcb) == report["checked_PCB_sha256"]
    record = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),pcb,folder/"review.json"]},
                  native_plot_sha256={p.name:sha(p) for p in artifacts},commands=commands,
                  visual_inspection_pending=True,fabrication_released=False)
    (output / "native-plots.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Eight actual native copper SVG views exported")


if __name__ == "__main__":
    run()
