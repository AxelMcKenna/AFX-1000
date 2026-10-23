"""E14 candidate main rail generation; protected12V input is an external boundary.

No mains input, input eFuse or downstream OV disconnect is implemented here.
Generate native sources from this file; production passive MPNs/layout are open.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
STAGES = []
BUCKS = []
SO8 = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
SO14 = "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"
MSOP = "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm"
DFN = "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm"
ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"
TI = "https://www.ti.com/lit/ds/symlink/"


def pin(n, name, kind, side, net):
    return dict(number=str(n), name=name, kind=kind, side=side, net=net)


def component(ref, part, footprint, pins, x=0, y=0, source="", note=""):
    COMPONENTS.append(
        dict(ref=ref, part=part, footprint=footprint, pins=pins, x=x, y=y, source=source, note=note)
    )


def value(v):
    if v >= 1e6:
        return f"{v / 1e6:g}M"
    if v >= 1000:
        return f"{v / 1000:g}k"
    return f"{v:g}"


r_count = 0
c_count = 0
l_count = 0


def resistor(a, b, v, precision=False, note=""):
    global r_count
    r_count += 1
    ref = f"R{r_count}"
    component(
        ref,
        value(v) + (" 0.01% 5ppm" if precision else " 1%"),
        "Resistor_SMD:R_0805_2012Metric",
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        note=note,
    )
    return ref


def capacitor(a, b, v, large=False, note=""):
    global c_count
    c_count += 1
    ref = f"C{c_count}"
    fp = (
        "Capacitor_THT:C_Rect_L7.2mm_W5.0mm_P5.00mm"
        if "film" in v
        else "Capacitor_SMD:" + ("C_1210_3225Metric" if large else "C_0805_2012Metric")
    )
    component(ref, v, fp, [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)], note=note)
    return ref


def inductor(a, b, v, raw=False):
    global l_count
    l_count += 1
    ref = f"L{l_count}"
    component(
        ref,
        v,
        "Inductor_SMD:" + ("L_Bourns_SRP6060FA" if raw else "L_Bourns_SRP1050WA"),
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        note="Footprint candidate only; exact shielded inductor MPN/derating/height and current ratings must be selected.",
    )
    return ref


# One boost and one Cuk inverter. The negative transfer capacitor sees VIN+|VOUT|.
component(
    "U1",
    "LT3471EDD#PBF",
    DFN,
    [
        pin(1, "FB1N", "input", "L", "RAW_P_FB"),
        pin(2, "FB1P", "input", "L", "SW_REF_1V"),
        pin(3, "VREF", "power_out", "R", "SW_REF_1V"),
        pin(4, "FB2P", "input", "L", "RAW_N_FB"),
        pin(5, "FB2N", "input", "L", "AGND"),
        pin(6, "SW2", "passive", "R", "RAW_N_SW"),
        pin(7, "SHDN/SS2", "input", "L", "RAW_N_SS"),
        pin(8, "VIN", "power_in", "L", "VIN_PROTECTED"),
        pin(9, "SHDN/SS1", "input", "L", "RAW_P_SS"),
        pin(10, "SW1", "passive", "R", "RAW_P_SW"),
        pin(11, "EP/GND", "power_in", "L", "AGND"),
    ],
    100,
    100,
    ADI + "lt3471.pdf",
    "EP is ground. Switches rated42V; raw rails are nominal+/-22V, subject to allocated error/ripple.",
)
inductor("VIN_PROTECTED", "RAW_P_SW", "33uH 20% Isat>=3A Irms>=1.5A DCR<=0.2ohm", True)
inductor("VIN_PROTECTED", "RAW_N_SW", "68uH 20% Isat>=3A Irms>=1.5A DCR<=0.2ohm")
inductor("CUK_NODE", "RAW_N22", "68uH 20% Isat>=3A Irms>=1.5A DCR<=0.2ohm")
for ref, a, k in [("D1", "RAW_P_SW", "RAW_P22"), ("D2", "CUK_NODE", "AGND")]:
    component(
        ref,
        "SS16-E3/61T",
        "Diode_SMD:D_SMA",
        [pin(1, "K", "passive", "L", k), pin(2, "A", "passive", "R", a)],
        source="https://www.vishay.com/docs/88746/ss12.pdf",
        note="Vishay60V1A; VF allowance1V includes cold margin; actual leakage/ripple and ringing require qualification.",
    )
capacitor(
    "RAW_N_SW",
    "CUK_NODE",
    "10uF 63V X7R",
    True,
    "Effective>=2.2uF; RMS ripple>=0.6A required at switching frequency",
)
for net in ("VIN_PROTECTED", "RAW_P22", "RAW_N22"):
    for _ in range(2):
        capacitor(
            net,
            "AGND",
            "22uF 50V X7R",
            True,
            "Each effective>=5uF; capacitor RMS/ESR and placement require qualification",
        )
    capacitor(net, "AGND", "100nF 50V X7R")
capacitor("SW_REF_1V", "AGND", "100nF 16V X7R")
resistor("RAW_P22", "RAW_P_RMID", 300000, True)
resistor("RAW_P_RMID", "RAW_P_FB", 15000, True)
resistor("RAW_P_FB", "AGND", 15000, True)
resistor("SW_REF_1V", "RAW_N_FB", 15000, True)
resistor("RAW_N_FB", "RAW_N22", 330000, True)
for rail, fb, ss in [("RAW_P22", "RAW_P_FB", "RAW_P_SS"), ("RAW_N22", "RAW_N_FB", "RAW_N_SS")]:
    capacitor(
        rail,
        fb,
        "68pF 50V C0G 5%",
        "",
        "Initial compensation candidate; manufacturer-model/load-step loop qualification open",
    )
    # 5V_DIG is safely below16V and introduces a deliberate startup dependency.
    resistor("5V_DIG", ss, 4700)
    capacitor(ss, "AGND", "330nF 16V X7R")

# E15 power-good drives a shared enable through receiving-end dividers. A
# missing guard harness leaves both converters disabled, independently of MCU.
for ref, name, output, top in [("U2", "DIG", "5V_DIG", 10500), ("U3", "PRE", "V5_PRE", 12500)]:
    component(
        ref,
        "TPS62933FDRLR",
        "Package_TO_SOT_SMD:SOT-583-8",
        [
            pin(1, "RT", "input", "L", None),
            pin(2, "EN", "input", "L", "SUPPLY_ENABLE"),
            pin(3, "VIN", "power_in", "L", "VIN_PROTECTED"),
            pin(4, "GND", "power_in", "L", "AGND"),
            pin(5, "SW", "passive", "R", name + "_SW"),
            pin(6, "BST", "passive", "R", name + "_BST"),
            pin(7, "SS", "input", "L", name + "_SS"),
            pin(8, "FB", "input", "L", name + "_FB"),
        ],
        400 if ref == "U2" else 700,
        100,
        TI + "tps62933f.pdf",
        "FCCM; RT floating selects500kHz nominal. Accuracy screen uses0..85C junction range; thermal qualification open.",
    )
    resistor("POWER_READY", "SUPPLY_ENABLE", 10000)
    resistor("SUPPLY_ENABLE", "AGND", 22000)
    if name == "PRE":
        rt = [
            resistor(output, name + "_RMID", 12400, True),
            resistor(name + "_RMID", name + "_FB", 100, True),
        ]
    else:
        rt = [resistor(output, name + "_FB", top, True)]
    rb = resistor(name + "_FB", "AGND", 2000, True)
    capacitor(name + "_BST", name + "_SW", "100nF 16V X7R")
    capacitor(name + "_SS", "AGND", "33nF 16V X7R")
    lr = inductor(name + "_SW", output, "10uH 20% Isat>=6A Irms>=3A DCR<=0.1ohm")
    for _ in range(2):
        capacitor(output, "AGND", "22uF 16V X7R", True, "Each effective>=10uF; combined20..60uF target")
    for _ in range(2):
        capacitor(
            "VIN_PROTECTED", "AGND", "10uF 25V X7R", True, "Each effective>=5uF; combined RMS allocation>=1A"
        )
    capacitor("VIN_PROTECTED", "AGND", "100nF 50V X7R")
    BUCKS.append(
        dict(
            ref=ref, name=name, output=output, top=rt, bottom=rb, inductor=lr, nominal=0.8 * (1 + top / 2000)
        )
    )

component(
    "U4",
    "REF5025EIDR",
    SO8,
    [
        pin(1, "EN", "input", "L", "5V_DIG"),
        pin(2, "VIN", "power_in", "L", "5V_DIG"),
        pin(3, "TEMP", "output", "R", None),
        pin(4, "GND", "power_in", "L", "AGND"),
        pin(5, "NR", "passive", "L", None),
        pin(6, "VOUT", "power_out", "R", "PREF_2V5"),
        pin(7, "NC", "no_connect", "R", None),
        pin(8, "DNC", "no_connect", "R", None),
    ],
    1000,
    100,
    TI + "ref50.pdf",
)
capacitor("5V_DIG", "AGND", "100nF 16V X7R")
capacitor("PREF_2V5", "AGND", "2.2uF 16V X7R", False, "Effective>=1uF")
resistor("PREF_2V5", "PREF_FILTER", 1000)
capacitor(
    "PREF_FILTER",
    "AGND",
    "1uF film 63V 10%",
    True,
    "Footprint is a reserve; select a suitable low-leakage part/package before PCB",
)

# The negative shunt is floated: cathode/VOUT at AGND, anode/GND at-2.5V.
component(
    "U12",
    "LT1634AIS8-2.5#PBF",
    SO8,
    [
        *[pin(n, "DNC", "no_connect", "L", None) for n in (1, 2, 3, 7)],
        pin(4, "GND/ANODE", "passive", "L", "NREF_2V5"),
        pin(5, "TEST", "input", "L", "NREF_2V5"),
        pin(6, "VOUT/CATHODE", "passive", "R", "AGND"),
        pin(8, "NC", "no_connect", "R", None),
    ],
    1000,
    340,
    ADI + "1634ff.pdf",
    "Industrial A grade. Do not connect pin4 to system ground.",
)
resistor("NREF_2V5", "RAW_N22", 100000)
resistor("NREF_2V5", "NREF_FILTER", 1000)
capacitor(
    "NREF_FILTER",
    "AGND",
    "1uF film 63V 10%",
    True,
    "Footprint is a reserve; exact low-leakage part/package pending",
)

# Positive targets use one quad on0..RAW_P22; negative targets one dual onRAW_N22..0.
pos_pins = [pin(4, "V+", "power_in", "R", "RAW_P22"), pin(11, "V-", "power_in", "R", "AGND")]
neg_pins = [pin(8, "V+", "power_in", "R", "AGND"), pin(4, "V-", "power_in", "R", "RAW_N22")]
for name, target, amp, pp, np, op, rf, rg, reg, vin, control, bleed in [
    ("P19", 19, "U5", 3, 2, 1, 660000, 100000, "U7", "RAW_P22", "RAW_P22", 9090),
    ("P12", 12, "U5", 5, 6, 7, 380000, 100000, "U8", "RAW_P17", "RAW_P17", 5620),
    ("V5_REG", 5, "U5", 10, 9, 8, 100000, 100000, "U9", "V5_PRE", "VIN_PROTECTED", 2210),
    ("N19", -19, "U6", 3, 2, 1, 660000, 100000, "U10", "RAW_N22", None, 9090),
    ("N12", -12, "U6", 5, 6, 7, 380000, 100000, "U11", "RAW_N17", None, 5620),
]:
    neg = target < 0
    out = name + "_DRIVE"
    sense = name + "_SET"
    fb = name + "_FB"
    reference = "NREF_FILTER" if neg else "PREF_FILTER"
    pins = [
        pin(pp, "+", "input", "L", reference),
        pin(np, "-", "input", "L", fb),
        pin(op, "OUT", "output", "R", out),
    ]
    (neg_pins if neg else pos_pins).extend(pins)
    terms = (330000, 330000) if rf == 660000 else (200000, 180000) if rf == 380000 else (100000,)
    if len(terms) == 2:
        top = [resistor(sense, name + "_RMID", terms[0], True), resistor(name + "_RMID", fb, terms[1], True)]
    else:
        top = [resistor(sense, fb, terms[0], True)]
    bottom = resistor(fb, "AGND", rg, True)
    isolation = resistor(
        out, sense, 6800, False, "Limit SET clamp current; Kelvin DC feedback is after this resistor"
    )
    comp = capacitor(
        out,
        fb,
        "47nF 50V C0G 5%",
        True,
        "Local HF feedback bypasses remote SET pole; finite loop/PCB qualification open",
    )
    cap = capacitor(sense, "AGND", "100nF 50V X7R", False, "Effective50..120nF for target-source loop screen")
    load = resistor(
        name,
        "AGND",
        bleed,
        False,
        "Minimum-load/discharge resistor; qualify power rating and thermal derating",
    )
    if not neg:
        if name == "P12":
            component(
                reg,
                "LT3080IQ#PBF",
                "Package_TO_SOT_SMD:TO-263-5_TabPin3",
                [
                    pin(1, "NC", "no_connect", "L", None),
                    pin(2, "SET", "input", "L", sense),
                    pin(3, "OUT/TAB", "power_out", "R", name),
                    pin(4, "VCONTROL", "power_in", "L", control),
                    pin(5, "IN", "power_in", "L", vin),
                ],
                400,
                340,
                ADI + "3080fc.pdf",
                "DD-PAK for12V thermal margin. Tab is OUT, not ground; use manufacturer copper/thermal guidance.",
            )
        else:
            component(
                reg,
                "LT3080IMS8E#PBF",
                MSOP,
                [
                    *[pin(n, "OUT", "power_out" if n == 1 else "passive", "R", name) for n in (1, 2, 3)],
                    pin(4, "SET", "input", "L", sense),
                    pin(5, "VCONTROL", "power_in", "L", control),
                    pin(6, "NC", "no_connect", "L", None),
                    *[pin(n, "IN", "power_in", "L", vin) for n in (7, 8)],
                    pin(9, "EP/OUT", "passive", "R", name),
                ],
                100 + 300 * (int(reg[1:]) - 7),
                340,
                ADI + "3080fc.pdf",
                "EP is OUT, not ground. Separate IN/VCONTROL dropout checks required.",
            )
    else:
        component(
            reg,
            "LT3090IDD#PBF",
            DFN,
            [
                pin(1, "OUT", "power_out", "R", name),
                pin(2, "OUT", "passive", "R", name),
                pin(3, "GND", "power_in", "L", "AGND"),
                pin(4, "SET", "input", "L", sense),
                pin(5, "SHDN", "input", "L", "5V_DIG"),
                pin(6, "IMONN", "output", "R", None),
                pin(7, "IMONP", "output", "R", None),
                pin(8, "ILIM", "input", "L", vin),
                pin(9, "IN", "power_in", "L", vin),
                pin(10, "IN", "power_in", "L", vin),
                pin(11, "EP/IN", "power_in", "L", vin),
            ],
            100 + 300 * (int(reg[1:]) - 10),
            470,
            ADI + "3090fa.pdf",
            "EP is negative IN, not ground. ILIM to IN selects internal current limit; faults/disconnects remain open.",
        )
    capacitor(vin, "AGND", "10uF 50V X7R", True, "Effective>=5uF at worst bias/temperature")
    capacitor(name, "AGND", "22uF 50V X7R", True, "Effective>=10uF; actual ESR/transient stability pending")
    capacitor(name, "AGND", "100nF 50V X7R")
    STAGES.append(
        dict(
            name=name,
            nominal=target,
            amp=amp,
            regulator=reg,
            reference=reference,
            drive=out,
            set=sense,
            fb=fb,
            top=top,
            bottom=bottom,
            isolation=isolation,
            compensation=comp,
            set_cap=cap,
            bleed=load,
            input=vin,
            control=control,
        )
    )
pos_pins.extend(
    [
        pin(12, "SPARE+", "input", "L", "AGND"),
        pin(13, "SPARE-", "input", "L", "SPARE_OUT"),
        pin(14, "SPARE_OUT", "output", "R", "SPARE_OUT"),
    ]
)
component("U5", "OPA4192ID", SO14, pos_pins, 100, 240, TI + "opa4192.pdf")
component("U6", "OPA2192ID", SO8, neg_pins, 400, 240, TI + "opa2192.pdf")
for rail in ("RAW_P22", "RAW_N22"):
    capacitor(rail, "AGND", "100nF 50V X7R")
    capacitor(rail, "AGND", "1uF 50V X7R")
for ref, nets, y in [
    ("J1", ["VIN_PROTECTED", "AGND"], 100),
    ("J2", ["P19", "AGND", "N19", "P12", "N12", "V5_REG"], 260),
    ("J3", ["5V_DIG", "AGND"], 410),
    ("J4", ["RAW_P22", "AGND", "RAW_N22", "RAW_P17", "RAW_N17", "V5_PRE"], 540),
    ("J5", ["AGND", "POWER_READY"], 580),
]:
    component(
        ref,
        "Header" + str(len(nets)),
        "Connector_PinHeader_2.54mm:PinHeader_1x" + f"{len(nets):02d}" + "_P2.54mm_Vertical",
        [pin(i + 1, net, "passive", "L", net) for i, net in enumerate(nets)],
        1400,
        y,
        note="Engineering interface only; current-rated keyed production connector/harness not selected",
    )

# A separate+/-17V pair supplies the higher-current12V audio stages. This keeps
# their current and heat out of the19V regulators;17V also avoids the boost
# converter's15% minimum-duty boundary at the highest13.2V input.
component(
    "U13",
    "LT3471EDD#PBF",
    DFN,
    [
        pin(1, "FB1N", "input", "L", "LO_P_FB"),
        pin(2, "FB1P", "input", "L", "LO_REF_1V"),
        pin(3, "VREF", "power_out", "R", "LO_REF_1V"),
        pin(4, "FB2P", "input", "L", "LO_N_FB"),
        pin(5, "FB2N", "input", "L", "AGND"),
        pin(6, "SW2", "passive", "R", "LO_N_SW"),
        pin(7, "SHDN/SS2", "input", "L", "LO_N_SS"),
        pin(8, "VIN", "power_in", "L", "VIN_PROTECTED"),
        pin(9, "SHDN/SS1", "input", "L", "LO_P_SS"),
        pin(10, "SW1", "passive", "R", "LO_P_SW"),
        pin(11, "EP/GND", "power_in", "L", "AGND"),
    ],
    700,
    470,
    ADI + "lt3471.pdf",
)
inductor("VIN_PROTECTED", "LO_P_SW", "33uH 20% Isat>=3A Irms>=1.5A DCR<=0.2ohm", True)
inductor("VIN_PROTECTED", "LO_N_SW", "68uH 20% Isat>=3A Irms>=1.5A DCR<=0.2ohm")
inductor("LO_CUK_NODE", "RAW_N17", "68uH 20% Isat>=3A Irms>=1.5A DCR<=0.2ohm")
for ref, a, k in [("D3", "LO_P_SW", "RAW_P17"), ("D4", "LO_CUK_NODE", "AGND")]:
    component(
        ref,
        "SS16-E3/61T",
        "Diode_SMD:D_SMA",
        [pin(1, "K", "passive", "L", k), pin(2, "A", "passive", "R", a)],
        source="https://www.vishay.com/docs/88746/ss12.pdf",
    )
resistor("RAW_P17", "LO_P_FB", 240000, True)
resistor("LO_P_FB", "AGND", 15000, True)
resistor("LO_REF_1V", "LO_N_FB", 15000, True)
resistor("LO_N_FB", "LO_N_RMID", 200000, True)
resistor("LO_N_RMID", "RAW_N17", 54900, True)
capacitor("LO_N_SW", "LO_CUK_NODE", "10uF 63V X7R", True, "Effective>=2.2uF; RMS ripple>=0.6A required")
for net in ("RAW_P17", "RAW_N17"):
    for _ in range(2):
        capacitor(net, "AGND", "22uF 50V X7R", True, "Each effective>=5uF")
    capacitor(net, "AGND", "100nF 50V X7R")
capacitor("VIN_PROTECTED", "AGND", "22uF 50V X7R", True, "Effective>=5uF")
capacitor("VIN_PROTECTED", "AGND", "100nF 50V X7R")
capacitor("LO_REF_1V", "AGND", "100nF 16V X7R")
for rail, fb, ss in [("RAW_P17", "LO_P_FB", "LO_P_SS"), ("RAW_N17", "LO_N_FB", "LO_N_SS")]:
    capacitor(
        rail,
        fb,
        "68pF 50V C0G 5%",
        False,
        "Initial compensation candidate; manufacturer loop models/load-step validation open",
    )
    resistor("5V_DIG", ss, 4700)
    capacitor(ss, "AGND", "330nF 16V X7R")

# E17 series switches need a small digital-voltage offset without weakening
# the4.90..5.10V protected-load target. Keep existing references stable; append
# R51 rather than renumbering the supply. Feedback remains before the switch.
for c in COMPONENTS:
    if c["ref"] == "R10":
        c["pins"][1]["net"] = "DIG_FB_TRIM"
trim = resistor(
    "DIG_FB_TRIM",
    "DIG_FB",
    10,
    True,
    "E17 digital5V source target5.004V; protected-load drop checked separately",
)
assert trim == "R51"
for b in BUCKS:
    if b["name"] == "DIG":
        b["top"].append(trim)
        b["nominal"] = 5.004
# Names must stay distinct when flattened with E17 and the load schematics.
source_rails = ("P19", "N19", "P12", "N12", "V5_REG", "5V_DIG")
for c in COMPONENTS:
    for p in c["pins"]:
        if p["net"] in source_rails:
            p["net"] += "_SRC"
for stage in STAGES:
    stage["source_net"] = stage["name"] + "_SRC"
for b in BUCKS:
    b["source_net"] = b["output"] + "_SRC" if b["output"] == "5V_DIG" else b["output"]

passives = [c for c in COMPONENTS if c["ref"][0] in "RCLD"]
for i, c in enumerate(passives):
    c["x"] = 60 + (i % 12) * 125
    c["y"] = 650 + (i // 12) * 40
for c in COMPONENTS:
    c["x"] = round(round(c["x"] / 1.27) * 1.27, 4)
    c["y"] = round(round(c["y"] / 1.27) * 1.27, 4)
NOTES = [
    (
        20,
        20,
        "E14 candidate rail generation: protected12V -> dual bucks + separate boost/Cuk +/-22V and+/-17V -> precision-driven linear +/-19V,+/-12V,5V analog.",
    ),
    (
        20,
        30,
        "E16 input guard required at J1/J5. E17 disconnects separate source rails(*_SRC) from protected load rails. No routed board or physical qualification.",
    ),
    (
        20,
        610,
        "U5/U6 SET-source feedback senses after6.8k isolation;47nF provides local HF feedback. Output and input capacitors must be placed at regulator pins.",
    ),
    (
        20,
        620,
        "Normal digital5V accuracy screen uses0..85C junction; target full-unit ambient0..40C, unverified. Extended-temperature rail/monitor behavior must be qualified.",
    ),
    (
        20,
        1210,
        "SET clamp-current and unpowered/short behavior require bench validation; no claim of complete pin protection. Internal LDO limits are not supply overvoltage disconnects.",
    ),
]
