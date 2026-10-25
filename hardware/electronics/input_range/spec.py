"""E10 stereo switched input attenuator / AC-coupled FET preamplifier.

This ends at a single-ended preamplifier boundary, not the raw ADC pins.
ADC bias/driver/protection and independent input precharge remain unfinished.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
FET = "https://www.ti.com/lit/ds/symlink/opa1656.pdf"
RELAY = "https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf"
FILM = "https://wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf"


def pin(number, name, kind, side, net):
    return dict(number=str(number), name=name, kind=kind, side=side, net=net)


def component(ref, part, footprint, pins, x, y, source="", note=""):
    COMPONENTS.append(
        dict(
            ref=ref,
            part=part,
            footprint=footprint,
            pins=pins,
            x=round(round(x / 1.27) * 1.27, 4),
            y=round(round(y / 1.27) * 1.27, 4),
            source=source,
            note=note,
        )
    )


component(
    "U1",
    "OPA1656ID",
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    [
        pin(1, "OUT_A", "output", "R", "BUF_OUT_L"),
        pin(2, "IN_A_N", "input", "L", "GAIN_FB_L"),
        pin(3, "IN_A_P", "input", "L", "BUF_IN_L"),
        pin(4, "V_N", "power_in", "L", "N12"),
        pin(5, "IN_B_P", "input", "L", "BUF_IN_R"),
        pin(6, "IN_B_N", "input", "L", "GAIN_FB_R"),
        pin(7, "OUT_B", "output", "R", "BUF_OUT_R"),
        pin(8, "V_P", "power_in", "R", "P12"),
    ],
    100,
    80,
    FET,
    "Dual FET input preamplifier, nominal gain1.365. +/-12V only. Gain resistor remains subject to full ADC-scale calibration.",
)
component(
    "K1",
    "G6K-2F-Y DC5",
    "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y",
    [
        pin(1, "COIL_P", "passive", "L", "5V"),
        pin(8, "COIL_N", "passive", "L", "GAIN_LOW"),
        pin(3, "COM_L", "passive", "R", "RANGE_L"),
        pin(2, "NC_L", "passive", "L", "ATTN_L"),
        pin(4, "NO_L", "passive", "L", "PROC_IN_L"),
        pin(6, "COM_R", "passive", "R", "RANGE_R"),
        pin(7, "NC_R", "passive", "L", "ATTN_R"),
        pin(5, "NO_R", "passive", "L", "PROC_IN_R"),
    ],
    290,
    80,
    RELAY,
    "Released NC=Master attenuated; energized NO=Send/Return. Second gain coil on E02 driver, independent of wet/dry selection.",
)


def connector(ref, nets, x, y, note):
    component(
        ref,
        "Conn_01x" + str(len(nets)).zfill(2),
        f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
        [pin(i + 1, str(i + 1), "passive", "L", net) for i, net in enumerate(nets)],
        x,
        y,
        note=note,
    )


connector(
    "J1",
    ["PROC_IN_L", "AGND", "PROC_IN_R"],
    460,
    70,
    "E03 processing input J3.1..3. Its input-isolation coil currently shares wet/dry enable; independent precharge sequencing is not implemented.",
)
connector(
    "J2",
    ["PRE_OUT_L", "AGND", "PRE_OUT_R"],
    580,
    70,
    "Single-ended preamplifier output to future ADC driver, NOT E09 raw ADC input. Analysis assumes load>=100kOhm; scale/bias/protection unresolved.",
)
connector(
    "J3", ["P12", "AGND", "N12"], 460, 145, "Qualified regulated +/-12V; rail generation/monitoring external."
)
connector(
    "J4",
    ["5V", "GAIN_LOW"],
    580,
    145,
    "Same pair/order as E02 J5 and E05 J3; second of two proposed gain coils.",
)

PASSIVES = []


def passive(ref, value, a, b, note="", footprint=None, source=""):
    kind = ref[0]
    PASSIVES.append(
        (
            ref,
            value,
            a,
            b,
            note,
            footprint or f"{'Resistor' if kind == 'R' else 'Capacitor'}_SMD:{kind}_0805_2012Metric",
            source,
        )
    )


for ci, ch in enumerate(("L", "R")):

    def n(s):
        return s + "_" + ch

    values = [
        ("33.2k 0.1%", n("PROC_IN"), n("ATTN"), "Master divider upper; remains connected in both ranges."),
        (
            "13.7k 0.1%",
            n("ATTN"),
            "AGND",
            "Master divider lower; includes the actual following bias network load.",
        ),
        (
            "4.99k 0.1% 1W",
            n("RANGE"),
            n("HP_SRC"),
            "Limits a hypothetical48V input/capacitor step to<10mA; exact resistor/pulse/temperature qualification open.",
        ),
        (
            "68k 0.1%",
            n("BUF_IN"),
            "AGND",
            "FET input DC return; hot bias/leakage allocation and input precharge interval required.",
        ),
        (
            "365 0.1%",
            n("GAIN_FB"),
            n("BUF_OUT"),
            "Nominal gain resistor. Final value requires complete ADC input-scale measurements.",
        ),
        ("1k 0.1%", n("GAIN_FB"), "AGND", "Noninverting gain ground leg."),
        (
            "33.2 0.1%",
            n("BUF_OUT"),
            n("PRE_OUT"),
            "Output isolation; future ADC driver must present>=100kOhm in-band.",
        ),
    ]
    for i, (value, a, b, note) in enumerate(values, 1):
        passive(
            f"R{ci * 7 + i}",
            value,
            a,
            b,
            note,
            footprint="Resistor_SMD:R_2512_6332Metric" if i == 3 else None,
        )
    passive(
        f"C{ci * 2 + 1}",
        "1uF film 63V 10%",
        n("HP_SRC"),
        n("BUF_IN"),
        "WIMA MKS2C041001F00KSSD candidate: nominal7.2x5x10mm body,5mm pitch. Nonpolar; leakage/temperature/fit not measured.",
        footprint="Capacitor_THT:C_Rect_L7.2mm_W5.0mm_P5.00mm",
        source=FILM,
    )
    passive(
        f"C{ci * 2 + 2}",
        "47pF 50V C0G 5%",
        n("BUF_IN"),
        "AGND",
        "RF shunt; not a rated surge/ESD suppressor.",
    )
for ref, rail in [("C5", "P12"), ("C6", "N12")]:
    passive(ref, "100nF 50V X7R", rail, "AGND", "Local U1 supply bypass")
for ref, rail in [("C7", "P12"), ("C8", "N12")]:
    passive(
        ref,
        "10uF 50V X7R 10%",
        rail,
        "AGND",
        "Require effective>=4.7uF on +/-12V; exact MPN, bias/temperature/ESR unqualified.",
        footprint="Capacitor_SMD:C_1210_3225Metric",
    )
for i, (ref, value, a, b, note, footprint, source) in enumerate(PASSIVES):
    component(
        ref,
        value,
        footprint,
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        50 + 83 * (i % 7),
        220 + 45 * (i // 7),
        source,
        note,
    )

NOTES = [
    (
        20,
        15,
        "E10 - stereo switched input range / AC-coupled FET preamplifier. Circuit prototype; no PCB or physical audio validation.",
    ),
    (
        20,
        24,
        "NC Master / NO Send-Return. This sheet ends at PRE_OUT, NOT raw ADC pins. ADC bias/driver/protection/calibration remain open.",
    ),
    (
        20,
        385,
        "Require independent input precharge before wet output selection; E02/E03 presently energize both bypass coils together and do not implement that sequence.",
    ),
]
