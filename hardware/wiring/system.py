"""External-profile logical interconnects; no production harness or power release."""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from ..electronics.common.netlists import netlist
from ..electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
ELECTRONICS = REPO / "hardware/electronics"
BOARDS = (
    "power_supply",
    "input_protection",
    "rail_disconnect",
    "rail_monitor",
    "processor_carrier",
    "control_inputs",
    "led_driver",
    "converter",
    "input_range",
    "adc_driver",
    "dac_receiver",
    "output_stage",
    "sequenced_bypass",
)

# Aliases are specific to a board/header/pin. Never rename all local 5 V nets.
ALIASES = {
    ("input_range", "J4", "1"): ("5V", "5V_DIG", "power_supply/README.md"),
    ("output_stage", "J3", "1"): ("5V", "5V_DIG", "power_supply/README.md"),
    ("sequenced_bypass", "J1", "1"): ("5V", "5V_DIG", "power_supply/README.md"),
    ("sequenced_bypass", "J5", "1"): ("5V", "5V_DIG", "power_supply/README.md"),
    ("sequenced_bypass", "J1", "3"): ("3V3", "V3V3_IO", "power_supply/README.md"),
    ("sequenced_bypass", "J3", "1"): ("3V3", "V3V3_IO", "power_supply/README.md"),
    ("control_inputs", "J5", "5"): ("CONTROL_RESET_N", "CODEC_RUN", "processor_carrier/verify.py"),
    ("control_inputs", "J4", "3"): ("MANUAL_BYPASS", "BYPASS_SENSE", "processor_carrier/verify.py"),
    ("adc_driver", "J4", "2"): ("DRV_ENABLE", "CHIP_EN", "adc_driver/integration.json"),
}


def canonical(endpoint, local_net):
    alias = ALIASES.get(tuple(endpoint))
    if alias is None:
        return local_net
    assert local_net == alias[0], ("Alias local net changed", endpoint, local_net)
    return alias[1]


