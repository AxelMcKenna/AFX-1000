#!/usr/bin/env python3
"""Independent E24 placed-only supply PCB check; open connections are reported."""

import argparse
import datetime
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ..common.netlists import netlist
from ..common.placement import footprint_root
from ..common.reports import sha, source_hashes
from ..common.sexpr import children, first, read_sexpr
from ..output_stage.check_placement import courtyard, transform
from .verify import contract

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def mechanical(pcb, expected):
    tree = read_sexpr(pcb.read_text())
    assert not children(tree, "segment") and not children(tree, "via") and not children(tree, "zone"), (
        "E24 evidence is placed-only, not routing verification"
    )
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    copper = {
        str(l[1]) for l in first(tree, "layers")[1:] if isinstance(l, list) and str(l[1]).endswith(".Cu")
    }
    assert copper == {"F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"}
    lines = children(tree, "gr_line")
    assert len(lines) == 4
    assert {tuple(map(float, first(l, t)[1:3])) for l in lines for t in ("start", "end")} == {
        (100, 100),
        (184, 100),
        (184, 138),
        (100, 138),
    }
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    actual, mounts, bodies, ep, side_counts = {}, {}, [], {}, dict(F=0, B=0)
    positions = {}
    for fp in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        pads = children(fp, "pad")
        if ref.startswith("H"):
            assert (
                len(pads) == 1 and pads[0][2] == "np_thru_hole" and float(first(pads[0], "drill")[1]) == 2.4
            )
            x, y = transform(fp, first(pads[0], "at")[1:3])
            mounts[ref] = [round(x - 100, 6), round(y - 100, 6)]
            continue
        assert ref not in actual and fp[1] == parts[ref]["footprint"] and props["Value"] == parts[ref]["part"]
        actual[ref] = {}
        for pad in pads:
            number = str(pad[1])
            if not number:
                assert not children(pad, "net") and not any(
                    str(l).endswith(".Cu") for l in first(pad, "layers")[1:]
                )
                continue
            net = str(first(pad, "net")[-1]).lstrip("/")
            if number in actual[ref]:
                assert actual[ref][number] == net, (ref, "duplicate pad net mismatch")
            actual[ref][number] = net
            if ref in ("U1", "U13", "U7", "U8", "U9", "U10", "U11") and number == (
                "3" if ref == "U8" else "9" if ref in ("U7", "U9") else "11"
            ):
                ep.setdefault(ref, set()).add(net)
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        positions[ref] = list(map(float, first(fp, "at")[1:3]))
        side_counts[side] += 1
        b = courtyard(fp, side + ".CrtYd")
        assert 100 <= b[0] < b[2] <= 184 and 100 <= b[1] < b[3] <= 138, (ref, b)
        bodies.append(
            dict(
                reference=ref,
                side=side,
                courtyard_relative_mm=[
                    round(b[0] - 100, 6),
                    round(b[1] - 100, 6),
                    round(b[2] - b[0], 6),
                    round(b[3] - b[1], 6),
                ],
            )
        )
    assert actual == expected
    assert mounts == {"H1": [4, 4], "H2": [74, 4], "H3": [4, 34], "H4": [74, 34]}
    assert ep == {
        "U1": {"AGND"},
        "U13": {"AGND"},
        "U7": {"P19_SRC"},
        "U8": {"P12_SRC"},
        "U9": {"V5_REG_SRC"},
        "U10": {"RAW_N22"},
        "U11": {"RAW_N17"},
    }
    thermal = {}
    for ref in ("U1", "U2", "U3", "U7", "U8", "U11", "U13"):
        x, y = positions[ref]
        x -= 100
        y -= 100
        w, h = (24, 14) if ref == "U8" else (8, 6) if ref == "U7" else (6, 6)
        if ref == "U8":
            x += 1
            y -= 1
        bounds = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]
        assert 0 <= bounds[0] < bounds[2] <= 84 and 0 <= bounds[1] < bounds[3] <= 38
        for body in bodies:
            if body["side"] != "B" and not (
                body["reference"].startswith("J") or body["reference"] in ("C32", "C33")
            ):
                continue
            px, py, pw, ph = body["courtyard_relative_mm"]
            assert (
                min(px + pw, bounds[2]) - max(px, bounds[0]) <= 0
                or min(py + ph, bounds[3]) - max(py, bounds[1]) <= 0
            ), (ref, "bottom thermal region occupied", body["reference"])
        thermal[ref] = bounds
    return dict(
        revision="E24",
        pcb_sha256=sha(pcb),
        board_size_mm=[84, 38, 1.6],
        copper_layers=6,
        circuit_components=157,
        mounts_relative_mm=mounts,
        mount_hole_mm=2.4,
        bodies=bodies,
        component_sides=side_counts,
        exposed_pad_nets={ref: next(iter(n)) for ref, n in ep.items()},
        bottom_thermal_region_allocations_mm=thermal,
        pcb_routed=False,
        housing_datum_proposal_mm=[207, 105, 6.5],
        housing_fit_verified=False,
        current_carrying_or_thermal_verified=False,
        switching_loop_or_emi_verified=False,
        remaining=[
            "all copper routing and actual converter hot-loop geometry",
            "regulator OUT/IN thermal copper, vias and loss/temperature qualification",
            "header/harness and THT tail bounds, actual housing integration",
            "startup, bulk-capacitor loop, fault/SOA, noise and physical assembly checks",
        ],
    )


