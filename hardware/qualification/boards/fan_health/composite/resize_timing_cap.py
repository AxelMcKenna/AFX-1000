"""Actual same-value C7 0603 repair, preserving the entire rest of routed PCB."""

import json
import shutil
from pathlib import Path

import pcbnew

from hardware.qualification.boards.fan_health.composite.finish_grid import mm

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/locked-signal-pass10"
OUT = ROOT / "routing/timing-cap13"
OUT.mkdir(exist_ok=True)
assert not (OUT / "staged.kicad_pcb").exists()
b = pcbnew.LoadBoard(str(SRC / "output.kicad_pcb"))
old = next(f for f in b.GetFootprints() if f.GetReference() == "C7")
pos = old.GetPosition()
angle = old.GetOrientationDegrees()
path = old.GetPath()
uid = old.m_Uuid
nets = {p.GetNumber(): p.GetNetname() for p in old.Pads()}
old_pad = {p.GetNumber(): p.GetPosition() for p in old.Pads()}
f = pcbnew.FootprintLoad(str(ROOT / "FPC01.pretty"), "Capacitor_SMD__C_0603_1608Metric")
assert f is not None
f.SetReference("C7")
f.SetValue("2.7nF 50V C0G5% C0603C272J5GACTU")
f.SetPosition(pos)
f.SetOrientationDegrees(angle)
f.SetPath(path)
f.SetFPID(pcbnew.LIB_ID("FPC01", "Capacitor_SMD__C_0603_1608Metric"))
f.GetField(pcbnew.FIELD_T_DATASHEET).SetText("https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf")
f.GetField(pcbnew.FIELD_T_DATASHEET).SetVisible(False)
f.Reference().SetVisible(False)
f.Reference().SetLayer(pcbnew.F_Fab)
f.Value().SetVisible(False)
f.Value().SetLayer(pcbnew.F_Fab)
for p in f.Pads():
    if not p.GetNumber():
        continue
    p.SetNet(b.FindNet(nets[p.GetNumber()]))
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(old_pad[p.GetNumber()])
    t.SetEnd(p.GetPosition())
    t.SetWidth(mm(0.2))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(b.FindNet(nets[p.GetNumber()]))
    t.SetLocked(True)
    b.Add(t)
b.Remove(old)
b.Add(f)
# Native via-only keepouts must follow the changed real copper pads.
removed = []
for z in list(b.Zones()):
    if z.GetZoneName().startswith("NO_UNFILLED_VIP_C7_"):
        removed.append(z.GetZoneName())
        b.Remove(z)
assert len(removed) == 2
for p in f.Pads():
    if not p.GetNumber():
        continue
    bb = p.GetBoundingBox()
    bb.Inflate(mm(0.1))
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.F_Cu)
    z.SetIsRuleArea(True)
    z.SetZoneName("NO_UNFILLED_VIP_C7_" + p.GetNumber())
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in [
        (bb.GetLeft(), bb.GetTop()),
        (bb.GetRight(), bb.GetTop()),
        (bb.GetRight(), bb.GetBottom()),
        (bb.GetLeft(), bb.GetBottom()),
    ]:
        o.Append(x, y)
    b.Add(z)
pcbnew.SaveBoard(str(OUT / "staged.kicad_pcb"), b)
for n in ["input", "output"]:
    shutil.copy2(ROOT / "fan_power_health.kicad_pro", OUT / (n + ".kicad_pro"))
    shutil.copy2(ROOT / "fan_power_health.kicad_sch", OUT / (n + ".kicad_sch"))
(OUT / "fp-lib-table").write_text(
    (ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../")
)
(OUT / "package-change.json").write_text(
    json.dumps(
        dict(
            ref="C7",
            old_part="C1206C272J5GACTU",
            new_part="C0603C272J5GACTU",
            same_nominal_value_f=2.7e-9,
            same_C0G_50V_5pct=True,
            unchanged_pose_mm=[pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), angle],
            changed_only_part_and_own_footprint_and_two_cap_lead_extensions_and_own_via_KOs=True,
            physical_qualified=False,
        ),
        indent=2,
    )
    + "\n"
)
