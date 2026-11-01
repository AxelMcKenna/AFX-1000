"""Remove actual offending copper and repair native connected components."""

import argparse
import json
import math
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from ..revision27.repair import CachedRouter
from .search import diagonal_connect
from .terminals import ALL_TERMINALS

ROOT = Path(__file__).resolve().parent
FROZEN_E27 = ROOT.parent / "revision27"


class Router(CachedRouter):
    def __init__(self, tree):
        super().__init__(tree)
        drilled_pads = {
            (next(p[2] for p in children(fp, "property") if p[1] == "Reference"), str(pad[1]))
            for fp in children(tree, "footprint")
            for pad in children(fp, "pad")
            if children(pad, "drill")
        }
        # Custom TI patterns contain paste-only aperture pads. They are stencil
        # shapes, not copper or holes. Preserve every real drilled reservation.
        self.geometry = [
            g
            for g in self.geometry
            if not (
                g["kind"] == "rect" and not g["layers"] and (g.get("ref"), g.get("pin")) not in drilled_pads
            )
        ]
        # E28requires filled/capped flush barrels. A capacitor-body-only via
        # prohibition from the conventional E26process is not physical copper
        # or a hole obstacle; actual leads, pad clearances and mounting hardware
        # remain in the geometry and all native checks remain enabled.
        self.geometry = [g for g in self.geometry if g["net"] != "BULK_BODY_NOVIA"]
        for ref, (x, y, net) in ALL_TERMINALS.items():
            if ref not in self.by_ref:
                continue
            # Exact annulus is checked natively. This conservative router reserve
            # prevents foreign routes and all vias through the physical terminal.
            self.geometry.append(dict(kind="via", xy=(x, y), radius=4.3, net=net, layers=(0,)))
            self.geometry.append(dict(kind="via", xy=(x, y), radius=2.35, net="NPTH", layers=tuple(range(6))))

    def existing_via(self, net, point):
        return next(
            (
                g["xy"]
                for g in self.geometry
                if g["kind"] == "via"
                and g["net"] == net
                and g.get("layers") == tuple(range(6))
                and math.dist(g["xy"], point) <= aid.STEP * 0.72
            ),
            None,
        )

    def via(self, net, point):
        # A grid point inside an existing physical barrel must reuse that drill.
        # Adding a second nearly-coincident hole is an actual fabrication defect.
        if self.existing_via(net, point) is None:
            return super().via(net, point)

    def path(self, net, layer, points, width):
        # Attach the actual trace centreline to the native barrel centre rather
        # than leaving off-grid endpoints or adding overlapping drills.
        points = [self.existing_via(net, p) or p for p in points]
        return super().path(net, layer, points, width)

    def connect(self, source, target, width):
        blocked, via = self.masks(source["net"], width)
        for endpoint in (source, target):
            ix, iy = (round(v / aid.STEP) for v in endpoint["xy"])
            for layer in endpoint["layers"]:
                blocked[layer, ix, iy] = False
            if self.existing_via(source["net"], endpoint["xy"]) is not None:
                via[ix, iy] = False
        return diagonal_connect(self, source, target, width)

    def masks(self, net, width):
        blocked, via = super().masks(net, width)
        # E28 explicitly permits signal corridors in the second return layer.
        # The actual remaining filled return geometry, including every cut, is
        # extracted independently; no E27 ground-plane resistance is inherited.
        blocked[4] = aid.Router.masks(self, net, width)[0][4]
        if getattr(self, "allow_pour_clearance", False) and getattr(self, "inner_escape", False):
            # A declared new routing pass may cut a pour through native refill.
            # Raw zone outlines are not immutable copper: they include the
            # clearance voids around existing pads. Every actual pad, track,
            # drill and keepout stays in the base geometry mask. The resulting
            # filled current paths require fresh extraction after routing.
            blocked[1] = aid.Router.masks(self, net, width)[0][1]
        for g in self.geometry:
            if g["kind"] == "via" and g["net"] == net and g.get("layers") == tuple(range(6)):
                ix, iy = (round(v / aid.STEP) for v in g["xy"])
                if 0 <= ix < self.nx and 0 <= iy < self.ny:
                    via[ix, iy] = False
        return blocked, via


