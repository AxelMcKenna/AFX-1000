"""E25 rail-disconnect placement candidate; no routing or physical approval."""

import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint, project_settings
from ...common.reports import sha
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard, transform
from ...power_supply.place import mount as supply_mount
from ..verify import contract

ROOT = Path(__file__).resolve().parent
SUPPLY = ROOT.parent
OUT = ROOT / "generated"
SIZE = (156, 45.25)
_angle = math.acos(-3 / 4.6)
OUTLINE = (
    (0, 0),
    (156, 0),
    *tuple(
        (
            round(159 + 4.6 * math.cos(-_angle - i * (2 * math.pi - 2 * _angle) / 32), 6),
            round(40.5 + 4.6 * math.sin(-_angle - i * (2 * math.pi - 2 * _angle) / 32), 6),
        )
        for i in range(33)
    ),
    (156, 45.25),
    (5, 45.25),
    (5, 35),
    (0, 35),
)
MOUNTS = ((4, 20), (152, 3.8), (10, 36), (100, 36))
DATUM = (8, 108.5, 4.6)
FIXED = {
    "Q1": (20, 7, 180, "F"),
    "Q2": (29, 7, 0, "F"),
    "Q3": (54, 7, 180, "F"),
    "Q4": (63, 7, 0, "F"),
    "Q5": (79, 7, 180, "F"),
    "Q6": (88, 7, 0, "F"),
    "Q7": (96, 7, 180, "F"),
    "Q8": (105, 7, 0, "F"),
    "Q9": (108, 25, 180, "F"),
    "Q10": (117, 25, 0, "F"),
    "Q11": (127, 7, 180, "F"),
    "Q12": (136, 7, 0, "F"),
    "Q13": (127, 13, 180, "F"),
    "Q14": (136, 13, 0, "F"),
    "U1": (24.5, 13.8, 0, "F"),
    "U2": (58.5, 13.8, 0, "F"),
    "U3": (83.5, 14.5, 0, "F"),
    "U4": (100.5, 14.5, 0, "F"),
    "U5": (112.5, 33.5, 0, "F"),
    "U6": (123.5, 19, 0, "F"),
    "U7": (10, 22, 0, "F"),
    "U8": (43.5, 13, 0, "F"),
    "U9": (43.5, 24.5, 0, "F"),
    "U10": (84, 35.25, 90, "F"),
    "U11": (12.5, 29, 0, "F"),
    "U12": (44, 34.5, 0, "F"),
    "C4": (23.25, 25.5, 0, "F"),
    "C8": (59.25, 25.5, 0, "F"),
    "C12": (81.25, 25.5, 0, "F"),
    "C16": (94.25, 25.5, 0, "F"),
    "C20": (142.5, 15.25, 0, "F"),
    "C24": (142.75, 37, 0, "F"),
    "J1": (4, 2.3, 90, "F"),
    "J2": (119, 3, 0, "F"),
    "J3": (50, 37.5, 90, "F"),
    "J4": (146, 2.5, 0, "F"),
    "J5": (5, 10, 90, "F"),
    "J6": (28, 36.8, 90, "F"),
}


def mount(name="REF**", position=None):
    f = supply_mount(name, position)
    f[1] = "RMX_Disconnect:M2_Clearance"
    return f


def overlap(p, q, gap=0.15):
    return min(p[2], q[2]) - max(p[0], q[0]) > -gap and min(p[3], q[3]) - max(p[1], q[1]) > -gap


