#!/usr/bin/env python3
"""Place and route E19; saved native DRC/parity and enclosure checks are required."""

import argparse
import json
import math
import os
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from ..common import netlists as eda
from ..common import placement as helper
from ..common.reports import sha
from ..common.sexpr import a, children, first, sexpr
from ..common.sexpr import read_sexpr as read
from ..control_inputs.board import Routing

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SIZE = (150, 65)
DATUM = (30, 42, 6.5)
MOUNTS = [(4, 4), (146, 4), (4, 61), (146, 61), (83, 5), (139, 5), (83, 51), (139, 51)]
POSES = {
    "U1": (59.63, 45.98, 270, "F"),
    "J1": (14, 5, 0, "F"),
    "J2": (20, 5, 0, "F"),
    "J3": (30, 5, 0, "F"),
    "J4": (40, 5, 0, "F"),
    "J5": (50, 5, 0, "F"),
    "J6": (60, 5, 0, "F"),
    "J7": (70, 5, 0, "F"),
    "J8": (14, 23, 0, "F"),
    "J9": (24, 23, 0, "F"),
    "J10": (34, 23, 0, "F"),
    "J11": (45, 19, 0, "F"),
    "J12": (53, 23, 90, "F"),
    "R1": (66, 45, 90, "F"),
    "R2": (24, 37, 90, "F"),
    "R3": (71, 31, 90, "F"),
    "R4": (29.15, 41.5, 90, "F"),
    "R5": (68, 27.5, 90, "F"),
    "R6": (64, 38, 90, "F"),
    "R10": (42, 41.5, 90, "F"),
    "R11": (39.31, 41.5, 90, "F"),
    "R12": (34.23, 41.5, 90, "F"),
    "R13": (24, 41.5, 90, "F"),
    "R14": (40, 58, 90, "B"),
    "R15": (50, 41.5, 90, "F"),
    "R16": (53.5, 41.5, 90, "F"),
    "R17": (57, 41.5, 90, "F"),
    "R18": (60.5, 41.5, 90, "F"),
    "R19": (46, 41.5, 90, "F"),
    "R20": (40.25, 37, 90, "F"),
    "C1": (65, 52.5, 0, "F"),
    "C2": (65, 57, 0, "F"),
    "C3": (7, 49, 90, "F"),
    "C4": (7, 53.5, 90, "F"),
    "C5": (65, 60.8, 0, "F"),
    "C6": (70, 48, 0, "F"),
}
for index in range(10):
    POSES[f"J{20 + index}"] = (69 + 7.5 * index, 57.8, 0, "F")
    x = round(13.91 + 2.54 * index, 6)
    POSES[f"R{31 + index}"] = (x, 58.1, 270, "B")
    POSES[f"C{11 + index}"] = (x, 53.6, 90, "B")
    POSES[f"R{41 + index}"] = (x, 49.1, 90, "B")


def mount(reference="REF**", xy=None, daughter=False):
    at = f"(at {100 + xy[0]} {100 + xy[1]})" if xy else ""
    front, back = (2.75, 2.25) if daughter else (2.8, 3.7)
    return read(f'''(footprint "RMX_Carrier:{"M2_Daughter" if daughter else "M2_Insert_Clearance"}" (layer "F.Cu") {at}
      (attr board_only exclude_from_pos_files exclude_from_bom)
      (property "Reference" "{reference}" (at 0 -4.2) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (property "Value" "M2_CLEARANCE" (at 0 4.2) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      (fp_circle (center 0 0) (end {front} 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center 0 0) (end {back} 0) (stroke (width .05) (type solid)) (fill none) (layer "B.CrtYd"))
      (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))''')


