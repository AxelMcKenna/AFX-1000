#!/usr/bin/env python3
"""E06 output-board footprint placement. No copper routing is generated.

Standard footprint geometry is embedded as in a normal KiCad PCB; libraries
remain external. Run check_placement.py before using the CAD placement packet.
"""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from ..common.placement import footprint_root, placed_footprint, project_settings
from ..common.sexpr import a, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
ORIGIN = (100, 100)
SIZE = (82, 34)
DATUM = (206, 40, 3.8)
MOUNTS = [(4, 4), (78, 4), (4, 30), (78, 30)]
POSES = {
    "U1": (10, 10, 0, "F"),
    "U2": (10, 23, 0, "F"),
    "R1": (4, 8, 0, "F"),
    "R2": (4, 11, 0, "F"),
    "R5": (16.5, 10.5, 0, "F"),
    "R6": (16.5, 13.5, 0, "F"),
    "R9": (4, 19, 0, "F"),
    "R10": (4, 24.5, 0, "F"),
    "R13": (16.5, 23.5, 0, "F"),
    "R14": (16.5, 26.5, 0, "F"),
    "R17": (10, 16, 0, "F"),
    "R18": (16.5, 16, 0, "F"),
    "C5": (16.5, 6.5, 0, "F"),
    "C6": (5.5, 15.5, 0, "F"),
    "C7": (16.5, 19, 0, "F"),
    "C8": (9.5, 25.8, 0, "B"),
    "C9": (59, 27, 0, "F"),
    "C10": (65, 27, 0, "F"),
    "C11": (71, 27, 0, "F"),
    "C12": (78, 22, 0, "F"),
    "K3": (65, 17, 0, "F"),
    "J1": (10.5, 3, 90, "F"),
    "J2": (65, 3, 90, "F"),
    "J3": (75, 13, 0, "F"),
    "J4": (59.5, 31, 90, "F"),
}
for i, ref in enumerate(("R3", "R7", "R11", "R15")):
    POSES[ref] = (20 + i * 12, 16, 0, "B")
for i, ref in enumerate(("R4", "R8", "R12", "R16")):
    POSES[ref] = (26 + i * 12, 16, 90, "B")
for i, x in enumerate((229.75, 239.25, 248.75, 258.25)):
    for row in (0, 1):
        y = (51.25 if i in (0, 3) else 49.25) + row * 13.5
        ref = (("C1", "C13", "C2", "C14") if row == 0 else ("C3", "C15", "C4", "C16"))[i]
        POSES[ref] = (x - DATUM[0] - 2.5, y - DATUM[1], 0, "F")


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E06:" + name))


def mount_footprint(reference="REF**", position=None):
    at = f"(at {position[0]} {position[1]})" if position else ""
    return read_sexpr(f'''(footprint "RMX_Output:M2_Insert_Clearance" (layer "F.Cu") {at}
      (attr board_only exclude_from_pos_files exclude_from_bom)
      (property "Reference" "{reference}" (at 0 -4.2) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (property "Value" "M2_CLEARANCE" (at 0 4.2) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12)) (hide yes)))
      (fp_circle (center 0 0) (end 2.8 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center 0 0) (end 3.7 0) (stroke (width .05) (type solid)) (fill none) (layer "B.CrtYd"))
      (fp_circle (center 0 0) (end 1.2 0) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))
      (fp_circle (center 0 0) (end 1.2 0) (stroke (width .1) (type solid)) (fill none) (layer "B.Fab"))
      (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    args = parser.parse_args()
    fp = footprint_root(args.kicad_cli, args.footprint_dir)
    components = json.loads((ROOT / "components.json").read_text())
    assert set(POSES) == {c["ref"] for c in components}
    nets = {net: i + 1 for i, net in enumerate(sorted({n for c in components for n in c["nets"].values()}))}
    board = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew)
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend([a("net"), code, "/" + net] for net, code in nets.items())
    hashes = {}
    for c in components:
        library, name = c["footprint"].split(":")
        path = fp / (library + ".pretty") / (name + ".kicad_mod")
        board.append(placed_footprint(c, POSES[c["ref"]], path, nets))
        hashes[c["footprint"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    for i, (x, y) in enumerate(MOUNTS, 1):
        board.append(mount_footprint(f"H{i}", (ORIGIN[0] + x, ORIGIN[1] + y)))
    x, y = ORIGIN
    w, h = SIZE
    for p, q in [
        ((x, y), (x + w, y)),
        ((x + w, y), (x + w, y + h)),
        ((x + w, y + h), (x, y + h)),
        ((x, y + h), (x, y)),
    ]:
        board.append(
            read_sexpr(
                f'(gr_line (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    (ROOT / "output_stage.kicad_pcb").write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    local = ROOT / "RMX_Output.pretty"
    local.mkdir(exist_ok=True)
    (local / "M2_Insert_Clearance.kicad_mod").write_text(sexpr(mount_footprint()) + "\n")
    pro = json.loads((ROOT / "output_stage.kicad_pro").read_text())
    pro["board"] = {"design_settings": project_settings()}
    (ROOT / "output_stage.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    (ROOT / "generated/placement-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E06",
                board_size_mm=[*SIZE, 1.6],
                pcb_native_origin_mm=ORIGIN,
                layout_origin_mm=DATUM,
                mounts_relative_mm=MOUNTS,
                footprint_library_hashes=hashes,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "E06: 41 footprints and four M2 holes placed on 82 x 34mm board. No copper routed; run check_placement.py."
    )


if __name__ == "__main__":
    main()
