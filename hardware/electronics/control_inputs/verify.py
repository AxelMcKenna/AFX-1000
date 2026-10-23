#!/usr/bin/env python3
"""Independent E18 schematic, PCB, F04 wiring and placement evidence."""

import argparse
import csv
import datetime
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.placement import footprint_root
from ..common.reports import source_hashes
from ..common.sexpr import children, first, read_sexpr
from ..output_stage import check_placement as placement

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract(parts, pins):
    expected = {}
    used = {}
    for chip in range(3):
        u = f"U{chip + 1}"
        nets = {
            9: "V3V3_IO",
            10: "AGND",
            12: "SCL",
            13: "SDA",
            15: "V3V3_IO" if chip == 1 else "AGND",
            16: "V3V3_IO" if chip == 2 else "AGND",
            17: "AGND",
            18: "CONTROL_RESET_N",
        }
        if chip < 2:
            nets.update({21 + n: f"CONTROL_{chip * 14 + n:02d}" for n in range(7)})
            nets.update({1 + n: f"CONTROL_{chip * 14 + 7 + n:02d}" for n in range(7)})
        else:
            nets.update({1 + n: f"CONTROL_{28 + n:02d}" for n in range(4)})
            nets.update({21: "MODE_SEND_RETURN", 22: "MANUAL_BYPASS", 23: "ANALOG_OK", 24: "INPUT_READY"})
        for n in range(1, 29):
            if n not in nets:
                name = (
                    "GPB" + str(n - 1)
                    if n <= 8
                    else "GPA" + str(n - 21)
                    if n >= 21
                    else "INTB"
                    if n == 19
                    else "INTA"
                    if n == 20
                    else "NC"
                )
                nets[n] = f"unconnected-({u}-{name}-Pad{n})"
        expected[u] = {str(n): net for n, net in nets.items()}
        used[u] = "MCP23017-E/SO"
    for chip in range(2):
        sequence = []
        for column in range(7):
            sequence += [f"CONTROL_{chip * 14 + 6 - column:02d}", f"CONTROL_{chip * 14 + 7 + column:02d}"]
        expected[f"J{chip + 1}"] = dict(zip(map(str, range(1, 17)), sequence + ["AGND", "AGND"]))
        used[f"J{chip + 1}"] = "Header16"
    for ref, sequence in [
        ("J3", ["AGND"] + [f"CONTROL_{i:02d}" for i in range(28, 32)]),
        ("J4", ["AGND", "MODE_SEND_RETURN", "MANUAL_BYPASS", "ANALOG_OK", "INPUT_READY"]),
        ("J5", ["AGND", "V3V3_IO", "SCL", "SDA", "CONTROL_RESET_N"]),
    ]:
        expected[ref] = dict(zip(map(str, range(1, 6)), sequence))
        used[ref] = "Header5"
    for ref, node, value in [
        ("R1", "CONTROL_RESET_N", "100k 1%"),
        ("R2", "ANALOG_OK", "47k 1%"),
        ("R3", "INPUT_READY", "270k 1%"),
    ]:
        expected[ref] = {"1": node, "2": "AGND"}
        used[ref] = value
    for i in range(1, 5):
        expected[f"C{i}"] = {"1": "V3V3_IO", "2": "AGND"}
        used[f"C{i}"] = "100nF 16V X7R" if i < 4 else "1uF 16V X7R"
    assert pins == expected, (pins, expected)
    assert {r: p.findtext("value") for r, p in parts.items()} == used
    assert len(parts) == 15
    mapping = json.loads((ROOT.parents[1] / "firmware/control-inputs.json").read_text())
    assert mapping["revision"] == "F04" and len(mapping["front_inputs"]) == 32
    for entry in mapping["front_inputs"]:
        n = entry["logical_index"]
        chip = n // 14 if n < 28 else 2
        local = n % 14 if n < 28 else n - 28
        pad = (21 + local if local < 7 else local - 6) if chip < 2 else local + 1
        assert entry["address"] == 0x20 + chip and entry["soic_pin"] == pad
        assert expected[f"U{chip + 1}"][str(pad)] == f"CONTROL_{n:02d}"
        assert not entry["gpio"].endswith("7")
    return expected


