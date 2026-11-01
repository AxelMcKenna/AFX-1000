"""Move seven trapped resistors to legal bodies with two real via escapes."""

import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ..revision26 import router as aid
from .focused import legal_line
from .repair import ROOT, Router
from .terminals import PORTS

REFS = ("R63", "R64", "R68", "R59", "R60", "R36", "R38")


def main():
    aid.STEP = 0.125
    aid.CLEARANCE = 0.18  # Router adds .02, giving actual .20 native clearance.
    path = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(path.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    r = Router(tree)
    r.inner_escape = True
    r.allow_pour_clearance = False
    receipts = []
    for ref in REFS:
        pads = r.by_ref[ref]
        old = [tuple(p["xy"]) for p in pads]
        original = tuple(float(v) - 100 for v in first(fps[ref], "at")[1:3])
        geometry = [g for g in r.geometry if g.get("ref") != ref]
        r.geometry = geometry
        bodies = []
        for other, fp in fps.items():
            if other == ref or first(fp, "layer")[1] != "B.Cu":
                continue
            box = courtyard(fp, "B.CrtYd")
            bodies.append(tuple(v - 100 for v in box))
        for x, y, _ in PORTS.values():
            bodies.append((x - 5, y - 5, x + 5, y + 5))
        masks = {}
        for pad in pads:
            r.cached = {}
            blocked, _ = r.masks(pad["net"], 1.50)
            r.cached = {}
            _, via = r.masks(pad["net"], 0.25)
            masks[pad["pin"]] = (blocked[5].copy(), via.copy())
        candidates = sorted(
            (
                (math.dist((x, y), original), x, y)
                for x in range(7, 151)
                for y in [i * 0.5 for i in range(5, 88)]
            )
        )
        good = False
        for _, x, y in candidates:
            box = (x - 1.68, y - 0.95, x + 1.68, y + 0.95)
            if any(
                min(box[2], b[2]) - max(box[0], b[0]) > -0.1 and min(box[3], b[3]) - max(box[1], b[1]) > -0.1
                for b in bodies
            ):
                continue
            if any(
                math.hypot(max(box[0] - mx, 0, mx - box[2]), max(box[1] - my, 0, my - box[3])) < 3.7
                for mx, my in ((4, 20), (152, 3.8), (10, 36), (100, 36))
            ):
                continue
            proposed = []
            for pad in pads:
                sign = -1 if pad["pin"] == "1" else 1
                pxy = (x + sign * 0.9125, y)
                via = (x + sign * 3, y)
                blocked, via_mask = masks[pad["pin"]]
                pix, piy = (round(v / aid.STEP) for v in pxy)
                vix, viy = (round(v / aid.STEP) for v in via)
                if blocked[pix, piy] or via_mask[vix, viy] or not legal_line(r, pad["net"], 5, pxy, via):
                    break
                proposed.append((pad, pxy, via))
            if len(proposed) != 2:
                continue
            for pad, pxy, via in proposed:
                pad["xy"] = pxy
                r.geometry.append(pad)
                r.path(pad["net"], 5, [pxy, via], 0.25)
                r.via(pad["net"], via)
            first(fps[ref], "at")[1:3] = [x + 100, y + 100]
            receipts.append(
                dict(
                    ref=ref,
                    old_pose_mm=original,
                    new_pose_mm=[x, y],
                    escapes=[dict(pin=p["pin"], net=p["net"], pin_mm=xy, via_mm=v) for p, xy, v in proposed],
                )
            )
            good = True
            print(ref, "moved", original, "to", (x, y), flush=True)
            break
        if not good:
            r.geometry.extend(pads)
            for pad, xy in zip(pads, old):
                pad["xy"] = xy
            print(ref, "no legal replacement", flush=True)
            receipts.append(dict(ref=ref, moved=False))
        r.cached = {}
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:move:{index}:{sexpr(node)}")))]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/moved-escapes.json").write_text(json.dumps(receipts, indent=2) + "\n")


if __name__ == "__main__":
    main()