def board_tables(kicad_cli=None):
    """Cross-check saved exports, component manifests and actual header lands."""
    result, sources, evidence = {}, {}, {}

    def track(path):
        sources[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()

    with tempfile.TemporaryDirectory(prefix="rmx-system-interconnect-") as directory:
        temp = Path(directory)
        env = dict(os.environ, KICAD_CONFIG_HOME=str(temp / "kicad"))
        for board in BOARDS:
            folder = ELECTRONICS / board
            xml = folder / "generated/netlist.xml"
            _, pins = netlist(xml)
            components = json.loads((folder / "components.json").read_text())
            headers = {}
            for part in components:
                if not part["ref"].startswith("J"):
                    continue
                expected = (
                    {str(p["number"]): p["net"] for p in part["pins"] if p.get("net")}
                    if "pins" in part
                    else {str(n): v for n, v in part["nets"].items() if v}
                )
                actual = {n: v for n, v in pins[part["ref"]].items() if not v.startswith("unconnected-")}
                assert expected == actual, ("Component/export header mismatch", board, part["ref"])
                headers[part["ref"]] = actual
            if kicad_cli:
                exported = temp / (board + ".xml")
                subprocess.run(
                    [
                        str(kicad_cli),
                        "sch",
                        "export",
                        "netlist",
                        "--format",
                        "kicadxml",
                        "-o",
                        str(exported),
                        str(folder / (board + ".kicad_sch")),
                    ],
                    check=True,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                _, fresh = netlist(exported)
                assert fresh == pins, ("Saved native netlist is stale", board)
            pcb = folder / (board + ".kicad_pcb")
            if board == "power_supply":
                pcb = folder / "routing/power_supply.kicad_pcb"
            elif board == "rail_disconnect":
                pcb = folder / "placement/rail_disconnect.kicad_pcb"
            physical = {}
            if pcb.exists():
                for footprint in children(read_sexpr(pcb.read_text()), "footprint"):
                    ref = next(p[2] for p in children(footprint, "property") if p[1] == "Reference")
                    if ref not in headers:
                        continue
                    lands = {}
                    for pad in children(footprint, "pad"):
                        if str(pad[1]) and children(pad, "net"):
                            lands[str(pad[1])] = str(first(pad, "net")[-1]).lstrip("/")
                    connected = {n: v for n, v in lands.items() if not v.startswith("unconnected-")}
                    assert connected == headers[ref], ("PCB/export header mismatch", board, ref)
                    physical[ref] = connected
                assert set(physical) == set(headers), ("Missing PCB header", board)
                track(pcb)
            result[board] = headers
            evidence[board] = dict(
                native_schematic_export_rechecked=bool(kicad_cli),
                component_header_contracts_match=True,
                physical_header_lands_checked=bool(physical),
                schematic_only_interfaces=not bool(physical),
                production_connector_qualified=False,
            )
            for path in [xml, folder / "components.json", folder / (board + ".kicad_sch")]:
                track(path)
    for _, _, reference in ALIASES.values():
        track(ELECTRONICS / reference)
    return result, sources, evidence


def specifications():
    """Pin contracts independent of exported net labels and routing results."""
    rows = []

    def link(harness, a, b, pairs):
        for pa, pb, net in pairs:
            rows.append((harness, (*a, str(pa)), (*b, str(pb)), net))

    def straight(harness, a, b, nets):
        link(harness, a, b, [(i, i, n) for i, n in enumerate(nets, 1)])

    straight("DC-PROTECTED", ("input_protection", "J2"), ("power_supply", "J1"), ["VIN_PROTECTED", "AGND"])
    straight("POWER-READY", ("power_supply", "J5"), ("input_protection", "J3"), ["AGND", "POWER_READY"])
    straight(
        "PWR-ANALOG",
        ("power_supply", "J2"),
        ("rail_disconnect", "J1"),
        ["P19_SRC", "AGND", "N19_SRC", "P12_SRC", "N12_SRC", "V5_REG_SRC"],
    )
    straight("PWR-DIGITAL", ("power_supply", "J3"), ("rail_disconnect", "J2"), ["5V_DIG_SRC", "AGND"])
    straight(
        "PWR-AUX-RUN",
        ("input_protection", "J6"),
        ("rail_disconnect", "J5"),
        ["V2V5_AUX", "AGND", "POWER_RUN"],
    )
    for name, header, pins in [
        ("output_stage", "J4", [(1, 1, "P19"), (2, 2, "AGND"), (3, 3, "N19"), (4, 4, "P12"), (5, 5, "N12")]),
        ("input_range", "J3", [(4, 1, "P12"), (2, 2, "AGND"), (5, 3, "N12")]),
        ("adc_driver", "J3", [(4, 1, "P12"), (2, 2, "AGND"), (5, 3, "N12"), (6, 4, "V5_REG")]),
        ("dac_receiver", "J3", [(4, 1, "P12"), (2, 2, "AGND"), (5, 3, "N12")]),
        ("converter", "J4", [(6, 1, "V5_REG")]),
        (
            "rail_monitor",
            "J2",
            [(1, 1, "P19"), (2, 2, "AGND"), (3, 3, "N19"), (4, 4, "P12"), (5, 5, "N12"), (6, 6, "V5_REG")],
        ),
    ]:
        link("LOAD-" + name.upper(), ("rail_disconnect", "J3"), (name, header), pins)
    straight("DIG-PROCESSOR", ("rail_disconnect", "J4"), ("processor_carrier", "J1"), ["5V_DIG", "AGND"])
    link(
        "DIG-BYPASS",
        ("rail_disconnect", "J4"),
        ("sequenced_bypass", "J1"),
        [(1, 1, "5V_DIG"), (2, 2, "AGND")],
    )
    link("DIG-MONITOR", ("rail_disconnect", "J4"), ("rail_monitor", "J1"), [(1, 1, "5V_DIG"), (2, 3, "AGND")])
    link("IO-BYPASS", ("processor_carrier", "J6"), ("sequenced_bypass", "J1"), [(2, 3, "V3V3_IO")])
    link("IO-MONITOR", ("processor_carrier", "J6"), ("rail_monitor", "J1"), [(2, 2, "V3V3_IO")])
    straight(
        "CONTROL-BUS",
        ("processor_carrier", "J2"),
        ("control_inputs", "J5"),
        ["AGND", "V3V3_IO", "SCL", "SDA", "CODEC_RUN"],
    )
    straight(
        "BYPASS-CONTROL",
        ("processor_carrier", "J3"),
        ("sequenced_bypass", "J2"),
        ["AGND", "HEARTBEAT", "MCU_PERMIT", "GAIN_REQ", "ARMED", "BYPASS_SENSE"],
    )
    straight(
        "REAR-STATUS",
        ("processor_carrier", "J4"),
        ("control_inputs", "J4"),
        ["AGND", "MODE_SEND_RETURN", "BYPASS_SENSE", "ANALOG_OK", "INPUT_READY"],
    )
    straight(
        "SAI-AUDIO",
        ("processor_carrier", "J5"),
        ("converter", "J3"),
        ["AGND", "BCLK", "WS", "ADC_DATA", "DAC_DATA"],
    )
    link(
        "CODEC-IO-POWER",
        ("processor_carrier", "J6"),
        ("converter", "J4"),
        [(1, 2, "AGND"), (2, 3, "V3V3_IO")],
    )
    link(
        "CODEC-CONTROL",
        ("processor_carrier", "J6"),
        ("converter", "J5"),
        [(1, 1, "AGND"), (3, 2, "SCL"), (4, 3, "SDA"), (5, 4, "CODEC_RUN"), (6, 6, "ANALOG_OK")],
    )
    straight("INPUT-READY", ("processor_carrier", "J7"), ("sequenced_bypass", "J6"), ["AGND", "INPUT_READY"])
    straight(
        "LED-CONTROL",
        ("processor_carrier", "J11"),
        ("led_driver", "J1"),
        ["AGND", "5V_DIG", "V3V3_IO", "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK", "AGND"],
    )
    link(
        "RAIL-HEALTH", ("rail_monitor", "J4"), ("converter", "J5"), [(1, 1, "AGND"), (2, 5, "PRE_ANALOG_OK")]
    )
    link("ADC-ENABLE", ("converter", "J5"), ("adc_driver", "J4"), [(8, 2, "CHIP_EN")])
    link(
        "ADC-BIAS-SENSE",
        ("adc_driver", "J4"),
        ("rail_monitor", "J3"),
        [(1, 1, "AGND"), (3, 2, "NBIAS_L"), (4, 3, "NBIAS_R")],
    )
    link("AUDIO-HEALTH", ("converter", "J5"), ("sequenced_bypass", "J3"), [(6, 3, "ANALOG_OK")])
    link(
        "ANALOG-IN",
        ("sequenced_bypass", "J9"),
        ("input_range", "J1"),
        [(1, 1, "PROC_IN_L"), (2, 2, "AGND"), (3, 3, "PROC_IN_R")],
    )
    straight("PREAMP-ADC", ("input_range", "J2"), ("adc_driver", "J1"), ["PRE_OUT_L", "AGND", "PRE_OUT_R"])
    straight(
        "ADC-CODEC",
        ("adc_driver", "J2"),
        ("converter", "J2"),
        ["ADC_LP", "ADC_LN", "AGND", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2"],
    )
    straight(
        "CODEC-DAC",
        ("converter", "J1"),
        ("dac_receiver", "J1"),
        ["DAC_LP", "DAC_LN", "AGND", "DAC_RP", "DAC_RN"],
    )
    straight("DAC-OUTPUT", ("dac_receiver", "J2"), ("output_stage", "J1"), ["RECV_L", "AGND", "RECV_R"])
    link(
        "ANALOG-OUT",
        ("output_stage", "J2"),
        ("sequenced_bypass", "J9"),
        [(1, 4, "PROC_OUT_L"), (2, 5, "AGND"), (3, 6, "PROC_OUT_R")],
    )
    for name, header in [("input_range", "J4"), ("output_stage", "J3")]:
        straight("GAIN-" + name.upper(), ("sequenced_bypass", "J5"), (name, header), ["5V_DIG", "GAIN_LOW"])
    return rows


def panel_specifications(tables):
    """Logical contacts only: actual purchased-part terminal numbers are unselected."""
    rows, virtual, sources = [], {}, {}

    def add(harness, source, component, terminal, net):
        target = ("panel", component, terminal)
        assert target not in virtual, ("Duplicated panel terminal", target)
        virtual[target] = net
        rows.append((harness, source, target, net))

    path = REPO / "hardware/firmware/control-inputs.json"
    controls = json.loads(path.read_text())["front_inputs"]
    assert len(controls) == 32 and len({c["logical_index"] for c in controls}) == 32
    for control in controls:
        index = control["logical_index"]
        net = f"CONTROL_{index:02d}"
        endpoints = [
            ("control_inputs", h, n)
            for h, pins in tables["control_inputs"].items()
            for n, v in pins.items()
            if v == net
        ]
        assert len(endpoints) == 1, ("Missing or duplicated control output", net)
        ground = (
            "control_inputs",
            "J1" if index < 14 else "J2" if index < 28 else "J3",
            str(15 + index % 2) if index < 28 else "1",
        )
        add("FRONT-CONTROLS", endpoints[0], control["id"], "signal", net)
        add("FRONT-CONTROLS", ground, control["id"], "return", "AGND")
    sources[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    path = ELECTRONICS / "processor_carrier/generated/connector-map.csv"
    with path.open(newline="") as stream:
        knobs = {row["Header"]: row["Knob_id"] for row in csv.DictReader(stream) if row["Knob_id"]}
    knob_order = (
        "input",
        "output",
        "low",
        "mid",
        "high",
        "scene_depth",
        "x_level",
        "x_pitch",
        "scene_time",
        "scene_resonance",
    )
    assert [knobs[f"J{20 + i}"] for i in range(10)] == list(knob_order)
    sources[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for index, knob in enumerate(knob_order):
        for pin, terminal, net in [
            (1, "return", "AGND"),
            (2, "wiper", f"POT_RAW_{index:02d}"),
            (3, "excitation", "V3V3_ANALOG"),
        ]:
            add(
                "FRONT-POTS",
                ("processor_carrier", f"J{20 + index}", str(pin)),
                "pot_" + knob,
                terminal,
                net,
            )
    path = ELECTRONICS / "led_driver/generated/channel-map.csv"
    with path.open(newline="") as stream:
        channels = list(csv.DictReader(stream))
    assert [int(row["Logical_channel"]) for row in channels] == list(range(96))
    for row in channels:
        channel = int(row["Logical_channel"])
        add(
            "PANEL-LED-SINKS",
            ("led_driver", row["Header"], row["Pin"]),
            row["Function"],
            "cathode",
            f"LED_{channel:02d}",
        )
    sources[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for header, component, nets in [
        ("J7", "line_input", ["IN_L", "AGND", "IN_R"]),
        ("J8", "line_output", ["OUT_L", "AGND", "OUT_R"]),
    ]:
        for pin, terminal, net in zip([1, 2, 3], ["left", "return", "right"], nets):
            add("REAR-AUDIO", ("sequenced_bypass", header, str(pin)), component, terminal, net)
    for pin, terminal, net in [
        (1, "loop_supply", "V3V3_IO"),
        (2, "process_loop", "PROCESS_OK"),
        (4, "sense_return", "AGND"),
        (5, "sense", "BYPASS_SENSE"),
    ]:
        add("MANUAL-BYPASS", ("sequenced_bypass", "J3", str(pin)), "manual_bypass", terminal, net)
    for pin, terminal, net in [(1, "return", "AGND"), (2, "sense", "MODE_SEND_RETURN")]:
        add("CONNECTION-MODE", ("processor_carrier", "J8", str(pin)), "connection_mode", terminal, net)
    return rows, virtual, sources


def validate(wires, tables, virtual):
    expected_rows = specifications() + panel_specifications(tables)[0]
    expected = {(h, a, b): n for h, a, b, n in expected_rows}
    assert len(expected) == len(expected_rows), "Duplicate connection in specification"
    assert len(wires) == len(expected), "Missing or duplicated interconnect"
    seen = set()
    for wire in wires:
        a, b = tuple(wire["from"]), tuple(wire["to"])
        key = (wire["harness"], a, b)
        assert key in expected and key not in seen, ("Wrong or duplicated endpoints", key)
        seen.add(key)
        assert wire["net"] == expected[key], ("Wrong canonical net", key)
        for endpoint in (a, b):
            if endpoint[0] == "panel":
                actual = virtual[endpoint]
            else:
                actual = canonical(endpoint, tables[endpoint[0]][endpoint[1]][endpoint[2]])
            assert actual == wire["net"], (
                "Pin/net mismatch or source/protected substitution",
                endpoint,
                actual,
                wire["net"],
            )
        assert wire["assembly_released"] is False
        assert wire["cut_length_mm"] is None and wire["production_connector"] is None
    assert seen == set(expected)


def plan(kicad_cli=None):
    tables, sources, evidence = board_tables(kicad_cli)
    panel_rows, virtual, panel_sources = panel_specifications(tables)
    rows = specifications() + panel_rows
    wires = [
        dict(
            harness=h,
            **{"from": list(a), "to": list(b)},
            net=n,
            cut_length_mm=None,
            production_connector=None,
            assembly_released=False,
        )
        for h, a, b, n in rows
    ]
    validate(wires, tables, virtual)
    sources.update(panel_sources)
    sources[str(Path(__file__).relative_to(REPO))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name in ["netlists.py", "sexpr.py"]:
        p = ELECTRONICS / "common" / name
        sources[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    used, branches = set(), defaultdict(list)
    for wire in wires:
        for endpoint in (tuple(wire["from"]), tuple(wire["to"])):
            used.add(endpoint)
            if endpoint[0] != "panel":
                branches[endpoint].append(wire["harness"])
    unresolved = []
    optional = {
        ("power_supply", "J4"): "Raw-rail diagnostic connector; never a protected load supply",
        ("input_protection", "J1"): "On-board DC inlet mating interface; not another internal harness",
        ("input_protection", "J4"): "Power-switch test/access header; do not duplicate the fitted switch",
        ("input_protection", "J5"): "Auxiliary duplicate access; J6 is the selected control interface",
        ("rail_disconnect", "J6"): "Interlock diagnostic access; not a load or external drive input",
        ("sequenced_bypass", "J4"): "Optional access to included K1/K2 coils; never add duplicate coils",
    }
    for board, headers in tables.items():
        for header, pins in headers.items():
            for pin, net in pins.items():
                if (board, header, pin) in used:
                    continue
                reason = optional.get((board, header))
                if board == "converter" and header == "J5" and pin == "7":
                    reason = "Codec PGOOD diagnostic output; not an external enable"
                unresolved.append(
                    dict(
                        endpoint=[board, header, pin],
                        net=net,
                        optional_access=reason is not None,
                        reason=reason or "Peripheral or emitter-anode assembly remains unselected/unwired",
                    )
                )
    fanouts = [
        dict(
            endpoint=list(endpoint),
            conductor_count=len(harnesses),
            harnesses=harnesses,
            splice_or_distribution_assembly_selected=False,
        )
        for endpoint, harnesses in sorted(branches.items())
        if len(harnesses) > 1
    ]
    counts = Counter(w["harness"] for w in wires)
    return dict(
        profile="standalone external converter; separate from B1 and onboard-codec wiring",
        scope="Logical point-to-point contracts, protected-load fanout, front contacts and LED sinks; not a fabrication or harness release",
        wires=wires,
        harness_pin_counts=dict(counts),
        boards=evidence,
        aliases=[
            dict(endpoint=list(e), local_net=a, canonical_net=b, evidence="hardware/electronics/" + c)
            for e, (a, b, c) in sorted(ALIASES.items())
        ],
        panel_endpoints_are_logical_contacts=True,
        purchased_part_terminal_numbers_verified=False,
        interface_construction={
            "LED-CONTROL": {
                "processor_header_pitch_mm": 2.54,
                "driver_header_pitch_mm": 1.27,
                "pitch_adapter_required": True,
                "mating_parts_selected": False,
            },
            "CODEC-DAC": {"raw_dac_interface": True, "permitted_cable_length_qualified": False},
            "ADC-CODEC": {"raw_adc_and_reference_interface": True, "permitted_cable_length_qualified": False},
        },
        fanouts=fanouts,
        unused_header_pins=unresolved,
        remaining_required_header_pins=sum(not x["optional_access"] for x in unresolved),
        source_sha256=sources,
        electrical_and_ground_return_topology_qualified=False,
        source_power_voltage_loss_failures_remain=True,
        protected_rail_source_names_preserved=True,
        signal_integrity_and_timing_qualified=False,
        production_contact_current_and_resistance_qualified=False,
        complete_system_wiring=False,
        build_ready=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kicad-cli", type=Path, help="Re-export all 13 schematics and compare to the saved native netlists"
    )
    args = parser.parse_args()
    data = plan(args.kicad_cli)
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    (out / "system-interconnect.json").write_text(json.dumps(data, indent=2) + "\n")
    with (out / "system-interconnect.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "Harness",
                "From_board",
                "From_header_or_part",
                "From_pin_or_role",
                "To_board",
                "To_header_or_part",
                "To_pin_or_role",
                "Canonical_net",
                "Assembly_released",
            ]
        )
        for w in data["wires"]:
            writer.writerow([w["harness"], *w["from"], *w["to"], w["net"], False])
    print(
        f"System interconnects: {len(data['wires'])} pin pairs across {len(data['boards'])} boards; {len(data['fanouts'])} unselected fanouts; {data['remaining_required_header_pins']} required peripheral/anode pins remain. Build-ready: false."
    )


if __name__ == "__main__":
    main()
