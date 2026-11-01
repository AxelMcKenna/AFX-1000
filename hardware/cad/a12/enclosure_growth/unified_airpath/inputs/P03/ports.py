"""Apply the final power-stud interfaces without discarding completed copper.

Conflicting components are physically moved and all copper at the new drilled
terminals is removed. Native ERC/parity/DRC/routing must then be repeated.
"""

import json

from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint
from ...common.reports import sha
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ...power_supply.place import overlap
from .board import valid_box
from .route import coded, named
from .spec import MOUNTS, ROOT, THERMAL_REGIONS

OUT = ROOT / "generated"
PORTS = {"J23": (38, 5.5), "J24": (36, 31)}
POSE_ADJUSTMENTS = {
    "C200": (44.25, 16.5, 180, "F"),
    "C201": (45, 9.4, 90, "F"),
    "C202": (48, 17.2, 0, "F"),
    "C203": (48, 8.8, 0, "F"),
    "C210": (47.75, 15.4, 0, "F"),
    "C211": (47.75, 10.6, 0, "F"),
    "C220": (132, 32.25, 180, "F"),
    "C221": (133.2, 23.5, 90, "F"),
    "C222": (136, 32.1, 0, "F"),
    "C223": (136, 23.8, 0, "F"),
    "C230": (135.75, 30.4, 0, "F"),
    "C231": (135.75, 25.6, 0, "F"),
    "R221": (139.6, 33.5, 0, "F"),
    "U26": (153, 10, 0, "B"),
    "C301": (153.5, 12.65, 180, "B"),
    "C302": (149.4, 14.25, 180, "B"),
    "R316": (151.5, 16.5, 0, "B"),
    "C70": (97.25, 18.55, 0, "B"),
    "R34": (95.9, 29, 90, "B"),
    "D4": (110.5, 12, 0, "F"),
    "C63": (116, 11.6, 270, "F"),
    "C71": (112.3, 7.5, 90, "F"),
    "C67": (120.9, 18, 90, "B"),
    "R46": (97.5, 4.5, 0, "B"),
    "R47": (97.5, 9, 0, "B"),
    "R48": (97.5, 11.25, 0, "B"),
    "C75": (97.5, 6.75, 0, "B"),
    "C72": (106.6, 5.83, 0, "F"),
    "C73": (100.75, 12.9, 0, "F"),
    "D3": (109, 3.4, 0, "F"),
    "C5": (84.5, 2.5, 0, "F"),
    "C8": (94, 10.5, 90, "B"),
    "R38": (81.5, 19.5, 0, "B"),
    "R36": (98, 14, 0, "B"),
}
ADJUSTMENTS = {
    "J106": (19, 24),
    "U101": (25.75, 12.5),
    "U102": (26.25, 20),
    "Q103": (25.25, 26),
    "R109": (31.5, 20),
}


