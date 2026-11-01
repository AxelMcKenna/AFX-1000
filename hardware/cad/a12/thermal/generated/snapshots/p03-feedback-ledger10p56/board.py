"""P03 native placement and retained bipolar copper, with explicit source binding.

New nets still require routed copper and native checks; a placed board is never
reported as a completed routing or physical validation result.
"""

import argparse
import copy
import json
import math
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint, project_settings
from ...common.reports import sha
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard, transform
from ...power_supply.place import mount, overlap
from .spec import MOUNTS, OUTLINE, REPO, ROOT, SIZE, THERMAL_REGIONS

BASE = REPO / "hardware/electronics/power_supply/routing/power_supply.kicad_pcb"
OUT = ROOT / "generated"
FIXED = {
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
    "U101": (25.75, 12.5, 0, "F"),
    "Q101": (10, 13, 0, "F"),
    "Q102": (10, 20, 0, "F"),
    "U102": (26.25, 20, 0, "F"),
    "U103": (16, 22, 0, "F"),
    "Q103": (25.25, 26, 0, "F"),
    "F101": (9, 7, 0, "F"),
    "C103": (22, 5, 0, "F"),
    "J101": (130, 16, 180, "F"),
    "J103": (8, 28, 0, "F"),
    "J104": (7, 33, 90, "F"),
    "J106": (19, 24, 90, "F"),
    "R109": (31.5, 20, 0, "F"),
    "J20": (10, 28, 0, "F"),
    "J21": (10, 14, 0, "F"),
    "J23": (38, 5.5, 0, "F"),
    "J24": (36, 31, 0, "F"),
    "J22": (45, 38, 0, "F"),
    "J2": (27, 4, 90, "F"),
    "J3": (48, 4, 90, "F"),
    "U20": (47, 13, 0, "F"),
    "L20": (55, 13, 0, "F"),
    "U23": (135, 28, 0, "F"),
    "L23": (144, 28, 0, "F"),
    "U21": (45, 27, 0, "F"),
    "U22": (56, 36, 0, "F"),
    "U24": (62, 40, 0, "F"),
    "C32": (90.5, 34, 0, "F"),
    "C33": (71.3, 7.2, 90, "F"),
    "U25": (146, 10, 0, "B"),
    "U26": (153, 10, 0, "B"),
    "U6": (135, 8, 0, "B"),
    "U11": (123, 27, 0, "F"),
    "U8": (108, 31.5, 0, "F"),
    "C202": (48, 15.5, 0, "F"),
    "C203": (48, 10.5, 0, "F"),
    "C201": (46.3, 8.7, 0, "F"),
    "C200": (45, 16.5, 180, "F"),
    "C222": (136, 30.5, 0, "F"),
    "C223": (136, 25.5, 0, "F"),
    "C221": (134.3, 23.7, 0, "F"),
    "C220": (133, 32, 180, "F"),
}


def valid_box(b):
    if not (0.5 <= b[0] < b[2] <= SIZE[0] - 0.5 and 0.5 <= b[1] < b[3] <= SIZE[1] - 0.5):
        return False
    return not (b[3] > 34.5 and (b[0] < 6.5 or b[2] > 151.5))