def mechanical(pcb, contract):
    tree = read_sexpr(pcb.read_text())
    bodies = []
    mounts = {}
    actual = {}
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    corners = {
        tuple(map(float, first(line, tag)[1:3]))
        for line in children(tree, "gr_line")
        for tag in ("start", "end")
    }
    assert corners == {(100, 100), (164, 100), (164, 154), (100, 154)}
    assert {str(first(z, "layer")[1]) for z in children(tree, "zone")} == {"In1.Cu"}
    zone = children(tree, "zone")[0]
    assert first(zone, "net")[1] == "/AGND" and children(zone, "filled_polygon")
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pads = children(fp, "pad")
        if ref.startswith("H"):
            assert (
                len(pads) == 1 and pads[0][2] == "np_thru_hole" and float(first(pads[0], "drill")[1]) == 2.4
            )
            x, y = placement.transform(fp, first(pads[0], "at")[1:3])
            mounts[ref] = [x - 100, y - 100]
            x, y = 111 + x - 100, 43 + y - 100
            bodies.extend(
                [
                    [
                        f"e18_{ref}_spacer",
                        x - 2.75,
                        y - 2.75,
                        8.1,
                        5.5,
                        5.5,
                        4.0,
                        "4mm spacer OD<=5.5mm on unrouted processor carrier; exact part and attachment unselected",
                    ],
                    [
                        f"e18_{ref}_head",
                        x - 2.75,
                        y - 2.75,
                        13.7,
                        5.5,
                        5.5,
                        2.0,
                        "M2 screw head/washer height<=2mm and OD<=5.5mm; final engagement unverified",
                    ],
                ]
            )
            continue
        actual[ref] = {str(p[1]): str(first(p, "net")[1]).lstrip("/") for p in pads}
        for p in pads:
            net = str(first(p, "net")[1]).lstrip("/")
            if net.startswith("unconnected-"):
                # Neither reserved pins nor unused outputs may acquire copper.
                assert not any(
                    str(first(item, "net")[1]).lstrip("/") == net
                    for tag in ("segment", "via")
                    for item in children(tree, tag)
                ), (ref, p[1])
        bounds = placement.courtyard(fp, "F.CrtYd")
        expand = 0.5 if ref.startswith("J") else 0
        x0, y0, x1, y1 = bounds[0] - expand, bounds[1] - expand, bounds[2] + expand, bounds[3] + expand
        height = (
            11.0
            if ref.startswith("J")
            else 2.9
            if ref.startswith("U")
            else 1.5
            if ref.startswith("C")
            else 0.9
        )
        x, y = 111 + x0 - 100, 43 + y0 - 100
        bodies.append(
            [
                f"e18_{ref}",
                round(x, 6),
                round(y, 6),
                13.7,
                round(x1 - x0, 6),
                round(y1 - y0, 6),
                round(0.31 + height, 6),
                "Courtyard + 0.5mm connector allowance; height includes nominal board top + 0.15 seat + 0.16 PCB tolerance. Connector/harness bounds and part MPNs unqualified.",
            ]
        )
        for pad in pads:
            if pad[2] == "thru_hole":
                x, y = placement.transform(fp, first(pad, "at")[1:3])
                bodies.append(
                    [
                        f"e18_{ref}_lead_{pad[1]}",
                        round(111 + x - 101, 6),
                        round(43 + y - 101, 6),
                        8.95,
                        2,
                        2,
                        3.15,
                        "Trim THT protrusion including solder <=3mm; 0.15mm low-seat allowance; carrier top/tolerance qualification open",
                    ]
                )
    assert actual == contract
    assert mounts == {"H1": [4, 4], "H2": [60, 4], "H3": [4, 50], "H4": [60, 50]}, mounts
    return dict(
        revision="E18",
        pcb_sha256=sha(pcb),
        board=["control_input_hub", 111, 43, 12.1, 64, 54, 1.6, "E18 routed digital input daughterboard"],
        mount_centers_layout_mm=[[111 + mounts[key][0], 43 + mounts[key][1]] for key in sorted(mounts)],
        mount_hole_mm=2.4,
        spacer_nominal_height_mm=4,
        spacer_outer_diameter_limit_mm=5.5,
        carrier_drill_pattern_is_proposal=True,
        pcb_routed=True,
        bodies=bodies,
        physical_fit_verified=False,
        limits=[
            "Digital input hub only; pots/LED/touch/angle sensor and full system boards still unfinished",
            "Processor carrier needs matching holes and routing keepouts; its shape remains a placement proposal",
            "Connector/harness, spacer/screw and height bounds require exact parts and physical qualification",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    fp = footprint_root(str(cli))
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e18-check-") as directory:
        temp = Path(directory)
        font = temp / "fonts.conf"
        font.write_text(
            "<fontconfig><dir>/System/Library/Fonts</dir><cachedir>"
            + str(temp / "cache")
            + "</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(fp),
            FONTCONFIG_FILE=str(font),
        )

        def run(*args):
            result = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert result.returncode == 0, (args, result.stdout, result.stderr)
            return result.stdout.strip()

        version = run("version")
        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "--exit-code-violations",
            "-o",
            OUT / "erc.json",
            ROOT / "control_inputs.kicad_sch",
        )
        erc = json.loads((OUT / "erc.json").read_text())
        assert not any(s["violations"] for s in erc["sheets"])
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            ROOT / "control_inputs.kicad_sch",
        )
        parts, pins = eda.netlist(OUT / "netlist.xml")
        expected = contract(parts, pins)
        integration = json.loads((ROOT / "integration.json").read_text())
        assert integration["firmware_revision"] == "F04" and integration["front_inputs"] == 32
        assert integration["receiving_reset_pulldown_ohm"] == 100000
        assert (
            integration["receiving_analog_ok_pulldown_ohm"] == 47000
            and integration["receiving_input_ready_pulldown_ohm"] == 270000
        )
        assert integration["bus_header_J5"] == [pins["J5"][str(i)] for i in range(1, 6)]
        assert integration["rear_header_J4"] == [pins["J4"][str(i)] for i in range(1, 6)]
        assert integration["rear_header_external_profile_only"] and not integration["physical_fit_verified"]
        assert not integration["full_control_board_complete"] and not integration["local_i2c_pullups_fitted"]
        labels = {
            p["logical_index"]: p["id"]
            for p in json.loads((ROOT.parents[1] / "firmware/control-inputs.json").read_text())[
                "front_inputs"
            ]
        }
        with (OUT / "connector-map.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Header", "Pin", "Net", "Front_control_id", "Profile_note"])
            for ref in ("J1", "J2", "J3", "J4", "J5"):
                for pin, net in sorted(pins[ref].items(), key=lambda pair: int(pair[0])):
                    writer.writerow(
                        [
                            ref,
                            pin,
                            net,
                            labels[int(net.split("_")[1])]
                            if net.startswith("CONTROL_") and net != "CONTROL_RESET_N"
                            else "",
                            "external only"
                            if ref == "J4"
                            else "both profiles; J5 reset source depends on profile",
                        ]
                    )
        run(
            "pcb",
            "drc",
            "--refill-zones",
            "--save-board",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "--exit-code-violations",
            "-o",
            OUT / "drc.json",
            ROOT / "control_inputs.kicad_pcb",
        )
        drc = json.loads((OUT / "drc.json").read_text())
        assert not drc["violations"] and not drc["unconnected_items"] and not drc["schematic_parity"]
        # Fresh source interfaces, with the documented reset/profile aliases.
        other = {}
        for name in ("converter", "sequenced_bypass"):
            source = ROOT.parent / name / (name + ".kicad_sch")
            dest = temp / (name + ".xml")
            run("sch", "export", "netlist", "--format", "kicadxml", "-o", dest, source)
            other[name] = eda.netlist(dest)[1]
        assert [other["converter"]["J5"][str(i)] for i in (1, 2, 3, 4, 6)] == [
            "AGND",
            "SCL",
            "SDA",
            "CODEC_RUN",
            "ANALOG_OK",
        ]
        assert other["sequenced_bypass"]["J6"] == {"1": "AGND", "2": "INPUT_READY"}
        footprint_hashes = {}
        for part in parts.values():
            identifier = part.findtext("footprint")
            library, name = identifier.split(":")
            path = fp / (library + ".pretty") / (name + ".kicad_mod")
            footprint_hashes[identifier] = sha(path)
            if identifier.startswith("Package_SO:SOIC-28W"):
                pads = children(read_sexpr(path.read_text()), "pad")
                assert {p[1] for p in pads} == set(map(str, range(1, 29)))
                for p in pads:
                    n = int(p[1])
                    x, y = map(float, first(p, "at")[1:3])
                    xx = -4.65 if n <= 14 else 4.65
                    yy = -8.255 + 1.27 * (n - 1) if n <= 14 else 8.255 - 1.27 * (n - 15)
                    assert math.isclose(x, xx, abs_tol=1e-6) and math.isclose(y, yy, abs_tol=1e-6)
        packet = mechanical(ROOT / "control_inputs.kicad_pcb", expected)
        assert integration["daughterboard_layout_origin_mm"] == packet["board"][1:4]
        assert integration["board_size_mm"] == packet["board"][4:7]
        assert integration["carrier_drill_centers_layout_mm"] == packet["mount_centers_layout_mm"]
        (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
        for name, layers in [
            ("top", "F.Cu,F.Fab,F.SilkS,Edge.Cuts"),
            ("bottom", "B.Cu,Edge.Cuts"),
            ("logic", "In2.Cu,Edge.Cuts"),
            ("ground", "In1.Cu,Edge.Cuts"),
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
                ROOT / "control_inputs.kicad_pcb",
            )
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", OUT, ROOT / "control_inputs.kicad_sch")
        files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".kicad_prl", ".pyc", ".lck")]
        files += [
            ROOT / "RMX_Control.pretty/M2_Clearance.kicad_mod",
            OUT / "placement.json",
            OUT / "routing-inputs.json",
            OUT / "connector-map.csv",
            ROOT.parents[1] / "firmware/control-inputs.json",
            ROOT.parent / "output_stage/place.py",
            ROOT.parent / "output_stage/verify.py",
            ROOT.parent / "output_stage/check_placement.py",
            ROOT.parent / "converter/converter.kicad_sch",
            ROOT.parent / "sequenced_bypass/sequenced_bypass.kicad_sch",
        ]
        tree = read_sexpr((ROOT / "control_inputs.kicad_pcb").read_text())
        report = dict(
            revision="E18",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            circuit_components=15,
            front_inputs=32,
            external_rear_inputs=4,
            mounting_holes=4,
            board_size_mm=[64, 54, 1.6],
            native_erc_violations=0,
            native_drc_violations=0,
            schematic_parity_issues=0,
            unconnected_items=0,
            routed_segments=len(children(tree, "segment")),
            through_vias=len(children(tree, "via")),
            saved_ground_plane_filled=True,
            pcb_routed=True,
            physical_fit_verified=False,
            physical_scan_bus_emi_verified=False,
            complete_control_board=False,
            source_load_interfaces_fresh=True,
            source_footprint_hashes=footprint_hashes,
            source_sha256=source_hashes(ROOT, files),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E18:15 parts,32 front inputs,4 rear/status inputs; zero native ERC/DRC/parity/unconnected; {report['routed_segments']} segments/{report['through_vias']} vias. Physical validation open."
    )


if __name__ == "__main__":
    main()
