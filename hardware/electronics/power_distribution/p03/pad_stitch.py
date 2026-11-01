"""Deliberate local source/SET/ground barrel access, native checks mandatory.

This repairs actual opposite-face and plane-override routing cages. Existing
foreign transits displaced at new barrel lands become explicit open obligations;
no fixed pad, support exclusion or direct EP thermal via is removed.
"""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root, group="priority"):
    pcb = root / "power_p03.kicad_pcb"
    out = root / "generated"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = out / f"history/before-pad-stitch-{digest[:16]}.kicad_pcb.gz"
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    router = PowerRouter(tree)
    records = []
    displaced = []
    holds = []

    def pad(r, ref, pin):
        return next(p for p in r.by_ref[ref] if p["pin"] == pin and p["layers"])

    groups = {
        "priority": [
            ("R38", "2", "AGND", (82.4125, 19.5), 0.16),
            ("C302", "2", "AGND", (142, 12), 0.16),
            ("U10", "4", "N19_SET", (89, 28), 0.16),
            ("C67", "1", "RAW_N17", (120.9, 19.475), 0.5),
            ("C71", "1", "VIN_PROTECTED", (119.5, 7.375), 0.25),
        ],
        "supervisor": [
            ("U25", "1", "P03_MON_DIG", (145.7, 12.2225), 0.16),
            ("U25", "2", "P03_MON_ANA", (144.7, 11.5875), 0.16),
            ("U25", "3", "P03_MON_P19", (145.7, 10.9525), 0.16),
            ("U25", "4", "P03_MON_P12", (144.7, 10.3175), 0.16),
            ("U25", "5", "P03_MON_BUCK_OK", (145.7, 9.6825), 0.16),
            ("U25", "6", "P03_MON_VIN", (144.7, 9.0475), 0.16),
            ("U25", "7", "P03_MON_N19", (145.7, 8.4125), 0.16),
            ("U25", "8", "P03_MON_N12", (144.7, 7.7775), 0.16),
        ],
        "buck": [
            ("U20", "2", "P03_D_MODE", (44.7, 11.9), 0.16),
            ("U20", "3", "P03_SOURCES_READY", (44.7, 13.1), 0.16),
            ("U23", "3", "P03_SOURCES_READY", (132.8, 28), 0.16),
            ("U23", "7", "P03_A_ENABLE", (134.4, 28.2), 0.16),
        ],
    }
    groups["monitor_missing"] = [groups["supervisor"][6], groups["supervisor"][7]]
    groups["remaining"] = [
        ("C31", "2", "AGND", (88, 21.95), 0.16),
        ("R302", "1", "V5_REG_SRC", (143, 10.9125), 0.16),
        ("R7", "1", "5V_DIG_SRC", (83, 16.2125), 0.25),
        ("R6", "1", "5V_DIG_SRC", (85.0875, 14.3), 0.16),
        ("U20", "1", "P03_D_FSEL", (45.6125, 12.0125), 0.16),
        ("U102", "7", "AUX_START_DELAY", (28.4, 19.675), 0.16),
        ("R306", "1", "P12_SRC", (141.0875, 7), 0.16),
    ]
    groups["last"] = [
        ("R302", "1", "V5_REG_SRC", (141.5, 10.9125), 0.16),
        ("R115", "1", "VIN_IC", (34, 19.4125), 0.25),
        ("R313", "1", "P03_MON_N19", (152.25, 12), 0.16),
        ("C301", "1", "V2V5_AUX", (141.725, 6), 0.16),
        ("C74", "1", "LO_P_SS", (122, 4.85), 0.16),
        ("R40", "1", "N12_RMID", (134, 13.9125), 0.16),
        ("R314", "2", "P03_MON_N12", (142.9125, 14), 0.16),
        ("U26", "1", "P03_SOURCES_READY", (151.8625, 10.95), 0.16),
        ("U23", "7", "P03_A_ENABLE", (134.8, 30.5), 0.16),
        ("U1", "9", "RAW_P_SS", (88.25, 9.8), 0.16),
        ("C110", "1", "AUX_START_DELAY", (32.5, 13.45), 0.16),
    ]
    if group == "monitor_missing":
        # The BUCK_OK transit at x142.2 descends beside the left SSOP bank.
        # Flood filling pin7's B.Cu corridor finds zero legal through-via
        # centres. Remove that actual fence and the obsolete N12 detour;
        # both remain explicit routing obligations after the N19 escape.
        for obj in list(children(tree, "segment")):
            if (
                names[str(first(obj, "net")[1])] not in {"P03_MON_N12", "P03_MON_BUCK_OK"}
                or first(obj, "layer")[1] != "B.Cu"
            ):
                continue
            points = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
            if (
                min(p[0] for p in points) <= 150
                and max(p[0] for p in points) >= 141
                and min(p[1] for p in points) <= 14.5
                and max(p[1] for p in points) >= 5.5
            ):
                tree.remove(obj)
                displaced.append(
                    dict(
                        net=names[str(first(obj, "net")[1])],
                        kind="segment",
                        reason="Remove actual left-bank fence",
                    )
                )
        router = PowerRouter(tree)
    if group in {"supervisor", "control"}:
        supervisor_nets = {task[2] for task in groups["supervisor"]}
        for obj in list(children(tree, "via")):
            net = names[str(first(obj, "net")[1])]
            x, y = [float(v) - 100 for v in first(obj, "at")[1:3]]
            if net in supervisor_nets and 141.5 <= x <= 149 and 6.5 <= y <= 14:
                tree.remove(obj)
                displaced.append(
                    dict(
                        net=net,
                        kind="via",
                        reason="Old all-layer barrel cage replaced by staged supervisor escape bank",
                    )
                )
        for obj in list(children(tree, "segment")):
            if first(obj, "layer")[1] != "B.Cu" or names[str(first(obj, "net")[1])] == "AGND":
                continue
            a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
            if (
                min(a[0], b[0]) <= 147
                and max(a[0], b[0]) >= 142
                and min(a[1], b[1]) <= 12.9
                and max(a[1], b[1]) >= 7.25
            ):
                tree.remove(obj)
                displaced.append(
                    dict(
                        net=names[str(first(obj, "net")[1])],
                        kind="segment",
                        reason="Deliberate B-side supervisor left-bank fanout corridor",
                    )
                )
        router = PowerRouter(tree)
    tasks = groups["supervisor"] + groups["buck"] if group == "control" else groups[group]
    for ref, pin, net, desired, width in tasks:
        assert pad(router, ref, pin)["net"] == net
        chosen = None
        points = sorted(
            [
                (desired[0] + i * 0.25, desired[1] + j * 0.25)
                for i in (range(-24, 25) if group == "monitor_missing" else range(-12, 13))
                for j in (
                    (0,)
                    if ref == "U25" and group != "monitor_missing"
                    else range(-24, 25)
                    if group == "monitor_missing"
                    else range(-12, 13)
                )
            ],
            key=lambda q: math.dist(q, desired),
        )
        # Native pads have .0125/.0875mm offsets. A quarter-mm lattice with
        # the source-row phase can miss the only legal capped via-in-pad site.
        # Try actual same-net terminal centres before the adaptive free sites.
        source_xy = pad(router, ref, pin)["xy"]
        points = list(
            dict.fromkeys(
                [
                    *(p["xy"] for p in router.pads if p["net"] == net and math.dist(p["xy"], source_xy) <= 6),
                    *points,
                ]
            )
        )
        for xy in points:
            # Fixed pads/barrels/holes cannot be repaired by displacing a
            # transit trace. Reject them before rebuilding the full router.
            geometry = router.geometry
            router.geometry = [g for g in geometry if g["kind"] != "line"]
            reuse = any(
                g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], xy) < 1e-6
                for g in router.geometry
            )
            fixed_clear = reuse or router.safe_via(net, xy, clearance=0.16)
            router.geometry = geometry
            if not fixed_clear:
                continue
            old = []
            for obj in list(children(tree, "segment")):
                if names[str(first(obj, "net")[1])] == net:
                    continue
                if group == "monitor_missing" and names[str(first(obj, "net")[1])].startswith("P03_MON_"):
                    # Preserve already-routed supervisor channels while
                    # repairing the remaining two actual source escapes.
                    continue
                a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
                dx, dy = b[0] - a[0], b[1] - a[1]
                t = (
                    max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                    if dx or dy
                    else 0
                )
                if (
                    math.dist(xy, (a[0] + t * dx, a[1] + t * dy))
                    < 0.3 + 0.16 + float(first(obj, "width")[1]) / 2
                ):
                    tree.remove(obj)
                    old.append(obj)
            trial = PowerRouter(tree)
            trial.max_search_nodes = 15000
            reuse = any(
                g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], xy) < 1e-6
                for g in trial.geometry
            )
            if (reuse or trial.safe_via(net, xy, clearance=0.16)) and trial.connect(
                pad(trial, ref, pin), dict(net=net, xy=xy, layers=pad(trial, ref, pin)["layers"]), width
            ):
                trial.via(net, xy)
                router = trial
                chosen = xy
                displaced.extend(dict(net=names[str(first(o, "net")[1])], kind="segment") for o in old)
                break
            tree.extend(old)
        if chosen is None:
            holds.append(dict(ref=ref, pin=pin, net=net, stage="barrel access"))
            continue
        records.append(dict(ref=ref, pin=pin, net=net, via_mm=chosen, width_mm=width))
        print("Local barrel", ref, pin, chosen, flush=True)
    # Reserve the entire selected fine-pin bank before long routes can fence
    # the next source pin. A failed target remains an explicit native open.
    for record in records:
        ref, net, chosen, width = record["ref"], record["net"], record["via_mm"], record["width_mm"]
        router.max_search_nodes = 400000
        source = dict(net=net, xy=chosen, layers=tuple(range(6)))
        targets = (
            [p for p in router.pads if p["net"] == net]
            if net not in {"AGND", "RAW_N17", "VIN_PROTECTED"}
            else [pad(router, "U11", "11")]
            if net == "RAW_N17"
            else [pad(router, "U13", "8")]
            if ref == "C71"
            else []
        )
        for target in targets:
            if not router.connect(source, target, width):
                holds.append(dict(ref=target["ref"], pin=target["pin"], net=net, stage="remote closure"))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (out / "pad-stitching.json").write_text(
        json.dumps(
            dict(
                prior_sha256=digest,
                selected_group=group,
                implemented_barrels=records,
                displaced_transit_copper=displaced,
                holds=holds,
                native_refill_and_connectivity_required=True,
                ampacity_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Local barrel access complete", len(records), "holds", len(holds), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument(
        "--group",
        choices=("priority", "supervisor", "buck", "control", "monitor_missing", "remaining", "last"),
        default="priority",
    )
    args = p.parse_args()
    implement(args.root, args.group)