def update(cli):
    pcb = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    _, pins = netlist(OUT / "netlist.xml")
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    footprints = {
        next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
        for fp in children(tree, "footprint")
    }
    moved = {}
    changed_ports = set()
    for ref, pose in POSE_ADJUSTMENTS.items():
        fp = footprints[ref]
        oldat = list(first(fp, "at")[1:])
        oldface = "F" if first(fp, "layer")[1] == "F.Cu" else "B"
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        converted = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            pose,
            footprint_root(str(cli)) / (lib + ".pretty") / (name + ".kicad_mod"),
            nets,
            namespace="rmx:P03:",
        )
        tree[tree.index(fp)] = converted
        footprints[ref] = converted
        moved[ref] = dict(before_pose=oldat + [oldface], after_pose=list(pose))
    for ref, xy in ADJUSTMENTS.items():
        at = first(footprints[ref], "at")
        before = [float(v) - 100 for v in at[1:3]]
        if any(abs(a - b) > 1e-6 for a, b in zip(before, xy)):
            at[1:3] = [a(100 + xy[0]), a(100 + xy[1])]
            moved[ref] = dict(before_mm=before, after_mm=list(xy))

    def box(fp):
        side = "F" if first(fp, "layer")[1] == "F.Cu" else "B"
        return [v - 100 for v in courtyard(fp, side + ".CrtYd")]

    for ref, fp in list(footprints.items()):
        if ref not in parts or fp[1] == parts[ref]["footprint"]:
            continue
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        if not lib.startswith("RMX_"):
            raise ValueError("Only explicitly local footprint replacement supported")
        at = first(fp, "at")
        pose = (
            float(at[1]) - 100,
            float(at[2]) - 100,
            float(at[3]) if len(at) > 3 else 0,
            "F" if first(fp, "layer")[1] == "F.Cu" else "B",
        )
        replacement = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            pose,
            ROOT / (lib + ".pretty") / (name + ".kicad_mod"),
            nets,
            namespace="rmx:P03:",
        )
        tree[tree.index(fp)] = replacement
        footprints[ref] = replacement
    # Newly generated values/pin metadata stay in parity with the real native
    # circuit. New ports use exactly the same footprint as quiet-ground studs.
    for ref, fp in footprints.items():
        if ref not in parts:
            continue
        for prop in children(fp, "property"):
            if prop[1] in {"Value", "MPN"}:
                prop[2] = parts[ref]["part"]
            if prop[1] == "Datasheet":
                prop[2] = parts[ref].get("source", "")
    for ref, xy in PORTS.items():
        if ref in footprints:
            if any(
                abs(float(v) - 100 - target) > 1e-6
                for v, target in zip(first(footprints[ref], "at")[1:3], xy)
            ):
                changed_ports.add(ref)
            first(footprints[ref], "at")[1:3] = [a(100 + xy[0]), a(100 + xy[1])]
            continue
        changed_ports.add(ref)
        c = parts[ref]
        fp = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            (*xy, 0, "F"),
            ROOT / "RMX_P03.pretty/Wurth_7466003R.kicad_mod",
            nets,
            namespace="rmx:P03:",
        )
        tree.append(fp)
        footprints[ref] = fp
    portboxes = {
        ref: [xy[0] - 5, xy[1] - 5, xy[0] + 5, xy[1] + 5] for ref, xy in PORTS.items() if ref in changed_ports
    }
    faces = {ref: ("F" if first(fp, "layer")[1] == "F.Cu" else "B") for ref, fp in footprints.items()}
    through = {ref for ref, fp in footprints.items() if any(p[2] == "thru_hole" for p in children(fp, "pad"))}
    both = {"J20", "J21", *PORTS, *through}
    locked = {*PORTS, *ADJUSTMENTS, *POSE_ADJUSTMENTS, "J20", "J21"}
    conflicting = {
        ref
        for ref, fp in footprints.items()
        if ref not in locked
        and not ref.startswith("H")
        and (
            any(
                (faces[ref] == faces[r] or r in both or ref in through)
                and overlap(box(fp), box(footprints[r]), 0.15)
                for r in locked
            )
            or faces[ref] == "B"
            and any(overlap(box(fp), b, 0.15) for b in THERMAL_REGIONS.values())
        )
    }
    fixed = {
        ref: box(fp) for ref, fp in footprints.items() if ref not in conflicting and not ref.startswith("H")
    }
    for ref in sorted(
        conflicting,
        key=lambda r: (
            -(box(footprints[r])[2] - box(footprints[r])[0]) * (box(footprints[r])[3] - box(footprints[r])[1])
        ),
    ):
        fp = footprints[ref]
        old = box(fp)
        side = faces[ref]
        choices = []
        for dx in range(-60, 61):
            for dy in range(-50, 51):
                b = [old[0] + dx * 0.5, old[1] + dy * 0.5, old[2] + dx * 0.5, old[3] + dy * 0.5]
                if not valid_box(b):
                    continue
                if any(overlap(b, [x - 3.7, y - 3.7, x + 3.7, y + 3.7], 0.15) for x, y in MOUNTS):
                    continue
                if side == "B" and any(overlap(b, q, 0.15) for q in THERMAL_REGIONS.values()):
                    continue
                if any(
                    (side == faces[r] or r in both or ref in through) and overlap(b, q, 0.15)
                    for r, q in fixed.items()
                ):
                    continue
                choices.append((dx * dx + dy * dy, dx, dy, b))
        if not choices:
            raise ValueError(f"No legal physical relocation for final stud: {ref}")
        _, dx, dy, b = min(choices)
        at = first(fp, "at")
        before = list(map(float, at[1:3]))
        at[1] = a(float(at[1]) + dx * 0.5)
        at[2] = a(float(at[2]) + dy * 0.5)
        fixed[ref] = b
        moved[ref] = dict(before_mm=[v - 100 for v in before], after_mm=[float(v) - 100 for v in at[1:3]])
    removed = 0
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"via", "segment"}:
            continue
        pts = (
            [first(obj, "at")[1:3]] if obj[0] == "via" else [first(obj, "start")[1:3], first(obj, "end")[1:3]]
        )
        xs = [float(p[0]) - 100 for p in pts]
        ys = [float(p[1]) - 100 for p in pts]
        bb = [min(xs) - 0.6, min(ys) - 0.6, max(xs) + 0.6, max(ys) + 0.6]
        if any(overlap(bb, b, 0.25) for b in portboxes.values()):
            tree.remove(obj)
            removed += 1
    pcb.write_text(sexpr(named(tree)) + "\n")
    report = json.loads((OUT / "placement.json").read_text())
    report["final_power_ports_mm"] = PORTS
    report["power_port_relocations"] = moved
    for ref, fp in footprints.items():
        if ref.startswith("H"):
            continue
        at = first(fp, "at")
        report["poses"][ref] = [
            float(at[1]) - 100,
            float(at[2]) - 100,
            float(at[3]) if len(at) > 3 else 0,
            faces[ref],
        ]
        report["courtyards"][ref] = box(fp)
    collisions = []
    for ref, b in report["courtyards"].items():
        if not valid_box(b):
            collisions.append([ref, "outline", b])
        for other, q in report["courtyards"].items():
            if ref >= other:
                continue
            if faces[ref] == faces[other] or ref in both or other in both:
                if overlap(b, q, 0):
                    collisions.append([ref, other])
        for x, y in MOUNTS:
            if overlap(b, [x - 3.7, y - 3.7, x + 3.7, y + 3.7], 0):
                collisions.append([ref, "mount", x, y])
    report["physical_courtyard_collisions"] = collisions
    report["native_pcb_sha256"] = sha(pcb)
    (OUT / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Final positive power studs added; moved {moved}; removed {removed} old copper objects. Native routing/parity pending."
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    update(parser.parse_args().kicad_cli)
