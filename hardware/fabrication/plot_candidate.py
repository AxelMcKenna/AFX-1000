"""Native review plots of a strict checked development PCB, using Linux only."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent


def run():
    assert sys.platform == "linux"
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    parser.add_argument("--board-name",required=True)
    parser.add_argument("--help-only",action="store_true")
    parser.add_argument("--inspection-pdf",action="store_true")
    parser.add_argument("--bottom",action="store_true")
    args = parser.parse_args()
    if args.help_only:
        p = subprocess.run(["kicad-cli","pcb","export","svg","--help"],capture_output=True,text=True,timeout=15)
        print(p.stdout+p.stderr)
        return
    for label in (args.source,args.board_name):
        assert label and all(c.isalnum() or c in "-_" for c in label)
    source = ROOT/"staging"/args.source
    pcb = source/(args.board_name+".kicad_pcb")
    report = json.loads((source/"review.json").read_text())
    assert report["status"]["all_native_rule_checks_enabled"]
    assert report["status"]["counts"]["violations"] == report["status"]["counts"]["schematic_parity"] == 0
    assert sha(pcb) == report["checked_PCB_sha256"]
    if args.inspection_pdf:
        # A temporary read-only rendering of existing CAD for inspection,
        # not an authored document or fabrication drawing release.
        target = source/"plots"/("inspection-bottom.pdf" if args.bottom else "inspection.pdf")
        assert not target.exists()
        layers = "B.Cu,F.Fab,Edge.Cuts" if args.bottom else "F.Cu,F.Silkscreen,F.Fab,Edge.Cuts"
        command = ["kicad-cli","pcb","export","pdf","--layers",layers,
                   "--mode-single","--output",str(target),str(pcb)]
        p = subprocess.run(command,capture_output=True,text=True,timeout=30)
        assert p.returncode == 0,(p.stdout,p.stderr)
        assert sha(pcb) == report["checked_PCB_sha256"]
        print("Created temporary CAD inspection rendering",target)
        return
    output = source/"plots"
    output.mkdir(exist_ok=False)
    commands = []
    for name,layers in (("top","F.Cu,F.Silkscreen,F.Fab,Edge.Cuts"),("bottom","B.Cu,B.Silkscreen,B.Fab,Edge.Cuts")):
        folder = output/name
        folder.mkdir()
        command = ["kicad-cli","pcb","export","svg","--layers",layers,"--page-size-mode","2",
                   "--mode-single","--exclude-drawing-sheet","--output",str(folder/(name+".svg")),str(pcb)]
        p = subprocess.run(command,capture_output=True,text=True,timeout=30)
        (output/(name+".log")).write_text(p.stdout+p.stderr)
        assert p.returncode == 0,(command,p.stdout,p.stderr)
        commands.append(command)
    plots = list(output.rglob("*.svg"))
    assert plots and sha(pcb) == report["checked_PCB_sha256"]
    (output/"review.json").write_text(json.dumps(dict(source_PCB_sha256=sha(pcb),commands=commands,
        native_plot_sha256={str(p.relative_to(source)):sha(p) for p in plots},
        actual_board_copper_and_footprints=True,visual_review_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Generated",len(plots),"native SVG review plots")


if __name__ == "__main__":
    run()
