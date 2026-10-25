#!/usr/bin/env python3
"""E07 native routing DRC/parity and actual-PCB mechanical packet.

Refill/save the reference plane and require zero unconnected items by default.
--unrouted checks an intentionally placed-only intermediate. No bench claim.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..common.placement import footprint_root
from ..common.reports import source_hashes
from ..common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def transform(fp, xy):
    pos = first(fp, "at")
    x, y = map(float, pos[1:3])
    angle = math.radians(float(pos[3]) if len(pos) > 3 else 0)
    px, py = map(float, xy)
    return (x + px * math.cos(angle) + py * math.sin(angle), y - px * math.sin(angle) + py * math.cos(angle))


def courtyard(fp, layer):
    points = []
    for shape in children(fp, "fp_line") + children(fp, "fp_rect") + children(fp, "fp_circle"):
        if first(shape, "layer")[1] != layer:
            continue
        if shape[0] == "fp_circle":
            c = tuple(map(float, first(shape, "center")[1:3]))
            end = tuple(map(float, first(shape, "end")[1:3]))
            r = math.dist(c, end)
            points.extend((c[0] + dx * r, c[1] + dy * r) for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        else:
            start = tuple(map(float, first(shape, "start")[1:3]))
            end = tuple(map(float, first(shape, "end")[1:3]))
            points.extend([start, end])
            if shape[0] == "fp_rect":
                points.extend([(start[0], end[1]), (end[0], start[1])])
    assert points, ("Missing courtyard", fp[1], layer)
    actual = [transform(fp, p) for p in points]
    return [
        min(p[0] for p in actual),
        min(p[1] for p in actual),
        max(p[0] for p in actual),
        max(p[1] for p in actual),
    ]


def mechanical_packet():
    pcb = ROOT / "output_stage.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    edges = children(tree, "gr_line")
    corners = {tuple(map(float, first(line, tag)[1:3])) for line in edges for tag in ("start", "end")}
    assert corners == {(100, 100), (182, 100), (182, 134), (100, 134)}
    nets = {str(v[1]): str(v[2]).lstrip("/") for v in children(tree, "net") if str(v[1]) != "0"}
    components = json.loads((ROOT / "components.json").read_text())
    contract = {c["ref"]: c["nets"] for c in components}
    bodies = []
    actual = {}
    mounts = {}
    film = {f"C{i}" for i in (1, 2, 3, 4, 13, 14, 15, 16)}
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pads = children(fp, "pad")
        if ref.startswith("H"):
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole"
            assert float(first(pads[0], "drill")[1]) == 2.4
            xy = transform(fp, first(pads[0], "at")[1:3])
            mounts[ref] = [round(xy[0] - 100, 5), round(xy[1] - 100, 5)]
            continue
        actual[ref] = {
            str(p[1]): (
                str(first(p, "net")[1]).lstrip("/")
                if len(first(p, "net")) == 2
                else nets[str(first(p, "net")[1])]
            )
            for p in pads
        }
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        bounds = courtyard(fp, side + ".CrtYd")
        expand = 0.5 if ref in film or ref.startswith("J") else 0
        x0, y0, x1, y1 = [bounds[0] - expand, bounds[1] - expand, bounds[2] + expand, bounds[3] + expand]
        # Native PCB +Y points toward performer, like the panel layout. Convert
        # datum only here; enclosure.scad handles the final Cartesian Y flip.
        x, y = 206 + x0 - 100, 40 + y0 - 100
        w, d = x1 - x0, y1 - y0
        assert 206 <= x and x + w <= 288 and 40 <= y and y + d <= 74, (ref, x, y, w, d)
        if side == "B":
            height = 1.5 if ref == "C8" else 1.3
            z = 3.8 - 0.15 - height
            top = 3.8
            note = "bottom SMD height limit including solder and seat tolerance; MPN qualification pending"
        else:
            height = (
                19.0
                if ref in film
                else 15.0
                if ref.startswith("J")
                else 5.6
                if ref == "K3"
                else 2.1
                if ref.startswith("U")
                else 3.0
                if ref in ("C9", "C10", "C11", "C12")
                else 1.5
                if ref.startswith("C")
                else 0.9
            )
            z = 5.4
            top = 3.8 + 0.15 + 1.76 + height
            note = (
                "film case max18.5 plus seating0.5, courtyard expansion0.5 and board/seat tolerance"
                if ref in film
                else "prototype header/harness height reserve; final connector and wiring unselected"
                if ref.startswith("J")
                else "component class height limit including solder; qualification pending"
            )
        bodies.append(["e06_" + ref, *[round(v, 6) for v in (x, y, z, w, d, top - z)], note])
        for pad in pads:
            if pad[2] != "thru_hole":
                continue
            px, py = transform(fp, first(pad, "at")[1:3])
            bodies.append(
                [
                    f"e06_{ref}_lead_{pad[1]}",
                    round(206 + px - 101, 6),
                    round(40 + py - 101, 6),
                    2.15,
                    2,
                    2,
                    1.65,
                    "THT solder/lead reserve; trim protrusion <=1.5mm including solder",
                ]
            )
    assert actual == contract, (actual, contract)
    assert mounts == {"H1": [4, 4], "H2": [78, 4], "H3": [4, 30], "H4": [78, 30]}, mounts
    routed = bool(children(tree, "segment"))
    return dict(
        revision="E07" if routed else "E06",
        pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        board=[
            "audio_carrier",
            206,
            40,
            3.8,
            82,
            34,
            1.6,
            "E07 routed output stage" if routed else "E06 placed output stage; unrouted",
        ],
        mount_centers_layout_mm=[[206 + p[0], 40 + p[1]] for p in mounts.values()],
        mount_boss_diameter_mm=7.2,
        insert_through_bore_mm=3.2,
        insert="CNC Kitchen M2 x 3mm, OD3.6; through bore; M2x4 board screws",
        floor_pocket=["e06_output", 206.5, 40.5, 81, 33, 1.6],
        assembly_limits_mm=dict(
            seat_tolerance=0.15,
            pcb_thickness_nominal=1.6,
            pcb_thickness_tolerance=0.16,
            film_case_max_height=18.5,
            film_seating_max=0.5,
            film_xy_courtyard_expansion=0.5,
            tht_solder_protrusion_max=1.5,
            bottom_2512_height_including_solder_max=1.3,
            bottom_c8_height_including_solder_max=1.5,
            prototype_header_and_wire_handoff_height=15,
        ),
        bodies=bodies,
        physical_fit_verified=False,
        limits=[
            "Output stage only; converter/input and power PCB placement incomplete",
            "Output subassembly only; remaining system circuitry and fabrication review incomplete",
            "Conditional on documented body/seat/PCB/assembly height bounds",
            "Wire bends, thermal behavior, insert installation and real fit unverified",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--footprint-dir", type=Path)
    parser.add_argument(
        "--unrouted", action="store_true", help="Check a placed-only intermediate, retaining open connections"
    )
    args = parser.parse_args()
    cli = Path(shutil.which(args.kicad_cli) or args.kicad_cli).resolve()
    fp = footprint_root(str(cli), args.footprint_dir)
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-placement-kicad-") as temporary:
        temp = Path(temporary)
        env = dict(os.environ, KICAD_CONFIG_HOME=str(temp / "config"), KICAD10_FOOTPRINT_DIR=str(fp))
        if Path("/System/Library/Fonts").is_dir():
            (temp / "cache").mkdir()
            font = temp / "fonts.conf"
            font.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'
                + str(temp / "cache")
                + "</cachedir></fontconfig>"
            )
            env["FONTCONFIG_FILE"] = str(font)

        def run(*command):
            r = subprocess.run([str(cli), *map(str, command)], capture_output=True, text=True, env=env)
            if r.returncode:
                raise RuntimeError(f"{command}: {r.returncode}\n{r.stdout}\n{r.stderr}")
            return r.stdout.strip()

        version = run("version")
        flags = [] if args.unrouted else ["--refill-zones", "--save-board", "--exit-code-violations"]
        destination = OUT / ("placement-drc.json" if args.unrouted else "routing-drc.json")
        run(
            "pcb",
            "drc",
            *flags,
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            destination,
            ROOT / "output_stage.kicad_pcb",
        )
        drc = json.loads(destination.read_text())
        assert not drc["violations"], drc["violations"]
        assert not drc["schematic_parity"], drc["schematic_parity"]
        board = read_sexpr((ROOT / "output_stage.kicad_pcb").read_text())
        if args.unrouted:
            assert not children(board, "segment") and not children(board, "zone")
            assert len(drc["unconnected_items"]) > 0
        else:
            assert not drc["unconnected_items"], drc["unconnected_items"]
            assert len(children(board, "segment")) > 0 and len(children(board, "via")) > 0
            zones = children(board, "zone")
            assert len(zones) == 1 and first(zones[0], "layer")[1] == "In1.Cu"
            assert children(zones[0], "filled_polygon"), "Native saved AGND fill is missing"
            assert first(zones[0], "net")[1] == "/AGND"
        packet = mechanical_packet()
        packet.update(
            native_drc_nonrouting_violations=0,
            schematic_parity_issues=0,
            unconnected_items=len(drc["unconnected_items"]),
            pcb_routed=not args.unrouted,
        )
        (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
        for name, layers in [
            ("placement-top", "F.Cu,F.Fab,F.SilkS,Edge.Cuts"),
            ("placement-bottom", "B.Cu,B.Fab,B.SilkS,Edge.Cuts"),
        ]:
            run(
                "pcb",
                "export",
                "svg",
                "--mode-single",
                "--page-size-mode",
                "2",
                "--exclude-drawing-sheet",
                "--layers",
                layers,
                "-o",
                OUT / (name + ".svg"),
                ROOT / "output_stage.kicad_pcb",
            )
        if not args.unrouted:
            for name, layer in [("reference-plane", "In1.Cu"), ("inner-routing", "In2.Cu")]:
                run(
                    "pcb",
                    "export",
                    "svg",
                    "--mode-single",
                    "--page-size-mode",
                    "2",
                    "--exclude-drawing-sheet",
                    "--layers",
                    layer + ",Edge.Cuts",
                    "-o",
                    OUT / (name + ".svg"),
                    ROOT / "output_stage.kicad_pcb",
                )
        files = [
            ROOT / f
            for f in [
                "place.py",
                "check_placement.py",
                "generate.py",
                "output_stage.kicad_pcb",
                "output_stage.kicad_sch",
                "output_stage.kicad_pro",
                "fp-lib-table",
                "components.json",
                "RMX_Output.pretty/M2_Insert_Clearance.kicad_mod",
                "generated/placement-inputs.json",
                "generated/placement.json",
            ]
        ]
        if not args.unrouted:
            files.extend(ROOT / f for f in ["route.py", "generated/routing-inputs.json"])
        report = dict(
            revision=packet["revision"],
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            placed_circuit_components=41,
            mounting_holes=4,
            board_size_mm=[82, 34, 1.6],
            nonrouting_drc_violations=0,
            schematic_parity_issues=0,
            unconnected_items=len(drc["unconnected_items"]),
            pcb_routed=not args.unrouted,
            routed_segments=len(children(board, "segment")),
            through_vias=len(children(board, "via")),
            saved_reference_plane_filled=not args.unrouted,
            body_and_solder_reserves=len(packet["bodies"]),
            physical_fit_verified=False,
            source_hashes=source_hashes(ROOT, files),
        )
        (OUT / "placement-verification.json").write_text(json.dumps(report, indent=2) + "\n")
        if not args.unrouted:
            (OUT / "routing-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"{packet['revision']} KiCad {version}: zero DRC/library/parity issues; {len(drc['unconnected_items'])} open connections. Actual PCB mechanical packet exported."
    )


if __name__ == "__main__":
    main()
