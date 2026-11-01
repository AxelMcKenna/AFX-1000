"""Repair actual TPS2663 fine-pin escapes before routing remote guard nets."""

import gzip
import hashlib
import json
import math

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import OUT, ROOT, PowerRouter, coded, named


def implement():
    pcb = ROOT / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = OUT / f"history/before-guard-fanout-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"segment", "via"}:
            continue
        if names[str(first(obj, "net")[1])] == "AGND":
            continue
        points = (
            [first(obj, "at")[1:3]] if obj[0] == "via" else [first(obj, k)[1:3] for k in ("start", "end")]
        )
        xy = [tuple(float(v) - 100 for v in p) for p in points]
        if obj[0] == "via" and 24.45 <= xy[0][0] <= 27.05 and 11.2 <= xy[0][1] <= 13.8:
            continue
        if (
            min(p[0] for p in xy) <= 31.5
            and max(p[0] for p in xy) >= 19.5
            and min(p[1] for p in xy) <= 18.3
            and max(p[1] for p in xy) >= 8.5
        ):
            removed.append(obj)
            tree.remove(obj)
    router = PowerRouter(tree)
    router.max_search_nodes = 15000
    records = []
    for number, desired in [
        ("4", (21.5, 12.75)),
        ("3", (22, 11.75)),
        ("5", (21.5, 13.5)),
        ("6", (22.75, 14.5)),
        ("7", (24.5, 15.25)),
        ("9", (25.5, 15.25)),
        ("10", (26.5, 15.25)),
        ("12", (28.5, 14.5)),
        ("15", (29.25, 12.75)),
        ("16", (29.5, 11.75)),
        ("1", (22, 11)),
    ]:
        pad = next(p for p in router.by_ref["U101"] if p["pin"] == number and p["layers"])
        candidates = sorted(
            (
                (i * 0.25, j * 0.25)
                for i in range(76, 130)
                for j in range(30, 75)
                if router.safe_via(pad["net"], (i * 0.25, j * 0.25))
            ),
            key=lambda xy: math.dist(xy, desired) + 0.3 * math.dist(xy, pad["xy"]),
        )
        chosen = None
        for point in candidates[:80]:
            if router.connect(pad, dict(net=pad["net"], xy=point, layers=(0,)), 0.16):
                chosen = point
                break
        if chosen is None:
            raise ValueError(f"Guard{number} has no legal front escape to actual through-via")
        router.via(pad["net"], chosen)
        records.append(dict(pin=number, net=pad["net"], via_mm=chosen))
        print("Reserved guard escape", number, chosen, flush=True)
    # Reserve ALL source escapes before greedy long routing can fence another
    # fine-pitch pin. Complete actual remote connections before native cleanup
    # can legitimately remove a via attached on only the source face.
    router.max_search_nodes = 400000
    completed = []
    failed = []
    for row in records:
        source = dict(net=row["net"], xy=row["via_mm"], layers=tuple(range(6)))
        targets = [p for p in router.pads if p["net"] == row["net"] and p["ref"] != "U101"]
        for target in sorted(targets, key=lambda p: math.dist(source["xy"], p["xy"])):
            if router.connect(source, target, 0.16):
                completed.append(dict(net=row["net"], target=[target["ref"], target["pin"]]))
            else:
                failed.append(dict(net=row["net"], target=[target["ref"], target["pin"]]))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (OUT / "guard-fanout.json").write_text(
        json.dumps(
            dict(
                prior_sha256=digest,
                archive=str(archive.relative_to(ROOT)),
                obsolete_copper_removed=len(removed),
                actual_fanouts=records,
                completed_remote_targets=completed,
                unresolved_remote_targets=failed,
                no_ground_copper_removed=True,
                native_closure_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Guard fine-pin escapes",
        records,
        "old copper removed",
        len(removed),
        "remote completed",
        len(completed),
        "holds",
        len(failed),
        flush=True,
    )


if __name__ == "__main__":
    implement()
