"""Local U13 negative feedback repair outside the actual underside TIM cut.

The moved raw cap is nearer its rectifier; the low-current feedback parts form
one compact row. This authoring step invalidates routing/thermal/MCAD receipts.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ...power_supply.place import overlap
from .board import valid_box
from .route import OUT, ROOT, coded, named
from .spec import MOUNTS, THERMAL_REGIONS

POSES = {
    "C5": (84.5, 2.5, 0, "F"),
    "C8": (94, 10.5, 90, "B"),
    "R38": (81.5, 19.5, 0, "B"),
    "R36": (98, 14, 0, "B"),
    "R46": (97.5, 4.5, 0, "B"),
    "C75": (97.5, 6.75, 0, "B"),
    "R47": (97.5, 9, 0, "B"),
    "R48": (97.5, 11.25, 0, "B"),
    "C72": (106.6, 5.83, 0, "F"),
    "C73": (100.75, 12.9, 0, "F"),
    "D3": (109, 3.4, 0, "F"),
}


def implement(cli):
    pcb = ROOT / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = OUT / f"history/before-local-feedback-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    parts = {c["ref"]: c for c in json.load(open(ROOT / "components.json"))}
    _, pins = netlist(OUT / "netlist.xml")
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    names = {str(v): k for k, v in nets.items()}
    fps = {
        next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
        for fp in children(tree, "footprint")
    }

    def box(fp):
        side = "F" if first(fp, "layer")[1] == "F.Cu" else "B"
        return [v - 100 for v in courtyard(fp, side + ".CrtYd")]

    old = {
        ref: dict(courtyard_mm=box(fps[ref]), side="F" if first(fps[ref], "layer")[1] == "F.Cu" else "B")
        for ref in POSES
    }
    for ref, pose in POSES.items():
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        fp = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            pose,
            footprint_root(str(cli)) / (lib + ".pretty") / (name + ".kicad_mod"),
            nets,
            namespace="rmx:P03:",
        )
        tree[tree.index(fps[ref])] = fp
        fps[ref] = fp
    for ref, pose in POSES.items():
        b = box(fps[ref])
        assert valid_box(b), (ref, "outline")
        assert not any(overlap(b, [x - 3.7, y - 3.7, x + 3.7, y + 3.7], 0.15) for x, y in MOUNTS), (
            ref,
            "metal support",
        )
        if pose[3] == "B":
            assert not any(overlap(b, q, 0.15) for q in THERMAL_REGIONS.values()), (
                ref,
                "bottom thermal contact",
            )
        for other, fp in fps.items():
            if other == ref:
                continue
            through = any(p[2] == "thru_hole" for p in children(fp, "pad")) or other in {
                "J20",
                "J21",
                "J23",
                "J24",
            }
            if first(fp, "layer")[1] != pose[3] + ".Cu" and not through:
                continue
            assert not overlap(b, box(fp), 0.15), (ref, other, "native courtyard")
    removed = []
    areas = [(q["side"], q["courtyard_mm"]) for q in old.values()] + [
        (pose[3], box(fps[ref])) for ref, pose in POSES.items()
    ]
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"segment", "via"}:
            continue
        net = names[str(first(obj, "net")[1])]
        points = (
            [first(obj, "at")[1:3]] if obj[0] == "via" else [first(obj, k)[1:3] for k in ("start", "end")]
        )
        xx = [float(p[0]) - 100 for p in points]
        yy = [float(p[1]) - 100 for p in points]
        b = [min(xx) - 0.15, min(yy) - 0.15, max(xx) + 0.15, max(yy) + 0.15]
        hit = net in {"LO_N_FB", "LO_REF_1V", "LO_N_RMID"} or any(
            (obj[0] == "via" or first(obj, "layer")[1] == side + ".Cu") and overlap(b, q, 0.15)
            for side, q in areas
        )
        if hit:
            tree.remove(obj)
            removed.append(dict(net=net, kind=obj[0]))
    pcb.write_text(sexpr(named(tree)) + "\n")
    report = json.load(open(OUT / "placement.json"))
    for ref, pose in POSES.items():
        report["poses"][ref] = list(pose)
        report["courtyards"][ref] = box(fps[ref])
    (OUT / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "feedback-layout.json").write_text(
        json.dumps(
            dict(
                prior_sha256=digest,
                archive=str(archive.relative_to(ROOT)),
                poses_mm=POSES,
                prior_regions=old,
                removed_copper=removed,
                quiet_inner_layer="In2.Cu",
                direct_ep_via_count_must_remain=12,
                authoring_erratum="Temporary unvalidated development substitution targeted C73; corrected to C72 actual100nF VREF bypass, with C73 restored68pF positive compensation. Native contract and mutation test reject recurrence.",
                physical_and_thermal_qualified=False,
                native_checks_required=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Local feedback placement written; removed copper", len(removed), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    implement(p.parse_args().kicad_cli)
