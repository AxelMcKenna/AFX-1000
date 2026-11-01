"""Actual source-side feedback escapes and compact local wiring.

Only quiet LO_N_FB/LO_REF_1V may use In2 in the U13 TIM field. Any existing
foreign trace displaced by a via becomes an explicit native routing obligation.
No EP thermal via is removed and no thermal acceptance is inferred.
"""

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
    archive = OUT / f"history/before-feedback-route-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    records = []
    removed = []

    def pad(r, ref, pin):
        return next(p for p in r.by_ref[ref] if p["pin"] == pin and p["layers"])

    router = PowerRouter(tree)
    for pin, net, desired in [("3", "LO_REF_1V", (106.3, 8.0)), ("4", "LO_N_FB", (106.3, 9.1))]:
        chosen = None
        candidates = sorted(
            [(105.8 + i * 0.125, 7.3 + j * 0.125) for i in range(9) for j in range(20)],
            key=lambda p: math.dist(p, desired),
        )
        for xy in candidates:
            displaced = []
            for obj in list(children(tree, "segment")):
                if names[str(first(obj, "net")[1])] == net:
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
                    displaced.append(obj)
            trial = PowerRouter(tree)
            trial.max_search_nodes = 10000
            if trial.safe_via(net, xy, clearance=0.16) and trial.connect(
                pad(trial, "U13", pin), dict(net=net, xy=xy, layers=(0,)), 0.16
            ):
                trial.via(net, xy)
                router = trial
                chosen = xy
                removed.extend(dict(net=names[str(first(o, "net")[1])], kind="segment") for o in displaced)
                break
            tree.extend(displaced)
        if chosen is None:
            raise ValueError(("No legal quiet source escape", net))
        records.append(dict(ref="U13", pin=pin, net=net, via_mm=chosen))
        print("Quiet escape", net, chosen, flush=True)
    router.max_search_nodes = 400000
    completed = []
    holds = []
    for row in records:
        source = dict(net=row["net"], xy=row["via_mm"], layers=tuple(range(6)))
        for target in [p for p in router.pads if p["net"] == row["net"]]:
            result = router.connect(source, target, 0.16)
            (completed if result else holds).append(
                dict(net=row["net"], target=[target["ref"], target["pin"]])
            )
    # Compact divider midpoint is a real B-side local route, not a new source.
    a = pad(router, "R47", "2")
    b = pad(router, "R48", "1")
    result = router.connect(a, b, 0.16)
    (completed if result else holds).append(dict(net=a["net"], target=["R48", "1"]))
    cap = pad(router, "C72", "2")
    assert cap["net"] == "AGND"
    grounds = sorted(
        [g for g in router.geometry if g["kind"] == "via" and g["net"] == "AGND"],
        key=lambda g: math.dist(g["xy"], cap["xy"]),
    )
    for g in grounds[:12]:
        if router.connect(cap, dict(net="AGND", xy=g["xy"], layers=tuple(range(6))), 0.16):
            completed.append(dict(net="AGND", target=["C72", "2"]))
            break
    else:
        holds.append(dict(net="AGND", target=["C72", "2"]))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (OUT / "feedback-routing.json").write_text(
        json.dumps(
            dict(
                prior_sha256=digest,
                archive=str(archive.relative_to(ROOT)),
                source_escapes=records,
                displaced_transit_copper=removed,
                completed_targets=completed,
                unresolved_targets=holds,
                direct_ep_vias_removed=0,
                quiet_inner_layer="In2.Cu",
                native_thermal_ground_extractions_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Quiet routes completed", len(completed), "holds", len(holds), flush=True)


if __name__ == "__main__":
    implement()
