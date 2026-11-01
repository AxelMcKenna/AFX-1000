"""Independent E25 placed-only PCB, original pin contracts and native parity."""

import argparse
import datetime
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard, transform
from ..verify import contract

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
OUT = ROOT / "generated"
BULK = {"C4": (16, 20), "C8": (16, 20), "C12": (8, 11.5), "C16": (8, 11.5), "C20": (10, 20), "C24": (16, 25)}


def mechanical(tree, parts, pins):
    assert not any(children(tree, k) for k in ("segment", "via", "zone")), (
        "Placed-only record cannot qualify routed copper"
    )
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    edges = children(tree, "gr_line")
    points = {tuple(map(float, first(l, t)[1:3])) for l in edges for t in ("start", "end")}
    corners = {(100, 100), (256, 100), (256, 145.25), (105, 145.25), (105, 135), (100, 135)}
    assert len(edges) == 39 and len(points) == 39 and corners <= points, "Relieved board outline changed"
    for x, y in points - corners:
        assert 254.39999 <= x <= 256.00001 and abs(math.hypot(x - 259, y - 140.5) - 4.6) < 1e-5, (
            "case-fastener relief changed",
            x,
            y,
        )
    assert all(
        first(edges[i], "end")[1:3] == first(edges[(i + 1) % len(edges)], "start")[1:3]
        for i in range(len(edges))
    ), "Outline must be closed in order"
    assert {
        str(l[1]) for l in first(tree, "layers")[1:] if isinstance(l, list) and str(l[1]).endswith(".Cu")
    } == {"F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"}
    actual = {}
    mounts = {}
    records = []
    bodies = []
    tails = []
    groups = {}
    for f in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(f, "property")}
        ref = props["Reference"]
        pads = children(f, "pad")
        if ref.startswith("H"):
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole" and not children(pads[0], "net")
            assert float(first(pads[0], "drill")[1]) == 2.4
            mounts[ref] = [round(v - 100, 6) for v in transform(f, first(pads[0], "at")[1:3])]
            continue
        assert (
            ref in parts
            and ref not in actual
            and props["Value"] == parts[ref].findtext("value")
            and f[1] == parts[ref].findtext("footprint")
        ), (ref, "value/footprint contract")
        actual[ref] = {}
        side = str(first(f, "layer")[1]).split(".")[0]
        bounds = courtyard(f, side + ".CrtYd")
        assert side == ("B" if ref.startswith("R") else "F"), (ref, "unexpected assembly face")
        assert 100.5 <= bounds[0] < bounds[2] <= 255.5 and 100.5 <= bounds[1] < bounds[3] <= (
            145.25 if ref == "C24" else 144.75
        ), (
            ref,
            "courtyard beyond allocated edge",
            bounds,
        )
        b = [
            round(bounds[0] - 100, 6),
            round(bounds[1] - 100, 6),
            round(bounds[2] - bounds[0], 6),
            round(bounds[3] - bounds[1], 6),
        ]
        for p in pads:
            if not str(p[1]):
                continue
            n = str(first(p, "net")[-1]).lstrip("/")
            number = str(p[1])
            assert number not in actual[ref] or actual[ref][number] == n
            actual[ref][number] = n
            if p[2] == "thru_hole":
                xy = [v - 100 for v in transform(f, first(p, "at")[1:3])]
                tails.append(
                    dict(
                        reference=ref,
                        pin=number,
                        center_relative_mm=xy,
                        maximum_protrusion_mm=1.5,
                        reserve_width_mm=2.8,
                    )
                )
        if ref.startswith("Q"):
            count = {n: len([p for p in pads if str(p[1]) == n]) for n in ("1", "2", "3")}
            assert count == {"1": 3, "2": 1, "3": 5}, (ref, "physical grouped MOSFET lands changed")
            assert actual[ref]["1"].endswith("_COMMON") and actual[ref]["2"].endswith("_GATE")
            groups[ref] = dict(
                physical_lands=count, source=actual[ref]["1"], gate=actual[ref]["2"], drain=actual[ref]["3"]
            )
        if ref in BULK:
            d, l = BULK[ref]
            height = l + (2 if l >= 20 else 1.5) + 0.41
            assert side == "F"
            assert (actual[ref]["1"] == "AGND") == (ref in ("C8", "C16")), (ref, "electrolytic polarity")
        else:
            height = 1.1 if side == "B" else 13.31 if ref.startswith("J") else 2.31
        records.append(
            dict(
                reference=ref,
                side=side,
                courtyard_relative_mm=b,
                height_allocation_mm=height,
                manufacturer_dimensions_from_datasheet=ref in BULK,
            )
        )
        bodies.append((ref, side, b))
    assert actual == pins
    assert mounts == {"H1": [4, 20], "H2": [152, 3.8], "H3": [10, 36], "H4": [100, 36]}
    for i, (ref, side, b) in enumerate(bodies):
        for other, face, c in bodies[i + 1 :]:
            if face == side:
                assert (
                    min(b[0] + b[2], c[0] + c[2]) - max(b[0], c[0]) <= 0
                    or min(b[1] + b[3], c[1] + c[3]) - max(b[1], c[1]) <= 0
                ), (ref, other, "overlapping courtyards")
    return dict(
        revision="E25",
        board_size_mm=[156, 45.25, 1.6],
        copper_layers=6,
        outline_relative_mm=[[float(v) - 100 for v in first(l, "start")[1:3]] for l in edges],
        circuit_components=164,
        mounts_relative_mm=mounts,
        mount_hole_mm=2.4,
        components=records,
        leads=tails,
        mosfet_pin_groups=groups,
        bulk_caps={
            ref: dict(
                nominal_diameter_mm=d,
                nominal_length_mm=l,
                maximum_diameter_mm=d + 0.5,
                maximum_length_mm=l + (2 if l >= 20 else 1.5),
                seat_and_board_allowance_mm=0.41,
                vent_air_qualified=False,
            )
            for ref, (d, l) in BULK.items()
        },
        housing_datum_proposal_mm=[8, 108.5, 4.6],
        pcb_routed=False,
        housing_fit_verified=False,
        copper_drop_or_thermal_qualified=False,
        physical_protection_verified=False,
        build_ready=False,
    )


