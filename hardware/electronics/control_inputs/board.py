#!/usr/bin/env python3
"""Place E18 and route digital nets; native DRC/parity remains authoritative."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common import placement as helper
from ..common.sexpr import a, children, first, sexpr
from ..common.sexpr import read_sexpr as read

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SIZE = (64, 54)
DATUM = (109, 43, 12.1)
MOUNTS = [(4, 4), (60, 4), (4, 50), (60, 50)]
POSES = {
    "U1": (20, 24, 90, "F"),
    "U2": (44, 24, 90, "F"),
    "U3": (32, 39.5, 90, "F"),
    "J1": (12, 6, 90, "F"),
    "J2": (36, 6, 90, "F"),
    "J3": (12, 51, 90, "F"),
    "J4": (29.4, 51, 90, "F"),
    "J5": (44.5, 51, 90, "F"),
    "C1": (23, 32, 0, "F"),
    "C2": (47, 32, 0, "F"),
    "C3": (34, 47, 0, "F"),
    "C4": (44, 38, 0, "F"),
    "R1": (50, 38, 0, "F"),
    "R2": (16, 37, 0, "F"),
    "R3": (16, 40, 0, "F"),
}


def mount(reference="REF**", position=None):
    at = f"(at {position[0]} {position[1]})" if position else ""
    return read(f'''(footprint "RMX_Control:M2_Clearance" (layer "F.Cu") {at}
      (attr board_only exclude_from_pos_files exclude_from_bom)
      (property "Reference" "{reference}" (at 0 -3.6) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (property "Value" "M2_CLEARANCE" (at 0 3.6) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12)) (hide yes)))
      (fp_circle (center 0 0) (end 2.75 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center 0 0) (end 2.75 0) (stroke (width .05) (type solid)) (fill none) (layer "B.CrtYd"))
      (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))''')


class Routing:
    def __init__(self, board, nets):
        self.board, self.nets, self.pads, self.vias, self.paths = board, nets, {}, [], []
        self.geometry = []
        self.counts = {"segments": 0, "vias": 0}
        for fp in children(board, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            pos = first(fp, "at")
            x, y = map(float, pos[1:3])
            angle = math.radians(float(pos[3]) if len(pos) > 3 else 0)
            for pad in children(fp, "pad"):
                px, py = map(float, first(pad, "at")[1:3])
                px, py = (
                    x + px * math.cos(angle) + py * math.sin(angle) - 100,
                    y - px * math.sin(angle) + py * math.cos(angle) - 100,
                )
                if children(pad, "net"):
                    net = str(first(pad, "net")[2]).lstrip("/")
                    self.pads[(ref, str(pad[1]))] = (round(px, 6), round(py, 6), net)
                else:
                    net = "HOLE_" + ref
                w, h = map(float, first(pad, "size")[1:3])
                if abs(math.sin(angle)) > 0.5:
                    w, h = h, w
                layers = [n for n in first(pad, "layers")[1:] if str(n).endswith(".Cu")]
                if "*.Cu" in layers:
                    layers = ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"]
                self.geometry.append(dict(kind="rect", net=net, layers=layers, x=px, y=py, w=w, h=h))

    def p(self, ref, pin):
        return self.pads[(ref, str(pin))][:2]

    def path(self, net, layer, *points, width=0.25):
        self.paths.append(dict(net=net, layer=layer, width=width, points=points))
        for start, end in zip(points, points[1:]):
            start, end = tuple(round(v, 6) for v in start), tuple(round(v, 6) for v in end)
            if start == end:
                continue
            self.counts["segments"] += 1
            self.board.append(
                read(
                    f'(segment (start {100 + start[0]} {100 + start[1]}) (end {100 + end[0]} {100 + end[1]}) (width {width}) (layer "{layer}.Cu") (net {self.nets[net]}))'
                )
            )
            self.geometry.append(
                dict(kind="line", net=net, layers=[layer + ".Cu"], start=start, end=end, w=width)
            )

    def via(self, net, xy, size=0.6):
        if any(other == net and math.dist(at, xy) < 1e-6 for other, at in self.vias):
            return
        self.counts["vias"] += 1
        self.vias.append((net, xy))
        self.board.append(
            read(
                f'(via (at {100 + xy[0]} {100 + xy[1]}) (size {size}) (drill .3) (layers "F.Cu" "B.Cu") (net {self.nets[net]}))'
            )
        )
        self.geometry.append(
            dict(
                kind="circle",
                net=net,
                layers=["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"],
                x=xy[0],
                y=xy[1],
                r=size / 2,
            )
        )

    def escape(self, ref, pin, dy):
        p = self.p(ref, pin)
        xy = (p[0], round(p[1] + dy, 6))
        net = self.pads[(ref, str(pin))][2]
        self.path(net, "F", p, xy)
        self.via(net, xy)
        return xy


def route(board, nets):
    r = Routing(board, nets)
    p = r.p
    power_straps = []
    # Monotonic A-side fans on F.Cu; B-side fans use B.Cu under the ICs.
    for chip in (1, 2):
        u, j = f"U{chip}", f"J{chip}"
        for column in range(7):
            src = p(u, 27 - column)
            target = p(j, 1 + 2 * column)
            exit = (src[0], src[1] - 1.5)
            bend = (target[0], exit[1] - abs(target[0] - src[0]))
            r.path(f"CONTROL_{(chip - 1) * 14 + 6 - column:02d}", "F", src, exit, bend, target)
            start = r.escape(u, 1 + column, 2)
            target = p(j, 2 + 2 * column)
            spine = target[0] + 1.27
            bend = (spine, start[1] - abs(spine - start[0]))
            r.path(
                f"CONTROL_{(chip - 1) * 14 + 7 + column:02d}", "B", start, bend, (spine, target[1]), target
            )
    # Supply arrives at each IC's bypass before the quiet DC distribution trunk.
    for chip in (1, 2, 3):
        u = f"U{chip}"
        v = r.escape(u, 9, 1.55)
        g = r.escape(u, 10, 1.55)
        cap = f"C{chip}"
        r.path("V3V3_IO", "F", v, p(cap, 1), width=0.35)
        r.path("AGND", "F", g, p(cap, 2), width=0.35)
        r.path("V3V3_IO", "B", v, (v[0], 35), width=0.5)
        for pin in (15, 16, 17):
            start = p(u, pin)
            net = r.pads[(u, str(pin))][2]
            end = (
                (start[0], start[1] + 4.15)
                if pin == 15
                else (start[0], start[1] + 2.65)
                if pin == 16
                else (start[0] - 0.8, start[1] + 1.65)
            )
            r.path(net, "F", start, (start[0], start[1] + 0.85), end)
            r.via(net, end)
            if net == "V3V3_IO":
                power_straps.append(end)
    r.path("V3V3_IO", "B", (21.905, 35), (57.5, 35), (57.5, 49), (46.54, 49), p("J5", 2), width=0.5)
    r.path("V3V3_IO", "F", p("C4", 1), (42.5, 38), width=0.35)
    r.via("V3V3_IO", (42.5, 38))
    r.path("V3V3_IO", "B", (42.5, 38), (42.5, 35), width=0.5)
    for ref in ("R1", "R2", "R3", "C4"):
        xy = (p(ref, 2)[0] + 0.8, p(ref, 2)[1])
        r.path("AGND", "F", p(ref, 2), xy, width=0.35)
        r.via("AGND", xy)
    # Inner-layer/bottom maze routing for the remaining slow digital signals.
    # Its conservative geometric masks are only a routing aid; native DRC
    # subsequently checks all actual pads, copper, drills and schematic parity.
    tasks = {
        net: []
        for net in (
            "SCL",
            "SDA",
            "CONTROL_RESET_N",
            "MODE_SEND_RETURN",
            "MANUAL_BYPASS",
            "ANALOG_OK",
            "INPUT_READY",
        )
    }
    tasks["V3V3_IO"] = [p("J5", 2), *power_straps]
    for chip in (1, 2, 3):
        for pin in (12, 13, 18):
            net = r.pads[(f"U{chip}", str(pin))][2]
            tasks[net].append(r.escape(f"U{chip}", pin, -1.35 if pin == 18 else 1.55))
    for pin in (21, 22, 23, 24):
        net = r.pads[("U3", str(pin))][2]
        tasks[net].append(r.escape("U3", pin, -1.45))
    for ref in ("R1", "R2", "R3"):
        xy = (p(ref, 1)[0] - 0.8, p(ref, 1)[1])
        net = r.pads[(ref, "1")][2]
        r.path(net, "F", p(ref, 1), xy)
        r.via(net, xy)
        tasks[net].append(xy)
    for pin, net in [(3, "SCL"), (4, "SDA"), (5, "CONTROL_RESET_N")]:
        tasks[net].insert(0, p("J5", pin))
    for pin, net in [(2, "MODE_SEND_RETURN"), (3, "MANUAL_BYPASS"), (4, "ANALOG_OK"), (5, "INPUT_READY")]:
        tasks[net].insert(0, p("J4", pin))
    for index in range(4):
        net = f"CONTROL_{28 + index:02d}"
        tasks[net] = [p("J3", index + 2), r.escape("U3", index + 1, 2)]
    from .maze import connect

    connect(r, tasks, SIZE)
    # A continuous inner AGND plane connects all plated ground pads and vias.
    board.append(
        read(f"""(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "In1.Cu") (hatch edge .5)
      (connect_pads (clearance .25)) (min_thickness .25) (fill yes (thermal_gap .25) (thermal_bridge_width .3))
      (polygon (pts (xy 100.7 100.7) (xy 163.3 100.7) (xy 163.3 153.3) (xy 100.7 153.3))))""")
    )
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    fp = helper.footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e18-place-") as temp:
        env = dict(os.environ, KICAD_CONFIG_HOME=temp, KICAD10_FOOTPRINT_DIR=str(fp))
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
                str(ROOT / "control_inputs.kicad_sch"),
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    parts, pins = eda.netlist(OUT / "netlist.xml")
    components = json.loads((ROOT / "components.json").read_text())
    assert set(POSES) == set(parts) == {c["ref"] for c in components}
    nets = {net: i + 1 for i, net in enumerate(sorted({net for p in pins.values() for net in p.values()}))}
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
        library, name = c["footprint"].split(":")
        path = fp / (library + ".pretty") / (name + ".kicad_mod")
        c = dict(c, nets=pins[c["ref"]], value=c["part"], mpn=c["part"])
        placed = helper.placed_footprint(c, POSES[c["ref"]], path, nets)
        for pad in children(placed, "pad"):
            net = first(pad, "net")
            if str(net[2]).startswith("/unconnected-"):
                net[2] = str(net[2])[1:]
        board.append(placed)
        hashes[c["footprint"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    for i, (x, y) in enumerate(MOUNTS, 1):
        board.append(mount(f"H{i}", (100 + x, 100 + y)))
    for p, q in [((0, 0), (64, 0)), ((64, 0), (64, 54)), ((64, 54), (0, 54)), ((0, 54), (0, 0))]:
        board.append(
            read(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    local = ROOT / "RMX_Control.pretty"
    local.mkdir(exist_ok=True)
    (local / "M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    pro = json.loads((ROOT / "control_inputs.kicad_pro").read_text())
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
    (ROOT / "control_inputs.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    result = route(board, nets)
    (ROOT / "control_inputs.kicad_pcb").write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    (OUT / "routing-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E18",
                board_size_mm=[64, 54, 1.6],
                layout_origin_mm=DATUM,
                mounts_relative_mm=MOUNTS,
                footprint_library_sha256=hashes,
                counts=result.counts,
                paths=result.paths,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E18 placement/routing generated; run independent native ERC/DRC/parity verifier.", flush=True)


if __name__ == "__main__":
    main()
