#!/usr/bin/env python3
"""E23 placement of the E16/E21 input circuit; no routing or housing-fit claim."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from ..common.netlists import netlist
from ..common.placement import footprint_root, placed_footprint, project_settings
from ..common.reports import sha
from ..common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SIZE = (64, 44)
MOUNTS = [(17.5, 8), (60, 12), (4, 33), (60, 40)]
OUTLINE = [(0, 0), (59, 0), (59, 2), (64, 2), (64, 44), (33, 44), (33, 39), (0, 39)]
POSES = {
    "J1": (40, 10.7, 180, "F"),
    "S1": (54, 1.2, 180, "F"),
    "F1": (4.8, 20.5, 0, "F"),
    "D1": (9, 26.5, 0, "F"),
    "Q1": (20, 21, 0, "F"),
    "Q2": (25, 26, 0, "F"),
    "U1": (30, 22, 0, "F"),
    "U2": (13, 33, 0, "F"),
    "U3": (43, 28, 0, "F"),
    "Q3": (34, 28.5, 0, "F"),
    "D2": (35, 15, 0, "B"),
    "D3": (40, 22, 0, "F"),
    "C1": (16, 26.5, 0, "F"),
    "C2": (20, 16.5, 0, "F"),
    "C3": (49, 21, 0, "F"),
    "C4": (55, 28.5, 0, "F"),
    "C5": (30.5, 33.2, 90, "F"),
    "C6": (13, 37, 0, "F"),
    "C7": (14.5, 29.5, 0, "F"),
    "C8": (44, 25.25, 0, "F"),
    "C9": (51.5, 33, 90, "F"),
    "C10": (18, 31, 0, "F"),
    "R1": (8, 7, 0, "F"),
    "R2": (8, 10, 0, "F"),
    "R3": (12.5, 7.5, 0, "F"),
    "R4": (13, 11, 0, "F"),
    "R5": (36, 25, 0, "F"),
    "R6": (36, 31.3, 0, "F"),
    "R7": (28, 30, 90, "F"),
    "R8": (8, 32, 90, "F"),
    "R9": (8, 36, 90, "F"),
    "R10": (48, 35, 0, "F"),
    "R11": (43, 39.5, 0, "F"),
    "R12": (22, 31, 90, "F"),
    "R13": (48, 5, 90, "F"),
    "R14": (55.5, 33, 90, "F"),
    "R15": (39, 27, 90, "F"),
    "R16": (39, 31, 90, "F"),
    "R17": (43, 32, 0, "F"),
    "R18": (47, 28, 90, "F"),
    "R19": (47, 32, 90, "F"),
    "R20": (33, 32, 90, "F"),
    "R21": (30.5, 28.6, 90, "F"),
    "J2": (60, 20, 0, "F"),
    "J3": (60, 30, 0, "F"),
    "J4": (26, 4, 90, "F"),
    "J5": (26, 11, 90, "F"),
    "J6": (48, 40, 90, "F"),
}


def clip_rear_silkscreen(footprint, pose):
    """Keep ink on the PCB when the selected connector body overhangs it."""
    assert pose[2] == 180
    limit = pose[1] - 0.25
    for line in list(children(footprint, "fp_line")):
        if first(line, "layer")[1] != "F.SilkS":
            continue
        start, end = first(line, "start"), first(line, "end")
        sx, sy, ex, ey = *map(float, start[1:3]), *map(float, end[1:3])
        if sy > limit and ey > limit:
            footprint.remove(line)
        elif sy > limit:
            start[1:3] = [sx + (ex - sx) * (limit - sy) / (ey - sy), limit]
        elif ey > limit:
            end[1:3] = [sx + (ex - sx) * (limit - sy) / (ey - sy), limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    args = parser.parse_args()
    cli = args.kicad_cli.resolve()
    libraries = footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    for name in ("placement-verification.json", "routing-verification.json"):
        (OUT / name).unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e23-place-") as temporary:
        result = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(OUT / "placement-netlist.xml"),
                str(ROOT / "input_protection.kicad_sch"),
            ],
            env=dict(
                os.environ,
                KICAD_CONFIG_HOME=temporary,
                KICAD10_FOOTPRINT_DIR=str(libraries),
                FONTCONFIG_FILE=str(ROOT.parents[2] / "build-hardware/kicad-fonts.conf"),
            ),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
    parts, pins = netlist(OUT / "placement-netlist.xml")
    components = json.loads((ROOT / "components.json").read_text())
    assert set(POSES) == set(parts) == {c["ref"] for c in components}
    nets = {
        net: index + 1 for index, net in enumerate(sorted({n for p in pins.values() for n in p.values()}))
    }
    board = read_sexpr("""(kicad_pcb (version 20240108) (generator pcbnew)
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" signal) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))""")
    board.extend(
        [a("net"), code, net if net.startswith("unconnected-") else "/" + net] for net, code in nets.items()
    )
    hashes = {}
    upstream = {}
    for ref, name, identifier in [
        ("J1", "PJ102AH_RearEdge_E23", "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal"),
        ("S1", "JS102011SAQN_RearEdge_E23", "Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN"),
    ]:
        lib, base_name = identifier.split(":")
        source = libraries / (lib + ".pretty") / (base_name + ".kicad_mod")
        custom = read_sexpr(source.read_text())
        custom[1] = name
        clip_rear_silkscreen(custom, POSES[ref])
        local = ROOT / "RMX_Input.pretty" / (name + ".kicad_mod")
        local.parent.mkdir(exist_ok=True)
        local.write_text(sexpr(custom) + "\n")
        upstream[identifier] = sha(source)
    for component in components:
        lib, name = component["footprint"].split(":")
        library = (ROOT if lib == "RMX_Input" else libraries) / (lib + ".pretty") / (name + ".kicad_mod")
        part = dict(component, value=component["part"], mpn=component["part"], nets=pins[component["ref"]])
        footprint = placed_footprint(part, POSES[part["ref"]], library, nets, namespace="rmx:E23:")
        for pad in children(footprint, "pad"):
            if children(pad, "net") and str(first(pad, "net")[-1]).startswith("/unconnected-"):
                first(pad, "net")[-1] = str(first(pad, "net")[-1])[1:]
        board.append(footprint)
        hashes[component["footprint"]] = sha(library)
    mount_path = libraries / "MountingHole.pretty/MountingHole_2.2mm_M2.kicad_mod"
    hashes["MountingHole:MountingHole_2.2mm_M2"] = sha(mount_path)
    for index, (x, y) in enumerate(MOUNTS, 1):
        component = dict(
            ref=f"H{index}",
            footprint="MountingHole:MountingHole_2.2mm_M2",
            value="M2_CLEARANCE",
            mpn="",
            source="",
            nets={},
        )
        footprint = placed_footprint(component, (x, y, 0, "F"), mount_path, nets, namespace="rmx:E23:")
        first(footprint, "attr").extend([a("board_only"), a("exclude_from_bom"), a("exclude_from_pos_files")])
        board.append(footprint)
    for p, q in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        board.append(
            read_sexpr(
                f'(gr_line (start {100 + p[0]} {100 + p[1]}) (end {100 + q[0]} {100 + q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
            )
        )
    (ROOT / "input_protection.kicad_pcb").write_text(
        "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
    )
    settings = project_settings()
    settings["rules"].update(min_clearance=0.15, min_track_width=0.15)
    project = json.loads((ROOT / "input_protection.kicad_pro").read_text())
    project["board"] = {"design_settings": settings}
    project["net_settings"] = {
        "classes": [
            dict(
                name="Default",
                clearance=0.15,
                track_width=0.15,
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
    (ROOT / "input_protection.kicad_pro").write_text(json.dumps(project, indent=2) + "\n")
    table = read_sexpr((ROOT / "fp-lib-table").read_text())
    if not any(first(entry, "name")[1] == "MountingHole" for entry in children(table, "lib")):
        table.append(
            read_sexpr(
                '(lib (name "MountingHole") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/MountingHole.pretty") (options "") (descr "Standard M2 clearance hole"))'
            )
        )
    (ROOT / "fp-lib-table").write_text(sexpr(table) + "\n")
    (OUT / "placement-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E23",
                circuit_revision="E16/E21",
                board_size_mm=[*SIZE, 1.6],
                native_origin_mm=[100, 100],
                mounts_relative_mm=MOUNTS,
                outline_relative_mm=OUTLINE,
                footprint_library_sha256=hashes,
                local_footprint_upstream_sha256=upstream,
                pcb_routed=False,
                housing_datum_selected=False,
                thermal_design_qualified=False,
                physical_fit_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "E23: 48 circuit parts and four M2 holes placed on 64 x 44 mm; routing and independent checks required."
    )


if __name__ == "__main__":
    main()
