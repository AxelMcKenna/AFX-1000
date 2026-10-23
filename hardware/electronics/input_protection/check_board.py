#!/usr/bin/env python3
"""Independent E23 native PCB connectivity, geometry and review exports."""

import argparse
import datetime
import heapq
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
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    assert {
        str(layer[1])
        for layer in first(tree, "layers")[1:]
        if isinstance(layer, list) and str(layer[1]).endswith(".Cu")
    } == {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}
    lines = children(tree, "gr_line")
    assert len(lines) == 8
    assert {tuple(map(float, first(line, tag)[1:3])) for line in lines for tag in ("start", "end")} == {
        (100, 100),
        (159, 100),
        (159, 102),
        (164, 102),
        (164, 144),
        (133, 144),
        (133, 139),
        (100, 139),
    }
    actual, mounts, bodies, terminal_positions = {}, {}, [], {}
    components = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    for footprint in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(footprint, "property")}
        ref = props["Reference"]
        pads = children(footprint, "pad")
        if ref.startswith("H"):
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole"
            assert float(first(pads[0], "drill")[1]) == 2.2
            x, y = transform(footprint, first(pads[0], "at")[1:3])
            mounts[ref] = [round(x - 100, 6), round(y - 100, 6)]
            continue
        assert ref not in actual
        assert footprint[1] == components[ref]["footprint"]
        assert props["Value"] == components[ref]["part"]
        actual[ref] = {}
        for pad in pads:
            number = str(pad[1])
            if not number:
                assert not children(pad, "net")
                assert pad[2] == "np_thru_hole" or not any(
                    str(l).endswith(".Cu") for l in first(pad, "layers")[1:]
                )
                continue
            actual[ref][number] = str(first(pad, "net")[-1]).lstrip("/")
            terminal_positions[(ref, number)] = transform(footprint, first(pad, "at")[1:3])
        side = "B" if first(footprint, "layer")[1] == "B.Cu" else "F"
        bounds = courtyard(footprint, side + ".CrtYd")
        assert 100 <= bounds[0] < bounds[2] <= 164 and bounds[3] <= 144, (ref, bounds)
        if ref in ("J1", "S1"):
            assert 95 <= bounds[1] < bounds[3] and first(footprint, "layer")[1] == "F.Cu"
        else:
            assert 100 <= bounds[1] < bounds[3], (ref, bounds)
        # These height allocations support a later enclosure placement review.
        # They are deliberately separate from guaranteed supplier dimensions.
        height = (
            1.5
            if side == "B"
            else 14
            if ref == "C3"
            else 12
            if ref.startswith("J")
            else 4
            if ref == "S1"
            else 2.5
            if ref == "F1"
            else 1.7
        )
        bodies.append(
            dict(
                reference=ref,
                side=side,
                courtyard_relative_mm=[
                    round(bounds[0] - 100, 6),
                    round(bounds[1] - 100, 6),
                    round(bounds[2] - bounds[0], 6),
                    round(bounds[3] - bounds[1], 6),
                ],
                height_allocation_mm=height,
                height_qualified=False,
            )
        )
    assert actual == expected
    assert mounts == {"H1": [17.5, 8], "H2": [60, 12], "H3": [4, 33], "H4": [60, 40]}
    # Independent selected-terminal geometry checks. Net parity alone cannot
    # establish that the actual package terminals follow the selected pin map.
    for pin, delta in {"1": (0, 0), "2": (0, -6), "3": (-4.7, -3)}.items():
        x, y = terminal_positions[("J1", pin)]
        assert math.dist((x, y), (140 + delta[0], 110.7 + delta[1])) < 1e-6
    assert actual["J1"]["1"] == "DC_IN" and actual["J1"]["2"] == "AGND"
    assert actual["J1"]["3"].startswith("unconnected-")
    assert [actual["S1"][str(i)] for i in (1, 2, 3)] == ["SWITCH_SUPPLY", "POWER_RUN", "AGND"]
    segments = children(tree, "segment")
    assert segments
    graph = {}
    for segment in segments:
        if first(segment, "net")[1] != "/POWER_RUN" or first(segment, "layer")[1] != "F.Cu":
            continue
        p, q = (tuple(round(float(v), 6) for v in first(segment, tag)[1:3]) for tag in ("start", "end"))
        distance = math.dist(p, q)
        graph.setdefault(p, []).append((q, distance))
        graph.setdefault(q, []).append((p, distance))
    start = tuple(round(v, 6) for v in terminal_positions[("Q3", "3")])
    end = tuple(round(v, 6) for v in terminal_positions[("U1", "12")])
    queue, distances = [(0, start)], {start: 0}
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distances[node]:
            continue
        for other, length in graph.get(node, []):
            value = cost + length
            if value < distances.get(other, float("inf")):
                distances[other] = value
                heapq.heappush(queue, (value, other))
    assert end in distances and distances[end] < 8, "Q3-to-SHDN local F.Cu path must remain below 8 mm"
    for net in ("DC_IN", "VIN_SYS", "VIN_IC", "VIN_PROTECTED"):
        assert any(
            str(first(s, "net")[1]) == "/" + net and float(first(s, "width")[1]) >= 1.2 for s in segments
        ), net
    zones = children(tree, "zone")
    planes = [z for z in zones if not children(z, "keepout")]
    keepouts = [z for z in zones if children(z, "keepout")]
    assert len(planes) == 2 and {first(z, "layer")[1] for z in planes} == {"In1.Cu", "B.Cu"}
    assert all(first(z, "net")[1] == "/AGND" and children(z, "filled_polygon") for z in planes)
    assert len(keepouts) == 4
    actual_keepouts = set()
    for zone in keepouts:
        assert set(first(zone, "layers")[1:]) == {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}
        assert all(
            first(first(zone, "keepout"), k)[1] == "not_allowed" for k in ("tracks", "vias", "copperpour")
        )
        points = children(first(first(zone, "polygon"), "pts"), "xy")
        assert len(points) == 32
        center = tuple(sum(float(p[axis]) for p in points) / 32 for axis in (1, 2))
        ref = next(ref for ref, at in mounts.items() if math.dist(center, (100 + at[0], 100 + at[1])) < 1e-5)
        actual_keepouts.add(ref)
        for p, q in zip(points, points[1:] + points[:1]):
            px, py, qx, qy = float(p[1]), float(p[2]), float(q[1]), float(q[2])
            distance = abs((qx - px) * (py - center[1]) - (px - center[0]) * (qy - py)) / math.hypot(
                qx - px, qy - py
            )
            assert distance >= 3.7 - 1e-6
    assert actual_keepouts == set(mounts)
    return dict(
        revision="E23",
        circuit_revision="E16/E21",
        pcb_sha256=sha(pcb),
        board_size_mm=[64, 44, 1.6],
        outline_relative_mm=[[0, 0], [59, 0], [59, 2], [64, 2], [64, 44], [33, 44], [33, 39], [0, 39]],
        mounts_relative_mm=mounts,
        mount_hole_mm=2.2,
        bodies=bodies,
        circuit_components=len(actual),
        routed_segments=len(segments),
        through_vias=len(children(tree, "via")),
        pcb_routed=True,
        rear_control_x_spacing_mm=14,
        local_shutdown_trace_mm=distances[end],
        copper_ampacity_qualified=False,
        housing_placement_verified=False,
        complete_unit_build_ready=False,
        remaining_mechanical_work=[
            "rear wall/PCB outline and jack insertion-depth reconciliation",
            "switch actuator height and accessible slot",
            "component/lead tolerance, harness and board support integration",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    args = parser.parse_args()
    cli = args.kicad_cli.resolve()
    OUT.mkdir(exist_ok=True)
    (OUT / "routing-verification.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e23-check-") as folder:
        temp = Path(folder)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp}/cache</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            FONTCONFIG_FILE=str(font),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )

        def run(*words):
            result = subprocess.run([str(cli), *map(str, words)], env=env, capture_output=True, text=True)
            assert result.returncode == 0, (words, result.stdout, result.stderr)
            return result.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "placement-netlist.xml",
            ROOT / "input_protection.kicad_sch",
        )
        parts, pins = netlist(OUT / "placement-netlist.xml")
        contract(parts, pins)
        library_root = footprint_root(str(cli))
        for name, upstream in [
            ("PJ102AH_RearEdge_E23", "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal"),
            ("JS102011SAQN_RearEdge_E23", "Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN"),
        ]:
            lib, part = upstream.split(":")
            original = read_sexpr((library_root / (lib + ".pretty") / (part + ".kicad_mod")).read_text())
            local = read_sexpr((ROOT / "RMX_Input.pretty" / (name + ".kicad_mod")).read_text())
            assert children(original, "pad") == children(local, "pad"), (
                "Rear-edge variants may change ink only"
            )
        pcb = ROOT / "input_protection.kicad_pcb"
        run(
            "pcb",
            "drc",
            "--refill-zones",
            "--save-board",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            pcb,
        )
        drc = json.loads((OUT / "drc.json").read_text())
        assert not any(drc[k] for k in ("violations", "unconnected_items", "schematic_parity"))
        packet = mechanical(pcb, pins)
        (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
        for name, layers in (
            ("pcb-top", "F.Cu,F.Fab,F.SilkS,Edge.Cuts"),
            ("pcb-bottom", "B.Cu,B.Fab,B.SilkS,Edge.Cuts"),
            ("pcb-ground", "In1.Cu,Edge.Cuts"),
            ("pcb-inner", "In2.Cu,Edge.Cuts"),
        ):
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
        files = list(ROOT.glob("*.py")) + [
            ROOT / f
            for f in (
                "input_protection.kicad_pcb",
                "input_protection.kicad_sch",
                "input_protection.kicad_pro",
                "fp-lib-table",
                "components.json",
                "generated/placement-inputs.json",
                "generated/routing-inputs.json",
                "generated/placement.json",
                "generated/drc.json",
            )
        ]
        files.extend(
            [
                ROOT.parent / "control_inputs/board.py",
                ROOT.parent / "output_stage/check_placement.py",
            ]
        )
        files.extend(ROOT.glob("RMX_Input.pretty/*.kicad_mod"))
        report = dict(
            revision="E23",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            physical_components=48,
            mounting_holes=4,
            native_drc_violations=0,
            schematic_parity_issues=0,
            unconnected_items=0,
            copper_layers=4,
            routed_segments=packet["routed_segments"],
            through_vias=packet["through_vias"],
            saved_ground_planes_filled=2,
            physical_fit_verified=False,
            physical_power_protection_verified=False,
            complete_unit_build_ready=False,
            source_sha256=source_hashes(ROOT, files),
        )
        (OUT / "routing-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E23 KiCad {version}: 48 parts, four M2 holes, {packet['routed_segments']} segments/{packet['through_vias']} vias; zero DRC, parity or open items. Housing and physical qualification remain open."
    )


if __name__ == "__main__":
    main()
