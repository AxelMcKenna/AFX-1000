"""Bounded native-shape routing, .20 tracks/.22 guard, no In1 signal cuts."""

import heapq
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pcbnew

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/stitch-pass5"
OUT = ROOT / "routing/grid-pass6"
STEP = 0.1
NX = 661
NY = 381
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]


def mm(v):
    return pcbnew.FromMM(float(v))


def xy(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def pt(p):
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def index(p):
    return round(p[0] / STEP), round(p[1] / STEP)


def maskshape(mask, shape, clear):
    bb = shape.BBox()
    bb.Inflate(mm(clear))
    x0 = max(0, math.floor(pcbnew.ToMM(bb.GetLeft()) / STEP))
    x1 = min(NX - 1, math.ceil(pcbnew.ToMM(bb.GetRight()) / STEP))
    y0 = max(0, math.floor(pcbnew.ToMM(bb.GetTop()) / STEP))
    y1 = min(NY - 1, math.ceil(pcbnew.ToMM(bb.GetBottom()) / STEP))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if pcbnew.SHAPE.Collide(shape, xy(x * STEP, y * STEP), mm(clear)):
                mask[x, y] = True


def masks(board, net):
    blocked = np.zeros((3, NX, NY), dtype=bool)
    via = np.zeros((NX, NY), dtype=bool)
    blocked[:, :8, :] = True
    blocked[:, -8:, :] = True
    blocked[:, :, :8] = True
    blocked[:, :, -8:] = True
    via[:10, :] = True
    via[-10:, :] = True
    via[:, :10] = True
    via[:, -10:] = True
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != net:
                for layer in [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]:
                    if p.IsOnLayer(layer):
                        shape = p.GetEffectiveShape(layer)
                        maskshape(via, shape, 0.545)
                        if layer in LAYERS:
                            maskshape(blocked[LAYERS.index(layer)], shape, 0.32)
            if p.GetDrillSize().x:
                pos = p.GetPosition()
                r = pcbnew.ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2
                circ = pcbnew.SHAPE_CIRCLE(pos, mm(r))
                maskshape(via, circ, 0.40)
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            maskshape(via, pcbnew.SHAPE_CIRCLE(t.GetPosition(), int(t.GetDrill() / 2)), 0.40)
            if t.GetNetname() != net:
                s = t.GetEffectiveShape(pcbnew.F_Cu)
                maskshape(via, s, 0.545)
                for m in blocked:
                    maskshape(m, s, 0.32)
        elif t.GetNetname() != net:
            s = t.GetEffectiveShape()
            maskshape(via, s, 0.545)
            if t.GetLayer() in LAYERS:
                maskshape(blocked[LAYERS.index(t.GetLayer())], s, 0.32)
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        if z.GetDoNotAllowVias():
            maskshape(via, z.Outline(), 0.325)
        if z.GetDoNotAllowTracks() and z.GetLayer() in LAYERS:
            maskshape(blocked[LAYERS.index(z.GetLayer())], z.Outline(), 0.1)
    return blocked, via


def route(board, net, start, end=None):
    blocked, vm = masks(board, net)
    sp, sl = start
    sx, sy = index(sp)
    if end:
        ep, el = end
        ex, ey = index(ep)
    starts = [(l, sx, sy) for l in sl]
    endstates = {(l, ex, ey) for l in el} if end else None
    for l, x, y in starts:
        blocked[l, x, y] = False
    if end:
        for l, x, y in endstates:
            blocked[l, x, y] = False
    iz = next(z for z in board.Zones() if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.In1_Cu)
    heap = []
    dist = {s: 0 for s in starts}
    came = {}
    serial = 0

    def h(s):
        return math.hypot(s[1] - ex, s[2] - ey) * 10 if end else 0

    for s in starts:
        heapq.heappush(heap, (h(s), 0, serial, s))
        serial += 1
    goal = None
    expanded = 0
    while heap and expanded < 220000:
        _, cost, _, s = heapq.heappop(heap)
        if dist.get(s) != cost:
            continue
        expanded += 1
        l, x, y = s
        if end and s in endstates:
            goal = s
            break
        if not end and not vm[x, y] and iz.HitTestFilledArea(pcbnew.In1_Cu, xy(x * STEP, y * STEP)):
            goal = s
            break
        nxt = []
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            xx, yy = x + dx, y + dy
            if not (0 <= xx < NX and 0 <= yy < NY) or blocked[l, xx, yy]:
                continue
            if dx and dy and (blocked[l, x + dx, y] or blocked[l, x, y + dy]):
                continue
            nxt.append(((l, xx, yy), 14 if dx and dy else 10))
        if not vm[x, y]:
            nxt += [((ll, x, y), 120) for ll in range(3) if ll != l and not blocked[ll, x, y]]
        for n, w in nxt:
            nc = cost + w
            if nc < dist.get(n, float("inf")):
                dist[n] = nc
                came[n] = s
                heapq.heappush(heap, (nc + h(n), nc, serial, n))
                serial += 1
    if goal is None:
        return dict(net=net, connected=False, expanded=expanded)
    path = [goal]
    while path[-1] in came:
        path.append(came[path[-1]])
    path.reverse()
    used = []

    def track(layer, a, b):
        if math.dist(a, b) < 1e-8:
            return
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(xy(*a))
        t.SetEnd(xy(*b))
        t.SetWidth(mm(0.2))
        t.SetLayer(LAYERS[layer])
        t.SetNet(board.FindNet(net))
        board.Add(t)
        used.append(t.m_Uuid.AsString())

    def barrel(x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(xy(x * STEP, y * STEP))
        v.SetWidth(mm(0.65))
        v.SetDrill(mm(0.3))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(board.FindNet(net))
        board.Add(v)
        used.append(v.m_Uuid.AsString())

    track(path[0][0], sp, (path[0][1] * STEP, path[0][2] * STEP))
    prevdir = None
    run = path[0]
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            track(a[0], (run[1] * STEP, run[2] * STEP), (a[1] * STEP, a[2] * STEP))
            barrel(a[1], a[2])
            run = b
            prevdir = None
        else:
            direction = (b[1] - a[1], b[2] - a[2])
            if prevdir is not None and direction != prevdir:
                track(a[0], (run[1] * STEP, run[2] * STEP), (a[1] * STEP, a[2] * STEP))
                run = a
            prevdir = direction
    last = path[-1]
    track(last[0], (run[1] * STEP, run[2] * STEP), (last[1] * STEP, last[2] * STEP))
    if end:
        track(last[0], (last[1] * STEP, last[2] * STEP), ep)
    else:
        barrel(last[1], last[2])
    return dict(net=net, connected=True, expanded=expanded, path=path, uuids=used)


def main():
    OUT.mkdir(exist_ok=True)
    assert not (OUT / "input.kicad_pcb").exists()
    b = pcbnew.LoadBoard(str(SRC / "input.kicad_pcb"))
    data = json.loads((SRC / "input-drc.json").read_text())
    records = []
    objects = {p.m_Uuid.AsString(): p for f in b.GetFootprints() for p in f.Pads()}
    objects.update({t.m_Uuid.AsString(): t for t in b.GetTracks()})

    def endpoint(item):
        obj = objects[item["uuid"]]
        pos = (item["pos"]["x"], item["pos"]["y"])
        if isinstance(obj, pcbnew.PAD):
            ls = [i for i, l in enumerate(LAYERS) if obj.IsOnLayer(l)]
        elif isinstance(obj, pcbnew.PCB_VIA):
            ls = [0, 1, 2]
        else:
            ls = [LAYERS.index(obj.GetLayer())]
        return pos, ls

    for row in data["unconnected_items"]:
        items = row["items"]
        if "[/GND]" in items[0]["description"]:
            continue
        first = objects[items[0]["uuid"]]
        record = route(b, first.GetNetname(), endpoint(items[0]), endpoint(items[1]))
        records.append(record)
        print(first.GetNetname(), record["connected"], record["expanded"], flush=True)
    # Small isolated local F return polygons need an actual off-pad barrel escape.
    fz = next(z for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.F_Cu)
    polys = fz.GetFilledPolysList(pcbnew.F_Cu)
    for i in range(polys.OutlineCount()):
        chain = polys.Outline(i)
        attached = any(
            isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "/GND" and chain.PointInside(t.GetPosition())
            for t in b.GetTracks()
        )
        if attached:
            continue
        pads = [
            p
            for f in b.GetFootprints()
            for p in f.Pads()
            if p.GetNetname() == "/GND" and chain.PointInside(p.GetPosition())
        ]
        if not pads:
            continue
        if any(p.GetDrillSize().x for p in pads):
            continue
        record = route(b, "/GND", (pt(pads[0].GetPosition()), [0]))
        record["island"] = i
        records.append(record)
        print("GND island", i, record["connected"], flush=True)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), b)
    for n in ["input.kicad_pro", "output.kicad_pro", "input.kicad_sch", "output.kicad_sch", "fp-lib-table"]:
        shutil.copy2(SRC / n, OUT / n)
    (OUT / "route-records.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
