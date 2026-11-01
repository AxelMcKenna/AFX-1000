"""Export the actual checked P03 layout without modifying CAD sources."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter"


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    review = json.loads((ROOT/"review.json").read_text())
    assert review["status"]["native_closed"] and review["uncapped_missing_connections"] == 0
    pcb = ROOT/"power_p03.kicad_pcb"
    before = hashlib.sha256(pcb.read_bytes()).hexdigest()
    svg = ROOT/"closed-top.svg"
    assert not svg.exists()
    command = ["kicad-cli", "pcb", "export", "svg", "--layers", "F.Cu,F.Fab,F.Silkscreen,Edge.Cuts",
               "--mode-single", "--page-size-mode", "2", "--exclude-drawing-sheet", "--drill-shape-opt", "2",
               "--output", str(svg), str(pcb)]
    p = subprocess.run(command, capture_output=True, text=True, timeout=45)
    (ROOT/"svg.log").write_text(p.stdout+p.stderr)
    assert p.returncode == 0 and svg.is_file()
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == before
    (ROOT/"svg-review.json").write_text(json.dumps(dict(command=command, source_PCB_sha256=before,
        SVG_sha256=hashlib.sha256(svg.read_bytes()).hexdigest(), source_unchanged=True,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Exported actual checked P03 top copper, component bodies and outline")


if __name__ == "__main__":
    run()
