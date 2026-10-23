#!/usr/bin/env python3
"""Independent E20 LED-driver pin, power-domain, channel and footprint audit."""

import argparse
import csv
import datetime
import itertools
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ..common import netlists as eda
from ..common.placement import footprint_root
from ..common.reports import sha, source_hashes
from ..common.sexpr import children, first, read_sexpr
from .check_board import verify as verify_board
from .power_review import reconcile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
FIRMWARE = ROOT.parents[1] / "firmware"


def contract(parts, pins):
    expected, values = {}, {}

    def add(ref, value, mapping):
        expected[ref] = {str(k): v for k, v in mapping.items()}
        values[ref] = value

    def sequence(ref, value, nets):
        add(ref, value, dict(enumerate(nets, 1)))

    for chip in range(4):
        ref = f"U{chip + 1}"
        mapping = {
            1: "AGND",
            2: "BLANK_5V",
            3: "CLOCK_5V",
            4: "DATA_5V" if chip == 0 else f"SERIAL_{chip - 1}",
            29: f"SERIAL_{chip}" if chip < 3 else "unconnected-(U4-SOUT-Pad29)",
            30: "LATCH_5V",
            31: f"IREF_{chip}",
            32: "5V_DIG",
            33: "AGND",
        }
        mapping.update({5 + i: f"LED_{chip * 24 + i:02d}" for i in range(24)})
        add(ref, "TLC5947DAPR", mapping)
    add(
        "U5",
        "SN74LVC8T245PWR",
        {
            1: "V3V3_IO",
            2: "V3V3_IO",
            3: "LED_MOSI",
            4: "LED_SCK",
            5: "LED_XLAT",
            6: "LED_BLANK",
            7: "AGND",
            8: "AGND",
            9: "AGND",
            10: "AGND",
            11: "AGND",
            12: "AGND",
            13: "AGND",
            14: "unconnected-(U5-B8-Pad14)",
            15: "unconnected-(U5-B7-Pad15)",
            16: "unconnected-(U5-B6-Pad16)",
            17: "unconnected-(U5-B5-Pad17)",
            18: "BLANK_5V_SRC",
            19: "LATCH_5V_SRC",
            20: "CLOCK_5V_SRC",
            21: "DATA_5V_SRC",
            22: "OE_N",
            23: "5V_DIG",
            24: "5V_DIG",
        },
    )
    for ref, value, rail, pg in [
        ("U6", "TPS3808G33DBVR", "V3V3_IO", "PG_3V3"),
        ("U7", "TPS3808G50DBVR", "5V_DIG", "PG_5V"),
    ]:
        add(ref, value, {1: pg, 2: "AGND", 3: rail, 4: f"unconnected-({ref}-CT-Pad4)", 5: rail, 6: rail})
    add("Q1", "AO3400A", {1: "PG_3V3", 2: "ENABLE_MID", 3: "OE_N"})
    add("Q2", "AO3400A", {1: "PG_5V", 2: "AGND", 3: "ENABLE_MID"})
    sequence(
        "J1", "Header8", ["AGND", "5V_DIG", "V3V3_IO", "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK", "AGND"]
    )
    for header, base, order in [
        ("J2", 0, range(23, 11, -1)),
        ("J3", 0, range(12)),
        ("J4", 48, range(23, 11, -1)),
        ("J5", 48, range(12)),
    ]:
        sequence(
            header,
            "Header26",
            [f"LED_{base + local + offset:02d}" for offset in (0, 24) for local in order]
            + ["5V_DIG", "5V_DIG"],
        )
    resistors = [(f"R{i + 1}", "16.5k 1%", f"IREF_{i}", "AGND") for i in range(4)] + [
        ("R5", "47k 1%", "OE_N", "V3V3_IO"),
        ("R6", "10k 1%", "PG_3V3", "V3V3_IO"),
        ("R7", "10k 1%", "PG_5V", "5V_DIG"),
        ("R8", "100k 1%", "PG_3V3", "AGND"),
        ("R9", "100k 1%", "PG_5V", "AGND"),
        ("R10", "10k 1%", "LED_BLANK", "V3V3_IO"),
        ("R11", "10k 1%", "BLANK_5V", "5V_DIG"),
        ("R12", "100k 1%", "DATA_5V", "AGND"),
        ("R13", "100k 1%", "CLOCK_5V", "AGND"),
        ("R14", "100k 1%", "LATCH_5V", "AGND"),
        ("R15", "33R 1%", "DATA_5V_SRC", "DATA_5V"),
        ("R16", "33R 1%", "CLOCK_5V_SRC", "CLOCK_5V"),
        ("R17", "33R 1%", "LATCH_5V_SRC", "LATCH_5V"),
        ("R18", "33R 1%", "BLANK_5V_SRC", "BLANK_5V"),
        ("R19", "100k 1%", "LED_MOSI", "AGND"),
        ("R20", "100k 1%", "LED_SCK", "AGND"),
        ("R21", "100k 1%", "LED_XLAT", "AGND"),
    ]
    for ref, value, a, b in resistors:
        sequence(ref, value, [a, b])
    caps = [("100nF 16V X7R", "5V_DIG"), ("4.7uF 16V X7R", "5V_DIG")] * 4 + [
        ("100nF 16V X7R", "V3V3_IO"),
        ("100nF 16V X7R", "5V_DIG"),
        ("100nF 16V X7R", "V3V3_IO"),
        ("100nF 16V X7R", "5V_DIG"),
        ("22uF 25V X7R", "5V_DIG"),
        ("4.7uF 16V X7R", "5V_DIG"),
    ]
    for i, (value, rail) in enumerate(caps):
        sequence(f"C{i + 1}", value, [rail, "AGND"])
    assert len(expected) == 49 and pins == expected, (pins, expected)
    assert {ref: part.findtext("value") for ref, part in parts.items()} == values
    return expected


