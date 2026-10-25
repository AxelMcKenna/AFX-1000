"""Generate a separate E12 placed PCB and optionally conservative exploratory copper."""

import argparse
import json
import math
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root, placed_footprint, project_settings
from ...common.reports import sha
from ...common.sexpr import a, read_sexpr, sexpr
from ...power_supply.place import mount

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
OUT = ROOT / "generated"
SIZE = (110, 78)
MOUNTS = [(4, 4), (106, 4), (4, 74), (106, 74)]
POSES = {
    "U1": (30, 43, 0, "F"),
    "U2": (80, 43, 0, "F"),
    "U3": (55, 43, 0, "F"),
    "U4": (55, 18, 0, "F"),
    "U5": (14, 11, 0, "F"),
    "U6": (94, 11, 0, "F"),
    "J1": (50, 6, 90, "F"),
    "J2": (47.38, 70, 90, "F"),
    "J3": (30, 6, 90, "F"),
    "J4": (81, 22, 90, "F"),
    "R1": (38, 36, 270, "F"),
    "R2": (22, 36, 270, "F"),
    "R3": (42, 39.5, 90, "F"),
    "R4": (18, 39.5, 90, "F"),
    "R5": (20, 49, 0, "F"),
    "R6": (40, 49, 180, "F"),
    "R7": (47, 38, 0, "F"),
    "R8": (43, 26, 0, "F"),
    "R9": (43, 30, 0, "F"),
    "R10": (44, 33, 0, "F"),
    "R11": (48, 33, 0, "F"),
    "R12": (38, 26, 0, "F"),
    "R13": (25, 30, 0, "F"),
    "R14": (34, 33, 0, "F"),
    "R15": (34, 30, 0, "F"),
    "R16": (24, 15, 0, "F"),
    "C1": (38, 43, 90, "F"),
    "C2": (22, 43, 90, "F"),
    "C3": (44, 63, 90, "F"),
    "C4": (40, 63, 90, "F"),
    "C5": (48, 63, 90, "F"),
    "C6": (47, 27, 0, "F"),
    "C7": (40, 20, 0, "F"),
    "C8": (14, 6, 0, "F"),
    "C9": (20, 6, 0, "F"),
    "C10": (24, 10, 0, "F"),
    "C11": (29, 15, 0, "F"),
    "C12": (9, 17, 0, "F"),
    "C13": (25, 46.4, 0, "F"),
    "C14": (35, 46.4, 0, "F"),
    "D1": (30, 30, 0, "F"),
    "R17": (88, 36, 270, "F"),
    "R18": (72, 36, 270, "F"),
    "R19": (92, 39.5, 90, "F"),
    "R20": (68, 39.5, 90, "F"),
    "R21": (70, 49, 0, "F"),
    "R22": (90, 49, 180, "F"),
    "R23": (63, 38, 0, "F"),
    "R24": (65, 26, 0, "F"),
    "R25": (65, 30, 0, "F"),
    "R26": (62, 33, 0, "F"),
    "R27": (66, 33, 0, "F"),
    "R28": (65, 12, 0, "F"),
    "R29": (85, 30, 0, "F"),
    "R30": (84, 33, 0, "F"),
    "R31": (80, 34, 0, "F"),
    "R32": (101, 16, 0, "F"),
    "C15": (88, 43, 90, "F"),
    "C16": (72, 43, 90, "F"),
    "C17": (65, 63, 90, "F"),
    "C18": (61, 63, 90, "F"),
    "C19": (69, 63, 90, "F"),
    "C20": (61, 27, 0, "F"),
    "C21": (64, 18, 0, "F"),
    "C22": (94, 6, 0, "F"),
    "C23": (100, 6, 0, "F"),
    "C24": (104, 11, 0, "F"),
    "C25": (95, 20, 0, "F"),
    "C26": (87, 16, 0, "F"),
    "C27": (75, 46.4, 0, "F"),
    "C28": (85, 46.4, 0, "F"),
    "D2": (80, 30, 0, "F"),
    "R33": (36, 15, 0, "F"),
    "C29": (58, 37, 0, "F"),
    "C30": (49, 49, 0, "F"),
    "C31": (49, 24, 0, "F"),
    "C32": (61, 23, 0, "F"),
    "C33": (34, 10, 0, "F"),
    "C34": (40, 10, 0, "F"),
}