def audit_inductors():
    results = {}
    for name, center, size, court in [
        ("SRP7050WA", 3, (3, 3.5), (9.5, 8)),
        ("SRP1050WA", 4.325, (3.65, 5), (12.8, 10.8)),
    ]:
        path = ROOT / "RMX_Power.pretty" / (name + ".kicad_mod")
        fp = read_sexpr(path.read_text())
        pads = children(fp, "pad")
        assert len(pads) == 2
        for p, number, x in zip(pads, ("1", "2"), (-center, center)):
            assert p[1] == number and p[2] == "smd"
            assert all(math.isclose(float(v), e, abs_tol=1e-9) for v, e in zip(first(p, "size")[1:], size))
            assert all(math.isclose(float(v), e, abs_tol=1e-9) for v, e in zip(first(p, "at")[1:3], (x, 0)))
        rectangle = next(r for r in children(fp, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
        assert tuple(map(float, first(rectangle, "start")[1:])) == (-court[0] / 2, -court[1] / 2)
        assert tuple(map(float, first(rectangle, "end")[1:])) == (court[0] / 2, court[1] / 2)
        results[name] = dict(
            pad_size_mm=size,
            pad_centers_x_mm=[-center, center],
            courtyard_size_mm=court,
            footprint_sha256=sha(path),
            manufacturer_land_dimensions_checked=True,
            stencil_or_assembly_process_qualified=False,
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    args = parser.parse_args()
    cli = args.kicad_cli.resolve()
    OUT.mkdir(exist_ok=True)
    (OUT / "placement-verification.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e24-check-") as folder:
        temp = Path(folder)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp}/cache</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
            FONTCONFIG_FILE=str(font),
        )

        def run(*words):
            p = subprocess.run([str(cli), *map(str, words)], env=env, capture_output=True, text=True)
            assert p.returncode == 0, (words, p.stdout, p.stderr)
            return p.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "placement-netlist.xml",
            ROOT / "power_supply.kicad_sch",
        )
        parts, pins = netlist(OUT / "placement-netlist.xml")
        contract(parts, pins)
        pcb = ROOT / "power_supply.kicad_pcb"
        packet = mechanical(pcb, pins)
        lands = audit_inductors()
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "placement-drc.json",
            pcb,
        )
        drc = json.loads((OUT / "placement-drc.json").read_text())
        assert not drc["violations"] and not drc["schematic_parity"]
        assert drc["unconnected_items"]
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
                pcb,
            )
        files = (
            list(ROOT.glob("*.py"))
            + list((ROOT / "RMX_Power.pretty").glob("*.kicad_mod"))
            + [
                ROOT / n
                for n in [
                    "README.md",
                    "components.json",
                    "power_supply.kicad_pcb",
                    "power_supply.kicad_sch",
                    "power_supply.kicad_pro",
                    "fp-lib-table",
                    "generated/placement-inputs.json",
                    "generated/placement.json",
                    "generated/placement-drc.json",
                ]
            ]
        )
        files.append(ROOT.parent / "output_stage/check_placement.py")
        report = dict(
            revision="E24",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=157,
            mounting_holes=4,
            board_size_mm=[84, 38, 1.6],
            copper_layers=6,
            nonrouting_drc_violations=0,
            schematic_parity_issues=0,
            unconnected_items=len(drc["unconnected_items"]),
            pcb_routed=False,
            inductor_lands=lands,
            exposed_pad_nets=packet["exposed_pad_nets"],
            physical_fit_verified=False,
            physical_power_verified=False,
            complete_unit_build_ready=False,
            source_sha256=source_hashes(ROOT, files),
        )
        (OUT / "placement-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E24 KiCad {version}: 157 components, zero placement DRC/parity issues; {len(drc['unconnected_items'])} open connections. This is an unrouted placement candidate."
    )


if __name__ == "__main__":
    main()
