"""Read-only exact-shape front-face control-cell placement preflight."""

import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard
from ..revision26.layout import POWER_NETS
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/reset-triple-remaining-batch1-work"
OUT = ROOT / "generated/analog-control-front-search2"


def main():
    t = read_sexpr((SOURCE / "rail_disconnect.kicad_pcb").read_text())
    r = Router(t)
    gs = []
    meta = []
    for g in r.geometry:
        if 0 not in g["layers"]:
            continue
        if g["kind"] == "line":
            s = LineString([g["start"], g["end"]]).buffer(g["width"] / 2, resolution=16)
        elif g["kind"] == "via":
            s = Point(g["xy"]).buffer(g["radius"], resolution=24)
        else:
            x, y = g["xy"]
            w, h = g["size"]
            s = box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        gs.append(s)
        meta.append(g)
    st = STRtree(gs)
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(t, "footprint")
    }
    othercourts = []
    for ref, f in fps.items():
        if ref in ("U30", "U31", "C75", "C76") or first(f, "layer")[1] != "F.Cu":
            continue
        try:
            b = courtyard(f, "F.CrtYd")
        except (IndexError, ValueError):
            continue
        othercourts.append(box(b[0] - 100, b[1] - 100, b[2] - 100, b[3] - 100))
    results = {}
    for ref, (xmin, xmax) in {"U30": (73, 80), "U31": (88, 93)}.items():
        f = fps[ref]
        pads = []
        for p in children(f, "pad"):
            x, y = map(float, first(p, "at")[1:3])
            w, h = map(float, first(p, "size")[1:])
            net = str(first(p, "net")[-1]).lstrip("/")
            pads.append((x, -y, w, h, net))
        rows = []
        for ix in range(round(xmin * 10), round(xmax * 10) + 1):
            for iy in range(466, 526):
                x, y = ix / 10, iy / 10
                c = box(x - 2.225, y - 1.25, x + 2.225, y + 1.25)
                if any(c.intersection(q).area > 1e-10 for q in othercourts):
                    continue
                hits = []
                for dx, dy, w, h, net in pads:
                    s = box(x + dx - w / 2, y + dy - h / 2, x + dx + w / 2, y + dy + h / 2).buffer(0.20001)
                    for i in st.query(s):
                        g = meta[int(i)]
                        if g["net"] != net and s.intersects(gs[int(i)]):
                            hits.append(
                                dict(
                                    net=g["net"],
                                    kind=g["kind"],
                                    ref=g.get("ref"),
                                    critical=g["net"] in POWER_NETS | {"AGND", "V2V5_AUX"},
                                )
                            )
                rows.append(
                    dict(
                        x=x,
                        y=y,
                        hard_object_count=len(hits),
                        critical_hits=sum(q["critical"] for q in hits),
                        hits=hits,
                    )
                )
        rows.sort(key=lambda q: (q["critical_hits"], q["hard_object_count"], abs(q["y"] - 49.5)))
        results[ref] = rows[:20]
    newcourts = [
        box(74.9 - 2.225, 46.6 - 1.25, 74.9 + 2.225, 46.6 + 1.25),
        box(89.6 - 2.225, 52.3 - 1.25, 89.6 + 2.225, 52.3 + 1.25),
    ]
    for ref, (cx, cy) in {"C75": (74.9, 46.6), "C76": (89.6, 52.3)}.items():
        pads = []
        for p in children(fps[ref], "pad"):
            dx, dy = map(float, first(p, "at")[1:3])
            w, h = map(float, first(p, "size")[1:])
            net = str(first(p, "net")[-1]).lstrip("/")
            pads.append((dx, -dy, w, h, net))
        rows = []
        for ix in range(round((cx - 4) * 10), round((cx + 4) * 10) + 1):
            for iy in range(460, 531):
                for angle in (0, 90):
                    x, y = ix / 10, iy / 10
                    rad = math.radians(angle)
                    co, si = math.cos(rad), math.sin(rad)
                    hw, hh = (1.7, 0.98) if not angle else (0.98, 1.7)
                    c = box(x - hw, y - hh, x + hw, y + hh)
                    if y + hh > 54.0 or any(c.intersection(q).area > 1e-10 for q in othercourts + newcourts):
                        continue
                    hits = []
                    for dx, dy, w, h, net in pads:
                        xx, yy = x + dx * co - dy * si, y + dx * si + dy * co
                        if angle:
                            w, h = h, w
                        sh = box(xx - w / 2, yy - h / 2, xx + w / 2, yy + h / 2).buffer(0.20001)
                        for i in st.query(sh):
                            g = meta[int(i)]
                            if g["net"] != net and sh.intersects(gs[int(i)]):
                                hits.append(
                                    dict(
                                        net=g["net"],
                                        kind=g["kind"],
                                        ref=g.get("ref"),
                                        critical=g["net"] in POWER_NETS | {"AGND", "V2V5_AUX"},
                                    )
                                )
                    rows.append(
                        dict(
                            x=x,
                            y=y,
                            angle=angle,
                            hard_object_count=len(hits),
                            critical_hits=sum(q["critical"] for q in hits),
                            distance=math.hypot(x - cx, y - cy),
                            hits=hits,
                        )
                    )
        rows.sort(key=lambda q: (q["critical_hits"], q["hard_object_count"], q["distance"]))
        results[ref] = rows[:20]
    OUT.mkdir(exist_ok=True)
    report = dict(
        source_pcb_sha256=hashlib.sha256((SOURCE / "rail_disconnect.kicad_pcb").read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        front_candidates=results,
        native_and_full_MCAD_pending=True,
        qualified=False,
    )
    (OUT / "search.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({r: v[:2] for r, v in results.items()}, indent=2))


if __name__ == "__main__":
    main()
