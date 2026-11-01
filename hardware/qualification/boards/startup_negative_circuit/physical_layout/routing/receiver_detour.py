"""Export/check/apply a bounded B-side signal detour around repaired C5."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "receiving-seeded-six-layer-02"
WORK = ROOT / "receiving-detour"
NET = "/N19_OUTPUT_OV_GOOD"
REMOVE = {"2676fa3a-933c-44bf-9a42-9b07fa33d2b8", "46521522-ad95-4458-bdd7-d1d4523dd7ff",
          "c0cb9306-555a-4329-b3f5-ad5e16fb0701", "d4669613-bf9b-425a-94fd-d26f8bf9b169"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def export():
    import pcbnew
    WORK.mkdir(exist_ok=False)
    source = SOURCE / "output.kicad_pcb"
    before = sha(source)
    b = pcbnew.LoadBoard(str(source))
    out = dict(source_PCB_sha256=before, pads=[], tracks=[], keepouts=[],
               removed_tracks=sorted(REMOVE), net=NET,
               start_mm=[122.3096, 5.6607], end_mm=[114.4267, 11.545])
    for f in b.GetFootprints():
        for p in f.Pads():
            if not p.IsOnLayer(pcbnew.B_Cu) or p.GetNetname() == NET:
                continue
            poly = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(poly, pcbnew.B_Cu, 0, pcbnew.FromMM(.001), pcbnew.ERROR_INSIDE)
            for i in range(poly.OutlineCount()):
                c = poly.COutline(i)
                assert poly.HoleCount(i) == 0
                out["pads"].append([[c.CPoint(j).x/1e6, c.CPoint(j).y/1e6] for j in range(c.PointCount())])
    for t in b.GetTracks():
        if t.GetNetname() == NET:
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            out["tracks"].append(dict(points=[[p.x/1e6, p.y/1e6]], width_mm=t.GetWidth(pcbnew.B_Cu)/1e6))
        elif t.GetLayer() == pcbnew.B_Cu:
            a, z = t.GetStart(), t.GetEnd()
            out["tracks"].append(dict(points=[[a.x/1e6, a.y/1e6], [z.x/1e6, z.y/1e6]], width_mm=t.GetWidth()/1e6))
    for z in b.Zones():
        if z.GetIsRuleArea() and z.IsOnLayer(pcbnew.B_Cu):
            p = z.Outline()
            for i in range(p.OutlineCount()):
                c = p.COutline(i)
                out["keepouts"].append([[c.CPoint(j).x/1e6, c.CPoint(j).y/1e6] for j in range(c.PointCount())])
    (WORK / "obstacles.json").write_text(json.dumps(out, indent=2) + "\n")
    assert sha(source) == before


def plan():
    import heapq
    import math

    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union
    from shapely.prepared import prep
    d = json.loads((WORK / "obstacles.json").read_text())
    obstacles = [Polygon(p).buffer(.302) for p in d["pads"]]
    obstacles += [(Point(t["points"][0]) if len(t["points"]) == 1 else LineString(t["points"]))
                  .buffer(t["width_mm"]/2+.302) for t in d["tracks"]]
    obstacles += [Polygon(p).buffer(.102) for p in d["keepouts"]]
    obstacle = unary_union(obstacles)
    assert obstacle.is_valid
    blocked = prep(obstacle)
    a, z = tuple(d["start_mm"]), tuple(d["end_mm"])
    assert not blocked.intersects(Point(a)) and not blocked.intersects(Point(z))
    step = .05

    def point(n):
        return (round(n[0]*step, 5), round(n[1]*step, 5))

    def clear(p, q):
        return not blocked.intersects(LineString([p, q]))

    nodes = [(round(a[0]/step)+dx, round(a[1]/step)+dy) for dx in range(-2, 3) for dy in range(-2, 3)]
    queue, cost, previous = [], {}, {}
    for n in nodes:
        if clear(a, point(n)):
            cost[n] = math.dist(a, point(n))
            previous[n] = None
            heapq.heappush(queue, (cost[n]+math.dist(point(n), z), n))
    found = None
    while queue:
        _, n = heapq.heappop(queue)
        p = point(n)
        if math.dist(p, z) < .15 and clear(p, z):
            found = n
            break
        for dx, dy in [(x, y) for x in [-1, 0, 1] for y in [-1, 0, 1] if x or y]:
            m = (n[0]+dx, n[1]+dy)
            q = point(m)
            if not (112 <= q[0] <= 125 and 4 <= q[1] <= 13) or not clear(p, q):
                continue
            c = cost[n]+math.dist(p, q)
            if c < cost.get(m, math.inf):
                cost[m], previous[m] = c, n
                heapq.heappush(queue, (c+math.dist(q, z), m))
    assert found is not None, "No detour in bounded window; do not relax geometry"
    path = [z]
    while found is not None:
        path.append(point(found))
        found = previous[found]
    path.append(a)
    path.reverse()
    simplified = [path[0]]
    i = 0
    while i < len(path)-1:
        j = len(path)-1
        while not clear(path[i], path[j]):
            j -= 1
        simplified.append(path[j])
        i = j
    assert all(clear(p, q) for p, q in zip(simplified, simplified[1:]))
    result = dict(obstacle_sha256=sha(WORK / "obstacles.json"), path_mm=simplified,
                  width_mm=.2, layer="B.Cu", net=NET, clearance_mm=.2,
                  planning_allowance_mm=.002, native_DRC_required=True)
    (WORK / "plan.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Planned", len(simplified)-1, "segments", flush=True)


def apply():
    import shutil

    import pcbnew
    source = SOURCE / "output.kicad_pcb"
    d = json.loads((WORK / "obstacles.json").read_text())
    assert sha(source) == d["source_PCB_sha256"]
    plan = json.loads((WORK / "plan.json").read_text())
    b = pcbnew.LoadBoard(str(source))
    removed = []
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString() in REMOVE:
            assert t.GetNetname() == NET and not t.IsLocked() and t.GetLayer() == pcbnew.B_Cu
            removed.append(t.m_Uuid.AsString())
            b.Remove(t)
    assert set(removed) == REMOVE
    for a, z in zip(plan["path_mm"], plan["path_mm"][1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(*(round(v*1e6) for v in a)))
        t.SetEnd(pcbnew.VECTOR2I(*(round(v*1e6) for v in z)))
        t.SetWidth(pcbnew.FromMM(.2))
        t.SetLayer(pcbnew.B_Cu)
        t.SetNet(b.FindNet(NET))
        b.Add(t)
    output = WORK / "output.kicad_pcb"
    assert not output.exists()
    pcbnew.SaveBoard(str(output), b)
    for name in ["output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
        shutil.copyfile(SOURCE / name, WORK / name)
    (WORK / "construction.json").write_text(json.dumps(dict(
        source_PCB_sha256=sha(source), output_PCB_sha256=sha(output),
        driver_sha256=sha(Path(__file__)), plan_sha256=sha(WORK / "plan.json"),
        removed_new_router_track_UUIDs=sorted(removed), all_seed_copper_unchanged=True,
        all267_component_poses_unchanged=True, native_DRC_required=True,
        physical_qualified=False, fabrication_released=False), indent=2) + "\n")


if __name__ == "__main__":
    {"export": export, "plan": plan, "apply": apply}[sys.argv[1]]()
