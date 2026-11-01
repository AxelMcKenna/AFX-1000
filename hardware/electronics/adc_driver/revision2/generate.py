"""Generate the independent E12-R2 native schematic and compact placement candidate."""

import argparse
import json
import math
import subprocess
import uuid
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint, project_settings
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...power_supply.place import mount
from .. import generate as schematic_engine
from ..pcb import generate as original_board
from .design import COMPONENTS, CONTRACT, ROOT

OUT = ROOT / "generated"
SIZE = (110, 78)
POSES = dict(original_board.POSES)
for ci in (0, 1):
    dx = 50 * ci
    for k, pose in {
        "C1": (35, 43, 90, "F"),
        "C2": (25, 43, 90, "F"),
        "R1": (35, 38.8, 270, "F"),
        "R2": (25, 38.8, 270, "F"),
        "R3": (35, 40.8, 270, "F"),
        "R4": (25, 40.8, 270, "F"),
        "R5": (25, 46, 0, "F"),
        "R6": (35, 46, 180, "F"),
        "C13": (29.4, 44.6, 270, "B"),
        "C14": (30.6, 44.6, 270, "B"),
    }.items():
        index = int(k[1:]) + (16 if k[0] == "R" else 14) * ci
        POSES[k[0] + str(index)] = (pose[0] + dx, *pose[1:])
    # Flying capacitor on the opposite side directly over the pump pins.
    pump = 14 if ci == 0 else 94
    POSES["C" + str(8 + 14 * ci)] = (pump, 9.65, 0, "B")
    POSES["C" + str(9 + 14 * ci)] = (pump + 5.5, 14.5, 0, "B")
    POSES["C" + str(12 + 14 * ci)] = (pump - 5.5, 13.9, 270, "F")
POSES.update(
    {
        "J2": (43, 74, 90, "F"),
        "U7": (55, 55, 0, "F"),
        "U8": (56.5, 67.3, 0, "F"),
        "R34": (47, 54, 0, "F"),
        "R35": (47, 57, 0, "F"),
        "R36": (63, 54, 0, "F"),
        "R37": (63, 57, 0, "F"),
        "R38": (53, 62, 0, "F"),
        "R39": (53, 65, 0, "F"),
        "R40": (58, 61, 0, "F"),
        "R41": (58, 64, 0, "F"),
        "R42": (40, 57, 0, "F"),
        "R43": (70, 56, 0, "F"),
        "R44": (70, 59, 0, "F"),
        "C35": (54, 48, 0, "F"),
        "C36": (51, 67, 0, "F"),
    }
)
# Candidate dielectric construction, not a fabricator-approved material stackup.
STACKUP = [
    ("F.Cu", 0.035),
    ("dielectric1", 0.1),
    ("In1.Cu", 0.035),
    ("dielectric2", 0.28),
    ("In2.Cu", 0.035),
    ("dielectric3", 0.63),
    ("In3.Cu", 0.035),
    ("dielectric4", 0.28),
    ("In4.Cu", 0.035),
    ("dielectric5", 0.1),
    ("B.Cu", 0.035),
]


def schematic(cli):
    # Reuse only a renderer, redirect all globals to new revision; restore afterwards.
    saved = schematic_engine.ROOT, schematic_engine.COMPONENTS, schematic_engine.NOTES, schematic_engine.uid
    try:
        schematic_engine.ROOT = ROOT
        schematic_engine.COMPONENTS = COMPONENTS
        schematic_engine.NOTES = [
            (30, 1035, "E12-R2 design-repair candidate; no fabrication or physical qualification"),
            (
                30,
                1045,
                "Separate force/sense interface; final ESS pin integration and parasitic model required",
            ),
            (
                30,
                1055,
                "Both bias windows and V5 supervisor inhibit PD. DRV_ENABLE requires system rail/reference health.",
            ),
        ]
        schematic_engine.uid = lambda value: str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E12-R2:" + value))
        schematic_engine.main()
    finally:
        schematic_engine.ROOT, schematic_engine.COMPONENTS, schematic_engine.NOTES, schematic_engine.uid = (
            saved
        )
    p = ROOT / "adc_driver.kicad_sch"
    s = (
        p.read_text()
        .replace('(paper "User" 900 640)', '(paper "User" 900 1100)')
        .replace('(rev "E12")', '(rev "E12-R2")')
        .replace(
            "Schematic prototype; no routed board or bench validation",
            "Separate R2 repair candidate; no physical qualification",
        )
    )
    p.write_text(s)
    for kind, extra in [("netlist", ["--format", "kicadxml"]), ("svg", [])]:
        output = OUT / ("netlist.xml" if kind == "netlist" else "schematic-svg")
        subprocess.run(
            [str(cli), "sch", "export", kind, *extra, "--output", str(output), str(p)],
            check=True,
            capture_output=True,
            text=True,
        )
    for command in [("sch", "erc", "--format", "json", "--output", str(OUT / "erc.json"), str(p))]:
        result = subprocess.run([str(cli), *command], capture_output=True, text=True)
        (OUT / "erc-log.txt").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, (result.returncode, result.stderr)


