"""Repair actual U7 VCC dogleg caging the final input; no placement/rule change."""

import json
import shutil
from pathlib import Path

import pcbnew

from hardware.qualification.boards.fan_health.composite.finish_grid import mm, route, xy

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/locked-signal-pass10"
OUT = ROOT / "routing/cage-repair12"
OUT.mkdir(exist_ok=True)
assert not (OUT / "input.kicad_pcb").exists()
b = pcbnew.LoadBoard(str(SRC / "output.kicad_pcb"))
removed = []
ids = {"54050cef-fd21-4b44-9094-9481fc5a9db4", "dfcf6a65-4321-4411-bfc8-1b764a2df465"}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in ids:
        assert t.GetNetname() == "/FAN5V_IN" and not t.IsLocked()
        removed.append(
            dict(
                uuid=t.m_Uuid.AsString(),
                start=[t.GetStart().x, t.GetStart().y],
                end=[t.GetEnd().x, t.GetEnd().y],
                width_nm=t.GetWidth(),
            )
        )
        b.Remove(t)
assert len(removed) == 2
net = b.FindNet("/FAN5V_IN")
for a, c in zip([(36.7375, 24.85), (36.7375, 24.0), (37.35, 23.8)], [(36.7375, 24.0), (37.35, 23.8)]):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(xy(*a))
    t.SetEnd(xy(*c))
    t.SetWidth(mm(0.2))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    t.SetLocked(True)
    b.Add(t)
v = pcbnew.PCB_VIA(b)
v.SetPosition(xy(37.35, 23.8))
v.SetWidth(mm(0.65))
v.SetDrill(mm(0.3))
v.SetViaType(pcbnew.VIATYPE_THROUGH)
v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
v.SetNet(net)
v.SetLocked(True)
b.Add(v)
pcbnew.SaveBoard(str(OUT / "staged.kicad_pcb"), b)
b = pcbnew.LoadBoard(str(OUT / "staged.kicad_pcb"))
records = []
for n, s, e in [
    ("/WD_OK_5", ((35.0625, 25.5), [0]), ((40.9823, 26.7403), [1])),
    ("/FAN5V_IN", ((37.35, 23.8), [0, 1, 2]), ((35.8784, 26.6034), [0])),
]:
    row = route(b, n, s, e)
    print(n, row["connected"], row["expanded"], flush=True)
    records.append(row)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), b)
for n in ["input.kicad_pro", "output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
    shutil.copy2(SRC / n, OUT / n)
shutil.copy2(SRC / "output.kicad_sch", OUT / "input.kicad_sch")
(OUT / "route-records.json").write_text(
    json.dumps(dict(removed_exact_objects=removed, routes=records), indent=2) + "\n"
)
