"""Generate a separate E10 placed PCB and optionally conservative exploratory copper."""

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
SIZE = (54, 36)
MOUNTS = [(3.8, 3.8), (50.2, 3.8), (3.8, 32.2), (50.2, 32.2)]
POSES = {
    "U1": (35, 18, 0, "F"),
    "K1": (12, 18, 0, "F"),
    "J1": (9, 7, 90, "F"),
    "J2": (44, 27.5, 90, "F"),
    "J3": (39, 6, 90, "F"),
    "J4": (7, 27, 90, "F"),
    "R1": (5, 12, 0, "F"),
    "R2": (9, 10.5, 0, "F"),
    "R3": (23, 15.8, 90, "F"),
    "R4": (29, 23, 0, "F"),
    "R5": (28.5, 17.365, 180, "F"),
    "R6": (28.5, 20.2, 180, "F"),
    "R7": (39, 27, 0, "F"),
    "R8": (19, 8, 0, "F"),
    "R9": (19, 11, 0, "F"),
    "R10": (23, 26, 90, "F"),
    "R11": (41, 23.5, 0, "F"),
    "R12": (42, 17.365, 0, "F"),
    "R13": (43, 20.5, 0, "F"),
    "R14": (44, 31, 0, "F"),
    "C1": (27, 11, 0, "F"),
    "C2": (33, 23, 0, "F"),
    "C3": (28, 28, 0, "F"),
    "C4": (45, 23.5, 0, "F"),
    "C5": (39, 13, 0, "F"),
    "C6": (35, 23.5, 0, "B"),
    "C7": (44, 12, 0, "F"),
    "C8": (48, 17, 0, "F"),
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
        board.append(placed_footprint(component, POSES[c["ref"]], path, nets, namespace="rmx:E10-PCB:"))
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
    (OUT / "placed.kicad_pcb").write_text(sexpr(board) + "\n")
    routes, failed = [], []
    if route:
        from .router import InputRouter

        router = InputRouter(board)
        router.route_all()
        routes, failed = router.routes, router.failed
    if reviewed:
        recipe = json.loads((ROOT / "reviewed-copper.json").read_text())
        assert recipe["placed_pcb_sha256"] == sha(OUT / "placed.kicad_pcb"), (
            "Placement or library baseline changed"
        )
        board.extend(read_sexpr(n) for n in recipe["copper_s_expressions"])
    (ROOT / "input_range.kicad_pcb").write_text(sexpr(board) + "\n")
    pro = json.loads((PARENT / "input_range.kicad_pro").read_text())
    pro["meta"]["filename"] = "input_range.kicad_pro"
    pro["board"] = {"design_settings": project_settings()}
    (ROOT / "input_range.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
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
                parent_schematic_sha256=sha(PARENT / "input_range.kicad_sch"),
                native_origin_mm=[100, 100],
                routes=routes,
                failed_search_attempts_before_ground_repairs=failed,
                reviewed_recipe_replayed=reviewed,
                reviewed_recipe_sha256=sha(ROOT / "reviewed-copper.json") if reviewed else None,
                pcb_routed=False,
                physical_fit_verified=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"E10 candidate:28parts,{SIZE[0]}x{SIZE[1]}mm; exploratory routing:{route}; check native DRC before use"
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
