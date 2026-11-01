#!/usr/bin/env python3
"""E24 main-supply placement candidate; routing, thermal/EMI and fit remain open."""

import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ..common.netlists import netlist
from ..common.placement import footprint_root, placed_footprint, project_settings
from ..common.reports import sha
from ..common.sexpr import a, children, first, read_sexpr, sexpr
from ..output_stage.check_placement import courtyard

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SIZE = (84, 38)
MOUNTS = [(4, 4), (74, 4), (4, 34), (74, 34)]
FIXED = {
    "L1": (6.5, 11.85, 0, "F"),
    "L2": (7.5, 23, 0, "F"),
    "L3": (20.5, 23, 0, "F"),
    "L6": (36.5, 7, 0, "F"),
    "L7": (35, 19.5, 0, "F"),
    "L8": (48.5, 19.5, 0, "F"),
    "L4": (69, 13.5, 0, "F"),
    "L5": (62.5, 31, 0, "F"),
    "U1": (21, 10.3, 0, "F"),
    "U13": (49, 7.5, 0, "F"),
    "U2": (58, 13.5, 0, "F"),
    "U3": (71, 23, 0, "F"),
    "U4": (18, 25, 0, "B"),
    "U5": (20, 33.1, 0, "F"),
    "U6": (43, 14, 0, "B"),
    "U7": (12.5, 32, 0, "F"),
    "U8": (43, 32, 0, "F"),
    "U9": (65, 33, 0, "B"),
    "U10": (27.5, 28.5, 0, "B"),
    "U11": (57.5, 17, 0, "F"),
    "U12": (12, 18, 0, "B"),
    "D1": (23, 6.65, 0, "F"),
    "D2": (23, 15, 0, "F"),
    "D3": (44, 4.5, 90, "F"),
    "D4": (49, 12, 0, "F"),
    "J1": (55, 3, 90, "F"),
    "J2": (9.6, 3, 90, "F"),
    "J3": (76, 21.2, 0, "F"),
    "J4": (79.6, 28, 0, "F"),
    "J5": (64, 3, 90, "F"),
    "C32": (25.5, 34, 0, "F"),
    "C33": (15, 13.2, 90, "F"),
    "C1": (25.5, 10.83, 90, "F"),
    "C63": (54.3, 10.5, 90, "F"),
    "C20": (58, 8.5, 90, "F"),
    "C22": (61, 11, 90, "F"),
    "C16": (60.75, 14.5, 90, "F"),
    "C27": (66, 21.3, 90, "F"),
    "C29": (69.5, 20.4, 0, "F"),
    "C23": (72, 26.1, 90, "F"),
}


def overlap(p, q, gap=0.1):
    return min(p[2], q[2]) - max(p[0], q[0]) > -gap and min(p[3], q[3]) - max(p[1], q[1]) > -gap


def mount(name="REF**", position=None):
    at = f"(at {100 + position[0]} {100 + position[1]})" if position else ""
    return read_sexpr(f'''(footprint "RMX_Power:M2_Clearance" (layer "F.Cu") {at}
      (attr board_only exclude_from_bom exclude_from_pos_files)
      (property "Reference" "{name}" (at 0 -4) (layer "F.Fab") (effects (font (size .8 .8))))
      (property "Value" "M2_CLEARANCE" (at 0 4) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      (fp_circle (center 0 0) (end 2.8 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center 0 0) (end 3.7 0) (stroke (width .05) (type solid)) (fill none) (layer "B.CrtYd"))
      (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))''')


