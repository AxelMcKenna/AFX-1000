"""Bounded last watchdog interconnect repair on native-zero-clearance draft."""

import json
import shutil
from pathlib import Path

import pcbnew

from hardware.qualification.boards.fan_health.composite.finish_grid import route

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/locked-signal-pass10"
OUT = ROOT / "routing/last-route11"
OUT.mkdir(exist_ok=True)
assert not (OUT / "input.kicad_pcb").exists()
b = pcbnew.LoadBoard(str(SRC / "output.kicad_pcb"))
record = route(b, "/WD_OK_5", ((35.0625, 25.5), [0]), ((40.9823, 26.7403), [1]))
print(record["connected"], record["expanded"], flush=True)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), b)
for n in ["input.kicad_pro", "output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
    shutil.copy2(SRC / n, OUT / n)
shutil.copy2(SRC / "output.kicad_sch", OUT / "input.kicad_sch")
(OUT / "route-record.json").write_text(json.dumps(record, indent=2) + "\n")
