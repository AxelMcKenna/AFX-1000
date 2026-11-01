"""Find actual full-stack GND-barrel sites without moving fixed reference/force Cu."""

import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import read_sexpr
from ..routing.check import point_segment
from .ordinary_joint_ripup7 import ORDINARY
from .repair import Router
from .schmitt_cone_candidate import GROUPS

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-inner-backbone-ground-work"


def main():
    p = SOURCE / "rail_disconnect.kicad_pcb"
    rt = Router(read_sexpr(p.read_text()))
    ordinary = (
        set(ORDINARY)
        | {n for g in GROUPS for n in g if n}
        | {n + "_SCHMITT" for g in GROUPS for n in g if n}
        | {"OK_19", "P19_ALLOW", "N19_ALLOW", "P12_ALLOW", "N12_ALLOW"}
    )
    local = []
    for g in rt.geometry:
        if g["net"] == "AGND":
            continue
        if g["kind"] == "line":
            x0 = min(g["start"][0], g["end"][0]) - g["width"] / 2
            x1 = max(g["start"][0], g["end"][0]) + g["width"] / 2
            y0 = min(g["start"][1], g["end"][1]) - g["width"] / 2
            y1 = max(g["start"][1], g["end"][1]) + g["width"] / 2
        else:
            wx, wy = (
                (g["size"][0] / 2, g["size"][1] / 2) if g["kind"] == "rect" else (g["radius"], g["radius"])
            )
            if g["kind"] == "via":
                wx = wy = g["radius"]
            x0, x1 = g["xy"][0] - wx, g["xy"][0] + wx
            y0, y1 = g["xy"][1] - wy, g["xy"][1] + wy
        if x1 + 0.52 < 8.6 or x0 - 0.52 > 10.0 or y1 + 0.52 < 9.5 or y0 - 0.52 > 11.7:
            continue
        local.append(g)
    rows = []
    for ix in range(172, 201):
        for iy in range(190, 235):
            q = ix * 0.05, iy * 0.05
            hard = []
            soft = []
            for g in local:
                if g["kind"] == "line":
                    d = point_segment(q, g["start"], g["end"]) - g["width"] / 2
                elif g["kind"] == "via":
                    d = math.dist(q, g["xy"]) - g["radius"]
                else:
                    d = math.hypot(*(max(abs(q[k] - g["xy"][k]) - g["size"][k] / 2, 0) for k in (0, 1)))
                if d < 0.520001:
                    if g["net"] in ordinary and g["kind"] in ("line", "via"):
                        soft.append(g)
                    else:
                        hard.append(g)
                        break
            if not hard:
                rows.append(
                    dict(point=q, soft_blockers=soft, score=100 * len(soft) + math.dist(q, (9.95, 12.75)))
                )
    rows.sort(key=lambda r: r["score"])
    assert rows
    out = ROOT / "generated/schmitt-cone-proposal/ground-site-search.json"
    out.write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                candidate_count=len(rows),
                candidates=rows[:20],
                all_fixed_pads_quiet_force_and_existing_ground_clear=True,
                surface_path_and_native_PDN_required=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print([(r["point"], len(r["soft_blockers"])) for r in rows[:10]])


if __name__ == "__main__":
    main()