def remove_conflicts(report, keep_ids=(), label="removed-conflicts", source_pcb=None):
    keep_ids = set(keep_ids)
    path = ROOT / "rail_disconnect.kicad_pcb" if source_pcb is None else Path(source_pcb)
    assert path.resolve().is_relative_to(ROOT.resolve())
    tree = read_sexpr(path.read_text())
    parent_tree = read_sexpr((FROZEN_E27 / "rail_disconnect.kicad_pcb").read_text())
    original_ids = {
        str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:copper:{i}"))
        for i, n in enumerate(parent_tree)
        if isinstance(n, list) and n and n[0] in ("segment", "via")
    }
    ids = set()
    for row in report["violations"]:
        selected = [str(item["uuid"]) for item in row["items"] if str(item["uuid"]) not in keep_ids]
        if row["severity"] == "error":
            new = [uid for uid in selected if uid not in original_ids]
            if new:
                selected = new
        ids.update(selected)
    removed = []
    result = []
    for node in tree:
        if (
            isinstance(node, list)
            and node
            and node[0] in ("segment", "via")
            and children(node, "uuid")
            and str(first(node, "uuid")[1]) in ids
        ):
            removed.append(sexpr(node))
        else:
            result.append(node)
    path.write_text(sexpr(result) + "\n")
    (ROOT / f"generated/{label}.json").write_text(json.dumps(removed, indent=2) + "\n")
    print("Removed", len(removed), "native-reported conflicting or dangling copper items", flush=True)


def route(attempts=40):
    path = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(path.read_text())
    aid.STEP = 0.125
    aid.CLEARANCE = 0.22  # Includes enough guard for 45-degree grid corners.
    r = Router(tree)
    r.max_search_nodes = 100000
    r.search_bias = 1.7
    r.allow_pour_clearance = False
    r.inner_escape = True
    opens = json.loads((ROOT / "generated/open-components.json").read_text())
    result = []
    for row in opens:
        r.cached = {}
        blocked, via = r.masks(row["net"], 0.25)

        def viable(point):
            ix, iy = (round(v / aid.STEP) for v in point["xy"])
            return any(
                not blocked[layer, ix + dx, iy + dy]
                for layer in point["layers"]
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 <= ix + dx < r.nx and 0 <= iy + dy < r.ny
            )

        pairs = sorted(
            (
                (math.dist(a["xy"], b["xy"]), a, b)
                for a in row["components"][0]
                if viable(a)
                for b in row["components"][1]
                if viable(b)
            ),
            key=lambda p: p[0],
        )
        seen = set()
        good = False
        count = 0
        usage = {}

        def anchor(p):
            return tuple(round(v / aid.STEP) for v in p["xy"]), tuple(p["layers"])

        while pairs:
            index = min(
                range(len(pairs)),
                key=lambda i: (
                    max(usage.get(anchor(pairs[i][1]), 0), usage.get(anchor(pairs[i][2]), 0)),
                    usage.get(anchor(pairs[i][1]), 0) + usage.get(anchor(pairs[i][2]), 0),
                    pairs[i][0],
                ),
            )
            _, source, target = pairs.pop(index)
            key = (
                tuple(round(v / aid.STEP) for v in source["xy"]),
                tuple(source["layers"]),
                tuple(round(v / aid.STEP) for v in target["xy"]),
                tuple(target["layers"]),
            )
            if key in seen:
                continue
            seen.add(key)
            usage[anchor(source)] = usage.get(anchor(source), 0) + 1
            usage[anchor(target)] = usage.get(anchor(target), 0) + 1
            count += 1
            if count > attempts:
                break
            if r.connect(dict(source, net=row["net"]), dict(target, net=row["net"]), 0.25):
                good = True
                break
        result.append(dict(net=row["net"], connected=good, attempts=count))
        print(row["net"], good, count, flush=True)
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:repair:{index}:{sexpr(node)}")))]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/repair.json").write_text(
        json.dumps(dict(attempts=result, routes=r.routes), indent=2) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove-report", type=Path)
    parser.add_argument("--attempts", type=int, default=40)
    args = parser.parse_args()
    if args.remove_report:
        remove_conflicts(json.loads(args.remove_report.read_text()))
    else:
        route(args.attempts)
