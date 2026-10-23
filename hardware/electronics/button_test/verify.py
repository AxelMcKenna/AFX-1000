#!/usr/bin/env python3
"""Check B01 with native KiCad, verify exported pin nets, and export SVG reviews."""

import argparse
import datetime
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ..common.reports import source_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def measure_board():
    # Read the accepted native PCB rather than reporting the generator's intent.
    # Only KiCad S-expression syntax used by this small board is needed here.
    tokens = iter(
        re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', (ROOT / "button_test.kicad_pcb").read_text())
    )

    def read(token):
        if token == "(":
            result = []
            for token in tokens:
                if token == ")":
                    return result
                result.append(read(token))
            raise ValueError("Unclosed PCB expression")
        if token.startswith('"'):
            return json.loads(token)
        try:
            return float(token)
        except ValueError:
            return token

    board = read(next(tokens))

    def children(node, tag):
        return [v for v in node if isinstance(v, list) and v and v[0] == tag]

    def first(node, tag):
        return children(node, tag)[0]

    actual = {}
    for footprint in children(board, "footprint"):
        reference = next(p[2] for p in children(footprint, "property") if p[1] == "Reference")
        at = first(footprint, "at")
        assert len(at) == 3 or at[3] == 0, "Unexpected footprint rotation"
        pads = {}
        for pad in children(footprint, "pad"):
            xy = first(pad, "at")
            assert len(xy) == 3 or xy[3] == 0, "Unexpected pad rotation"
            pads[str(pad[1])] = dict(
                x=round(at[1] + xy[1] - 50, 6),
                y=round(at[2] + xy[2] - 50, 6),
                drill=first(pad, "drill")[1],
                kind=pad[2],
            )
        actual[reference] = pads
    expected = {"1": (3.25, 2.25), "2": (-3.25, 2.25), "3": (3.25, -2.25), "4": (-3.25, -2.25)}
    assert set(actual["SW1"]) == set(expected)
    for pin, xy in expected.items():
        p = actual["SW1"][pin]
        assert (p["x"], p["y"], p["drill"], p["kind"]) == (*xy, 1, "thru_hole"), (pin, p)
    for pin, x in [("1", -1.27), ("2", 1.27)]:
        p = actual["J1"][pin]
        assert (p["x"], p["y"], p["drill"]) == (x, 6, 1), (pin, p)
    pitch = float(
        re.search(
            r"mount_pitch\s*=\s*([0-9.]+)",
            (ROOT.parents[1] / "cad/generated/button-fixture.scad").read_text(),
        ).group(1)
    )
    for reference, x in [("H1", -pitch / 2), ("H2", pitch / 2)]:
        p = actual[reference][""]
        assert (p["x"], p["y"], p["drill"], p["kind"]) == (x, 0, 2.4, "np_thru_hole"), (reference, p)
    points = [tuple(first(line, t)[1:3]) for line in children(board, "gr_line") for t in ("start", "end")]
    assert set(points) == {(34, 42), (66, 42), (66, 58), (34, 58)}, points
    thickness = first(first(board, "general"), "thickness")[1]
    assert thickness == 1.6, thickness
    return dict(
        footprint_pad_centers_relative_to_fixture_mm=actual,
        board_size_mm=[32, 16],
        board_thickness_mm=thickness,
        mount_pitch_matches_cad_mm=pitch,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-button-kicad-") as temporary:
        temp = Path(temporary)
        env = dict(os.environ, KICAD_CONFIG_HOME=str(temp / "config"))
        if Path("/System/Library/Fonts").is_dir():
            # Use system fonts and a writable isolated cache, not user settings.
            (temp / "font-cache").mkdir()
            fonts = temp / "fonts.conf"
            fonts.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'
                + str(temp / "font-cache")
                + "</cachedir></fontconfig>"
            )
            env["FONTCONFIG_FILE"] = str(fonts)

        def run(*command):
            p = subprocess.run([args.kicad_cli, *map(str, command)], capture_output=True, text=True, env=env)
            if p.returncode:
                raise RuntimeError(f"{command}: exit {p.returncode}\n{p.stdout}\n{p.stderr}")
            return p.stdout.strip()

        version = run("version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            ROOT / "button_test.kicad_sch",
        )
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            ROOT / "button_test.kicad_pcb",
        )
        erc = json.loads((OUT / "erc.json").read_text())
        drc = json.loads((OUT / "drc.json").read_text())
        for sheet in erc["sheets"]:
            assert not sheet["violations"], sheet["violations"]
        for key in ("violations", "unconnected_items", "schematic_parity"):
            assert not drc[key], (key, drc[key])
        geometry = measure_board()
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "button_test.kicad_sch",
        )
        tree = ET.parse(OUT / "netlist.xml")
        nets = {
            n.attrib["name"].lstrip("/"): sorted(
                (node.attrib["ref"], node.attrib["pin"]) for node in n.findall("node")
            )
            for n in tree.findall("./nets/net")
        }
        assert nets == {
            "SIGNAL": [("J1", "1"), ("SW1", "3"), ("SW1", "4")],
            "GND": [("J1", "2"), ("SW1", "1"), ("SW1", "2")],
        }, nets
        for name, layers in [("board-top", "F.Cu,F.SilkS,Edge.Cuts"), ("board-bottom", "B.Cu,Edge.Cuts")]:
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
                ROOT / "button_test.kicad_pcb",
            )
        run(
            "sch",
            "export",
            "svg",
            "--exclude-drawing-sheet",
            "-o",
            str(OUT) + os.sep,
            ROOT / "button_test.kicad_sch",
        )
        sources = [
            ROOT / "generate.py",
            ROOT / "verify.py",
            ROOT / "button_test.kicad_sch",
            ROOT / "button_test.kicad_pcb",
            ROOT / "button_test.kicad_pro",
            ROOT / "RMX.kicad_sym",
            ROOT / "fp-lib-table",
            ROOT / "sym-lib-table",
            ROOT / "dependencies.json",
            *sorted((ROOT / "RMX_Button.pretty").glob("*.kicad_mod")),
        ]
        report = dict(
            revision="B01",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            erc_violations=0,
            drc_violations=0,
            unconnected_pads=0,
            schematic_parity_issues=0,
            exported_pin_nets=nets,
            board_size_mm=[32, 16],
            board_thickness_mm=1.6,
            mount_hole_diameter_mm=2.4,
            mount_hole_pitch_mm=22,
            switch_hole_pitch_mm=[6.5, 4.5],
            switch_drill_mm=1,
            minimum_clearance_mm=0.25,
            track_width_mm=0.35,
            assembled=False,
            measured_pcb_geometry=geometry,
            physical_fit_verified=False,
            full_control_pcb=False,
            source_hashes=source_hashes(ROOT, sources),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"KiCad {version}: zero ERC/DRC/unconnected/parity issues; exported pin pairs match the manufacturer top view."
    )


if __name__ == "__main__":
    main()