def board(cli):
    library = footprint_root(str(cli))
    names = sorted({n for p in CONTRACT.values() for n in p.values()})
    nets = {name: i + 1 for i, name in enumerate(names)}
    board = read_sexpr(
        '(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4") (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal) (3 "In3.Cu" signal) (4 "In4.Cu" power) (31 "B.Cu" signal) (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user)) (setup (pad_to_mask_clearance 0)) (net 0 ""))'
    )
    assert abs(sum(t for _, t in STACKUP) - 1.6) < 1e-9
    layers = []
    for name, t in STACKUP:
        if name.startswith("dielectric"):
            layers.append(
                f'(layer "{name}" (type "core") (thickness {t}) (material "FR4 candidate; fabricator approval required") (epsilon_r 4.2) (loss_tangent 0.02))'
            )
        else:
            layers.append(f'(layer "{name}" (type "copper") (thickness {t}))')
    first(board, "setup").append(
        read_sexpr("(stackup " + " ".join(layers) + ' (copper_finish "ENIG") (dielectric_constraints no))')
    )
    board.extend(
        [a("net"), i, name if name.startswith("unconnected-") else "/" + name] for name, i in nets.items()
    )
    for c in COMPONENTS:
        name, fp = c["footprint"].split(":")
        pins = CONTRACT[c["ref"]]
        # NC has a declared zero-code blank net on the board and explicit no-connect on schematic.

        fp_nets = dict(nets)
        fp_nets[""] = 0
        placed = placed_footprint(
            dict(
                ref=c["ref"],
                value=c["part"],
                footprint=c["footprint"],
                nets=pins,
                source=c["source"],
                mpn=c.get("mpn") or "",
            ),
            POSES[c["ref"]],
            library / (name + ".pretty") / (fp + ".kicad_mod"),
            fp_nets,
            namespace="rmx:E12-R2:",
        )
        for terminal in children(placed, "pad"):
            if children(terminal, "net") and str(first(terminal, "net")[2]).startswith("/unconnected-"):
                first(terminal, "net")[2] = str(first(terminal, "net")[2])[1:]
        board.append(placed)
    for index, xy in enumerate(original_board.MOUNTS, 1):
        board.append(mount("H" + str(index), xy))
        x, y = xy
        pts = " ".join(
            f"(xy {100 + x + 3.7 * math.cos(t * math.pi / 16):.6f} {100 + y + 3.7 * math.sin(t * math.pi / 16):.6f})"
            for t in range(32)
        )
        board.append(
            read_sexpr(
                f'(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu" "B.Cu") (hatch edge .5) (connect_pads (clearance .25)) (min_thickness .15) (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) (polygon (pts {pts})))'
            )
        )
    local = ROOT / "RMX_Power.pretty"
    local.mkdir(exist_ok=True)
    (local / "M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    table = ROOT / "fp-lib-table"
    text = table.read_text()
    if "RMX_Power" not in text:
        table.write_text(
            text.rstrip().removesuffix(")")
            + '\n(lib (name "RMX_Power") (type "KiCad") (uri "${KIPRJMOD}/RMX_Power.pretty") (options "") (descr "M2 mounting clearance")))\n'
        )
    for p, q in [((0, 0), (110, 0)), ((110, 0), (110, 78)), ((110, 78), (0, 78)), ((0, 78), (0, 0))]:
        board.append(
            read_sexpr(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    for layer in ["In1.Cu", "In4.Cu"]:
        board.append(
            read_sexpr(
                f'(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "{layer}") (hatch edge .5) (connect_pads yes (clearance .2)) (min_thickness .15) (fill yes (thermal_gap .3) (thermal_bridge_width .3)) (polygon (pts (xy 100.6 100.6) (xy 209.4 100.6) (xy 209.4 177.4) (xy 100.6 177.4))))'
            )
        )
    # Full local sensitive branch rectangles, covering input resistors, feedback caps and output pads.
    for x in [30, 80]:
        for xa, xb in [(x - 6.5, x - 1), (x + 1, x + 6.5)]:
            board.append(
                read_sexpr(
                    f'(zone (net 0) (net_name "") (layers "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu" "B.Cu") (hatch edge .5) (connect_pads (clearance .2)) (min_thickness .15) (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) (polygon (pts (xy {100 + xa} 138.7) (xy {100 + xb} 138.7) (xy {100 + xb} 145.0) (xy {100 + xa} 145.0))))'
                )
            )
    path = ROOT / "adc_driver.kicad_pcb"
    path.write_text(sexpr(board) + "\n")
    pro = json.loads((ROOT / "adc_driver.kicad_pro").read_text())
    settings = project_settings()
    settings["rules"]["min_clearance"] = 0.15
    settings["rules"]["min_track_width"] = 0.15
    pro["board"] = {"design_settings": settings}
    (ROOT / "adc_driver.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    (ROOT / "adc_driver.kicad_dru").write_text(
        '(version 1)\n(rule "R2 minimum copper clearance" (constraint clearance (min 0.15mm)))\n'
    )
    (OUT / "placement.json").write_text(
        json.dumps(
            dict(
                poses=POSES,
                stackup=STACKUP,
                stackup_fabricator_approved=False,
                routed=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    return board


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    schematic(args.kicad_cli)
    board(args.kicad_cli)
    print(
        "E12-R2 native schematic + placed board generated; copper routing and native parity/DRC still required"
    )


if __name__ == "__main__":
    main()
