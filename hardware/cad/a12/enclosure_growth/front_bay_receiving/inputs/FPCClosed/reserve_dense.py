"""Reserve supervisor sense and WD-enable escapes before remaining signal routes."""

import json
import shutil
from pathlib import Path

import pcbnew

from hardware.qualification.boards.fan_health.composite.finish_grid import pt, route

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/ground-first-pass7"
OUT = ROOT / "routing/dense-escape-pass8"
OUT.mkdir(exist_ok=True)
assert not (OUT / "input.kicad_pcb").exists()
b = pcbnew.LoadBoard(str(SRC / "input.kicad_pcb"))
pads = {(f.GetReference(), p.GetNumber()): p for f in b.GetFootprints() for p in f.Pads()}
records = []
for source, target in [(("U4", "3"), ("R7", "2")), (("U9", "1"), ("R11", "2"))]:
    a, c = pads[source], pads[target]
    assert a.GetNetname() == c.GetNetname()
    row = route(b, a.GetNetname(), (pt(a.GetPosition()), [0]), (pt(c.GetPosition()), [0]))
    records.append(row)
    print(a.GetNetname(), row["connected"], row["expanded"], flush=True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), b)
for n in ["input.kicad_pro", "output.kicad_pro", "input.kicad_sch", "output.kicad_sch", "fp-lib-table"]:
    shutil.copy2(SRC / n, OUT / n)
(OUT / "route-records.json").write_text(json.dumps(records, indent=2) + "\n")
