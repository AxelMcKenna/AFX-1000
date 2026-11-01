"""Deliberate P03 current-distribution planes and actual terminal via banks.

These are implemented copper, not ampacity/transfer-impedance qualification.
Native fill/connectivity and finite geometry extraction remain mandatory.
"""

import json
import math

from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import transform
from .route import PowerRouter, coded, named
from .spec import ROOT

OUT = ROOT / "generated"


def zone(net, code, layer, points, priority=1):
    points = " ".join(f"(xy {100 + x} {100 + y})" for x, y in points)
    return read_sexpr(f'''(zone (net {code}) (net_name "/{net}") (layer "{layer}")
      (name "P03_CURRENT_DISTRIBUTION") (priority {priority})
      (hatch edge .5) (connect_pads yes (clearance .16)) (min_thickness .16)
      (fill yes (thermal_gap .25) (thermal_bridge_width .8)) (polygon (pts {points})))''')


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def implement():
    pcb = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    tree[:] = [
        z
        for z in tree
        if not (
            isinstance(z, list)
            and z
            and z[0] == "zone"
            and children(z, "name")
            and first(z, "name")[1] == "P03_CURRENT_DISTRIBUTION"
        )
    ]
    # Wide B.Cu feed replaces obsolete narrow front-side cross-board traces.
    # Retain guard-local fanout; remove long unanchored remote stubs in one edit
    # rather than deleting one0.125mm dangling fragment per native refill.
    netnames = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    obsolete = []
    for track in list(children(tree, "segment")):
        if netnames[str(first(track, "net")[1])] != "DC_IN":
            continue
        if max(float(first(track, t)[1]) - 100 for t in ("start", "end")) > 40:
            tree.remove(track)
            obsolete.append([list(first(track, t)[1:3]) for t in ("start", "end")])
    router = PowerRouter(tree)
    fp_by_ref = {
        next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
        for fp in children(tree, "footprint")
    }
    terminal_vias = {}
    for ref, net in (("J20", "AGND"), ("J21", "AGND"), ("J23", "5V_DIG_SRC"), ("J24", "V5_REG_SRC")):
        at = first(fp_by_ref[ref], "at")
        x, y = [float(v) - 100 for v in at[1:3]]
        added = []
        for i in range(16):
            xy = (x + 3.3 * math.cos(i * math.pi / 8), y + 3.3 * math.sin(i * math.pi / 8))
            if router.safe_via(net, xy):
                router.via(net, xy)
                added.append(xy)
        terminal_vias[ref] = dict(net=net, new_vias_mm=added, desired_bank_count=16)
        circle = [
            (x + 4.25 * math.cos(i * math.pi / 32), y + 4.25 * math.sin(i * math.pi / 32)) for i in range(64)
        ]
        tree.append(zone(net, router.nets[net], "B.Cu", circle, 2))
    # Actual source-positive current planes; source feedback never crosses E28.
    # Keep the lower analog source separate from the upper digital source.
    for layer in ("In2.Cu", "In3.Cu"):
        tree.append(zone("VIN_PROTECTED", router.nets["VIN_PROTECTED"], layer, rect(17, 0.6, 151, 44), 0))
        if layer == "In2.Cu":
            tree.append(zone("5V_DIG_SRC", router.nets["5V_DIG_SRC"], layer, rect(33, 0.6, 62, 21), 1))
            tree.append(zone("V5_REG_SRC", router.nets["V5_REG_SRC"], layer, rect(31, 24, 65, 42), 1))
    # Short local VIN hot-loop copper around the two real buck VIN terminals.
    for ref in ("U20", "U23"):
        at = first(fp_by_ref[ref], "at")
        x, y = [float(v) - 100 for v in at[1:3]]
        tree.append(
            zone("VIN_PROTECTED", router.nets["VIN_PROTECTED"], "F.Cu", rect(x - 4, y - 6, x + 4, y + 5), 1)
        )
    # The rear inlet is at the right edge; the guard is intentionally separate.
    # These are genuine two-ounce current paths, not a zero-ohm jumper/fuse.
    points = [
        (7, 0.6),
        (19, 0.6),
        (19, 18),
        (125, 18),
        (125, 14),
        (133, 14),
        (133, 18),
        (134, 18),
        (134, 24),
        (7, 24),
    ]
    tree.append(zone("DC_IN", router.nets["DC_IN"], "B.Cu", points, 0))
    # Actual reverse-blocking FET drain to guard input; a separate live node.
    for layer in ("F.Cu", "In2.Cu", "In3.Cu", "B.Cu"):
        tree.append(zone("VIN_IC", router.nets["VIN_IC"], layer, rect(9, 3.5, 24.5, 12.5), 2))
    # Bridge selected wide pads/capacitors onto real planes with capped barrels.
    # Fine-pitch pins are attempted only when actual opposite-face copper permits.
    wanted = {"DC_IN", "VIN_IC", "VIN_PROTECTED", "5V_DIG_SRC", "V5_REG_SRC"}
    local = []
    for pad in router.pads:
        if pad["net"] not in wanted or pad.get("through") or len(pad["layers"]) != 1:
            continue
        if router.safe_via(pad["net"], pad["xy"]):
            router.via(pad["net"], pad["xy"])
            local.append(dict(ref=pad["ref"], pin=pad["pin"], net=pad["net"], at_mm=pad["xy"]))
    # The digital inductor's output land gets a real parallel via bank. Each
    # proposed barrel must pass actual current native copper/hole screening.
    fp = fp_by_ref["L20"]
    pad = next(p for p in children(fp, "pad") if p[1] == "2")
    cx, cy = transform(fp, first(pad, "at")[1:3])
    cx -= 100
    cy -= 100
    for dx in (-0.6, 0, 0.6):
        for dy in (-1.2, -0.6, 0, 0.6, 1.2):
            xy = (cx + dx, cy + dy)
            if router.safe_via("5V_DIG_SRC", xy):
                router.via("5V_DIG_SRC", xy)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (OUT / "current-copper-intent.json").write_text(
        json.dumps(
            dict(
                terminal_via_banks=terminal_vias,
                removed_obsolete_front_feed_track_endpoints=obsolete,
                local_plane_vias=local,
                native_connectivity_verified=False,
                minimum_neck_and_ampacity_extracted=False,
                source_port_resistance_measured=False,
                physical_qualified=False,
                build_ready=False,
                notes=[
                    "Every current path requires native filled copper and finite extraction.",
                    "Copper zones do not make discrete regulator/reference ground electrodes equipotential.",
                    "Via-in-pad requires a qualified filled/capped construction; no open solder-wicking holes.",
                ],
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "P03 deliberate current planes and terminal via banks implemented; extraction/physical qualification false",
        flush=True,
    )


if __name__ == "__main__":
    implement()