def generate(cli):
    libs = footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    for n in ("verification.json", "placement.json"):
        (OUT / n).unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e25-export-") as folder:
        r = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(OUT / "netlist.xml"),
                str(SUPPLY / "rail_disconnect.kicad_sch"),
            ],
            env=dict(os.environ, KICAD_CONFIG_HOME=folder),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (r.stdout, r.stderr)
    parts, pins = netlist(OUT / "netlist.xml")
    contract(parts, pins)
    cs = {c["ref"]: c for c in json.loads((SUPPLY / "components.json").read_text())}
    assert len(cs) == 164 and set(cs) == set(parts)
    nets = {n: i + 1 for i, n in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    board = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal) (3 "In3.Cu" signal) (4 "In4.Cu" power) (31 "B.Cu" signal)
       (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user)
       (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend([a("net"), v, n if n.startswith("unconnected-") else "/" + n] for n, v in nets.items())
    paths = {}
    hashes = {}
    bounds = {}
    for ref, c in cs.items():
        lib, name = c["footprint"].split(":")
        p = libs / (lib + ".pretty") / (name + ".kicad_mod")
        paths[ref] = p
        hashes[c["footprint"]] = sha(p)
        for side in ("F", "B"):
            for angle in (0, 90, 180, 270):
                key = (c["footprint"], side, angle)
                if key not in bounds:
                    f = placed_footprint(
                        dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
                        (0, 0, angle, side),
                        p,
                        nets,
                        origin=(0, 0),
                    )
                    bounds[key] = courtyard(f, side + ".CrtYd")

    def box(ref, pose):
        x, y, angle, side = pose
        b = bounds[(cs[ref]["footprint"], side, angle)]
        return [x + b[0], y + b[1], x + b[2], y + b[3]]

    used = {
        side: [("H" + str(i), [x - 3.7, y - 3.7, x + 3.7, y + 3.7]) for i, (x, y) in enumerate(MOUNTS, 1)]
        for side in ("F", "B")
    }
    poses = dict(FIXED)
    for ref, pose in poses.items():
        b = box(ref, pose)
        assert 0.5 <= b[0] < b[2] <= SIZE[0] - 0.5 and 0.5 <= b[1] < b[3] <= SIZE[1] - (
            0 if ref == "C24" else 0.5
        ), (ref, b)
        assert not any(overlap(b, q) for _, q in used[pose[3]]), (
            ref,
            "fixed courtyard overlap",
            b,
            [n for n, q in used[pose[3]] if overlap(b, q)],
        )
        used[pose[3]].append((ref, b))
        if ref.startswith("J") or ref in ("C4", "C8", "C12", "C16", "C20", "C24"):
            f = placed_footprint(
                dict(cs[ref], value=cs[ref]["part"], mpn=cs[ref]["part"], nets=pins[ref]),
                pose,
                paths[ref],
                nets,
                origin=(0, 0),
            )
            for pad in children(f, "pad"):
                x, y = transform(f, first(pad, "at")[1:3])
                used["B"].append((ref + "_tail", [x - 1.4, y - 1.4, x + 1.4, y + 1.4]))

    def anchor(ref):
        if ref.startswith("C") and int(ref[1:]) <= 24:
            return FIXED["U" + str((int(ref[1:]) - 1) // 4 + 1)][:2]
        if ref.startswith("R") and int(ref[1:]) <= 42:
            return FIXED["U" + str((int(ref[1:]) - 1) // 7 + 1)][:2]
        special = set(pins[ref].values()) - {"AGND", "V2V5_AUX", "PROTECT_REF", "ALL_RAILS_ALLOW"}
        ranked = sorted(((-len(special & set(pins[u].values())), u) for u in FIXED if u.startswith("U")))
        return FIXED[ranked[0][1]][:2]

    for ref in sorted(set(cs) - set(poses), key=lambda n: (n[0], int(n[1:]))):
        side = "B" if ref.startswith("R") else "F"
        ax, ay = anchor(ref)
        candidates = []
        for angle in (0, 90):
            bb = bounds[(cs[ref]["footprint"], side, angle)]
            for ix in range(math.ceil((0.5 - bb[0]) * 2), math.floor((SIZE[0] - 0.5 - bb[2]) * 2) + 1):
                for iy in range(math.ceil((0.5 - bb[1]) * 2), math.floor((SIZE[1] - 0.5 - bb[3]) * 2) + 1):
                    x, y = ix / 2, iy / 2
                    candidates.append(((x - ax) ** 2 + (y - ay) ** 2, angle, x, y))
        for _, angle, x, y in sorted(candidates):
            pose = (x, y, angle, side)
            b = box(ref, pose)
            if (b[0] < 5.25 and b[3] > 34.75) or (b[2] > 153.75 and b[3] > 35.25):
                continue
            if not any(overlap(b, q) for _, q in used[side]):
                poses[ref] = pose
                used[side].append((ref, b))
                break
        else:
            raise RuntimeError(("no legal placement", ref))
    for ref, c in cs.items():
        f = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            poses[ref],
            paths[ref],
            nets,
            namespace="rmx:E25:",
        )
        for pad in children(f, "pad"):
            if children(pad, "net") and str(first(pad, "net")[-1]).startswith("/unconnected-"):
                first(pad, "net")[-1] = str(first(pad, "net")[-1])[1:]
        board.append(f)
    for i, xy in enumerate(MOUNTS, 1):
        board.append(mount("H" + str(i), xy))
    local = ROOT / "RMX_Disconnect.pretty"
    local.mkdir(exist_ok=True)
    (local / "M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    for p, q in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        board.append(
            read_sexpr(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(board) + "\n")
    pro = json.loads((SUPPLY / "rail_disconnect.kicad_pro").read_text())
    settings = project_settings()
    settings["rules"].update(min_clearance=0.2, min_track_width=0.2)
    pro["board"] = {"design_settings": settings}
    pro["net_settings"] = {
        "classes": [
            dict(
                name="Default",
                clearance=0.2,
                track_width=0.25,
                via_diameter=0.6,
                via_drill=0.3,
                bus_width=12,
                line_style=0,
                microvia_diameter=0.3,
                microvia_drill=0.1,
                wire_width=6,
            )
        ]
    }
    (ROOT / "rail_disconnect.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    entries = [
        f'(lib (name "{n}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty") (options "") (descr ""))'
        for n in sorted({c["footprint"].split(":")[0] for c in cs.values()})
    ]
    entries.append(
        '(lib (name "RMX_Disconnect") (type "KiCad") (uri "${KIPRJMOD}/RMX_Disconnect.pretty") (options "") (descr ""))'
    )
    (ROOT / "fp-lib-table").write_text("(fp_lib_table\n" + "\n".join(entries) + "\n)\n")
    (OUT / "inputs.json").write_text(
        json.dumps(
            dict(
                revision="E25",
                source_schematic_sha256=sha(SUPPLY / "rail_disconnect.kicad_sch"),
                components_sha256=sha(SUPPLY / "components.json"),
                poses=poses,
                footprint_library_sha256=hashes,
                board_size_mm=[156, 45.25, 1.6],
                outline_relative_mm=OUTLINE,
                mounts_relative_mm=MOUNTS,
                housing_datum_proposal_mm=DATUM,
                pcb_routed=False,
                physical_fit_verified=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E25: 164 parts placed on 156x45.25mm relieved candidate; no copper, no fabrication or fit claim.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", required=True, type=Path)
    generate(p.parse_args().kicad_cli.resolve())