def main(cli):
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    with tempfile.TemporaryDirectory(prefix="rmx-e25-check-") as folder:
        temp = Path(folder)
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
            FONTCONFIG_FILE=str(ROOT.parents[3] / "build-hardware/kicad-fonts.conf"),
        )
        for name in ("rail_disconnect.kicad_sch", "sym-lib-table", "RMX_E17.kicad_sym"):
            shutil.copy2(PARENT / name, temp / name)
        for name in ("rail_disconnect.kicad_pcb", "rail_disconnect.kicad_pro", "fp-lib-table"):
            shutil.copy2(ROOT / name, temp / name)
        shutil.copytree(ROOT / "RMX_Disconnect.pretty", temp / "RMX_Disconnect.pretty")

        def run(*args):
            r = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert r.returncode == 0, (args, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            temp / "rail_disconnect.kicad_sch",
        )
        parts, pins = netlist(OUT / "netlist.xml")
        contract(parts, pins)
        packet = mechanical(read_sexpr(pcb.read_text()), parts, pins)
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            temp / "rail_disconnect.kicad_pcb",
        )
        d = json.loads((OUT / "drc.json").read_text())
        assert not d["violations"] and not d["schematic_parity"], (d["violations"], d["schematic_parity"])
        assert d["unconnected_items"], "Placed-only stage must report actual native opens"
        for name, layers in (("top", "F.Cu,F.Fab,Edge.Cuts"), ("bottom", "B.Cu,B.Fab,Edge.Cuts")):
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
                temp / "rail_disconnect.kicad_pcb",
            )
    packet["pcb_sha256"] = sha(pcb)
    (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
    inputs = json.loads((OUT / "inputs.json").read_text())
    assert inputs["source_schematic_sha256"] == sha(PARENT / "rail_disconnect.kicad_sch") and inputs[
        "components_sha256"
    ] == sha(PARENT / "components.json")
    files = [
        *ROOT.glob("*.py"),
        ROOT / "README.md",
        pcb,
        ROOT / "rail_disconnect.kicad_pro",
        ROOT / "fp-lib-table",
        *list((ROOT / "RMX_Disconnect.pretty").glob("*.kicad_mod")),
        OUT / "inputs.json",
        OUT / "placement.json",
        OUT / "drc.json",
        OUT / "netlist.xml",
        PARENT / "rail_disconnect.kicad_sch",
        PARENT / "components.json",
        PARENT / "verify.py",
        ROOT.parents[1] / "common/placement.py",
        ROOT.parents[1] / "common/sexpr.py",
        ROOT.parents[1] / "common/netlists.py",
        ROOT.parents[1] / "output_stage/check_placement.py",
        ROOT.parents[1] / "power_supply/place.py",
    ]
    record = dict(
        revision="E25",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kicad_version=version,
        physical_components=164,
        native_nonrouting_drc_violations=0,
        schematic_parity_issues=0,
        native_open_connections=len(d["unconnected_items"]),
        pcb_routed=False,
        enclosure_placement_complete=False,
        physical_protection_verified=False,
        build_ready=False,
        source_sha256={os.path.relpath(p, ROOT): sha(p) for p in files},
    )
    (OUT / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        f"E25: 164 parts; zero native nonrouting DRC/parity issues; {len(d['unconnected_items'])} actual open connections. Unrouted, unqualified."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", required=True, type=Path)
    main(p.parse_args().kicad_cli.resolve())
