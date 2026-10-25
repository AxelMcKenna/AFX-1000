#!/usr/bin/env python3
"""Generate buck/raw/positive-linear/negative-reference copper; the board remains incomplete."""

import argparse
import json
import math
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...control_inputs.board import Routing
from .analog_5v import MOVES as ANALOG_MOVES
from .analog_5v import QUIET_PAD as ANALOG_PAD
from .analog_5v import QUIET_VIAS as ANALOG_QUIET
from .analog_5v import add_output_plane
from .analog_5v import route as route_analog
from .junctions import split_ground_junctions
from .negative_amp import MOVES as NEGATIVE_MOVES
from .negative_amp import route as route_negative_amp
from .negative_amp import route_distribution as negative_amp_distribution
from .negative_power import MOVES as POWER_MOVES
from .negative_power import add_input_planes
from .negative_power import route as route_negative_power
from .negative_power import route_distribution as negative_power_distribution
from .negative_reference import QUIET_PAD as NREF_PAD
from .negative_reference import QUIET_VIAS as NREF_QUIET
from .negative_reference import route as route_nref
from .negative_reference import route_distribution as nref_distribution
from .negative_target import ALIASES as TARGET_ALIASES
from .negative_target import MOVES as TARGET_MOVES
from .negative_target import route as route_negative_target
from .negative_target import route_distribution as negative_target_distribution
from .positive_linear import MOVES as POSITIVE_MOVES
from .positive_linear import QUIET_VIAS as POSITIVE_QUIET
from .positive_linear import add_output_planes as add_positive_planes
from .positive_linear import route as route_positive
from .positive_linear import route_distribution as positive_distribution
from .pre_buck import MOVES as PRE_MOVES
from .pre_buck import QUIET_VIAS
from .pre_buck import route as route_pre
from .raw_17 import MOVES as RAW_MOVES
from .raw_17 import QUIET_VIAS as RAW_QUIET
from .raw_17 import route as route_raw
from .raw_17 import route_controls as controls_raw
from .raw_22 import MOVES as HI_MOVES
from .raw_22 import QUIET_VIAS as HI_QUIET
from .raw_22 import route as route_hi
from .raw_22 import route_controls as controls_hi
from .raw_22 import route_power as power_hi

ROOT = Path(__file__).resolve().parent
SUPPLY = ROOT.parent
OUT = ROOT / "generated"