def route(board, nets):
    router = Routing(board, nets)
    # Preserve copper clearance around metal fixing hardware on all layers,
    # independently of the much smaller NPTH drill-clearance rule.
    for index, (x, y) in enumerate(MOUNTS):
        radius = 3.8 if index < 4 else 2.85
        router.geometry.append(
            dict(
                kind="circle",
                net=f"MOUNT_KEEP_OUT_{index}",
                layers=["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"],
                x=x,
                y=y,
                r=radius,
            )
        )
    tasks = defaultdict(list)
    # All SMD terminals get short same-side escapes. Bottom filters remain near
    # the ADC pins; their long knob-harness traces carry the unfiltered signal.
    for (ref, number), (x, y, net) in router.pads.items():
        if ref.startswith(("R", "C")):
            if net.startswith("POT_ADC_"):
                continue
            cx, cy, _, side = POSES[ref]
            dx, dy = x - cx, y - cy
            length = (dx * dx + dy * dy) ** 0.5
            at = (round(x + 0.65 * dx / length, 6), round(y + 0.65 * dy / length, 6))
            width = 0.5 if net in ("5V_DIG", "SEED_VIN") else 0.35 if net == "AGND" else 0.25
            router.path(net, side, (x, y), at, width=width)
            router.via(net, at)
            if net != "AGND":
                tasks[net].append(at)
        elif net != "AGND" and not net.startswith("unconnected-"):
            tasks[net].append((x, y))
    # Short, entirely bottom-side ADC connections. Each bus runs beside its
    # component column; no grid detours or extra digital-layer vias are needed.
    for index in range(10):
        net = f"POT_ADC_{index:02d}"
        r, c, bleed = f"R{31 + index}", f"C{11 + index}", f"R{41 + index}"
        front = router.p(r, 2)
        side_x = round(front[0] + 1.2, 6)
        router.path(net, "B", front, router.p("U1", 22 + index))
        router.path(net, "B", front, (side_x, front[1]), (side_x, router.p(bleed, 1)[1]), router.p(bleed, 1))
        router.path(net, "B", router.p(c, 1), (side_x, router.p(c, 1)[1]))
        tasks.pop(net)
    # Hand-route raw-wiper escapes through the exact socket-pitch midpoints.
    # Terminate above the socket row, where the grid has room for the harness
    # fanout. This avoids trapping connections among the bottom filter columns.
    for index in range(10):
        net = f"POT_RAW_{index:02d}"
        at = tasks[net][-1]
        end = (round(at[0] + 1.27, 6), 34.0)
        router.path(net, "F", at, (end[0], round(at[1] - 1.27, 6)), end)
        router.via(net, end)
        tasks[net][-1] = end
    # A quiet excitation trunk outside the module/knob-header pin rows. Clock
    # routing stays on other layers and needs a later measured SI/noise audit.
    analog = "V3V3_ANALOG"
    trunk = (11.37, 63.7)
    router.path(analog, "F", router.p("U1", 21), trunk, (136.5, 63.7), width=0.4)
    for index in range(10):
        point = router.p(f"J{20 + index}", 3)
        router.path(analog, "F", point, (point[0], 63.7), width=0.4)
    tasks[analog] = [
        router.p("U1", 21),
        *[
            p
            for p in tasks[analog]
            if p not in [router.p(f"J{20 + i}", 3) for i in range(10)] and p != router.p("U1", 21)
        ],
    ]
    # Route short ADC networks first, then source-power trunks and long harness
    # nets. The router is a geometric aid; native KiCad remains authoritative.
    ordered = {net: tasks.pop(net) for net in sorted(list(tasks)) if net.startswith("POT_ADC_")}
    ordered.update({net: tasks.pop(net) for net in sorted(list(tasks)) if net.startswith("POT_RAW_")})
    for net in ("5V_DIG", "SEED_VIN", "V3V3_IO", "V3V3_ANALOG"):
        ordered[net] = tasks.pop(net)
    ordered.update(tasks)
    from .route_grid import connect

    connect(router, ordered, SIZE)
    board.append(
        read(f"""(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "In1.Cu") (hatch edge .5)
      (connect_pads (clearance .25)) (min_thickness .25) (fill yes (thermal_gap .25) (thermal_bridge_width .3))
      (polygon (pts (xy 100.7 100.7) (xy 249.3 100.7) (xy 249.3 164.3) (xy 100.7 164.3))))""")
    )
    return router


