#!/usr/bin/env python3
"""E20 component placement intermediate; no copper routing or fit approval."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.placement import footprint_root, placed_footprint, project_settings
from ..common.reports import sha
from ..common.sexpr import a, children, first, sexpr
from ..common.sexpr import read_sexpr as read

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SIZE = (91, 27)
DATUM = (197, 77, 6.5)
MOUNTS = [(3, 7), (87, 7), (3, 22), (87, 22)]
POSES = {
    "J1": (45.5, 10.0, 0, "F"),
    "J2": (10, 4.5, 90, "F"),
    "J3": (10, 22.5, 90, "F"),
    "J4": (50, 4.5, 90, "F"),
    "J5": (50, 22.5, 90, "F"),
    "U5": (24.5, 13, 90, "B"),
    "U6": (41, 10, 0, "B"),
    "U7": (41, 14, 0, "B"),
    "Q1": (49.8, 7.0, 0, "B"),
    "Q2": (45.5, 16.7, 0, "B"),
    "R5": (49, 10.5, 90, "B"),
    "R6": (81, 11, 0, "B"),
    "R7": (85.5, 11, 0, "B"),
    "R8": (81, 14, 0, "B"),
    "R9": (85.5, 14, 0, "B"),
    "R10": (51, 15, 90, "B"),
    "R11": (66, 16, 0, "B"),
    "R12": (81, 15.5, 0, "B"),
    "R13": (81, 8, 0, "B"),
    "R14": (63, 16, 0, "B"),
    "R15": (24.5, 7.5, 0, "B"),
    "R16": (28.5, 6.8, 0, "B"),
    "R17": (24.5, 17.7, 0, "B"),
    "R18": (25.5, 16.5, 0, "F"),
    "R19": (24.5, 9, 0, "F"),
    "R20": (65.5, 11, 0, "F"),
    "R21": (66.5, 14, 0, "F"),
    "C9": (18.8, 16, 0, "B"),
    "C10": (30.5, 16, 0, "B"),
    "C11": (37.8, 11.5, 90, "B"),
    "C12": (37.8, 15, 90, "B"),
    "C13": (67, 12, 0, "B"),
    "C14": (64, 8, 0, "B"),
}
for chip, x in enumerate((16, 35, 57, 76)):
    POSES[f"U{chip + 1}"] = (x, 12, 90, "F")
    # Keep the current-setting resistors beside the ICs rather than beneath
    # their heat paddles, where a through-layer escape would be obstructed.
    POSES[f"R{chip + 1}"] = (x - 7.5 + (0.35 if chip == 2 else 0), 9.5, 270, "F")
    POSES[f"C{2 * chip + 1}"] = (x - 4.875, 10.3, 270, "B")
    POSES[f"C{2 * chip + 2}"] = (x, 8.8, 0, "B")
for ref, (x, y, angle, side) in list(POSES.items()):
    y += 1  # Preserve component layout coordinates as the board expands fore/aft.
    if ref in ("J2", "J4"):
        y -= 1
    if ref in ("J3", "J5"):
        y += 1
    POSES[ref] = (x, y, angle, side)


def mount(ref="REF**", xy=None):
    at = f"(at {100 + xy[0]} {100 + xy[1]})" if xy else ""
    return read(f'''(footprint "RMX_LED:M2_Insert_Clearance" (layer "F.Cu") {at}
      (attr board_only exclude_from_pos_files exclude_from_bom)
      (property "Reference" "{ref}" (at 0 -4.2) (layer "F.Fab") (effects (font (size .8 .8))))
      (property "Value" "M2_CLEARANCE" (at 0 4.2) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      (fp_circle (center 0 0) (end 2.8 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center 0 0) (end 3.7 0) (stroke (width .05) (type solid)) (fill none) (layer "B.CrtYd"))
      (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    fp_root = footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e20-place-") as folder:
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
                str(ROOT / "led_driver.kicad_sch"),
            ],
            env=dict(os.environ, KICAD_CONFIG_HOME=folder, KICAD10_FOOTPRINT_DIR=str(fp_root)),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
    parts, pins = eda.netlist(OUT / "netlist.xml")
    components = json.loads((ROOT / "components.json").read_text())
    assert set(POSES) == set(parts) == {c["ref"] for c in components}
    nets = {net: i + 1 for i, net in enumerate(sorted({net for p in pins.values() for net in p.values()}))}
    board = read("""(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal)
        (3 "In3.Cu" signal) (4 "In4.Cu" power) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend(
        [a("net"), code, net if net.startswith("unconnected-") else "/" + net] for net, code in nets.items()
    )
    hashes = {}
    for component in components:
        lib, name = component["footprint"].split(":")
        library = (ROOT if lib.startswith("RMX_") else fp_root) / (lib + ".pretty") / (name + ".kicad_mod")
        c = dict(component, value=component["part"], mpn=component["part"], nets=pins[component["ref"]])
        fp = placed_footprint(c, POSES[c["ref"]], library, nets, namespace="rmx:E20:")
        for pad in children(fp, "pad"):
            if not children(pad, "net"):
                continue
            net = first(pad, "net")
            if str(net[2]).startswith("/unconnected-"):
                net[2] = str(net[2])[1:]
        board.append(fp)
        hashes[component["footprint"]] = sha(library)
    for i, xy in enumerate(MOUNTS, 1):
        board.append(mount(f"H{i}", xy))
    for p, q in [((0, 0), (91, 0)), ((91, 0), (91, 27)), ((91, 27), (0, 27)), ((0, 27), (0, 0))]:
        board.append(
            read(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    (ROOT / "RMX_LED.pretty/M2_Insert_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    settings = project_settings()
    settings["rules"]["min_clearance"] = 0.15
    settings["rules"]["min_track_width"] = 0.15
    pro = json.loads((ROOT / "led_driver.kicad_pro").read_text())
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
    (ROOT / "led_driver.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    (ROOT / "led_driver.kicad_pcb").write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    (OUT / "placement-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E20",
                board_size_mm=[*SIZE, 1.6],
                layout_origin_proposal_mm=DATUM,
                mounts_relative_mm=MOUNTS,
                source_footprint_hashes=hashes,
                pcb_routed=False,
                physical_fit_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E20:49 parts and4 M2 holes placed; no copper routed. Independent DRC/parity/fit checks required.")


if __name__ == "__main__":
    main()
