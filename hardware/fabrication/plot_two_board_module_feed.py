"""Export native review views without mutating the checked CAD."""
import json
import subprocess
import sys
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform=="linux"
    folder=STAGING/"two-board-power-native-08"
    review=json.loads((folder/"review.json").read_text())
    pcb=folder/"power_protection.kicad_pcb";sch=folder/"power_protection.kicad_sch"
    assert sha(pcb)==review["artifact_sha256"][pcb.name]
    out=folder/"plots";out.mkdir(exist_ok=False)
    help_result=subprocess.run(["kicad-cli","sch","export","svg","--help"],capture_output=True,text=True,check=True)
    (out/"schematic-export-help.txt").write_text(help_result.stdout)
    assert "--pages" in help_result.stdout
    commands=[
        ["kicad-cli","sch","export","svg","--pages","8","-o",str(out/"schematic"),str(sch)],
        ["kicad-cli","pcb","export","svg","--layers","F.Cu,F.Fab,Edge.Cuts","--page-size-mode","2",
         "--mode-single","--exclude-drawing-sheet","--output",str(out/"front.svg"),str(pcb)]]
    for cmd in commands:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        assert result.returncode==0,(cmd,result.stdout,result.stderr)
    assert sha(pcb)==review["artifact_sha256"][pcb.name]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),pcb,sch,folder/"review.json"]},
        commands=commands,artifact_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob("*.svg")},
        visual_review_pending=True,fabrication_released=False)
    (out/"native-plots.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Exported module sheet and front PCB SVG")


if __name__=="__main__":run()
