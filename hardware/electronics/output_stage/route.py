#!/usr/bin/env python3
"""E07 explicit output-stage routing; run native KiCad DRC/refill afterwards.

Coordinates are millimetres relative to the E06 board origin. Feedback and
local bypass paths are explicit, rather than an unconstrained autorouter run.
In1 is the analog reference plane; In2 carries the input pair, analog supplies
and the isolated relay-coil circuit. Physical performance remains unmeasured.
"""

import hashlib
import json
import math
import uuid

from ..common.sexpr import children, first, read_sexpr, sexpr
from .place import ORIGIN, ROOT


def main():
    pcb = ROOT / "output_stage.kicad_pcb"
    board = read_sexpr(pcb.read_text())
    board[:] = [v for v in board if not (isinstance(v, list) and v and v[0] in ("segment", "via", "zone"))]
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net")}
    # KiCad 10 saves net names directly; older files use the root net table.
    modern = int(first(board, "version")[1]) >= 20260206

    def net_field(net):
        return sexpr("/" + net) if modern else str(nets[net])

    pads = {}
    for fp in children(board, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pos = first(fp, "at")
        x, y = map(float, pos[1:3])
        angle = math.radians(float(pos[3]) if len(pos) > 3 else 0)
        for pad in children(fp, "pad"):
            if not children(pad, "net"):
                continue
            px, py = map(float, first(pad, "at")[1:3])
            pads[(ref, str(pad[1]))] = (
                round(x + px * math.cos(angle) + py * math.sin(angle) - ORIGIN[0], 6),
                round(y - px * math.sin(angle) + py * math.cos(angle) - ORIGIN[1], 6),
            )

    def p(ref, num):
        return pads[(ref, str(num))]

    counts = {"segments": 0, "vias": 0}
    paths = []

    def ident(kind):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E07:{kind}:{counts[kind]}"))

    def path(net, layer, *points, width=0.3):
        paths.append(dict(net=net, layer=layer, width=width, points=points))
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            counts["segments"] += 1
            x, y = (ORIGIN[0] + start[0], ORIGIN[1] + start[1])
            u, v = (ORIGIN[0] + end[0], ORIGIN[1] + end[1])
            board.append(
                read_sexpr(
                    f'(segment (start {x} {y}) (end {u} {v}) (width {width}) (layer "{layer}.Cu") (net {net_field(net)}) (uuid "{ident("segments")}"))'
                )
            )

    def via(net, xy, size=0.7, drill=0.3):
        counts["vias"] += 1
        board.append(
            read_sexpr(
                f'(via (at {ORIGIN[0] + xy[0]} {ORIGIN[1] + xy[1]}) (size {size}) (drill {drill}) (layers "F.Cu" "B.Cu") (net {net_field(net)}) (uuid "{ident("vias")}"))'
            )
        )

    def ground(ref, num, xy, layer="F"):
        path("AGND", layer, p(ref, num), xy, width=0.4)
        via("AGND", xy)

    # Local amplifier feedback. Output-current branches leave the output pad;
    # no load current is routed through the feedback-resistor takeoff.
    path("M_FB_L", "F", p("U1", 2), (3.0875, 9.365), p("R1", 1))
    path("M_FB_L", "F", (3.0875, 9.365), p("R2", 1))
    path("M_DRV_L", "F", p("U1", 1), (6.1, 8.095), (6.005, 8), p("R1", 2))
    path("M_DRV_L", "F", p("U1", 1), (7.525, 6.5))
    via("M_DRV_L", (7.525, 6.5))
    path("M_DRV_L", "B", (7.525, 6.5), (17.0375, 6.5), p("R3", 1))
    path("M_FB_R", "F", p("U1", 6), (14, 10.635), (14.135, 10.5), p("R5", 1), p("R6", 1))
    path("M_DRV_R", "F", p("U1", 7), (17.4125, 9.365), p("R5", 2))
    path("M_DRV_R", "F", (17.4125, 9.365), (18.8, 9.365), (18.8, 7.5), (27.5375, 7.5), (29.0375, 6))
    via("M_DRV_R", (29.0375, 6))
    path("M_DRV_R", "B", (29.0375, 6), p("R7", 1))
    path("S_FB_L", "F", p("U2", 2), (3.0875, 22.365), p("R9", 1))
    path("S_FB_L", "F", (3.0875, 22.365), p("R10", 1))
    path("S_DRV_L", "F", p("U2", 1), (6.1, 21.095), (6.1, 20.1875), p("R9", 2))
    path("S_DRV_L", "F", p("U2", 1), (7.525, 19.5))
    via("S_DRV_L", (7.525, 19.5))
    path("S_DRV_L", "B", (7.525, 19.5), (4, 19.5), (4, 27), (6, 29), (42.5, 29), (42.5, 20.4))
    via("S_DRV_L", (42.5, 20.4))
    via("S_DRV_L", (42.5, 16.8))
    path("S_DRV_L", "In2", (42.5, 20.4), (42.5, 16.8))
    path("S_DRV_L", "B", (42.5, 16.8), p("R11", 1))
    path("S_FB_R", "F", p("U2", 6), (14, 23.635), (14.135, 23.5), p("R13", 1), p("R14", 1))
    path("S_DRV_R", "F", p("U2", 7), (17.4125, 22.365), p("R13", 2))
    path(
        "S_DRV_R",
        "F",
        (17.4125, 22.365),
        (18.8, 22.365),
        (20, 21.165),
        (20, 19.1),
        (21.2, 17.9),
        (54.5, 17.9),
    )
    via("S_DRV_R", (54.5, 17.9))
    path("S_DRV_R", "B", (54.5, 17.9), (53.0375, 16.4375), p("R15", 1))

    # Each input has a single short inner-layer spine below the AGND plane.
    for net, num, xy1, xy2 in [
        ("RECV_L", 3, (6.15, 10.635), (6.15, 23.635)),
        ("RECV_R", 5, (14.3, 11.905), (14.3, 24.905)),
    ]:
        path(net, "F", p("U1", num), xy1)
        via(net, xy1)
        path(net, "F", p("U2", num), xy2)
        via(net, xy2)
    path("RECV_L", "In2", p("J1", 1), (8.7, 4.8), (8.7, 24.5), (7.015, 24.5), (6.15, 23.635))
    path("RECV_L", "In2", (6.15, 10.635), (8.7, 10.635))
    path("RECV_L", "F", p("R17", 1), (7.75, 16))
    via("RECV_L", (7.75, 16))
    path("RECV_L", "In2", (7.75, 16), (8.7, 16))
    path("RECV_R", "In2", p("J1", 3), (14.3, 4.28), (14.3, 24.905))
    path("RECV_R", "F", p("R18", 1), (14, 16))
    via("RECV_R", (14, 16))
    path("RECV_R", "In2", (14, 16), (14.3, 16))

    # The four independent AC-coupled branches are never joined before K3.
    path("M_SER_L", "B", p("R3", 2), (22.9625, 12.9625), p("C1", 1))
    path("M_SER_L", "F", p("C1", 1), (23.25, 9.25), p("C13", 1), width=0.4)
    path("M_AC_L", "F", p("C1", 2), (32, 11.25), (34, 9.25), p("C13", 2), width=0.4)
    path("M_AC_L", "F", p("C1", 2), (27.5, 12.5), (27.5, 17))
    via("M_AC_L", (27.5, 17))
    path("M_AC_L", "B", (27.5, 17), p("R4", 1))
    path(
        "M_AC_L",
        "F",
        p("C13", 2),
        (35.75, 7),
        (37, 5.75),
        (57, 5.75),
        (59, 7.75),
        (59, 13.9),
        p("K3", 2),
        width=0.4,
    )
    path("M_SER_R", "B", p("R7", 2), (36, 14.9625), (36, 12), (38.75, 12), (40.25, 10.5), p("C2", 1))
    path("M_SER_R", "F", p("C2", 1), (40.25, 7), (47.75, 7), (49.75, 9), p("C14", 1), width=0.4)
    path("M_AC_R", "B", p("C2", 2), (45.25, 12), (46.55, 13.3), (54.75, 13.3), p("C14", 2), width=0.4)
    path("M_AC_R", "F", p("C2", 2), (43.25, 11.25), (39.5, 11.25), (39.5, 17))
    via("M_AC_R", (39.5, 17))
    path("M_AC_R", "B", (39.5, 17), p("R8", 1))
    path(
        "M_AC_R",
        "B",
        p("C14", 2),
        (55.75, 11.25),
        (58.5, 8.5),
        (71.5, 8.5),
        (71.5, 15.1),
        (70.2, 16.4),
        width=0.4,
    )
    via("M_AC_R", (70.2, 16.4))
    path("M_AC_R", "F", (70.2, 16.4), p("K3", 7), width=0.4)
    path("S_SER_L", "B", p("R11", 2), (46.9625, 19.5), (34, 19.5), p("C15", 1))
    path("S_SER_L", "F", p("C3", 1), (21.25, 21), (29, 21), p("C15", 1), width=0.4)
    path("S_AC_L", "F", p("C3", 2), (31.5, 24.75), (33.5, 22.75), p("C15", 2), width=0.4)
    path(
        "S_AC_L",
        "F",
        p("C15", 2),
        (35.75, 21.1),
        (37.75, 19.1),
        (58.1, 19.1),
        (59.8, 20.8),
        p("K3", 4),
        width=0.4,
    )
    path("S_AC_L", "F", (50, 19.1), (50, 18.8))
    via("S_AC_L", (50, 18.8))
    path("S_AC_L", "B", (50, 18.8), p("R12", 1))
    path(
        "S_SER_R",
        "B",
        p("R15", 2),
        (58.9625, 18.25),
        (57.2125, 20),
        (50, 20),
        (48.25, 21.75),
        (48.25, 24),
        (49, 24.75),
        p("C16", 1),
    )
    path("S_SER_R", "F", p("C4", 1), (40.25, 26.5), (48, 26.5), p("C16", 1), width=0.4)
    path("S_AC_R", "F", p("C4", 2), (45.25, 21), (51, 21), p("C16", 2), width=0.4)
    path("S_AC_R", "F", p("C16", 2), (57.5, 23), (66.3, 23), p("K3", 5), width=0.4)
    path("S_AC_R", "F", p("K3", 5), (66.8, 20.8))
    via("S_AC_R", (66.8, 20.8))
    path("S_AC_R", "B", (66.8, 20.8), (62.9125, 16.9125), p("R16", 1))

    path(
        "PROC_OUT_L", "F", p("K3", 3), (63.2, 18.6), (64.2, 17.6), (64.2, 6), (65, 5.2), p("J2", 1), width=0.4
    )
    path("PROC_OUT_R", "F", p("K3", 6), (70, 18.6), (71, 17.6), (71, 4), p("J2", 3), width=0.4)
    # Coil current returns solely to E02. There is no coil-to-AGND connection.
    path("5V", "F", p("K3", 1), (61.5, 11.6), width=0.4)
    via("5V", (61.5, 11.6))
    path("5V", "In2", (61.5, 11.6), (61.5, 10), (72, 10), p("J3", 1), width=0.4)
    path("GAIN_LOW", "F", p("K3", 8), (68.5, 11.6), width=0.4)
    via("GAIN_LOW", (68.5, 11.6))
    path("GAIN_LOW", "In2", (68.5, 11.6), (70, 13.1), (72.44, 15.54), p("J3", 2), width=0.4)

    # Supply pins reach local 100nF capacitors first, then the inner trunks.
    path("P19", "F", p("U1", 8), (14, 8.095), p("C5", 1), (15.55, 4.8), width=0.5)
    via("P19", (15.55, 4.8))
    via("P19", (56, 27))
    path("P19", "In2", (15.55, 4.8), (19.9, 4.8), (19.9, 27), width=0.4)
    path("P19", "In2", (19.9, 27), (56, 27), width=0.6)
    path("P19", "F", p("J4", 1), (57.525, 29.025), p("C9", 1), (56, 27), width=0.6)
    path("N19", "F", p("U1", 4), (6.1, 11.905), (6.1, 13.95), p("C6", 1), (4.55, 17.3), width=0.5)
    via("N19", (4.55, 17.3))
    via("N19", (61, 32.6))
    path("N19", "In2", (4.55, 17.3), (2, 17.3), (2, 32.6), (61, 32.6), width=0.6)
    path("N19", "F", p("J4", 3), (63.525, 29.945), p("C10", 1), width=0.6)
    path("N19", "F", p("J4", 3), (64.58, 32.6), (61, 32.6), width=0.6)
    path("P12", "F", p("U2", 8), (14, 21.095), p("C7", 1), (15.2, 18.65), (15.2, 17.5), width=0.5)
    via("P12", (15.2, 17.5))
    via("P12", (68, 28))
    path("P12", "In2", (15.2, 17.5), (17.75, 17.5), (17.75, 28), (68, 28), width=0.6)
    path("P12", "F", p("J4", 4), (69.525, 28.595), p("C11", 1), width=0.6)
    path("P12", "F", (69.525, 28.595), (68, 28), width=0.6)
    path("N12", "F", p("U2", 4), (7.2, 25.23), (7.2, 25.8), width=0.5)
    via("N12", (7.2, 25.8))
    path("N12", "B", (7.2, 25.8), p("C8", 1), width=0.5)
    via("N12", (73.8, 29))
    path("N12", "In2", (7.2, 25.8), (7.2, 29), (73.8, 29), width=0.6)
    path("N12", "F", p("J4", 5), (71.2, 31), (73.8, 29), (74.5, 28.3), (74.5, 24.025), p("C12", 1), width=0.6)

    for ref, num, xy, layer in [
        ("R2", 2, (4.9125, 12.6), "F"),
        ("R6", 2, (18.9, 13.5), "F"),
        ("R10", 2, (4.9125, 26.5), "F"),
        ("R14", 2, (18.9, 26.5), "F"),
        ("R17", 2, (10.9125, 17.5), "F"),
        ("R18", 2, (18.9, 16), "F"),
        ("C5", 2, (18.85, 6.5), "F"),
        ("C6", 2, (6.45, 17), "F"),
        ("C7", 2, (18.85, 19), "F"),
        ("C8", 2, (11.9, 26), "B"),
        ("C9", 2, (60.475, 25), "F"),
        ("C10", 2, (66.475, 25), "F"),
        ("C11", 2, (72.475, 25), "F"),
        ("C12", 2, (80.8, 22), "F"),
        ("R4", 2, (24.4, 15.0875), "B"),
        ("R8", 2, (38, 13.5), "B"),
        ("R12", 2, (48.4, 15.0875), "B"),
        ("R16", 2, (63, 14.5), "B"),
    ]:
        ground(ref, num, xy, layer)
    zone_name = "" if modern else '(net_name "/AGND")'
    board.append(
        read_sexpr(f'''(zone (net {net_field("AGND")}) {zone_name} (layer "In1.Cu")
      (uuid "{uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E07:AGND-plane")}") (hatch edge .5)
      (connect_pads (clearance .3)) (min_thickness .25) (fill yes (thermal_gap .3) (thermal_bridge_width .3))
      (polygon (pts (xy 100.7 100.7) (xy 181.3 100.7) (xy 181.3 133.3) (xy 100.7 133.3))))''')
    )
    pcb.write_text("(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n")
    report = dict(
        revision="E07",
        routed_segments=counts["segments"],
        through_vias=counts["vias"],
        plane="In1.Cu AGND; native refill required",
        paths=paths,
        source_sha256=hashlib.sha256(__import__("pathlib").Path(__file__).read_bytes()).hexdigest(),
        native_drc_verified=False,
        physical_performance_verified=False,
    )
    (ROOT / "generated/routing-inputs.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"E07 copper generated: {counts}. Native zone refill and all-severity DRC/parity are required.")


if __name__ == "__main__":
    main()