def build(cli, route=False, reviewed=False):
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    _, pins = netlist(PARENT / "generated/netlist.xml")
    parts = json.loads((PARENT / "components.json").read_text())
    assert set(POSES) == {c["ref"] for c in parts}
    nets = {n: i + 1 for i, n in enumerate(sorted({n for r in pins.values() for n in r.values()}))}
    board = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew)
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal)
       (3 "In3.Cu" signal) (4 "In4.Cu" power) (31 "B.Cu" signal)
       (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
       (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
       (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend([a("net"), code, "/" + name] for name, code in nets.items())
    library = footprint_root(str(cli))
    hashes = {}
    for c in parts:
        name, fp = c["footprint"].split(":")
        path = library / (name + ".pretty") / (fp + ".kicad_mod")
        component = dict(
            ref=c["ref"],
            value=c["part"],
            footprint=c["footprint"],
            nets=pins[c["ref"]],
            source=c.get("source", ""),
            mpn="",
        )
        board.append(placed_footprint(component, POSES[c["ref"]], path, nets, namespace="rmx:E12-PCB:"))
        hashes[c["footprint"]] = sha(path)
    for i, xy in enumerate(MOUNTS, 1):
        board.append(mount(f"H{i}", xy))
    for p, q in [((0, 0), (SIZE[0], 0)), ((SIZE[0], 0), SIZE), (SIZE, (0, SIZE[1])), ((0, SIZE[1]), (0, 0))]:
        board.append(
            read_sexpr(
                f'(gr_line (start {p[0] + 100} {p[1] + 100}) (end {q[0] + 100} {q[1] + 100}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    for x, y in MOUNTS:
        points = " ".join(
            f"(xy {100 + x + 3.7 * math.cos(t * math.pi / 16):.6f} {100 + y + 3.7 * math.sin(t * math.pi / 16):.6f})"
            for t in range(32)
        )
        board.append(
            read_sexpr(f"""(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu" "B.Cu")
          (hatch edge .5) (connect_pads (clearance .25)) (min_thickness .25)
          (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
          (polygon (pts {points})))""")
        )
    code = nets["AGND"]
    for layer in ["In1.Cu", "In4.Cu"]:
        board.append(
            read_sexpr(f"""(zone (net {code}) (net_name "/AGND") (layer "{layer}")
          (hatch edge .5) (connect_pads yes (clearance .25)) (min_thickness .25)
          (fill yes (thermal_gap .3) (thermal_bridge_width .4))
          (polygon (pts (xy 100.6 100.6) (xy 209.4 100.6) (xy 209.4 177.4) (xy 100.6 177.4))))""")
        )
    (OUT / "placed.kicad_pcb").write_text(sexpr(board) + "\n")
    routes, failed, removed_vias = [], [], []
    if route:
        from .router import AdcRouter

        router = AdcRouter(board)
        router.route_all()
        removed_vias = router.prune_unused_vias()
        routes, failed = router.routes, router.failed
    if reviewed:
        recipe = json.loads((ROOT / "reviewed-copper.json").read_text())
        assert recipe["placed_pcb_sha256"] == sha(OUT / "placed.kicad_pcb"), (
            "Placement or library baseline changed"
        )
        board.extend(read_sexpr(n) for n in recipe["copper_s_expressions"])
    (ROOT / "adc_driver.kicad_pcb").write_text(sexpr(board) + "\n")
    pro = json.loads((PARENT / "adc_driver.kicad_pro").read_text())
    pro["meta"]["filename"] = "adc_driver.kicad_pro"
    settings = project_settings()
    settings["rules"]["min_clearance"] = 0.15
    pro["board"] = {"design_settings": settings}
    (ROOT / "adc_driver.kicad_dru").write_text("""(version 1)
(rule "general copper clearance" (constraint clearance (min 0.25mm)))
(rule "VSSOP adjacent library lands"
 (condition "A.Type == 'Pad' && B.Type == 'Pad' && ((A.memberOfFootprint('U1') && B.memberOfFootprint('U1')) || (A.memberOfFootprint('U2') && B.memberOfFootprint('U2')) || (A.memberOfFootprint('U5') && B.memberOfFootprint('U5')) || (A.memberOfFootprint('U6') && B.memberOfFootprint('U6')))")
 (constraint clearance (min 0.15mm)))
""")
    (ROOT / "adc_driver.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    local = ROOT / "RMX_Power.pretty"
    local.mkdir(exist_ok=True)
    (local / "M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    table = (PARENT / "fp-lib-table").read_text().rstrip().removesuffix(")")
    table += '\n(lib (name "RMX_Power") (type "KiCad") (uri "${KIPRJMOD}/RMX_Power.pretty") (options "") (descr "M2 clearance only")))\n'
    (ROOT / "fp-lib-table").write_text(table)
    (OUT / "inputs.json").write_text(
        json.dumps(
            dict(
                board_size_mm=[*SIZE, 1.6],
                mounts_relative_mm=MOUNTS,
                poses=POSES,
                footprint_library_sha256=hashes,
                parent_schematic_sha256=sha(PARENT / "adc_driver.kicad_sch"),
                native_origin_mm=[100, 100],
                routes=routes,
                removed_redundant_single_layer_vias=removed_vias,
                failed_search_attempts_before_ground_repairs=failed,
                reviewed_recipe_replayed=reviewed,
                reviewed_recipe_sha256=sha(ROOT / "reviewed-copper.json") if reviewed else None,
                native_drc_required=True,
                physical_fit_verified=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"E12 candidate:79parts,{SIZE[0]}x{SIZE[1]}mm; exploratory routing:{route}; check native DRC before use"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--route", action="store_true")
    modes.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    build(args.kicad_cli, args.route, args.reviewed)


if __name__ == "__main__":
    main()
