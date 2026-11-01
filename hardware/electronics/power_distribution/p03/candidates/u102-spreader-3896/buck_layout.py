"""Implement local VIN/BP5 capacitor repair; actual native checks decide closure.

The prior board is archived. Effective capacitance and AC/EM performance are
explicit requirements, never inferred from nominal capacitor markings.
"""

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ...power_supply.place import overlap
from .board import valid_box
from .route import PowerRouter, coded, named
from .spec import MOUNTS, ROOT

POSES = {
    "C200": (44.25, 16.5, 180, "F"),
    "C201": (45, 9.4, 90, "F"),
    "C202": (48, 17.2, 0, "F"),
    "C203": (48, 8.8, 0, "F"),
    "C220": (132, 32.25, 180, "F"),
    "C221": (133.2, 23.5, 90, "F"),
    "C222": (136, 32.1, 0, "F"),
    "C223": (136, 23.8, 0, "F"),
}

POWER_PAIRS = (
    ("U20", "C202", "8", "9", "local_bulk"),
    ("U20", "C203", "12", "11", "local_bulk"),
    ("U23", "C222", "8", "9", "local_bulk"),
    ("U23", "C223", "12", "11", "local_bulk"),
    ("U20", "C210", "8", "9", "high_frequency"),
    ("U20", "C211", "12", "11", "high_frequency"),
    ("U23", "C230", "8", "9", "high_frequency"),
    ("U23", "C231", "12", "11", "high_frequency"),
)


