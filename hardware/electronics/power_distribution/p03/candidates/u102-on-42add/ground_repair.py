"""Explicit quiet/PGND and negative-LDO returns, checked by fresh native DRC."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from .route import OUT, ROOT, PowerRouter, coded, named

POSES = {"C200": (45, 16.5, 180, "F"), "C220": (133, 32, 180, "F")}


def implement(cli):
    pcb = ROOT / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    archive = OUT / f"history/before-ground-repair-{sha[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    _, pins = netlist(OUT / "netlist.xml")
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    names = {str(v): k for k, v in nets.items()}
    changed = []
    for ref, pose in POSES.items():
        fp = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(fp, "property"))
        )
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        new = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            pose,
            footprint_root(str(cli)) / (lib + ".pretty") / (name + ".kicad_mod"),
            nets,
            namespace="rmx:P03:",
        )
        tree[tree.index(fp)] = new
        changed.append(ref)
    # Both BP5 caps originally faced their ground land toward the BP5 pin,
    # forcing a signal escape across the quiet-reference ground escape.
    removed = 0
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"segment", "via"}:
            continue
        net = names[str(first(obj, "net")[1])]
        points = (
            [first(obj, "at")[1:3]] if obj[0] == "via" else [first(obj, k)[1:3] for k in ("start", "end")]
        )
        xs = [float(p[0]) - 100 for p in points]
        ys = [float(p[1]) - 100 for p in points]
        obsolete = net in {"P03_D_BP5", "P03_A_BP5"}
        if net == "AGND":
            obsolete |= any(
                min(xs) < cx + 1 and max(xs) > cx - 1 and min(ys) < cy + 1.7 and max(ys) > cy - 1.7
                for cx, cy in [(46.475, 16.5), (134.475, 32)]
            )
        if obsolete:
            tree.remove(obj)
            removed += 1
    router = PowerRouter(tree)

    def pad(ref, pin, near):
        return min(
            [p for p in router.by_ref[ref] if p["pin"] == str(pin) and p["layers"]],
            key=lambda p: math.dist(p["xy"], near),
        )

    returns = [
        ("U20", "5", (45.1, 14.9), 0.16),
        ("U20", "11", (48.2, 11.3), 0.50),
        ("U23", "5", (133.1, 29.9), 0.16),
        ("U23", "11", (136.625, 26.5), 0.50),
        ("U10", "3", (89.8, 28.5), 0.25),
        ("U11", "3", (117.5, 27), 0.25),
        ("C200", "2", (43.525, 16.5), 0.35),
        ("C220", "2", (131.525, 32), 0.35),
    ]
    # Remove actual foreign-net transit at the deliberately selected ground
    # landings. Those nets become explicit routing obligations, never shorts.
    removed_foreign = []
    for obj in list(children(tree, "segment")):
        net = names[str(first(obj, "net")[1])]
        if net == "AGND":
            continue
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = b[0] - a[0], b[1] - a[1]
        w = float(first(obj, "width")[1])
        for _, _, xy, _ in returns:
            t = (
                max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if math.dist(xy, (a[0] + t * dx, a[1] + t * dy)) < 0.30 + 0.16 + w / 2:
                tree.remove(obj)
                removed_foreign.append(net)
                break
    for obj in list(children(tree, "via")):
        net = names[str(first(obj, "net")[1])]
        p = tuple(float(v) - 100 for v in first(obj, "at")[1:3])
        if net != "AGND" and any(math.dist(p, xy) < 0.76 for _, _, xy, _ in returns):
            tree.remove(obj)
            removed_foreign.append(net)
    router = PowerRouter(tree)
    records = []
    for ref, pin, xy, width in returns:
        p = pad(ref, pin, xy)
        assert p["net"] == "AGND"
        if not any(
            g["kind"] == "via" and g["net"] == "AGND" and math.dist(g["xy"], xy) < 1e-5
            for g in router.geometry
        ) and not router.safe_via("AGND", xy, clearance=0.16):
            for g in router.geometry:
                if g["kind"] in {"via", "rect"} and g["net"] != "AGND" and math.dist(xy, g["xy"]) < 2:
                    print(g)
            raise ValueError(f"Actual ground return via blocked: {ref}.{pin} {xy}")
        router.path("AGND", p["layers"][0], [p["xy"], xy], width)
        router.via("AGND", xy)
        records.append(dict(ref=ref, pin=pin, via_mm=xy, width_mm=width))
    for ic, cap, net in [("U20", "C200", "P03_D_BP5"), ("U23", "C220", "P03_A_BP5")]:
        pin = pad(ic, "6", (0, 0))
        dest = pad(cap, "1", pin["xy"])
        assert pin["net"] == dest["net"] == net
        router.path(net, 0, [pin["xy"], dest["xy"]], 0.25)
    pcb.write_text(sexpr(named(tree)) + "\n")
    report = json.loads((OUT / "placement.json").read_text())
    for ref, pose in POSES.items():
        fp = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(fp, "property"))
        )
        report["poses"][ref] = list(pose)
        report["courtyards"][ref] = [v - 100 for v in courtyard(fp, "F.CrtYd")]
    (OUT / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "ground-repair.json").write_text(
        json.dumps(
            dict(
                prior_sha256=sha,
                rotated_caps=changed,
                obsolete_copper_removed=removed,
                foreign_transit_nets_requiring_reroute=removed_foreign,
                implemented_ground_returns=records,
                native_refill_and_connectivity_required=True,
                physical_ground_transfer_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Ground returns implemented", len(records), "old copper removed", removed)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    implement(p.parse_args().kicad_cli)
