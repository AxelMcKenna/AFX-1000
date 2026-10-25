"""E18 digital input hub. F04 wiring; no pots, LEDs or audio on this board."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MCP = "https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf"
MAP = json.loads((ROOT.parents[1] / "firmware/control-inputs.json").read_text())
COMPONENTS = []


def part(ref, value, fp, pins, x, y, note="", source=""):
    COMPONENTS.append(
        dict(
            ref=ref,
            part=value,
            footprint=fp,
            pins=pins,
            x=round(round(x / 1.27) * 1.27, 4),
            y=round(round(y / 1.27) * 1.27, 4),
            note=note,
            source=source,
        )
    )


def pin(n, name, kind, net, side="L"):
    return dict(number=str(n), name=name, kind=kind, net=net, side=side)


for chip in range(3):
    address = 0x20 + chip
    front = {
        p["soic_pin"]: f"CONTROL_{p['logical_index']:02d}"
        for p in MAP["front_inputs"]
        if p["address"] == address
    }
    if chip == 2:
        front.update({21: "MODE_SEND_RETURN", 22: "MANUAL_BYPASS", 23: "ANALOG_OK", 24: "INPUT_READY"})
    pins = [
        pin(n, "GPB" + str(n - 1), "output" if n == 8 else "bidirectional", front.get(n)) for n in range(1, 9)
    ]
    pins += [
        pin(n, "GPA" + str(n - 21), "output" if n == 28 else "bidirectional", front.get(n))
        for n in range(21, 29)
    ]
    pins += [
        pin(n, name, kind, net, "R")
        for n, name, kind, net in [
            (9, "VDD", "power_in", "V3V3_IO"),
            (10, "VSS", "power_in", "AGND"),
            (11, "NC", "passive", None),
            (12, "SCL", "input", "SCL"),
            (13, "SDA", "bidirectional", "SDA"),
            (14, "NC", "passive", None),
            (15, "A0", "input", "V3V3_IO" if chip == 1 else "AGND"),
            (16, "A1", "input", "V3V3_IO" if chip == 2 else "AGND"),
            (17, "A2", "input", "AGND"),
            (18, "RESET_N", "input", "CONTROL_RESET_N"),
            (19, "INTB", "open_collector", None),
            (20, "INTA", "open_collector", None),
        ]
    ]
    part(
        f"U{chip + 1}",
        "MCP23017-E/SO",
        "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm",
        pins,
        75 + 170 * chip,
        100,
        f"7-bit address0x{address:02x}; GPA7/GPB7 unused output-only pins; F04 required",
        MCP,
    )


def header(ref, nets, x, y, note="", double=False):
    footprint = (
        "PinHeader_2x08_P2.54mm_Vertical" if double else f"PinHeader_1x{len(nets):02d}_P2.54mm_Vertical"
    )
    part(
        ref,
        "Header" + str(len(nets)),
        "Connector_PinHeader_2.54mm:" + footprint,
        [pin(i + 1, str(i + 1), "passive", net) for i, net in enumerate(nets)],
        x,
        y,
        note,
    )


for chip in range(2):
    nets = []
    for column in range(7):
        nets += [f"CONTROL_{chip * 14 + 6 - column:02d}", f"CONTROL_{chip * 14 + 7 + column:02d}"]
    nets += ["AGND", "AGND"]
    header(
        f"J{chip + 1}",
        nets,
        75 + 170 * chip,
        250,
        "Two-row bench header; pin order follows routing, not logical index. Production connector/harness unselected.",
        True,
    )
header(
    "J3",
    ["AGND"] + [f"CONTROL_{i:02d}" for i in range(28, 32)],
    415,
    210,
    "Scene9, settings and release endpoints; close active-low inputs to ground.",
)
header(
    "J4",
    ["AGND", "MODE_SEND_RETURN", "MANUAL_BYPASS", "ANALOG_OK", "INPUT_READY"],
    415,
    260,
    "Connect only with PROFILE=external. Onboard firmware configures GPA0..3 as unused low outputs; leave J4 unplugged.",
)
header(
    "J5",
    ["AGND", "V3V3_IO", "SCL", "SDA", "CONTROL_RESET_N"],
    415,
    310,
    "Shared MCU3.3V only; external reset=D0/CODEC_RUN, onboard=D27. I2C pullups external: E09 has sole2k pair.",
)
for i, value, a, b in [
    (1, "100k 1%", "CONTROL_RESET_N", "AGND"),
    (2, "47k 1%", "ANALOG_OK", "AGND"),
    (3, "270k 1%", "INPUT_READY", "AGND"),
]:
    part(
        f"R{i}",
        value,
        "Resistor_SMD:R_0805_2012Metric",
        [pin(1, "~", "passive", a), pin(2, "~", "passive", b, "R")],
        45 + 70 * i,
        345,
        "Receiving-end pull-down; do not enable status pull-ups in firmware.",
    )
for i in range(1, 5):
    part(
        f"C{i}",
        "100nF 16V X7R" if i < 4 else "1uF 16V X7R",
        "Capacitor_SMD:C_0805_2012Metric",
        [pin(1, "~", "passive", "V3V3_IO"), pin(2, "~", "passive", "AGND", "R")],
        45 + 70 * (i - 1),
        305,
        "Local bypass per IC plus input bulk; effective capacitance and exact MPN require qualification.",
    )
NOTES = [
    (
        20,
        15,
        "E18 - F04 digital input hub:32 front inputs +4 external rear/status inputs. No GPA7/GPB7 inputs.",
    ),
    (
        20,
        24,
        "Shared MCU3.3V. No local I2C pullups; E09 supplies sole2k pair. Do not use5V. Physical bus/EMI/ESD/scan timing unverified.",
    ),
    (
        20,
        377,
        "J4 is external-profile only. Status pull-downs47k/270k; reset100k pull-down holds all expanders reset on missing drive.",
    ),
    (
        20,
        386,
        "64x54mm daughterboard candidate; 4mm spacers on processor carrier. Final carrier routing, harnesses and full unit fit remain open.",
    ),
]
