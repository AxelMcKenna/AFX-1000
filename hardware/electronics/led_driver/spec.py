"""E20: supervised 96-channel LED/display sink driver, F04 wire order."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
TI = "https://www.ti.com/lit/ds/symlink/"


def pin(n, name, kind, net, side="L"):
    return dict(number=str(n), name=name, kind=kind, net=net, side=side)


def part(ref, value, footprint, pins, x, y, note="", source=""):
    COMPONENTS.append(
        dict(
            ref=ref,
            part=value,
            footprint=footprint,
            pins=pins,
            x=round(round(x / 1.27) * 1.27, 4),
            y=round(round(y / 1.27) * 1.27, 4),
            note=note,
            source=source,
        )
    )


for chip in range(4):
    nets = {
        1: ("GND", "power_in", "AGND"),
        2: ("BLANK", "input", "BLANK_5V"),
        3: ("SCLK", "input", "CLOCK_5V"),
        4: ("SIN", "input", "DATA_5V" if chip == 0 else f"SERIAL_{chip - 1}"),
        29: ("SOUT", "output", f"SERIAL_{chip}" if chip < 3 else None),
        30: ("XLAT", "input", "LATCH_5V"),
        31: ("IREF", "output", f"IREF_{chip}"),
        32: ("VCC", "power_in", "5V_DIG"),
        33: ("EP", "power_in", "AGND"),
    }
    nets.update({5 + i: (f"OUT{i}", "open_collector", f"LED_{chip * 24 + i:02d}") for i in range(24)})
    part(
        f"U{chip + 1}",
        "TLC5947DAPR",
        "RMX_LED:TLC5947_DAP0032C",
        [pin(n, *nets[n], "L" if n in (1, 2, 3, 4, 29, 30, 31, 32, 33) else "R") for n in range(1, 34)],
        100 + 240 * chip,
        110,
        "DAP32:24 sinks; EP to ground. 2.98mA nominal; low-current accuracy, assembled thermal and optical output unqualified.",
        TI + "tlc5947.pdf",
    )

translator = {
    1: ("VCCA", "power_in", "V3V3_IO"),
    2: ("DIR", "input", "V3V3_IO"),
    11: ("GND", "power_in", "AGND"),
    12: ("GND", "power_in", "AGND"),
    13: ("GND", "power_in", "AGND"),
    22: ("OE_N", "input", "OE_N"),
    23: ("VCCB", "power_in", "5V_DIG"),
    24: ("VCCB", "power_in", "5V_DIG"),
}
for i, (incoming, outgoing) in enumerate(
    zip(
        ["LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK", "AGND", "AGND", "AGND", "AGND"],
        ["DATA_5V_SRC", "CLOCK_5V_SRC", "LATCH_5V_SRC", "BLANK_5V_SRC", None, None, None, None],
    )
):
    translator[3 + i] = (f"A{i + 1}", "input", incoming)
    translator[21 - i] = (f"B{i + 1}", "output", outgoing)
part(
    "U5",
    "SN74LVC8T245PWR",
    "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
    [pin(n, *translator[n], "L" if n <= 13 else "R") for n in range(1, 25)],
    100,
    530,
    "A-to-B only; spare A inputs grounded, B outputs NC. VCC isolation/Ioff prevents a direct5V return into processor signals.",
    TI + "sn74lvc8t245.pdf",
)
for index, (rail, value, output) in enumerate(
    [("V3V3_IO", "TPS3808G33DBVR", "PG_3V3"), ("5V_DIG", "TPS3808G50DBVR", "PG_5V")]
):
    part(
        f"U{6 + index}",
        value,
        "Package_TO_SOT_SMD:SOT-23-6",
        [
            pin(n, name, kind, net, "L" if n <= 3 else "R")
            for n, name, kind, net in [
                (1, "RESET_N", "open_collector", output),
                (2, "GND", "power_in", "AGND"),
                (3, "MR_N", "input", rail),
                (4, "CT", "passive", None),
                (5, "SENSE", "input", rail),
                (6, "VDD", "power_in", rail),
            ]
        ],
        350 + 240 * index,
        530,
        "CT open selects20ms nominal delay; threshold/delay corners and physical brownout behavior need qualification.",
        TI + "tps3808.pdf",
    )
for i, (gate, source, drain) in enumerate(
    [("PG_3V3", "ENABLE_MID", "OE_N"), ("PG_5V", "AGND", "ENABLE_MID")]
):
    part(
        f"Q{i + 1}",
        "AO3400A",
        "Package_TO_SOT_SMD:SOT-23",
        [pin(1, "G", "input", gate), pin(2, "S", "passive", source, "R"), pin(3, "D", "passive", drain, "R")],
        790 + 140 * i,
        530,
        "Series NMOS enables translator only when both supervisors release; body diodes face away from OE pull-up current.",
        "https://www.aosmd.com/res/data_sheets/AO3400A.pdf",
    )


def header(ref, nets, x, y, footprint, note):
    part(
        ref,
        f"Header{len(nets)}",
        footprint,
        [pin(i + 1, str(i + 1), "passive", net) for i, net in enumerate(nets)],
        x,
        y,
        note,
    )


header(
    "J1",
    ["AGND", "5V_DIG", "V3V3_IO", "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK", "AGND"],
    60,
    310,
    "Connector_PinHeader_1.27mm:PinHeader_2x04_P1.27mm_Vertical",
    "Matches E19 J11 by pin number; pitch/row differs, so use a documented adapter harness. No5V logic goes back to E19.",
)
for connector in range(4):
    pair = connector // 2
    top = connector % 2 == 0
    header(
        f"J{connector + 2}",
        [
            f"LED_{(pair * 2 + chip) * 24 + output:02d}"
            for chip in (0, 1)
            for output in (range(23, 11, -1) if top else range(12))
        ]
        + ["5V_DIG", "5V_DIG"],
        280 + 240 * (connector % 3),
        310 + 190 * (connector // 3),
        "Connector_PinHeader_2.54mm:PinHeader_2x13_P2.54mm_Vertical",
        "J2/3 carry U1/2 top/bottom banks; J4/5 carry U3/4. Pins1..12 first chip,13..24 second. Pins25/26 common-anode5V. Use channel-map.csv.",
    )


def passive(ref, value, a, b, x, y, footprint=None, note=""):
    kind = "Resistor" if ref.startswith("R") else "Capacitor"
    size = "0603_1608Metric" if ref.startswith("R") or value.startswith("100nF") else "0805_2012Metric"
    part(
        ref,
        value,
        footprint or f"{kind}_SMD:{ref[0]}_{size}",
        [pin(1, "~", "passive", a), pin(2, "~", "passive", b, "R")],
        x,
        y,
        note,
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
for i, (ref, value, a, b) in enumerate(resistors):
    passive(ref, value, a, b, 50 + 125 * (i % 8), 635 + 40 * (i // 8))
caps = [("100nF 16V X7R", "5V_DIG"), ("4.7uF 16V X7R", "5V_DIG")] * 4 + [
    ("100nF 16V X7R", "V3V3_IO"),
    ("100nF 16V X7R", "5V_DIG"),
    ("100nF 16V X7R", "V3V3_IO"),
    ("100nF 16V X7R", "5V_DIG"),
    ("22uF 25V X7R", "5V_DIG"),
    ("4.7uF 16V X7R", "5V_DIG"),
]
for i, (value, rail) in enumerate(caps):
    passive(
        f"C{i + 1}",
        value,
        rail,
        "AGND",
        50 + 125 * (i % 8),
        760 + 40 * (i // 8),
        "Capacitor_SMD:C_1210_3225Metric" if i == 12 else None,
    )

NOTES = [
    (
        20,
        18,
        "E20 -96-channel constant-current LED/display driver. MCU->U1->U2->U3->U4; global n uses chip n/24 and OUT(n%24).",
    ),
    (
        20,
        28,
        "5V powers driver logic and common anodes; dual-supply translator isolates processor3.3V. Both rails must qualify before outputs enable.",
    ),
    (
        20,
        840,
        "Proposed91x27mm PCB at(197,77), seat6.5mm beneath scene controls; exact footprints/PCB/fit remain to be verified.",
    ),
    (
        20,
        850,
        "3mA is nominal, not a guaranteed low-current bound. E14/E17 digital power budget must include driver ICC. No fabrication or physical validation approval.",
    ),
]