def anchor(ref):
    n = int(ref[1:])
    groups = (
        [
            (15, "U1"),
            (22, "U2"),
            (29, "U3"),
            (32, "U4"),
            (33, "U12"),
            (38, "U7"),
            (43, "U8"),
            (48, "U9"),
            (53, "U10"),
            (58, "U11"),
            (60, "U5"),
            (62, "U6"),
            (76, "U13"),
        ]
        if ref[0] == "C"
        else [
            (7, "U1"),
            (11, "U2"),
            (16, "U3"),
            (17, "U4"),
            (19, "U12"),
            (24, "U7"),
            (29, "U8"),
            (33, "U9"),
            (38, "U10"),
            (43, "U11"),
            (50, "U13"),
            (51, "U2"),
        ]
    )
    return FIXED[next(name for end, name in groups if n <= end)][:2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    args = parser.parse_args()
    cli = args.kicad_cli.resolve()
    libraries = footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    for name in ("placement-verification.json", "routing-verification.json"):
        (OUT / name).unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e24-place-") as folder:
        result = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(OUT / "placement-netlist.xml"),
                str(ROOT / "power_supply.kicad_sch"),
            ],
            env=dict(
                os.environ,
                KICAD_CONFIG_HOME=folder,
                KICAD10_FOOTPRINT_DIR=str(libraries),
                FONTCONFIG_FILE=str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf"),
            ),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
    parts, pins = netlist(OUT / "placement-netlist.xml")
    components = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    assert len(parts) == 157 and set(parts) == set(components) and set(FIXED) <= set(parts)
    nets = {net: i + 1 for i, net in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    board = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal) (3 "In3.Cu" signal) (4 "In4.Cu" power) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend(
        [a("net"), code, net if net.startswith("unconnected-") else "/" + net] for net, code in nets.items()
    )
    hashes, paths, bounds = {}, {}, {}
    for ref, c in components.items():
        lib, name = c["footprint"].split(":")
        path = (ROOT if lib == "RMX_Power" else libraries) / (lib + ".pretty") / (name + ".kicad_mod")
        paths[ref] = path
        hashes[c["footprint"]] = sha(path)
        for side in ("F", "B"):
            for angle in (0, 90):
                p = placed_footprint(
                    dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
                    (0, 0, angle, side),
                    path,
                    nets,
                    origin=(0, 0),
                )
                bounds[(ref, side, angle)] = courtyard(p, side + ".CrtYd")
    used = {
        side: [(f"H{i}", [x - 3.7, y - 3.7, x + 3.7, y + 3.7]) for i, (x, y) in enumerate(MOUNTS, 1)]
        for side in ("F", "B")
    }

    def box(ref, pose):
        x, y, angle, side = pose
        b = bounds[(ref, side, angle)]
        return [b[0] + x, b[1] + y, b[2] + x, b[3] + y]

    poses = dict(FIXED)
    for ref, pose in FIXED.items():
        b = box(ref, pose)
        side = pose[3]
        assert 0 <= b[0] < b[2] <= 84 and 0 <= b[1] < b[3] <= 38, (ref, b)
        conflicts = [r for r, q in used[side] if overlap(b, q)]
        assert not conflicts, (ref, conflicts, b)
        used[side].append((ref, b))
    for ref in ("J1", "J2", "J3", "J4", "J5", "C32", "C33"):
        used["B"].append((ref + "_lead_reserve", box(ref, poses[ref])))
    thermal = []
    for ref in ("U1", "U2", "U3", "U7", "U8", "U11", "U13"):
        x, y, _, _ = FIXED[ref]
        if ref == "U8":
            x += 1  # Center the allocation on the large output tab.
            y -= 1  # Keep the full24x14 thermal allocation inside the PCB.
        w, h = (24, 14) if ref == "U8" else (8, 6) if ref == "U7" else (6, 6)
        b = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]
        conflicts = [r for r, q in used["B"] if (r in FIXED or r.endswith("_lead_reserve")) and overlap(b, q)]
        assert not conflicts, (ref, "thermal reserve", conflicts)
        thermal.append([ref, *b])
        used["B"].append((ref + "_thermal_via_reserve", b))
    pending = sorted(
        set(parts) - set(poses),
        key=lambda ref: (
            -(bounds[(ref, "B", 0)][2] - bounds[(ref, "B", 0)][0])
            * (bounds[(ref, "B", 0)][3] - bounds[(ref, "B", 0)][1]),
            ref,
        ),
    )
    for ref in pending:
        assert ref[0] in "RC"
        target = anchor(ref)
        candidates = []
        for angle in (0, 90):
            b = bounds[(ref, "B", angle)]
            for ix in range(math.ceil((0.5 - b[0]) * 2), math.floor((83.5 - b[2]) * 2) + 1):
                for iy in range(math.ceil((0.5 - b[1]) * 2), math.floor((37.5 - b[3]) * 2) + 1):
                    x, y = ix / 2, iy / 2
                    score = (x - target[0]) ** 2 + (y - target[1]) ** 2
                    candidates.append((score, angle, x, y))
        for _, angle, x, y in sorted(candidates):
            pose = (x, y, angle, "B")
            b = box(ref, pose)
            if not any(overlap(b, q) for _, q in used["B"]):
                poses[ref] = pose
                used["B"].append((ref, b))
                break
        else:
            raise RuntimeError(f"No legal bottom placement for {ref}")
    for ref in components:
        c = components[ref]
        fp = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pins[ref]),
            poses[ref],
            paths[ref],
            nets,
            namespace="rmx:E24:",
        )
        for pad in children(fp, "pad"):
            if children(pad, "net") and str(first(pad, "net")[-1]).startswith("/unconnected-"):
                first(pad, "net")[-1] = str(first(pad, "net")[-1])[1:]
        board.append(fp)
    for i, xy in enumerate(MOUNTS, 1):
        board.append(mount(f"H{i}", xy))
    (ROOT / "RMX_Power.pretty/M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    for p, q in [((0, 0), (84, 0)), ((84, 0), (84, 38)), ((84, 38), (0, 38)), ((0, 38), (0, 0))]:
        board.append(
            read_sexpr(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    (ROOT / "power_supply.kicad_pcb").write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    pro = json.loads((ROOT / "power_supply.kicad_pro").read_text())
    settings = project_settings()
    settings["rules"].update(min_clearance=0.15, min_track_width=0.15)
    pro["board"] = {"design_settings": settings}
    pro["net_settings"] = {
        "classes": [
            dict(
                name="Default",
                clearance=0.15,
                track_width=0.15,
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
    (ROOT / "power_supply.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    (OUT / "placement-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E24",
                board_size_mm=[*SIZE, 1.6],
                copper_layers=6,
                mounts_relative_mm=MOUNTS,
                poses=poses,
                footprint_library_sha256=hashes,
                bottom_thermal_region_allocations_mm=thermal,
                pcb_routed=False,
                thermal_layout_qualified=False,
                switching_loop_qualified=False,
                enclosure_fit_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "E24: 157 parts and four M2 holes placed; no copper routed. Run independent native DRC/parity and placement checks."
    )


if __name__ == "__main__":
    main()
