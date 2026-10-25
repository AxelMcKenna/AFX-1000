#!/usr/bin/env python3
"""E23 candidate DC input routing; no current, thermal or physical qualification."""

import json
import math

from ..common.sexpr import children, first, read_sexpr, sexpr
from ..control_inputs.board import Routing as BaseRouting
from .place import MOUNTS, OUT, POSES, ROOT, SIZE
from .route_grid import connect

DEBUG = ROOT.parents[2] / "build/artifacts/research/e23-routing"
COPPER = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")


class Routing(BaseRouting):
    def __init__(self, board, nets):
        super().__init__(board, nets)
        pads = [(fp, pad) for fp in children(board, "footprint") for pad in children(fp, "pad")]
        assert len(pads) == len(self.geometry)
        for shape, (fp, pad) in zip(self.geometry, pads):
            shape["is_pad"] = True
            angle = float(first(fp, "at")[3])
            local = first(pad, "at")
            angle += float(local[3]) if len(local) > 3 else 0
            w, h = map(float, first(pad, "size")[1:3])
            if abs(math.sin(math.radians(angle))) > 0.5:
                w, h = h, w
            shape.update(w=w, h=h)
            if pad[3] in ("circle", "oval") and abs(w - h) < 1e-6:
                shape.update(kind="circle", r=w / 2)
            if pad[2] == "np_thru_hole":
                # NPTH drill-to-copper requires .25 mm, above the .15 mm
                # electrical clearance used by the grid's other obstacles.
                shape.update(w=w + 0.2, h=h + 0.2)
                if shape["kind"] == "circle":
                    shape["r"] += 0.1
        self.endpoint_layers = {}


def save(board, path):
    path.write_text("(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n")


