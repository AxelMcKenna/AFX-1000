"""Joint physical pin escapes for the remaining linear fourteen-pin IC rows."""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import segment_distance
from .repair import ROOT, Router
from .row_solver import solve

TARGETS = ("U28", "U23", "U26", "U11", "U10", "U24")


def main(refs=TARGETS):
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    backup = ROOT / f"generated/ic-row-before-{hashlib.sha256(before).hexdigest()[:12]}.kicad_pcb"
    if not backup.exists():
        backup.write_bytes(before)
    tree = read_sexpr(before.decode())
    old = Router(tree)
    protected = set()
    for name in ("force-stem-repair", "terminal-stitching"):
        p = ROOT / f"generated/{name}.json"
        if p.exists():
            protected.update(json.loads(p.read_text()).get("protected_ids", []))
    regions = []
    for ref in refs:
        pads = old.by_ref[ref]
        xs = [p["xy"][0] for p in pads]
        ys = [p["xy"][1] for p in pads]
        face = pads[0]["layers"][0]
        regions.append((ref, face, (min(xs) - 1.2, min(ys) - 0.7, max(xs) + 1.2, max(ys) + 0.7)))
    removed = []
    keep = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            uid = str(first(node, "uuid")[1]) if children(node, "uuid") else None
            if uid not in protected:
                if node[0] == "segment" and float(first(node, "width")[1]) < 0.35:
                    face = next(
                        (
                            i
                            for i, n in enumerate(("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"))
                            if n == first(node, "layer")[1]
                        ),
                        None,
                    )
                    pts = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in ("start", "end")]

                    def crosses(box):
                        x0, y0, x1, y1 = box
                        if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts):
                            return True
                        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                        return any(
                            segment_distance(pts[0], pts[1], s, t) < 1e-7
                            for s, t in zip(corners, corners[1:] + corners[:1])
                        )

                    # A new through barrel must clear every physical copper
                    # layer. Rip up intersecting narrow routes on all layers;
                    # retained wide force paths and zones are not exempted.
                    drop = any(crosses(box) for _, _, box in regions)
                elif node[0] == "via":
                    xy = tuple(float(v) - 100 for v in first(node, "at")[1:3])
                    foreign_pad = any(
                        p["ref"] not in refs and math.dist(p["xy"], xy) < 0.15 for p in old.pads
                    )
                    drop = not foreign_pad and any(
                        x0 <= xy[0] <= x1 and y0 <= xy[1] <= y1 for _, _, (x0, y0, x1, y1) in regions
                    )
        if drop:
            removed.append(sexpr(node))
        else:
            keep.append(node)
    tree = keep
    rt = Router(tree)
    plans = []
    failed = []
    diagnostics = {}
    for ref in refs:
        complete, remaining, trace = solve(rt, rt.by_ref[ref])
        plans.extend(complete)
        failed.extend(remaining)
        diagnostics[ref] = trace
        print(ref, len(complete), "installed;", len(remaining), "remaining;", trace, flush=True)
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:ICrows:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/ic-row-bundle-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                targets=list(refs),
                actual_escapes=plans,
                failed=failed,
                joint_search=diagnostics,
                removed_items=removed,
                exact_before_snapshot=str(backup),
                protected_ids=ids,
                filled_capped_flush_process_accepted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Joint rows:", len(plans), "installed;", len(failed), "actual geometric obstructions remain.")


if __name__ == "__main__":
    main()