def footprint_check():
    path = ROOT / "RMX_LED.pretty/TLC5947_DAP0032C.kicad_mod"
    pads = children(read_sexpr(path.read_text()), "pad")
    copper = {
        str(p[1]): p for p in pads if any(str(layer).endswith(".Cu") for layer in first(p, "layers")[1:])
    }
    assert set(copper) == set(map(str, range(1, 34)))
    for n in range(1, 33):
        pad = copper[str(n)]
        x, y = (-3.75, -4.875 + 0.65 * (n - 1)) if n <= 16 else (3.75, 4.875 - 0.65 * (n - 17))
        assert all(math.isclose(float(a), b, abs_tol=1e-6) for a, b in zip(first(pad, "at")[1:3], (x, y)))
        assert list(map(float, first(pad, "size")[1:3])) == [1.5, 0.45]
    assert list(map(float, first(copper["33"], "size")[1:3])) == [5.2, 11]
    mask = [p for p in pads if list(first(p, "layers")[1:]) == ["F.Mask"]]
    paste = [p for p in pads if list(first(p, "layers")[1:]) == ["F.Paste"]]
    assert len(mask) == 1 and list(map(float, first(mask[0], "size")[1:3])) == [3.04, 3.74]
    assert len(paste) == 4
    area = sum(math.prod(map(float, first(p, "size")[1:3])) for p in paste)
    assert 0.70 < area / (3.04 * 3.74) < 0.76
    return {
        "source": "TI TLC5947 DAP0032C drawing4223691/A",
        "sha256": sha(path),
        "signal_pads": 32,
        "thermal_pad": 33,
        "paste_coverage_fraction": area / (3.04 * 3.74),
        "package_variant_assembler_qualification_complete": False,
    }


