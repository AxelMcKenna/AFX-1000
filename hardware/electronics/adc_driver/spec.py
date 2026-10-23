"""E12 stereo remote-feedback ADC driver and reference common-mode servo.

Prototype: actual codec load, loop stability, noise and power faults need bench
qualification. NEG_BIAS rails must join the future power qualification window.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
FDA = "https://www.ti.com/lit/ds/symlink/ths4551.pdf"
BUF = "https://www.ti.com/lit/ds/symlink/opa1656.pdf"
SERVO = "https://www.ti.com/lit/ds/symlink/opa4192.pdf"
PUMP = "https://www.ti.com/lit/ds/symlink/lm7705.pdf"


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


for i, ch in enumerate(("L", "R")):
    component(
        f"U{i + 1}",
        "THS4551IDGKR",
        "Package_SO:VSSOP-8_3x3mm_P0.65mm",
        [
            pin(1, "IN-", "input", "L", "FB_N_" + ch),
            pin(8, "IN+", "input", "L", "FB_P_" + ch),
            pin(2, "VOCM", "input", "L", "VOCM_" + ch),
            pin(7, "PD", "input", "L", "PD_" + ch),
            pin(3, "VS+", "power_in", "R", "V5_REG"),
            pin(6, "VS-", "power_in", "R", "NBIAS_" + ch),
            pin(4, "OUT+", "output", "R", "DRV_" + ch + "P"),
            pin(5, "OUT-", "output", "R", "DRV_" + ch + "N"),
        ],
        60 + 180 * i,
        65,
        FDA,
        "Remote raw-pin resistive feedback; local1pF high-frequency feedback. Low-voltage rails only.",
    )

component(
    "U3",
    "OPA1656ID",
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    [
        pin(3, "A+", "input", "L", "PRE_OUT_L"),
        pin(2, "A-", "input", "L", "BUF_L"),
        pin(5, "B+", "input", "L", "PRE_OUT_R"),
        pin(6, "B-", "input", "L", "BUF_R"),
        pin(1, "A_OUT", "output", "R", "BUF_L"),
        pin(7, "B_OUT", "output", "R", "BUF_R"),
        pin(8, "V+", "power_in", "R", "P12"),
        pin(4, "V-", "power_in", "R", "N12"),
    ],
    420,
    65,
    BUF,
    "High-impedance unity buffers preserve E10 load >=100k;1M returns per channel.",
)

component(
    "U4",
    "OPA4192ID",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    [
        pin(3, "A+", "input", "L", "REF_DIV_L"),
        pin(2, "A-", "input", "L", "REF_HALF_L"),
        pin(5, "B+", "input", "L", "REF_HALF_L"),
        pin(6, "B-", "input", "L", "CM_SENSE_L"),
        pin(10, "C+", "input", "L", "REF_DIV_R"),
        pin(9, "C-", "input", "L", "REF_HALF_R"),
        pin(12, "D+", "input", "L", "REF_HALF_R"),
        pin(13, "D-", "input", "L", "CM_SENSE_R"),
        pin(1, "A_OUT", "output", "R", "REF_HALF_L"),
        pin(7, "B_OUT", "output", "R", "CM_DRIVE_L"),
        pin(8, "C_OUT", "output", "R", "REF_HALF_R"),
        pin(14, "D_OUT", "output", "R", "CM_DRIVE_R"),
        pin(4, "V+", "power_in", "R", "P12"),
        pin(11, "V-", "power_in", "R", "N12"),
    ],
    620,
    65,
    SERVO,
    "A/C buffer separate reference halves;B/D slow average raw ADC pins to reference/2. No shared channel reference.",
)

for i, ch in enumerate(("L", "R")):
    component(
        f"U{i + 5}",
        "LM7705MM/NOPB",
        "Package_SO:VSSOP-8_3x3mm_P0.65mm",
        [
            pin(1, "CF+", "passive", "L", "FLY_P_" + ch),
            pin(8, "CF-", "passive", "L", "FLY_N_" + ch),
            pin(3, "SD", "input", "L", "AGND"),
            pin(4, "VDD", "power_in", "L", "V5_REG"),
            pin(2, "VSS_A", "power_in", "R", "AGND"),
            pin(5, "VSS_B", "power_in", "R", "AGND"),
            pin(6, "VOUT", "power_out", "R", "NPUMP_" + ch),
            pin(7, "CRES", "passive", "R", "RES_" + ch),
        ],
        60 + 180 * i,
        170,
        PUMP,
        "One bias generator/channel; output-current allocation <=20mA; effective pump capacitors must meet datasheet test values.",
    )


def passive(ref, value, a, b, note="", footprint=None, source=""):
    prefix = ref[0]
    if footprint is None:
        footprint = "Resistor_SMD:R_0805_2012Metric" if prefix == "R" else "Capacitor_SMD:C_0805_2012Metric"
    component(
        ref,
        value,
        footprint,
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        0,
        0,
        source,
        note,
    )


for i, ch in enumerate(("L", "R")):

    def n(s):
        return s + "_" + ch

    resistors = [
        (
            "2.49k 0.1%",
            n("BUF"),
            n("FB_P"),
            "FDA source resistor; source buffer directly drives this resistive load",
        ),
        ("2.49k 0.1%", "AGND", n("FB_N"), "Matched ground leg"),
        (
            "1.21k 0.1%",
            "ADC_" + ch + "N",
            n("FB_P"),
            "Remote negative-output feedback; gain reserves ADC clipping margin",
        ),
        ("1.21k 0.1%", "ADC_" + ch + "P", n("FB_N"), "Remote positive-output feedback"),
        (
            "3.32R 0.1%",
            "DRV_" + ch + "P",
            "ADC_" + ch + "P",
            "Raw-pin isolation; inside low-frequency feedback",
        ),
        (
            "3.32R 0.1%",
            "DRV_" + ch + "N",
            "ADC_" + ch + "N",
            "Raw-pin isolation; inside low-frequency feedback",
        ),
        ("1M 1%", n("PRE_OUT"), "AGND", "E10 load1M plus FET input; no direct low-resistance FDA load"),
        (
            "1M 0.1%",
            "REF_ADC" + str(i + 1),
            n("REF_DIV"),
            "High-impedance reference divider; load about1.65uA/channel",
        ),
        (
            "1M 0.1%",
            n("REF_DIV"),
            "AGND",
            "Reference half; hot input bias/offset allocation included in analysis",
        ),
        ("100k 0.1%", "ADC_" + ch + "P", n("CM_SENSE"), "Common-mode average sense"),
        ("100k 0.1%", "ADC_" + ch + "N", n("CM_SENSE"), "Common-mode average sense"),
        (
            "100M 1%",
            n("CM_DRIVE"),
            n("CM_SENSE"),
            "Finite dc servo gain; clean board/leakage qualification required",
        ),
        ("10k 1%", n("CM_DRIVE"), n("VOCM"), "VOCM clamp current limit"),
        ("4.7k 1%", "DRV_ENABLE", n("PD"), "3.3V CHIP_EN from E09; missing enable defaults off"),
        ("100k 1%", n("PD"), "AGND", "PD pull-down"),
        (
            "1R 1%",
            n("NPUMP"),
            n("NBIAS"),
            "Bias-rail ripple filter; signed load drop included in headroom screen",
        ),
    ]
    for j, (value, a, b, note) in enumerate(resistors, 1):
        passive(f"R{i * 16 + j}", value, a, b, note)
    capacitors = [
        (
            "1pF C0G +/-0.1pF",
            "DRV_" + ch + "N",
            n("FB_P"),
            "Local high-frequency feedback; PCB parasitics and actual FDA loop need verification",
            None,
        ),
        ("1pF C0G +/-0.1pF", "DRV_" + ch + "P", n("FB_N"), "Local high-frequency feedback", None),
        (
            "47pF C0G 5%",
            "ADC_" + ch + "P",
            "ADC_" + ch + "N",
            "Differential RF capacitor, not a proven switched-capacitor kickback model",
            None,
        ),
        ("22pF C0G 5%", "ADC_" + ch + "P", "AGND", "Raw-pin RF common-mode cap", None),
        ("22pF C0G 5%", "ADC_" + ch + "N", "AGND", "Raw-pin RF common-mode cap", None),
        ("100nF 25V X7R", n("REF_DIV"), "AGND", "Effective50..150nF allocation; reference-half filter", None),
        (
            "1uF 63V film 10%",
            n("CM_DRIVE"),
            n("CM_SENSE"),
            "WIMA MKS2C041001F00KSSD; servo effective0.9..1.1uF, leakage qualification required",
            "Capacitor_THT:C_Rect_L7.2mm_W5.0mm_P5.00mm",
        ),
        (
            "10uF 16V X7R",
            n("FLY_P"),
            n("FLY_N"),
            "Require effective >=5uF at actual flying-cap bias",
            "Capacitor_SMD:C_1206_3216Metric",
        ),
        (
            "47uF 16V X7R",
            n("RES"),
            "AGND",
            "Require effective >=22uF at about5V negative reserve bias",
            "Capacitor_SMD:C_1210_3225Metric",
        ),
        (
            "47uF 6.3V X7R",
            n("NPUMP"),
            "AGND",
            "Require effective >=22uF; native LM7705 output capacitor",
            "Capacitor_SMD:C_1206_3216Metric",
        ),
        (
            "47uF 6.3V X7R",
            n("NBIAS"),
            "AGND",
            "Require effective >=22uF; post1Ohm bias filter",
            "Capacitor_SMD:C_1206_3216Metric",
        ),
        ("2.2uF 16V X7R", "V5_REG", "AGND", "Local pump input; require effective >=1uF", None),
        ("100nF 16V X7R", "V5_REG", "AGND", "Local FDA positive bypass", None),
        ("100nF 16V X7R", n("NBIAS"), "AGND", "Local FDA negative bypass", None),
    ]
    for j, (value, a, b, note, fp) in enumerate(capacitors, 1):
        passive(f"C{i * 14 + j}", value, a, b, note, fp)
    component(
        f"D{i + 1}",
        "BAT54S,215",
        "Package_TO_SOT_SMD:SOT-23",
        [
            pin(1, "A1", "passive", "L", "AGND"),
            pin(2, "K2", "passive", "R", "V5_REG"),
            pin(3, "K1_A2", "passive", "R", n("VOCM")),
        ],
        0,
        0,
        "https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf",
        "Series Schottky pair clamps VOCM; not a raw ADC signal shunt.",
    )

passive(
    "R33",
    "1k 1%",
    "V5_REG",
    "AGND",
    "5V bleeder; does not establish zero back-power or arbitrary fault protection",
)
for ref, rail, note in [
    ("C29", "P12", "U3 local positive"),
    ("C30", "N12", "U3 local negative"),
    ("C31", "P12", "U4 local positive"),
    ("C32", "N12", "U4 local negative"),
]:
    passive(ref, "100nF 50V X7R", rail, "AGND", note)
for ref, rail in [("C33", "P12"), ("C34", "N12")]:
    passive(
        ref,
        "10uF 50V X7R",
        rail,
        "AGND",
        "Require effective >=4.7uF; exact MPN unselected",
        "Capacitor_SMD:C_1210_3225Metric",
    )

for ref, nets, x, y, note in [
    ("J1", ["PRE_OUT_L", "AGND", "PRE_OUT_R"], 420, 170, "Same order as E10 J2; high-impedance input"),
    (
        "J2",
        ["ADC_LP", "ADC_LN", "AGND", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2"],
        620,
        180,
        "Same order as E09 J2; short traces on converter PCB, not long raw-ADC harness",
    ),
    (
        "J3",
        ["P12", "AGND", "N12", "V5_REG"],
        760,
        65,
        "Qualified +/-12V and4.90..5.10V input; common reference",
    ),
    (
        "J4",
        ["AGND", "DRV_ENABLE", "NBIAS_L", "NBIAS_R"],
        760,
        170,
        "DRV_ENABLE <- E09 J5.8 CHIP_EN; both filtered bias rails need future hardware window monitoring",
    ),
]:
    component(
        ref,
        "Conn_01x" + str(len(nets)).zfill(2),
        f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
        [pin(i + 1, str(i + 1), "passive", "L", net) for i, net in enumerate(nets)],
        x,
        y,
        note=note,
    )

index = 0
for c in COMPONENTS:
    if c["ref"].startswith(("R", "C", "D")):
        c["x"] = round(round((40 + (index % 9) * 90) / 1.27) * 1.27, 4)
        c["y"] = round(round((270 + (index // 9) * 35) / 1.27) * 1.27, 4)
        index += 1

NOTES = [
    (
        20.32,
        17.78,
        "E12 ADC driver prototype: remote raw-pin gain feedback, separate reference-half servos, low-voltage output rails.",
    ),
    (
        20.32,
        25.4,
        "No PCB or bench validation. Actual converter loading, stability, full scale/noise, bias-rail windows and power faults require qualification.",
    ),
    (
        20.32,
        596.9,
        "THS4551 +/-outputs use V5_REG and per-channel LM7705 negative bias; no direct +/-12V output rail on raw ADC drivers.",
    ),
    (
        20.32,
        604.52,
        "Future PRE_ANALOG_OK must include V5_REG and BOTH filtered negative-bias windows. E09 CHIP_EN drives DRV_ENABLE.",
    ),
    (
        20.32,
        612.14,
        "U3 preserves E10 high input impedance. U4 buffers references/2 and slowly controls ADC-pin average; no unbuffered shared reference load.",
    ),
]