def build(cli):
    old = read_sexpr(BASE.read_text())
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    _, pins = netlist(OUT / "netlist.xml")
    nets = {n: i + 1 for i, n in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    library = footprint_root(str(cli))
    tree = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew)
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal)
       (3 "In3.Cu" signal) (4 "In4.Cu" power) (31 "B.Cu" signal)
       (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
       (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
       (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    tree.extend([a("net"), code, n if n.startswith("unconnected-") else "/" + n] for n, code in nets.items())
    stack = """(stackup
      (layer "F.Cu" (type "copper") (thickness .085))
      (layer "dielectric 1" (type "prepreg") (thickness .10) (material "FR4 Tg>=170C") (epsilon_r 4.2) (loss_tangent .02))
      (layer "In1.Cu" (type "copper") (thickness .07))
      (layer "dielectric 2" (type "core") (thickness .34) (material "FR4 Tg>=170C") (epsilon_r 4.2) (loss_tangent .02))
      (layer "In2.Cu" (type "copper") (thickness .07))
      (layer "dielectric 3" (type "prepreg") (thickness .27) (material "FR4 Tg>=170C") (epsilon_r 4.2) (loss_tangent .02))
      (layer "In3.Cu" (type "copper") (thickness .07))
      (layer "dielectric 4" (type "core") (thickness .34) (material "FR4 Tg>=170C") (epsilon_r 4.2) (loss_tangent .02))
      (layer "In4.Cu" (type "copper") (thickness .07))
      (layer "dielectric 5" (type "prepreg") (thickness .10) (material "FR4 Tg>=170C") (epsilon_r 4.2) (loss_tangent .02))
      (layer "B.Cu" (type "copper") (thickness .085)) (copper_finish "ENIG") (dielectric_constraints yes))"""
    first(tree, "setup").append(read_sexpr(stack))
    paths, bounds, hashes = {}, {}, {}
    through = set()
    for ref, c in parts.items():
        lib, name = c["footprint"].split(":")
        paths[ref] = (ROOT if lib.startswith("RMX_") else library) / (lib + ".pretty") / (name + ".kicad_mod")
        if not paths[ref].exists():
            raise FileNotFoundError((ref, paths[ref]))
        hashes[c["footprint"]] = sha(paths[ref])
        if any(p[2] == "thru_hole" for p in children(read_sexpr(paths[ref].read_text()), "pad")):
            through.add(ref)
        for side in ("F", "B"):
            for angle in (0, 90, 180, 270):
                fp = placed_footprint(
                    dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
                    (0, 0, angle, side),
                    paths[ref],
                    nets,
                    origin=(0, 0),
                )
                bounds[ref, side, angle] = courtyard(fp, side + ".CrtYd")

    used = {
        s: [(f"H{i}", [x - 3.7, y - 3.7, x + 3.7, y + 3.7]) for i, (x, y) in enumerate(MOUNTS)]
        for s in ("F", "B")
    }
    used["B"].extend((ref + "_thermal_contact", b) for ref, b in THERMAL_REGIONS.items())
    poses, collisions = {}, []
    original_anchors = {}
    for ref in ("J20", "J21", "J23", "J24", "J101", "U8", "U11"):
        poses[ref] = FIXED[ref]
        for side in ("F", "B") if ref.startswith("J") else (FIXED[ref][3],):
            b = bounds[ref, "F", FIXED[ref][2]]
            x, y = FIXED[ref][:2]
            used[side].append((ref, [b[0] + x, b[1] + y, b[2] + x, b[3] + y]))

    def box(ref, pose):
        x, y, angle, side = pose
        b = bounds[ref, side, angle]
        return [b[0] + x, b[1] + y, b[2] + x, b[3] + y]

    # Preserve the already routed bipolar placement rigidly. Existing selected
    # packages are rebuilt from the exact native pin map, without other stages.
    for fp in children(old, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref not in parts or ref in FIXED:
            continue
        at = first(fp, "at")
        pose = (
            float(at[1]) - 35,
            float(at[2]) - 100,
            int(float(at[3])) if len(at) > 3 else 0,
            "F" if first(fp, "layer")[1] == "F.Cu" else "B",
        )
        b = box(ref, pose)
        if (ref in through and pose[3] == "B") or any(
            overlap(b, q, 0.15)
            for side in (("F", "B") if ref in through else (pose[3],))
            for _, q in used[side]
        ):
            original_anchors[ref] = pose
        else:
            poses[ref] = pose
            used[pose[3]].append((ref, b))
            if ref in through:
                used["B" if pose[3] == "F" else "F"].append((ref, b))
    # Permit adapting new stages to actual courtyards; store every actual pose.
    # Stud/mount access is reserved on BOTH faces, not just in the component list.
    anchors = {**original_anchors, **FIXED}
    pending = sorted(
        set(parts) - set(poses),
        key=lambda ref: (
            ref not in {"J20", "J21", "J23", "J24", "J101"},
            ref not in FIXED,
            -(
                (bounds[ref, "F", 0][2] - bounds[ref, "F", 0][0])
                * (bounds[ref, "F", 0][3] - bounds[ref, "F", 0][1])
            ),
            ref,
        ),
    )
    for ref in pending:
        target = anchors.get(ref)
        if target is None:
            n = int(ref[1:])
            anchor = (
                "U101" if n < 200 else "U20" if n < 220 else "U23" if n < 240 else "U24" if n < 300 else "U25"
            )
            target = anchors[anchor]
        choices = []
        sides = ("F",) if ref in through else (target[3],) if ref in FIXED else ("F", "B")
        for side in sides:
            for angle in (target[2],) if ref in FIXED else (0, 90):
                for dx in (0,) if ref in {"J20", "J21", "J23", "J24", "J101"} else range(-24, 25):
                    for dy in (0,) if ref in {"J20", "J21", "J23", "J24", "J101"} else range(-24, 25):
                        x, y = target[0] + dx / 2, target[1] + dy / 2
                        pose = (x, y, angle, side)
                        b = box(ref, pose)
                        if valid_box(b) and not any(
                            overlap(b, q, 0.15)
                            for face in (("F", "B") if ref in through else (side,))
                            for _, q in used[face]
                        ):
                            # Prefer bottom small passives; tall items are fixed top.
                            score = (
                                dx * dx + dy * dy + (4 if side == "F" and ref.startswith(("R", "C")) else 0)
                            )
                            choices.append((score, pose))
        if not choices:
            raise RuntimeError(f"No legal native courtyard placement: {ref}, anchor{target}")
        pose = min(choices)[1]
        poses[ref] = pose
        anchors[ref] = pose
        used[pose[3]].append((ref, box(ref, pose)))
        if ref in through:
            used["B" if pose[3] == "F" else "F"].append((ref, box(ref, pose)))
    for side, objects in used.items():
        for i, (ref, b) in enumerate(objects):
            if ref.endswith("_thermal_contact"):
                continue
            if not valid_box(b) and not ref.startswith("H"):
                collisions.append([ref, "outside_notched_outline", b])
            for other, q in objects[:i]:
                if other.endswith("_thermal_contact"):
                    continue
                if overlap(b, q, 0) and ref != other:
                    collisions.append([ref, other, side])
    for ref, c in parts.items():
        fp = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            poses[ref],
            paths[ref],
            nets,
            namespace="rmx:P03:",
        )
        for p in children(fp, "pad"):
            if children(p, "net") and str(first(p, "net")[-1]).startswith("/unconnected-"):
                first(p, "net")[-1] = str(first(p, "net")[-1])[1:]
        tree.append(fp)
    for i, xy in enumerate(MOUNTS, 1):
        fp = mount(f"H{i}", xy)
        fp[1] = "RMX_P03:M2_Clearance"
        tree.append(fp)
    for p, q in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        tree.append(
            read_sexpr(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    for x, y in MOUNTS:
        pts = " ".join(
            f"(xy {100 + x + 3.7 * math.cos(i * math.pi / 16):.6f} {100 + y + 3.7 * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        tree.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu" "B.Cu")
            (hatch edge .5) (connect_pads (clearance .16)) (min_thickness .15)
            (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
            (polygon (pts {pts})))""")
        )
    # Existing native copper is translated rigidly; new5Vnets are routed fresh.
    oldnets = {int(n[1]): str(n[2]).lstrip("/") for n in children(old, "net")}
    retained = 0
    pad_obstacles = []
    for fp in children(tree, "footprint"):
        for pad in children(fp, "pad"):
            if not children(pad, "size") or not children(pad, "net"):
                continue
            layers = first(pad, "layers")[1:]
            if not any(str(l).endswith("Cu") for l in layers):
                continue
            xy = transform(fp, first(pad, "at")[1:3])
            size = list(map(float, first(pad, "size")[1:3]))
            angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
            if int(angle) % 180:
                size.reverse()
            pad_obstacles.append((xy, size, int(first(pad, "net")[1]), layers))
    removed_copper = []
    for kind in ("segment", "via"):
        for obj in children(old, kind):
            name = oldnets[int(first(obj, "net")[1])]
            if name not in nets or name.startswith("unconnected-") or name in {"5V_DIG_SRC", "V5_REG_SRC"}:
                continue
            item = copy.deepcopy(obj)
            first(item, "net")[1] = a(nets[name])
            for tag in ("start", "end", "at"):
                for xy in children(item, tag):
                    xy[1] = a(float(xy[1]) + 65)
            if kind == "segment":
                start = list(map(float, first(item, "start")[1:3]))
                end = list(map(float, first(item, "end")[1:3]))
                radius = float(first(item, "width")[1]) / 2 + 0.16
                layer = first(item, "layer")[1]
                b = [
                    min(start[0], end[0]) - radius,
                    min(start[1], end[1]) - radius,
                    max(start[0], end[0]) + radius,
                    max(start[1], end[1]) + radius,
                ]
            else:
                xy = list(map(float, first(item, "at")[1:3]))
                radius = float(first(item, "size")[1]) / 2 + 0.26
                b = [xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius]
                layer = None
            hit = False
            for x, y in MOUNTS:
                q = [100 + x - 3.75, 100 + y - 3.75, 100 + x + 3.75, 100 + y + 3.75]
                if overlap(b, q, 0):
                    hit = True
                    break
            for xy, size, net, layers in pad_obstacles:
                if net == nets[name] or (layer and layer not in layers and "*.Cu" not in layers):
                    continue
                q = [xy[0] - size[0] / 2, xy[1] - size[1] / 2, xy[0] + size[0] / 2, xy[1] + size[1] / 2]
                if overlap(b, q, 0):
                    hit = True
                    break
            if hit:
                removed_copper.append(dict(kind=kind, net=name, bounds=b))
                continue
            tree.append(item)
            retained += 1
    # The minimum manufactured metal is a construction requirement; this
    # stackup is a concrete candidate awaiting fabricator acceptance/measurement.
    for layer in ("In1.Cu", "In4.Cu"):
        points = " ".join(f"(xy {100 + x} {100 + y})" for x, y in OUTLINE)
        tree.append(
            read_sexpr(f'''(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "{layer}")
          (hatch edge .5) (connect_pads yes (clearance .25)) (min_thickness .2)
          (fill yes (thermal_gap .3) (thermal_bridge_width .5)) (polygon (pts {points})))''')
        )
    (ROOT / "power_p03.kicad_pcb").write_text(sexpr(tree) + "\n")
    settings = project_settings()
    settings["rules"].update(
        min_clearance=0.15, min_track_width=0.16, min_through_hole_diameter=0.25, min_via_annular_width=0.16
    )
    (ROOT / "power_p03.kicad_pro").write_text(
        json.dumps(
            {
                "meta": {"filename": "power_p03.kicad_pro", "version": 1},
                "board": {"design_settings": settings},
            },
            indent=2,
        )
        + "\n"
    )
    (ROOT / "power_p03.kicad_dru").write_text(
        "(version 1)\n(rule \"default copper\" (constraint clearance (min 0.16mm)))\n(rule \"TI RPY manufacturer internal pad spacing\"\n (condition \"A.Type == 'Pad' && B.Type == 'Pad' && ((A.memberOfFootprint('U20') && B.memberOfFootprint('U20')) || (A.memberOfFootprint('U23') && B.memberOfFootprint('U23')))\")\n (constraint clearance (min 0.15mm)))\n"
    )
    from .construction import write_contract

    write_contract()
    (OUT / "placement.json").write_text(
        json.dumps(
            dict(
                revision="P03",
                board_size_mm=[*SIZE, 1.6],
                outline_mm=OUTLINE,
                mounts_mm=MOUNTS,
                poses=poses,
                courtyards={r: box(r, p) for r, p in poses.items()},
                footprint_source_sha256=hashes,
                retained_copper_objects=retained,
                original_bipolar_pcb_sha256=sha(BASE),
                physical_courtyard_collisions=collisions,
                bottom_thermal_contact_keepouts_mm=THERMAL_REGIONS,
                old_copper_removed_for_changed_pad_clearance=removed_copper,
                native_pcb_sha256=sha(ROOT / "power_p03.kicad_pcb"),
                bottom_assembled_height_limit_mm=3.0,
                stackup_manufacturer_accepted=False,
                all_new_copper_routed=False,
                physical_tests_performed=0,
                fabrication_released=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"P03 native PCB {len(parts)}parts,{len(collisions)}courtyard issues,{retained}retained copper objects; new routing pending",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    args = parser.parse_args()
    build(args.kicad_cli)


if __name__ == "__main__":
    main()
