"""Export a compact SVG review plot in the pinned Linux KiCad runtime."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WORK=Path(__file__).resolve().parents[4]/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    assert sys.platform=="linux","Mac CAD launches remain disabled"
    parser=argparse.ArgumentParser()
    parser.add_argument("--label",default="native-closed-control-layout")
    args=parser.parse_args()
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    root=WORK/"generated"/args.label
    pcb=root/"rail_disconnect.kicad_pcb"
    project=root/"rail_disconnect.kicad_pro"
    report=json.loads((root/"review.json").read_text())
    assert report["uncapped_missing_connections"]==0
    before={str(p):sha(p) for p in (pcb,project)}
    output=root/"closed-top.svg"
    assert not output.exists()
    command=["kicad-cli","pcb","export","svg","--layers","F.Cu,F.Silkscreen,Edge.Cuts",
        "--mode-single","--page-size-mode","2","--exclude-drawing-sheet","--drill-shape-opt","2",
        "--output",str(output),str(pcb)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=45)
    (root/"svg-export.log").write_text(p.stdout+p.stderr)
    assert p.returncode==0 and output.is_file(),p.stdout+p.stderr
    assert all(sha(Path(n))==h for n,h in before.items())
    (root/"svg-review.json").write_text(json.dumps(dict(input_sha256=before,command=command,
        output_sha256=sha(output),source_unchanged=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Exported actual closed-board copper, silkscreen and outline; source unchanged")


if __name__=="__main__":
    run()
