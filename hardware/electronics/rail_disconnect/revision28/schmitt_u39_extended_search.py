"""Screen a receiving-adjacent U39 pose without moving fixed copper or vias."""

import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, box

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard
from .repair import Router
from .schmitt_receiver_joint_surface import geometry, key

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/v5-nearest-components-work"


def main():
    path = SOURCE / "rail_disconnect.kicad_pcb"
    t = read_sexpr(path.read_text())
    rt = Router(t)
    ordinary = {
        "E28_SOURCE_READY",
        "E28_RUN_AND_SOURCE",
        "E28_SAFE_REQUEST",
        "E28_NORMAL_PRE",
        "E28_OUT_READY",
        "E28_USER_AUX",
        "E28_RUN_LOGIC",
        "E28_SOURCE_READY_LOGIC",
        "E28_SAFE_STAGE",
    }
    obs = []
    courts = []
    for g in rt.geometry:
        if 0 not in g["layers"] or g.get("ref") in ("U39", "C82"):
            continue
        if g["kind"] == "line":
            q = LineString([g["start"], g["end"]]).buffer(g["width"] / 2)
        elif g["kind"] == "via":
            q = Point(*g["xy"]).buffer(g["radius"])
        else:
            q = box(
                g["xy"][0] - g["size"][0] / 2,
                g["xy"][1] - g["size"][1] / 2,
                g["xy"][0] + g["size"][0] / 2,
                g["xy"][1] + g["size"][1] / 2,
            )
        if q.intersects(box(44, 39, 82, 54)):
            obs.append((g, q, g["kind"] == "line" and g["net"] in ordinary))
    for f in children(t, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if ref in ("U39", "C82") or first(f, "layer")[1] != "F.Cu":
            continue
        try:
            courts.append(box(*courtyard(f, "F.CrtYd")))
        except (IndexError, ValueError):
            pass

    def blockers(ref, xy, oldxy):
        soft = {}
        for p in rt.by_ref[ref]:
            xx, yy = [p["xy"][k] + xy[k] - oldxy[k] for k in (0, 1)]
            w, h = p["size"]
            pad = box(xx - w / 2, yy - h / 2, xx + w / 2, yy + h / 2)
            for g, z, allowed in obs:
                if g["net"] == p["net"] or pad.distance(z) >= 0.205:
                    continue
                if not allowed:
                    return None
                soft[key(g)] = g
        return soft

    rows = []
    for yi in range(175, 201):
        for xi in range(192, 305):
            x, y = xi * 0.25, yi * 0.25
            u = box(x - 2.225, y - 1.45, x + 2.225, y + 1.45)
            if any(u.intersects(c) for c in courts):
                continue
            soft = blockers("U39", (x, y), (111.25, 52.25))
            if soft is None:
                continue
            for cx, cy in [(x + 4.8, y), (x - 4.8, y), (x - 0.7, y - 3.2)]:
                c = box(cx - 1.55, cy - 0.75, cx + 1.55, cy + 0.75)
                if c.intersects(u) or any(c.intersects(z) for z in courts):
                    continue
                cs = blockers("C82", (cx, cy), (115.05, 52.25))
                if cs is not None:
                    union = {**soft, **cs}
                    rows.append(
                        dict(
                            U39=[x, y],
                            C82=[cx, cy],
                            ordinary_track_blockers=list(union.values()),
                            score=math.dist((x, y), (55.5, 48)) + 0.03 * len(union),
                        )
                    )
    from .band_router import BandRouter

    filled = SOURCE / "generated/filled-v5-nearest-components.kicad_pcb"
    pads = json.loads((SOURCE / "generated/native-pads.json").read_text())
    br = BandRouter(t, read_sexpr(filled.read_text()), pads, step=0.1)
    br.geometry = [
        g
        for g in br.geometry
        if g.get("ref") not in ("U39", "C82") and not (g["kind"] == "line" and g["net"] in ordinary)
    ]
    import numpy as np

    _, via = br.physical_masks("U39_SEARCH_FOREIGN", 0.2)
    xx, yy = np.nonzero(~via)
    free = np.column_stack([xx * 0.1, yy * 0.1])
    free = free[(free[:, 0] >= 44) & (free[:, 0] <= 82) & (free[:, 1] >= 39) & (free[:, 1] <= 54)]
    for row in rows:
        x, y = row["U39"]
        counts = []
        for dx in (-1.55, 1.55):
            for dy in (-0.75, -0.25, 0.25, 0.75):
                ds = ((free - np.array([x + dx, y + dy])) ** 2).sum(axis=1)
                counts.append(int(((ds <= 9) & (ds >= 0.2**2)).sum()))
        row["per_pin_nearby_clear_barrel_grid_count"] = counts
        row["score"] += 5 / (1 + min(counts))
    rows.sort(key=lambda r: (min(r["per_pin_nearby_clear_barrel_grid_count"]) == 0, r["score"]))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    by = {key(geometry(n, names)): n for n in children(t, "segment")}
    for row in rows[:30]:
        row["ordinary_track_objects"] = [
            dict(
                uuid=str(first(by[key(g)], "uuid")[1]),
                literal=__import__("hardware.electronics.common.sexpr", fromlist=["sexpr"]).sexpr(by[key(g)]),
            )
            for g in row["ordinary_track_blockers"]
        ]
    out = ROOT / "generated/schmitt-cone-proposal/u39-extended-placement-screen.json"
    out.write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                rows=rows[:30],
                candidate_count=len(rows),
                every_actual_via_pad_force_quiet_and_ground_primitive_hard=True,
                only_explicit_ordinary_tracks_allowed_for_declared_reroute=True,
                new_native_clearance_MCAD_and_PDN_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Receiving-adjacent candidates",
        len(rows),
        [(r["U39"], r["C82"], len(r["ordinary_track_blockers"])) for r in rows[:6]],
        flush=True,
    )


if __name__ == "__main__":
    main()