def screens(parts):
    current = 41 * 1.20 / eda.number(parts["R1"].findtext("value"))
    assert 0.002 < current < 0.0031
    cases = []
    for a, b, blank in itertools.product((False, True), repeat=3):
        # NMOS channels are bidirectional only when on; body diodes are S->D.
        edges = {"AGND": ["ENABLE_MID"], "ENABLE_MID": ["OE_N"], "OE_N": []}
        if a:
            edges["OE_N"].append("ENABLE_MID")
        if b:
            edges["ENABLE_MID"].append("AGND")
        seen, todo = set(), ["OE_N"]
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(edges[node])
        enabled = "AGND" in seen
        assert enabled == (a and b)
        local_blank = blank if enabled else True
        assert local_blank or (a and b and not blank)
        cases.append(
            dict(pg_3v3=a, pg_5v=b, mcu_blank=blank, buffer_enabled=enabled, driver_blank=local_blank)
        )
    allocated = 96 * 0.004 + 4 * 0.09 + 0.02
    return dict(
        nominal_sink_current_a=current,
        nominal_all_channels_a=current * 96,
        nominal_current_is_not_a_guaranteed_low_current_bound=True,
        allocated_sink_ceiling_per_channel_a=0.004,
        allocated_icc_per_driver_a=0.09,
        allocated_misc_driver_board_a=0.02,
        allocated_5v_board_total_a=allocated,
        allocation_requires_physical_validation=True,
        prior_led_sink_only_budget_a=0.288,
        additional_budget_to_reconcile_a=allocated - 0.288,
        e14_e17_total_digital_budget_reanalysis_required=True,
        note="ICC/reference/error specifications are given at other IREF test points. Allocation is an engineering requirement, not a guaranteed device bound at3mA. Verify thermal, brightness, ripple and system load.",
        settled_ideal_enable_cases=cases,
        actual_partial_power_brownout_and_restore_frames_verified=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    parser.add_argument(
        "--placed-only",
        action="store_true",
        help="Explicitly check placement without accepting unrouted copper",
    )
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="rmx-e20-check-") as folder:
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

        def run(*arguments):
            r = subprocess.run([str(cli), *map(str, arguments)], env=env, capture_output=True, text=True)
            assert r.returncode == 0, (arguments, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("version")
        source = ROOT / "led_driver.kicad_sch"
        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "--exit-code-violations",
            "-o",
            OUT / "erc.json",
            source,
        )
        assert not any(s["violations"] for s in json.loads((OUT / "erc.json").read_text())["sheets"])
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", OUT / "netlist.xml", source)
        parts, pins = eda.netlist(OUT / "netlist.xml")
        expected = contract(parts, pins)
        plan = json.loads((ROOT / "integration.json").read_text())
        assert plan["revision"] == "E20" and plan["firmware_pin_map"] == "F04"
        assert plan["board_size_mm"] == [91, 27, 1.6] and plan["copper_layers"] == 6
        assert plan["layout_origin_mm"] == [197, 77, 6.5]
        assert plan["ground_planes"] == ["In1.Cu", "In4.Cu"]
        assert plan["mount_centers_layout_mm"] == [[200, 84], [284, 84], [200, 99], [284, 99]]
        assert plan["J1"] == [pins["J1"][str(i)] for i in range(1, 9)]
        assert plan["logical_sink_channels"] == 96 and plan["nominal_iref_resistance_ohm"] == 16500
        assert not plan["full_led_display_system_complete"] and not plan["full_unit_power_budget_closed"]
        board_checks = verify_board(run, expected, args.placed_only)
        footprint = footprint_check()
        analysis = screens(parts)
        assert math.isclose(plan["allocated_board_and_emitters_5v_a"], analysis["allocated_5v_board_total_a"])
        power_review, upstream_sources = reconcile(analysis["allocated_5v_board_total_a"])
        (OUT / "power-reconciliation.json").write_text(json.dumps(power_review, indent=2) + "\n")
        carrier = ROOT.parent / "processor_carrier/processor_carrier.kicad_sch"
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", temp / "carrier.xml", carrier)
        assert eda.netlist(temp / "carrier.xml")[1]["J11"] == pins["J1"]
        io = (FIRMWARE / "BoardIO.h").read_text()
        assert re.search(
            r"DelayUs\(1\);\s*latch.Write\(true\);\s*daisy::System::DelayUs\(1\);\s*latch.Write\(false\);\s*daisy::System::DelayUs\(1\);\s*blank.Write\(false\);",
            io,
        )
        assert "BaudPrescaler::PS_64" in io
        labels = (
            [f"scene_{i}" for i in range(10)]
            + [f"isolate_{i}" for i in range(4)]
            + ["source_input", "source_xpad"]
            + [f"pad_{i}" for i in range(4)]
            + ["quantize", "auto", "roll", "overdub", "hold"]
            + [f"meter_{row}_{i}" for row in ("input", "output") for i in range(20)]
            + [f"bank_{i}" for i in range(4)]
            + [
                f"digit_{i}_{segment}"
                for i in range(3)
                for segment in ("a", "b", "c", "d", "e", "f", "g", "dp")
            ]
            + ["ring_r", "ring_g", "ring_b"]
        )
        assert len(labels) == len(set(labels)) == 96
        with (OUT / "channel-map.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                ["Logical_channel", "Function", "IC", "OUT", "DAP_pin", "Header", "Pin", "Anode_pins"]
            )
            for n, label in enumerate(labels):
                chip, output = divmod(n, 24)
                header_ref = f"J{2 + 2 * (chip // 2) + (1 if output < 12 else 0)}"
                header_pin = (output if output < 12 else 23 - output) + 1 + 12 * (chip % 2)
                assert (
                    pins[f"U{chip + 1}"][str(5 + output)]
                    == pins[header_ref][str(header_pin)]
                    == f"LED_{n:02d}"
                )
                writer.writerow(
                    [n, label, f"U{chip + 1}", output, 5 + output, header_ref, header_pin, "25/26=5V_DIG"]
                )
        (OUT / "electrical-screens.json").write_text(json.dumps(analysis, indent=2) + "\n")
        run("sch", "export", "svg", "--exclude-drawing-sheet", "-o", OUT, source)
        files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix not in (".kicad_prl", ".lck")]
        files += list((ROOT / "RMX_LED.pretty").glob("*.kicad_mod")) + [
            carrier,
            FIRMWARE / "BoardIO.h",
            FIRMWARE / "WireFormat.h",
            ROOT.parents[2] / "tests/firmware/hardware_wire_tests.cpp",
            OUT / "channel-map.csv",
            OUT / "electrical-screens.json",
            OUT / "placement-inputs.json",
            OUT / "placement.json",
            OUT / "power-reconciliation.json",
            ROOT.parent / "control_inputs/board.py",
            ROOT.parent / "output_stage/check_placement.py",
        ]
        files += upstream_sources
        if not args.placed_only:
            files.append(OUT / "routing-inputs.json")
        report = dict(
            revision="E20",
            load_update_revision=power_review["load_update_revision"],
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            kicad_version=version,
            circuit_components=49,
            led_sink_channels=96,
            native_erc_violations=0,
            independent_pin_contract_passed=True,
            carrier_interface_fresh=True,
            firmware_pin_map="F04",
            explicit_latch_guards_us=1,
            custom_footprint=footprint,
            **board_checks,
            physical_fit_verified=False,
            physical_timing_audio_thermal_verified=False,
            full_led_display_system_complete=False,
            full_unit_power_budget_closed=False,
            source_sha256=source_hashes(ROOT, files),
        )
        (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "E20:49 independent contracts,96 sink channels,zero native ERC/DRC/parity; fresh E19 wiring and explicit latch guards pass. Panel LEDs, power closure and physical qualification remain open."
    )


if __name__ == "__main__":
    main()
