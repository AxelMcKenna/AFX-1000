"""Reserve actual SMT return escapes before signal autorouting can cage them."""

import json
import shutil
from pathlib import Path

import pcbnew

from hardware.qualification.boards.fan_health.composite.finish_grid import pt, route

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "routing/ground-first-pass7"
OUT.mkdir(exist_ok=True)
assert not (OUT / "input.kicad_pcb").exists()
b = pcbnew.LoadBoard(str(ROOT / "fan_power_health.kicad_pcb"))
b.BuildConnectivity()
records = []
pads = [
    (f.GetReference(), p)
    for f in b.GetFootprints()
    for p in f.Pads()
    if p.GetNetname() == "/GND" and p.IsOnLayer(pcbnew.F_Cu)
]
for ref, p in pads:
    connected = b.GetConnectivity().GetConnectedItems(p)
    if any(
        isinstance(t, pcbnew.ZONE) and not t.GetIsRuleArea() and t.GetLayer() == pcbnew.In1_Cu
        for t in connected
    ):
        continue
    record = route(b, "/GND", (pt(p.GetPosition()), [0]))
    record["ref"] = ref
    record["pin"] = p.GetNumber()
    records.append(record)
    print(ref, p.GetNumber(), record["connected"], record["expanded"], flush=True)
    if record["connected"]:
        b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), b)
for n in ["input", "output"]:
    shutil.copy2(ROOT / "fan_power_health.kicad_pro", OUT / (n + ".kicad_pro"))
    shutil.copy2(ROOT / "fan_power_health.kicad_sch", OUT / (n + ".kicad_sch"))
(OUT / "fp-lib-table").write_text(
    (ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../")
)
(OUT / "ground-escapes.json").write_text(json.dumps(records, indent=2) + "\n")
