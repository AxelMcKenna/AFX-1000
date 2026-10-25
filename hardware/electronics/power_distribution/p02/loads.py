"""Independent actual native endpoint and source-domain regression contracts."""

import hashlib
import json

from ...common.netlists import netlist, number
from .distribution import MANIFEST, REPO

EXPECTED_WIRES = [
    ("LOAD-ADC_DRIVER", "adc_driver", "J3", "4", "V5_REG"),
    ("LOAD-CONVERTER", "converter", "J4", "1", "V5_REG"),
    ("LOAD-RAIL_MONITOR", "rail_monitor", "J2", "6", "V5_REG"),
    ("DIG-PROCESSOR", "processor_carrier", "J1", "1", "5V_DIG"),
    ("DIG-BYPASS", "sequenced_bypass", "J1", "1", "5V_DIG"),
    ("DIG-MONITOR", "rail_monitor", "J1", "1", "5V_DIG"),
    ("LED-CONTROL", "led_driver", "J1", "2", "5V_DIG"),
    ("GAIN-INPUT_RANGE", "input_range", "J4", "1", "5V_DIG"),
    ("GAIN-OUTPUT_STAGE", "output_stage", "J3", "1", "5V_DIG"),
]


def endpoint_contract():
    manifest = json.loads(MANIFEST.read_text())
    actual = {
        (w["harness"], *w["to"], w["net"]) for w in manifest["wires"] if w["net"] in ("5V_DIG", "V5_REG")
    }
    assert actual == set(EXPECTED_WIRES), ("P02 endpoint coverage changed", actual ^ set(EXPECTED_WIRES))
    checks = {
        "adc_driver": {("J3", "4"): "V5_REG", ("J3", "2"): "AGND"},
        "converter": {("J4", "1"): "V5_REG", ("J4", "2"): "AGND"},
        "rail_monitor": {
            ("J2", "6"): "V5_REG",
            ("J1", "1"): "5V_DIG",
            ("J2", "2"): "AGND",
            ("J1", "3"): "AGND",
        },
        "processor_carrier": {
            ("J1", "1"): "5V_DIG",
            ("J1", "2"): "AGND",
            ("R1", "1"): "5V_DIG",
            ("R1", "2"): "SEED_VIN",
            ("U1", "39"): "SEED_VIN",
        },
        "sequenced_bypass": {
            ("J1", "1"): "5V",
            ("J1", "2"): "AGND",
            ("J5", "1"): "5V",
            ("J5", "2"): "GAIN_LOW",
        },
        "input_range": {("J4", "1"): "5V", ("J4", "2"): "GAIN_LOW"},
        "output_stage": {("J3", "1"): "5V", ("J3", "2"): "GAIN_LOW"},
        "led_driver": {
            ("J1", "2"): "5V_DIG",
            **{(f"J{i}", str(p)): "5V_DIG" for i in range(2, 6) for p in (25, 26)},
        },
    }
    hashes = {}
    for board, expected in checks.items():
        path = REPO / "hardware/electronics" / board / "generated/netlist.xml"
        parts, pins = netlist(path)
        for (ref, pin), net in expected.items():
            assert pins[ref][pin] == net, (board, ref, pin, net)
        if board == "processor_carrier":
            assert number(parts["R1"].findtext("value")) == 0.47
        hashes[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(
        interboard_5v_positive_wires=len(actual),
        native_boards_checked=len(checks),
        led_anode_groups=4,
        gain_returns_are_gain_low=True,
        additional_converter_ground_required=True,
        source_sha256=hashes,
    )