def remove_redundant_vias(cli, fp_root):
    """Use native connectivity to remove only vias with no layer transition.

    This is generator cleanup, not approval: the independent verifier reruns
    every check and rejects other errors and remaining open connections.
    """
    with tempfile.TemporaryDirectory(prefix="rmx-e19-cleanup-") as folder:
        temp = Path(folder)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp}/cache</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            FONTCONFIG_FILE=str(font),
            KICAD10_FOOTPRINT_DIR=str(fp_root),
        )
        report = OUT / "generator-drc.json"
        pcb = ROOT / "processor_carrier.kicad_pcb"
        result = subprocess.run(
            [
                str(cli),
                "pcb",
                "drc",
                "--refill-zones",
                "--save-board",
                "--all-track-errors",
                "--schematic-parity",
                "--severity-all",
                "--format",
                "json",
                "-o",
                str(report),
                str(pcb),
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        drc = json.loads(report.read_text())
        ids = {
            item["uuid"]
            for violation in drc["violations"]
            if violation["type"] == "via_dangling"
            for item in violation["items"]
        }
        tree = read(pcb.read_text())
        removed = [via for via in children(tree, "via") if str(first(via, "uuid")[1]) in ids]
        assert len(removed) == len(ids)
        assert all(str(first(via, "net")[1]) != "/AGND" for via in removed)
        tree = [node for node in tree if node not in removed]
        pcb.write_text("(kicad_pcb\n" + "\n".join(sexpr(node) for node in tree[1:]) + "\n)\n")
        return len(removed), {"segments": len(children(tree, "segment")), "vias": len(children(tree, "via"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    parser.add_argument("--place-only", action="store_true")
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    fp_root = helper.footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e19-place-") as temp:
        result = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(OUT / "netlist.xml"),
                str(ROOT / "processor_carrier.kicad_sch"),
            ],
            env=dict(os.environ, KICAD_CONFIG_HOME=temp, KICAD10_FOOTPRINT_DIR=str(fp_root)),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    parts, pins = eda.netlist(OUT / "netlist.xml")
    components = json.loads((ROOT / "components.json").read_text())
    assert set(POSES) == set(parts) == {c["ref"] for c in components}
    nets = {net: i + 1 for i, net in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    board = read("""(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend(
        [a("net"), code, net if net.startswith("unconnected-") else "/" + net] for net, code in nets.items()
    )
    hashes = {}
    for c in components:
        lib, name = c["footprint"].split(":")
        source = (ROOT if lib.startswith("RMX_") else fp_root) / (lib + ".pretty") / (name + ".kicad_mod")
        c = dict(c, value=c["part"], mpn=c["part"], nets=pins[c["ref"]])
        placed = helper.placed_footprint(c, POSES[c["ref"]], source, nets, namespace="rmx:E19:")
        for pad in children(placed, "pad"):
            net = first(pad, "net")
            if str(net[2]).startswith("/unconnected-"):
                net[2] = str(net[2])[1:]
        board.append(placed)
        hashes[c["footprint"]] = sha(source)
    for index, xy in enumerate(MOUNTS, 1):
        board.append(mount(f"H{index}", xy, index > 4))
        # 32-sided circumscribed keepout, with .05mm beyond the hardware's
        # largest nominal radius. Router masks are slightly larger again.
        radius = (3.75 if index <= 4 else 2.8) / math.cos(math.pi / 32)
        points = " ".join(
            f"(xy {100 + xy[0] + radius * math.cos(i * math.pi / 16):.6f} "
            f"{100 + xy[1] + radius * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read(f"""(zone (net 0) (net_name "")
          (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu") (hatch edge .5)
          (connect_pads (clearance 0)) (min_thickness .25)
          (keepout (tracks not_allowed) (vias not_allowed) (pads allowed)
                   (copperpour not_allowed) (footprints allowed))
          (polygon (pts {points})))""")
        )
    for p, q in [((0, 0), (150, 0)), ((150, 0), (150, 65)), ((150, 65), (0, 65)), ((0, 65), (0, 0))]:
        board.append(
            read(
                f"(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) "
                '(stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    for daughter in (False, True):
        name = "M2_Daughter" if daughter else "M2_Insert_Clearance"
        (ROOT / f"RMX_Carrier.pretty/{name}.kicad_mod").write_text(sexpr(mount(daughter=daughter)) + "\n")
    pro = json.loads((ROOT / "processor_carrier.kicad_pro").read_text())
    pro["board"] = {"design_settings": helper.project_settings()}
    pro["net_settings"] = {
        "classes": [
            dict(
                name="Default",
                clearance=0.25,
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
    (ROOT / "processor_carrier.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    routed = None if args.place_only else route(board, nets)
    (ROOT / "processor_carrier.kicad_pcb").write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    removed, saved_counts = remove_redundant_vias(cli, fp_root) if routed else (0, {})
    (OUT / "routing-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E19",
                board_size_mm=[*SIZE, 1.6],
                layout_origin_mm=DATUM,
                mounts_relative_mm=MOUNTS,
                footprint_library_sha256=hashes,
                counts=saved_counts,
                redundant_vias_removed_by_native_connectivity=removed,
                paths=routed.paths if routed else [],
                pcb_routed=routed is not None,
                native_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E19 PCB generated; independent native DRC/parity and CAD checks required.", flush=True)


if __name__ == "__main__":
    main()