def implement(root, cli):
    path = root / "power_p03.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    archive = root / "generated/history" / f"before-buck-inputs-{digest[:16]}.kicad_pcb.gz"
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        archive.write_bytes(gzip.compress(original, mtime=0))
    tree = coded(read_sexpr(original.decode()))
    parts = {p["ref"]: p for p in json.loads((root / "components.json").read_text())}
    router = PowerRouter(tree)
    pads = [p for ref in POSES for p in router.by_ref[ref] if p["layers"]]
    netmap = router.nets
    library = footprint_root(str(cli))
    used = [(f"mount{i}", [x - 3.7, y - 3.7, x + 3.7, y + 3.7]) for i, (x, y) in enumerate(MOUNTS)]
    old = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in POSES:
            old.append(fp)
        elif first(fp, "layer")[1] == "F.Cu":
            used.append((ref, [v - 100 for v in courtyard(fp, "F.CrtYd")]))
    assert len(old) == len(POSES)
    replacement = []
    for ref, pose in POSES.items():
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        footprint = library / (lib + ".pretty") / (name + ".kicad_mod")
        c = dict(c, value=c["part"], mpn=c["part"], nets={p["number"]: p["net"] for p in c["pins"]})
        fp = placed_footprint(c, pose, footprint, netmap)
        box = [v - 100 for v in courtyard(fp, "F.CrtYd")]
        assert valid_box(box), (ref, "outside board")
        assert not any(overlap(box, b, 0.15) for _, b in used), (
            ref,
            [r for r, b in used if overlap(box, b, 0.15)],
        )
        used.append((ref, box))
        replacement.append(fp)
    for fp in old:
        tree.remove(fp)
    tree.extend(replacement)
    trial = PowerRouter(tree)
    pads.extend(p for ref in POSES for p in trial.by_ref[ref] if p["layers"])
    removed = []
    # Rip actual old attachment/foreign conflicting copper around the moved
    # terminal lands. Their disconnected destinations remain native airwires.
    for obj in list(children(tree, "segment")):
        layer = first(obj, "layer")[1]
        if layer != "F.Cu":
            continue
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = b[0] - a[0], b[1] - a[1]
        for pad in pads:
            q = pad["xy"]
            t = (
                max(0, min(1, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            # Conservative circular pad envelope for local rip-up only; this
            # never authorizes a trace/land clearance or removes a fixed pad.
            if (
                math.dist(q, (a[0] + t * dx, a[1] + t * dy))
                < max(pad["size"]) / 2 + 0.16 + float(first(obj, "width")[1]) / 2
            ):
                removed.append(copy.deepcopy(obj))
                tree.remove(obj)
                break
    path.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/buck-input-layout.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                poses=POSES,
                removed_front_transit_segments=len(removed),
                fixed_courtyard_margin_mm=0.15,
                physical_capacitance_and_hot_loop_qualified=False,
                native_routing_refill_required=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Buck input/BP5 layout:8 reviewed front capacitors; native closure required", flush=True)


def route_pairs(root):
    """Create real short .35mm F.Cu VIN/PGND links before remote routing.

    These traces intentionally take priority over old unrelated transits. Fixed
    lands and all direct EP thermal vias remain unchanged; native DRC must
    reject any incompatible source pad/assembly geometry.
    """
    path = root / "power_p03.kicad_pcb"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-buck-pairs-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    router = PowerRouter(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}

    def distance(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
        return math.dist(p, (a[0] + t * dx, a[1] + t * dy))

    def segdist(a, b, c, d):
        def cross(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

        if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
            return 0
        return min(distance(a, c, d), distance(b, c, d), distance(c, a, b), distance(d, a, b))

    records, removed = [], []
    for ref, cap, vin, ground, category in POWER_PAIRS:
        if cap not in router.by_ref:
            continue
        for pin, cap_pin in ((vin, "1"), (ground, "2")):
            source = next(p for p in router.by_ref[ref] if p["pin"] == pin and p["layers"])
            target = next(p for p in router.by_ref[cap] if p["pin"] == cap_pin and p["layers"])
            net, a, b = source["net"], source["xy"], target["xy"]
            assert target["net"] == net and source["layers"] == target["layers"] == (0,)
            for obj in list(children(tree, "segment")):
                if first(obj, "layer")[1] != "F.Cu" or names[str(first(obj, "net")[1])] == net:
                    continue
                c, d = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
                if segdist(a, b, c, d) < 0.175 + float(first(obj, "width")[1]) / 2 + 0.16:
                    tree.remove(obj)
                    removed.append(str(first(obj, "uuid")[1]) if children(obj, "uuid") else "unassigned")
            router.path(net, 0, [a, b], 0.35)
            records.append(
                dict(
                    regulator=ref,
                    pin=pin,
                    capacitor=cap,
                    cap_pin=cap_pin,
                    net=net,
                    points_mm=[a, b],
                    length_mm=math.dist(a, b),
                    width_mm=0.35,
                    layer="F.Cu",
                    category=category,
                )
            )
    path.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/buck-vin-pairs.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                connections=records,
                displaced_foreign_transits=removed,
                native_clearance_and_refill_required=True,
                switching_loop_em_and_thermal_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Buck VIN/PGND local F.Cu routes", len(records), "displaced transits", len(removed), flush=True)


def pair_inventory(tree):
    """Check the actual saved direct copper, independently of authoring logs."""
    tree = coded(copy.deepcopy(tree))
    router = PowerRouter(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    rows = []
    for ref, cap, vin, ground, category in POWER_PAIRS:
        if cap not in router.by_ref:
            continue
        for pin, cap_pin in ((vin, "1"), (ground, "2")):
            source = next(p for p in router.by_ref[ref] if p["pin"] == pin and p["layers"])
            target = next(p for p in router.by_ref[cap] if p["pin"] == cap_pin and p["layers"])
            a, b, net = source["xy"], target["xy"], source["net"]
            matches = []
            for s in children(tree, "segment"):
                if first(s, "layer")[1] != "F.Cu" or names[str(first(s, "net")[1])] != net:
                    continue
                if float(first(s, "width")[1]) < 0.35 - 1e-6:
                    continue
                c, d = [tuple(float(v) - 100 for v in first(s, k)[1:3]) for k in ("start", "end")]
                if (math.dist(a, c) < 1e-5 and math.dist(b, d) < 1e-5) or (
                    math.dist(a, d) < 1e-5 and math.dist(b, c) < 1e-5
                ):
                    matches.append(str(first(s, "uuid")[1]))
            rows.append(
                dict(
                    regulator=ref,
                    pin=pin,
                    capacitor=cap,
                    capacitor_pin=cap_pin,
                    net=net,
                    points_mm=[a, b],
                    length_mm=math.dist(a, b),
                    matching_native_segment_uuids=matches,
                    category=category,
                )
            )
    return dict(
        connections=rows,
        eight_native_direct_pairs_present=len([r for r in rows if r["category"] == "local_bulk"]) == 8
        and all(r["matching_native_segment_uuids"] for r in rows if r["category"] == "local_bulk"),
        eight_native_hf_pairs_present=len([r for r in rows if r["category"] == "high_frequency"]) == 8
        and all(r["matching_native_segment_uuids"] for r in rows if r["category"] == "high_frequency"),
        physical_hot_loop_em_and_thermal_qualified=False,
    )


def write_pair_inventory(root):
    path = root / "power_p03.kicad_pcb"
    report = pair_inventory(read_sexpr(path.read_text()))
    report["pcb_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    report["verifier_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (root / "generated/buck-vin-pairs-native.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--kicad-cli", type=Path, required=True)
    p.add_argument("--route-pairs", action="store_true")
    args = p.parse_args()
    if args.route_pairs:
        route_pairs(args.root)
    else:
        implement(args.root, args.kicad_cli)
