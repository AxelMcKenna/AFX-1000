"""Add only native-geometry-screened GND barrels to actual isolated F fills."""

import hashlib
import json
import math
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/return-pass4"
OUT = ROOT / "routing/stitch-pass5"


def mm(x):
    return pcbnew.FromMM(float(x))


def xy(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


OUT.mkdir(exist_ok=True)
assert not (OUT / "input.kicad_pcb").exists()
b = pcbnew.LoadBoard(str(SRC / "output.kicad_pcb"))
layers = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
net = b.FindNet("/GND")
gnd = net.GetNetCode()
shapes = []
holes = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetDrillSize().x:
            holes.append((p.GetPosition(), max(p.GetDrillSize().x, p.GetDrillSize().y) / 2))
        if p.GetNetCode() != gnd:
            for layer in layers:
                if p.IsOnLayer(layer):
                    shapes.append(p.GetEffectiveShape(layer))
for t in b.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        holes.append((t.GetPosition(), t.GetDrill() / 2))
        if t.GetNetCode() != gnd:
            shapes.append(t.GetEffectiveShape(pcbnew.F_Cu))
    elif t.GetNetCode() != gnd:
        shapes.append(t.GetEffectiveShape())
koz = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
fz = next(z for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.F_Cu)
iz = next(z for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.In1_Cu)
polys = fz.GetFilledPolysList(pcbnew.F_Cu)
records = []
for i in range(polys.OutlineCount()):
    chain = polys.Outline(i)
    if any(
        isinstance(t, pcbnew.PCB_VIA) and t.GetNetCode() == gnd and chain.PointInside(t.GetPosition())
        for t in b.GetTracks()
    ):
        records.append(dict(island=i, existing_barrel=True))
        continue
    bb = chain.BBox()
    x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    x1, y1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    points = [
        (x0 + j * 0.2, y0 + k * 0.2)
        for j in range(1, int((x1 - x0) / 0.2))
        for k in range(1, int((y1 - y0) / 0.2))
    ]
    points.sort(key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    selected = None
    for x, y in points:
        pt = xy(x, y)
        if not chain.PointInside(pt):
            continue
        if not all(
            fz.HitTestFilledArea(
                pcbnew.F_Cu, xy(x + 0.34 * math.cos(a * math.pi / 8), y + 0.34 * math.sin(a * math.pi / 8))
            )
            and iz.HitTestFilledArea(
                pcbnew.In1_Cu, xy(x + 0.34 * math.cos(a * math.pi / 8), y + 0.34 * math.sin(a * math.pi / 8))
            )
            for a in range(16)
        ):
            continue
        if any(z.Outline().Collide(pt, mm(0.325)) for z in koz):
            continue
        if any(s.Collide(pt, mm(0.525)) for s in shapes):
            continue
        if any(math.hypot(pt.x - p.x, pt.y - p.y) < r + mm(0.4) for p, r in holes):
            continue
        selected = (x, y)
        break
    if selected:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(xy(*selected))
        v.SetWidth(mm(0.65))
        v.SetDrill(mm(0.3))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(net)
        v.SetLocked(True)
        b.Add(v)
        holes.append((v.GetPosition(), mm(0.15)))
    records.append(dict(island=i, added_barrel_mm=selected, uuid=v.m_Uuid.AsString() if selected else None))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), b)
for n in ["input.kicad_pro", "output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
    shutil.copy2(SRC / n, OUT / n)
shutil.copy2(SRC / "output.kicad_sch", OUT / "input.kicad_sch")
(OUT / "stitch-proposal.json").write_text(
    json.dumps(
        dict(
            source_sha256=sha(SRC / "output.kicad_pcb"),
            result_sha256=sha(OUT / "input.kicad_pcb"),
            islands=records,
            geometry_screen_is_not_native_DRC=True,
            physical_qualified=False,
        ),
        indent=2,
    )
    + "\n"
)
print(records)