def generate(library):
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    (OUT / "filled.kicad_pcb").unlink(missing_ok=True)
    source = SUPPLY / "power_supply.kicad_pcb"
    board = read_sexpr(source.read_text())
    assert not any(children(board, key) for key in ("segment", "via", "zone"))
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net") if str(n[1]) != "0"}
    # Preserve the checked E24 source; enlarge only this routing candidate.
    for line in children(board, "gr_line"):
        if first(line, "layer")[1] == "Edge.Cuts":
            for tag in ("start", "end"):
                point = first(line, tag)
                point[1:3] = [
                    190 if float(point[1]) == 184 else point[1],
                    144 if float(point[2]) == 138 else point[2],
                ]
    # Keep the two-terminal nets and complete standard footprint geometry.
    # Recreate from the original KiCad library rather than rotating only pads.
    components = {c["ref"]: c for c in json.loads((SUPPLY / "components.json").read_text())}
    report = json.loads((SUPPLY / "generated/placement-inputs.json").read_text())
    moves = {
        "C22": (55.3, 12.3, 270, "F"),
        "C16": (60.8, 13.6, 270, "F"),
        "C63": (43.2, 11.7, 90, "F"),
        "C18": (67.9, 6.45, 180, "F"),
        "C19": (79.5, 13.5, 0, "F"),
        "C21": (54.3, 8.2, 90, "F"),
        "C17": (60.8, 17.25, 270, "F"),
        "R8": (52.9, 11.8, 0, "B"),
        "R9": (52.7, 15, 0, "B"),
        "R10": (61, 6.3, 270, "F"),
        "R51": (61, 9.8, 270, "F"),
        "R11": (63.9, 6, 0, "F"),
    }
    moves.update(PRE_MOVES)
    moves.update(RAW_MOVES)
    moves.update(HI_MOVES)
    moves.update(ANALOG_MOVES)
    moves.update(POSITIVE_MOVES)
    moves.update(NEGATIVE_MOVES)
    moves.update(TARGET_MOVES)
    moves.update(POWER_MOVES)
    for index, fp in enumerate(board):
        if not isinstance(fp, list) or not fp or fp[0] != "footprint":
            continue
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref not in moves:
            continue
        c = components[ref]
        pin_nets = {
            str(p[1]): str(first(p, "net")[-1]).lstrip("/") for p in children(fp, "pad") if children(p, "net")
        }
        lib, name = c["footprint"].split(":")
        board[index] = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets=pin_nets),
            moves[ref],
            (SUPPLY if lib == "RMX_Power" else library) / (lib + ".pretty") / (name + ".kicad_mod"),
            nets,
            namespace="rmx:power-routing:",
        )
    # KiCad's deliberately floating pins use reserved names without the root
    # net-label slash; moving an IC must retain that distinction.
    for fp in children(board, "footprint"):
        for pad in children(fp, "pad"):
            if children(pad, "net") and str(first(pad, "net")[-1]).startswith("/unconnected-"):
                first(pad, "net")[-1] = str(first(pad, "net")[-1])[1:]
    r = Routing(board, nets)
    p = r.p
    # Local input bypass return closes on the same F.Cu layer, without vias.
    r.path("VIN_PROTECTED", "F", p("U2", 3), (56.6, 13.75), (56.6, 12.5), p("C22", 1), width=0.35)
    r.path("AGND", "F", p("U2", 4), (55.5, 14.25), p("C22", 2), width=0.35)
    # Narrow neck only at SOT583; expand after clearing the neighboring pins.
    r.path("DIG_SW", "F", p("U2", 5), (59.45, 14.25), (59.75, 14.55), width=0.3)
    r.path("DIG_SW", "F", (59.75, 14.55), p("C16", 2), (61.95, 13.5), p("L4", 1), width=0.8)
    r.path("DIG_BST", "F", p("U2", 6), (59.4, 13.75), p("C16", 1), width=0.26)
    # Divider stays on F.Cu above the IC; it does not run under SW/L4.
    r.path("DIG_FB_TRIM", "F", p("R10", 2), p("R51", 1), width=0.26)
    r.path("DIG_FB", "F", p("R51", 2), (59.8, 10.7125), (59.8, 11.3), (58.74, 11.3), p("U2", 8), width=0.26)
    r.path("DIG_FB", "F", p("R11", 1), (62.2, 6), (62.2, 10.7125), p("R51", 2), width=0.26)
    # Sense the declared source port rather than an upstream capacitor land.
    # The input ground pin is also the feedback reference: dedicated Kelvin
    # return vias are isolated from In1 to avoid sharing the power-plane drop.
    r.path("AGND", "F", p("R11", 2), (65, 4.75), width=0.26)
    r.via("AGND", (65, 4.75))
    r.path("AGND", "In4", (65, 4.75), (63.2, 4.75), (63.2, 17.5), (58, 17.5), (58, 15.2), width=0.26)
    r.via("AGND", (58, 15.2))
    r.path("AGND", "F", (58, 15.2), (58, 14.25), p("U2", 4), width=0.26)
    r.path("5V_DIG_SRC", "In2", p("J3", 1), (78, 21.2), (78, 11), (62, 11), (62, 4.25), width=0.26)
    r.via("5V_DIG_SRC", (62, 4.25))
    r.path("5V_DIG_SRC", "F", (62, 4.25), p("R10", 1), width=0.26)
    # All four bulk capacitors now sit on F.Cu. These are explicit power
    # connections, distinct from the low-current sense path.
    r.path("VIN_PROTECTED", "F", p("C21", 1), (55.8, 9.675), p("C20", 1), width=0.8)
    r.path("VIN_PROTECTED", "F", p("C20", 1), (56.6, 10.8), p("C22", 1), width=0.8)
    r.path("5V_DIG_SRC", "F", p("L4", 2), (73.325, 8.5), (69.375, 8.5), p("C18", 1), width=1.2)
    r.path("5V_DIG_SRC", "F", p("L4", 2), p("C19", 1), width=1.2)
    r.path("5V_DIG_SRC", "F", p("C19", 1), (78.025, 21.2), p("J3", 1), width=1.2)
    # Parallel conventional via banks: no via-in-pad/capped process assumed.
    banks = {
        "input_vin": ("VIN_PROTECTED", [(52.1, 8.9), (52.1, 9.675), (52.1, 10.45)]),
        "input_ground": ("AGND", [(56.5, 5.5), (57.25, 5.5), (58, 5.5)]),
        "ic_ground": ("AGND", [(55.3, 14.8), (56.05, 14.8), (56.8, 14.8)]),
        "output_ground_1": ("AGND", [(65, 8), (65, 8.75), (68.5, 9.75)]),
        "output_ground_2": ("AGND", [(82.6, 12.75), (82.6, 13.5), (82.6, 14.25)]),
    }
    for net, points in banks.values():
        for at in points:
            r.via(net, at)
        r.path(net, "F", *points, width=0.8)
    r.path("VIN_PROTECTED", "F", p("C21", 1), (52.1, 9.675), width=0.8)
    r.path(
        "VIN_PROTECTED", "In4", p("J1", 1), (52.1, 3), (52.1, 8.9), (52.1, 9.675), (52.1, 10.45), width=1.4
    )
    r.path(
        "AGND",
        "F",
        p("C21", 2),
        (54.3, 5.5),
        (56.5, 5.5),
        (57.25, 5.5),
        (57.54, 5.5),
        (58, 5.5),
        p("C20", 2),
        width=1.2,
    )
    r.path("AGND", "F", p("J1", 2), (57.54, 5.5), width=1.2)
    r.path("AGND", "F", p("C22", 2), (55.3, 14.8), width=0.35)
    r.path("AGND", "F", p("C18", 2), (65, 8), width=1.2)
    r.path("AGND", "F", p("C19", 2), (82.6, 13.5), width=1.2)
    # Explicit In1 spines allow independent graph verification even without
    # relying on a filled zone's electrical connectivity.
    r.path("AGND", "In1", (56.5, 5.5), (57.25, 5.5), (58, 5.5), width=1.2)
    r.path(
        "AGND",
        "In1",
        (56.5, 5.5),
        (57.8, 5.5),
        (57.8, 8.6),
        (64, 8.6),
        (65, 8.6),
        (68.5, 8.6),
        (82.6, 8.6),
        (82.6, 12.75),
        (82.6, 13.5),
        (82.6, 14.25),
        width=1.2,
    )
    r.path("AGND", "In1", (65, 8), (65, 8.6), (65, 8.75), (68.5, 9.75), (68.5, 8.6), width=1.2)
    r.path(
        "AGND",
        "In1",
        (57.8, 8.6),
        (57.8, 10),
        (55.3, 10),
        (55.3, 14.8),
        (56.05, 14.8),
        (56.8, 14.8),
        width=1.2,
    )
    r.path("AGND", "In1", (82.6, 13.5), (82.6, 23.74), p("J3", 2), width=1.2)
    # Low-current SS and enable traces use In3, shielded by the In1 return.
    r.path("DIG_SS", "F", p("U2", 7), (59.28, 13.25), (59.55, 12.4), width=0.26)
    r.via("DIG_SS", (59.55, 12.4))
    r.path("DIG_SS", "In3", (59.55, 12.4), (62.1, 16.5), width=0.26)
    r.via("DIG_SS", (62.1, 16.5))
    r.path("DIG_SS", "F", (62.1, 16.5), p("C17", 1), width=0.26)
    r.path("AGND", "F", p("C17", 2), (60.8, 19.7), width=0.26)
    r.via("AGND", (60.8, 19.7))
    r.path("AGND", "In1", (60.8, 19.7), (55.3, 19.7), (55.3, 16.5), (55.3, 14.8), width=0.26)
    # EN escapes inside the lead rows: the left external corridor is occupied
    # by the local VIN bypass. No via lies in a SOT583 solder land.
    r.path("SUPPLY_ENABLE", "F", p("U2", 2), (58, 13.25), (58, 11.5), width=0.26)
    r.via("SUPPLY_ENABLE", (58, 11.5))
    r.path("SUPPLY_ENABLE", "In3", (58, 11.5), (54, 13.5), width=0.26)
    r.via("SUPPLY_ENABLE", (54, 13.5))
    r.path("SUPPLY_ENABLE", "B", p("R8", 2), (54, 13.5), (51.7875, 13.5), p("R9", 1), width=0.26)
    r.path("POWER_READY", "In3", p("J5", 2), (66.54, 1), (51, 1), (51, 14), width=0.26)
    r.via("POWER_READY", (51, 14))
    r.path("POWER_READY", "B", (51, 14), (51, 11.5), p("R8", 1), width=0.26)
    r.path("AGND", "B", p("R9", 2), (54, 15), (54, 16.5), (54.8, 16.5), width=0.26)
    r.via("AGND", (54.8, 16.5))
    r.path("AGND", "In1", (54.8, 16.5), (55.3, 16.5), width=0.26)
    r.path("AGND", "In1", p("J5", 1), (64, 8.6), width=0.8)
    route_pre(r)
    raw_tasks = route_raw(r, controls=False)
    hi_tasks = route_hi(r, controls=False)
    route_analog(r)
    route_positive(r)
    route_nref(r)
    route_negative_amp(r)
    route_negative_target(r)
    route_negative_power(r)
    power_hi(r)
    controls_raw(r, raw_tasks)
    controls_hi(r, hi_tasks)
    positive_distribution(r)
    nref_distribution(r)
    negative_amp_distribution(r)
    negative_target_distribution(r)
    negative_power_distribution(r)
    from .negative_power import remove_redundant_vias

    remove_redundant_vias(r)
    split_ground_junctions(board, "In1.Cu")
    split_ground_junctions(board, "In2.Cu")
    split_ground_junctions(board, "In3.Cu")
    r.counts["segments"] = len(children(board, "segment"))
    # All-layer fixing clearance, including the underside washer/head reserve.
    copper = '"F.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu" "B.Cu"'
    for x, y in ((4, 4), (74, 4), (4, 34), (74, 34)):
        radius = 3.7 / math.cos(math.pi / 32)
        points = " ".join(
            f"(xy {100 + x + radius * math.cos(i * math.pi / 16):.6f} {100 + y + radius * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layers {copper}) (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .15)
          (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
          (polygon (pts {points})))""")
        )
    board.append(
        read_sexpr(f"""(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "In1.Cu") (hatch edge .5)
      (connect_pads yes (clearance .15)) (min_thickness .15) (fill yes (thermal_gap .2) (thermal_bridge_width .3))
      (polygon (pts (xy 100.6 100.6) (xy 189.4 100.6) (xy 189.4 143.4) (xy 158 143.4) (xy 158 125.6) (xy 100.6 125.6))))""")
    )
    # Only the quiet-return via annuli are isolated from the power ground
    # plane; the separate In4 return reaches the regulator's ground pad.
    for x, y in (
        (65, 4.75),
        (58, 15.2),
        *QUIET_VIAS,
        *RAW_QUIET,
        *HI_QUIET,
        *ANALOG_QUIET,
        *POSITIVE_QUIET,
        *NREF_QUIET,
        *[at for net, at in r.vias if net == "NEG_TARGET_RETURN_ROUTE"],
    ):
        radius = 0.75 / math.cos(math.pi / 32)
        points = " ".join(
            f"(xy {100 + x + radius * math.cos(i * math.pi / 16):.6f} {100 + y + radius * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layer "In1.Cu") (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .15)
          (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
          (polygon (pts {points})))""")
        )
    # The film filter's through-hole ground pad has a larger annulus.
    for x, y in (ANALOG_PAD, NREF_PAD):
        radius = 1.2 / math.cos(math.pi / 32)
        points = " ".join(
            f"(xy {100 + x + radius * math.cos(i * math.pi / 16):.6f} {100 + y + radius * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layer "In1.Cu") (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .15)
      (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
      (polygon (pts {points})))""")
        )
    add_output_plane(board, nets)
    add_positive_planes(board, nets)
    add_input_planes(board, nets)
    pcb = ROOT / "power_supply.kicad_pcb"
    pcb.write_text("(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n")
    (ROOT / "power_supply.kicad_pro").write_bytes((SUPPLY / "power_supply.kicad_pro").read_bytes())
    (ROOT / "fp-lib-table").write_text(
        (SUPPLY / "fp-lib-table")
        .read_text()
        .replace("${KIPRJMOD}/RMX_Power.pretty", "${KIPRJMOD}/../RMX_Power.pretty")
    )
    inputs = dict(
        stage="main-power-complete-routing-candidate",
        board_size_mm=[90, 44, 1.6],
        negative_target_route_masks=TARGET_ALIASES,
        negative_target_quiet_vias_mm=[list(at) for net, at in r.vias if net == "NEG_TARGET_RETURN_ROUTE"],
        negative_set_neck_width_mm=0.15,
        source_placement_sha256=sha(source),
        source_poses_sha256=sha(SUPPLY / "generated/placement-inputs.json"),
        moved_components={
            ref: dict(previous=report["poses"][ref], candidate=pose) for ref, pose in moves.items()
        },
        routed_segments=r.counts["segments"],
        through_vias=r.counts["vias"],
        via_banks=banks,
        ground_plane="In1.Cu both bucks and both raw generators",
        analog_output_plane="In4.Cu V5_REG_SRC",
        fully_routed=False,
        native_verification_required=True,
        thermal_or_ampacity_qualified=False,
        switching_or_emi_qualified=False,
        housing_fit_verified=False,
        build_ready=False,
    )
    (OUT / "routing-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    print(
        f"Unverified supply candidate: {r.counts['segments']} segments, {r.counts['vias']} vias; native verification required"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    args = parser.parse_args()
    generate(footprint_root(str(args.kicad_cli.resolve())))