def main():
    pcb = ROOT / "input_protection.kicad_pcb"
    board = read_sexpr(pcb.read_text())
    assert not children(board, "segment"), "Regenerate placement before routing"
    (OUT / "routing-verification.json").unlink(missing_ok=True)
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net") if str(n[1]) != "0"}
    router = Routing(board, nets)
    p = router.p
    # Extra .35 mm plus the grid's .15 mm obstacle clearance preserves the
    # .5 mm copper-to-edge rule at the rear-right relief in the PCB profile.
    router.geometry.append(
        dict(kind="rect", net="OUTLINE_RELIEF", layers=list(COPPER), x=61.5, y=1, w=5.7, h=2.7)
    )
    router.geometry.append(
        dict(kind="rect", net="OUTPUT_BOARD_RELIEF", layers=list(COPPER), x=16.5, y=41.5, w=33.7, h=5.7)
    )
    for index, (x, y) in enumerate(MOUNTS):
        router.geometry.append(
            dict(kind="circle", net=f"MOUNT_{index}", layers=list(COPPER), x=x, y=y, r=3.75)
        )
        radius = 3.7 / math.cos(math.pi / 32)
        points = " ".join(
            f"(xy {100 + x + radius * math.cos(i * math.pi / 16):.6f} {100 + y + radius * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu")
          (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .15)
          (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
          (polygon (pts {points})))""")
        )
    # Short, explicit F.Cu main paths. Signal routing cannot replace these
    # with thin grid branches. Widths are design allocations, not ampacity proof.
    router.path("DC_IN", "F", p("F1", 1), (0.8, 20.5), width=0.6)
    router.path("DC_IN", "F", (0.8, 19.8), (0.8, 21.2), width=0.6)
    for at in ((0.8, 19.8), (0.8, 20.5), (0.8, 21.2)):
        router.via("DC_IN", at)
    router.path("DC_IN", "B", (0.8, 19.8), (0.8, 21.2), width=0.6)
    router.path("DC_IN", "B", (0.8, 20.5), (2, 20.5), width=0.6)
    router.path("DC_IN", "B", (2, 20.5), (2, 17.5), (40, 17.5), p("J1", 1), width=1.2)
    router.path("VIN_SYS", "F", p("F1", 2), (15, 20.5), width=1.2)
    router.path("VIN_SYS", "F", (15, 19.09), (15, 21.64), width=1.2)
    for pin in (1, 2, 3):
        at = p("Q1", pin)
        router.path("VIN_SYS", "F", (15, at[1]), at, width=0.45)
    router.path("VIN_IC", "F", p("Q1", 5), (22, 21), width=1.2)
    for pin in (1, 2):
        at = p("U1", pin)
        router.path("VIN_IC", "F", at, (27.4, at[1]), (27.4, 19.5), width=0.25)
    for at in ((21.3, 21), (22, 21), (22, 20.3), (26.7, 19.5), (27.4, 19.5), (27.4, 18.8)):
        router.via("VIN_IC", at)
    router.path("VIN_IC", "B", (22, 21), (25.5, 21), (25.5, 19.5), (27.4, 19.5), width=1.2)
    router.path("VIN_IC", "F", (26.7, 19.5), (27.4, 19.5), (27.4, 18.8), width=0.6)
    router.path("VIN_IC", "B", (27.4, 19.5), (27.4, 18.8), width=0.8)
    router.path("VIN_IC", "F", p("C2", 1), (18.525, 21), p("Q1", 5), width=0.5)
    for pin in (17, 18):
        at = p("U1", pin)
        router.path("VIN_PROTECTED", "F", at, (32.5, at[1]), (32.5, 21), (34, 19.5), (35, 19.5), width=0.25)
    router.path("VIN_PROTECTED", "F", (35, 19.5), (49, 19.5), p("C3", 1), width=1.2)
    router.path("VIN_PROTECTED", "F", (38, 19.5), p("D3", 1), width=0.8)
    router.path("VIN_PROTECTED", "F", p("C3", 1), (49, 18), (58, 18), p("J2", 1), width=1.2)
    manual = {
        ("J1", "1"),
        ("F1", "1"),
        ("F1", "2"),
        ("Q1", "5"),
        ("C2", "1"),
        ("D3", "1"),
        ("C3", "1"),
        ("J2", "1"),
    }
    manual.update(("Q1", str(pin)) for pin in (1, 2, 3))
    manual.update(("U1", str(pin)) for pin in (1, 2, 17, 18, 25))
    for dx in (-0.9, 0, 0.9):
        for dy in (-0.9, 0, 0.9):
            router.via("AGND", (30 + dx, 22 + dy))
    for dx in (-0.45, 0.45):
        router.via("AGND", (13 + dx, 33))
    manual.add(("U2", "9"))
    # Stagger 0.5-mm-pitch terminals before the general escape search. A
    # nearest-via choice at every land would fence the adjacent terminal in.
    fanouts = {
        3: ((27.4, 21.75), (26.75, 21.6)),
        4: ((27.4, 22.25), (25.5, 22.25)),
        5: ((27.4, 22.75), (26.75, 22.9)),
        6: ((27.4, 23.25), (26.75, 23.5), (25.5, 23.5)),
        7: ((28.75, 24.5), (28.6, 25.25)),
        8: ((29.25, 26.5),),
        9: ((29.75, 24.5), (29.9, 25.25)),
        10: ((30.25, 24.5), (30.5, 25), (30.5, 26.5)),
        12: ((31.25, 24.5), (31.4, 25.25)),
        15: ((32.5, 22.25), (33, 22.7), (34.5, 22.7)),
        16: ((32.5, 21.75), (33.25, 21.85)),
    }
    tasks, escapes = {}, {}
    for pin, path in fanouts.items():
        net = router.pads[("U1", str(pin))][2]
        router.path(net, "F", p("U1", pin), *path, width=0.15)
        router.via(net, path[-1])
        manual.add(("U1", str(pin)))
        tasks.setdefault(net, []).append(path[-1])
    router.path("POWER_RUN", "F", p("Q3", 3), (34.9375, 26.5), (31.4, 25.25), width=0.25)
    manual.add(("Q3", "3"))
    for (ref, pin), (x, y, net) in router.pads.items():
        if net.startswith("unconnected-") or (ref, pin) in manual:
            continue
        at = (x, y)
        tasks.setdefault(net, []).append(at)
        if not ref.startswith("J") and ref != "C3":
            router.endpoint_layers[(net, at)] = (POSES[ref][3] + ".Cu",)
            escapes.setdefault(net, []).append(at)
    roots = {
        "VIN_SYS": (14, 20.5),
        "VIN_IC": (22, 21),
        "VIN_PROTECTED": p("C3", 1),
        "POWER_RUN": (31.4, 25.25),
    }
    for net, at in roots.items():
        if net == "VIN_SYS":
            router.via(net, at)
        router.initially_connected = getattr(router, "initially_connected", {})
        router.initially_connected[net] = [at]
    try:
        connect(router, escapes, SIZE, escape=True)
        tasks = {
            net: [router.escape_points.get((net, at), at) for at in points] for net, points in tasks.items()
        }
        tasks.pop("AGND")  # Through vias/ground THT lands join the saved plane.
        connect(router, tasks, SIZE)
    except AssertionError:
        DEBUG.mkdir(parents=True, exist_ok=True)
        save(board, DEBUG / "route-debug.kicad_pcb")
        raise
    for layer in ("In1.Cu", "B.Cu"):
        board.append(
            read_sexpr(f'''(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "{layer}") (hatch edge .5)
          (connect_pads (clearance .15)) (min_thickness .15)
          (fill yes (thermal_gap .25) (thermal_bridge_width .3))
          (polygon (pts (xy 100.6 100.6) (xy 163.4 100.6) (xy 163.4 143.4) (xy 100.6 143.4))))''')
        )
    save(board, pcb)
    (OUT / "routing-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E23",
                board_size_mm=[*SIZE, 1.6],
                counts=router.counts,
                paths=router.paths,
                main_copper_width_mm=1.2,
                qfn_terminal_neck_width_mm=0.25,
                thermal_via_stencil_process_qualified=False,
                native_verified=False,
                current_or_temperature_qualified=False,
                housing_fit_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E23 copper generated; native DRC/parity/refill and physical qualification required.", flush=True)


if __name__ == "__main__":
    main()
