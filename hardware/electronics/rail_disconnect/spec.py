"""E17 independently powered, common-source rail switches and OV-only interlock.

Candidate schematic; no transient/PCB/physical protection proof. The standard
VSONP footprint groups physical pins1..3=S,4=G,5..8/EP=D into pads1=S,2=G,3=D.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
CHANNELS = []
COMPARATORS = []
TI = "https://www.ti.com/lit/ds/symlink/"
SO8 = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
TSS14 = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"
FET = "Package_SON:VSONP-8-1EP_5x6_P1.27mm"


def pin(n, name, kind, side, net):
    return dict(number=str(n), name=name, kind=kind, side=side, net=net)


def component(ref, part, footprint, pins, x=0, y=0, source="", note=""):
    COMPONENTS.append(
        dict(ref=ref, part=part, footprint=footprint, pins=pins, x=x, y=y, source=source, note=note)
    )


def value(v):
    if v >= 1e6:
        return f"{v / 1e6:g}M"
    if v >= 1e3:
        return f"{v / 1e3:g}k"
    return f"{v:g}"


nr = nc = 0


def resistor(a, b, v, precision=False, note=""):
    global nr
    nr += 1
    ref = f"R{nr}"
    component(
        ref,
        value(v) + (" 0.01% 5ppm" if precision else " 1%"),
        "Resistor_SMD:R_0805_2012Metric",
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        note=note,
    )
    return ref


def capacitor(a, b, v, fp="Capacitor_SMD:C_0805_2012Metric", note=""):
    global nc
    nc += 1
    ref = f"C{nc}"
    component(ref, v, fp, [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)], note=note)
    return ref


rails = ["P19", "N19", "P12", "N12", "V5_REG", "5V_DIG"]
for i, name in enumerate(rails, 1):
    source = name + "_SRC"
    common = name + "_COMMON"
    gate = name + "_GATE"
    drive = name + "_DRIVE"
    enable = name + "_ALLOW"
    part = "CSD18540Q5B" if i <= 4 else "CSD18510Q5B"
    for q, drain in [(f"Q{2 * i - 1}", source), (f"Q{2 * i}", name)]:
        component(
            q,
            part,
            FET,
            [
                pin(1, "SOURCE_GROUP", "passive", "L", common),
                pin(2, "GATE_GROUP", "input", "L", gate),
                pin(3, "DRAIN_GROUP", "passive", "R", drain),
            ],
            100 + (i - 1) % 3 * 300,
            80 + (i - 1) // 3 * 170,
            TI + part.lower() + ".pdf",
            "KiCad grouped footprint pads:1=S physical1..3;2=G physical4;3=D physical5..8/exposed drain. Footprint candidate; dimension/stencil approval open.",
        )
    component(
        f"U{i}",
        "SI8751AB-ISR",
        SO8,
        [
            pin(1, "VDD", "power_in", "L", "V2V5_AUX"),
            pin(2, "TT", "passive", "L", name + "_TT"),
            pin(3, "IN", "input", "L", enable),
            pin(4, "GND", "power_in", "L", "AGND"),
            pin(5, "SOURCE", "passive", "R", common),
            pin(6, "MCAP2", "passive", "R", name + "_MCAP2"),
            pin(7, "MCAP1", "passive", "R", name + "_MCAP1"),
            pin(8, "GATE", "output", "R", drive),
        ],
        180 + (i - 1) % 3 * 300,
        135 + (i - 1) // 3 * 170,
        "https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf",
        "Floating gate power is generated internally. No main-rail startup dependency.35us maximum turn-off uses100pF load and is NOT a bound for these MOSFETs.",
    )
    rg = resistor(drive, gate, 22)
    bleed = resistor(
        gate,
        common,
        20e6,
        note="Gate leakage budget includes both FETs; do not substitute a low-value gate-source shunt",
    )
    tt = resistor(name + "_TT", "AGND", 10000)
    ri = resistor("ALL_RAILS_ALLOW", enable, 100)
    rp = resistor(
        enable,
        "AGND",
        10000,
        note="Receiving pulldown; missing interlock drive is OFF under10uA input-leakage allocation",
    )
    capacitor("V2V5_AUX", "AGND", "100nF 16V X7R")
    for drain, mc in ((source, 1), (name, 2)):
        midpoint = name + f"_MCAP{mc}_LIMIT"
        resistor(
            drain,
            midpoint,
            15000,
            note="Limits step-driven MCAP current; 60V across minimum14.85k is below6mA. Actual clamp sensitivity/dVdt qualification open.",
        )
        capacitor(
            midpoint,
            name + f"_MCAP{mc}",
            "10pF 100V C0G 5%",
            note="Both drain transients monitored; no blanket surge/dVdt approval",
        )
    bulk = {
        1: "1500uF 35V electrolytic 20% EEUFR1V152S",
        2: "1500uF 35V electrolytic 20% EEUFR1V152S",
        3: "220uF 35V electrolytic 20% EEUFR1V221",
        4: "220uF 35V electrolytic 20% EEUFR1V221",
        5: "1500uF 16V electrolytic 20% EEUFR1C152",
        6: "4700uF 16V electrolytic 20% EEUFR1C472",
    }[i]
    # Negative electrolytics have their positive terminal at AGND.
    a, b = ("AGND", name) if name.startswith("N") else (name, "AGND")
    fp = (
        "CP_Radial_D16.0mm_P7.50mm"
        if i in (1, 2, 6)
        else "CP_Radial_D8.0mm_P3.50mm"
        if i in (3, 4)
        else "CP_Radial_D10.0mm_P5.00mm"
    )
    cap = capacitor(
        a,
        b,
        bulk,
        "Capacitor_THT:" + fp,
        "Panasonic FR candidate; nominal D16x20/P7.5 for19V,D16x25/P7.5 digital,D8x11.5/P3.5 for12V,D10x20/P5 analog5V. ESR/ripple/aging,regulator stability,inrush and fit need qualification.",
    )
    COMPONENTS[-1]["source"] = "https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf"
    discharge = resistor(
        name,
        "AGND",
        47000,
        note="Protected-side bleed is not a rapid discharge or safety-isolation guarantee",
    )
    CHANNELS.append(
        dict(
            name=name,
            source=source,
            common=common,
            gate=gate,
            drive=drive,
            enable=enable,
            driver=f"U{i}",
            fets=[f"Q{2 * i - 1}", f"Q{2 * i}"],
            gate_resistor=rg,
            gate_bleed=bleed,
            tt=tt,
            input_resistor=ri,
            input_pulldown=rp,
            bulk=cap,
            discharge=discharge,
        )
    )

component(
    "U7",
    "REF35125QDBVR",
    "Package_TO_SOT_SMD:SOT-23-6",
    [
        pin(1, "GND", "power_in", "L", "AGND"),
        pin(2, "GND", "power_in", "L", "AGND"),
        pin(3, "EN", "input", "L", "V2V5_AUX"),
        pin(4, "VIN", "power_in", "L", "V2V5_AUX"),
        pin(5, "NR", "passive", "R", None),
        pin(6, "VREF", "power_out", "R", "PROTECT_REF"),
    ],
    100,
    420,
    TI + "ref35.pdf",
    "Independent1.25V reference; allocate total error0.3%,not only initial0.05%.",
)
capacitor("V2V5_AUX", "AGND", "100nF 16V X7R")
capacitor("PROTECT_REF", "AGND", "1uF 16V X7R", note="Require effective0.1..10uF and ESR<400mOhm for REF35")
component(
    "U8",
    "OPA2333AID",
    SO8,
    [
        pin(1, "OUT_A", "output", "R", "N19_INV"),
        pin(2, "IN-_A", "input", "L", "N19_SUM"),
        pin(3, "IN+_A", "input", "L", "AGND"),
        pin(4, "V-", "power_in", "L", "AGND"),
        pin(5, "IN+_B", "input", "L", "AGND"),
        pin(6, "IN-_B", "input", "L", "N12_SUM"),
        pin(7, "OUT_B", "output", "R", "N12_INV"),
        pin(8, "V+", "power_in", "L", "V2V5_AUX"),
    ],
    400,
    420,
    TI + "opa333.pdf",
    "Negative-rail magnitude sensing uses AUX,not protected supplies. Unpowered/clamp and dynamic recovery need qualification.",
)
neg_sense = {}
for name, terms in [("N19", [150000, 6200]), ("N12", [100000])]:
    node = name + "_SRC"
    rs = []
    for j, r in enumerate(terms):
        end = name + "_SUM" if j == len(terms) - 1 else name + "_INPUT_MID"
        rs.append(resistor(node, end, r, True))
        node = end
    fb = resistor(name + "_INV", name + "_SUM", 10000, True)
    series = resistor(name + "_INV", name + "_OV_SENSE", 1000)
    capacitor(name + "_OV_SENSE", "AGND", "100pF 50V C0G 5%")
    neg_sense[name] = dict(input=rs, feedback=fb, series=series)
capacitor("V2V5_AUX", "AGND", "100nF 16V X7R")

for name in rails:
    sense = name + "_OV_SENSE"
    ref = name + "_OV_REF"
    out = name + "_OV_OK"
    rp = []
    if not name.startswith("N"):
        terms = {"P19": [143000, 3300], "P12": [90900], "V5_REG": [31600], "5V_DIG": [31600]}[name]
        node = name + "_SRC"
        for j, r in enumerate(terms):
            end = sense if j == len(terms) - 1 else name + "_SENSE_MID"
            rp.append(resistor(node, end, r, True))
            node = end
        rp.append(resistor(sense, "AGND", 10000, True))
        capacitor(sense, "AGND", "100pF 50V C0G 5%")
    sr = resistor("PROTECT_REF", ref, 10000, True)
    rh = resistor(out, ref, 20e6, note="Per-channel hysteresis; do not tie comparator outputs together")
    pull = resistor("V2V5_AUX", out, 10000)
    COMPARATORS.append(
        dict(
            name=name,
            positive=ref,
            negative=sense,
            output=out,
            sense_parts=rp,
            reference_series=sr,
            hysteresis=rh,
            pullup=pull,
            negative_amplifier=neg_sense.get(name),
        )
    )
# Broad reference window supplies startup/open/short qualification. It is not a
# second precision reference or proof of arbitrary reference-component faults.
for name, top in [("REF_LOW", 12400), ("REF_HIGH", 7500)]:
    sense = name + "_AUX"
    rp = [resistor("V2V5_AUX", sense, top, True), resistor(sense, "AGND", 10000, True)]
    positive = "PROTECT_REF" if name == "REF_LOW" else sense
    negative = sense if name == "REF_LOW" else "PROTECT_REF"
    ref = name + "_POSITIVE"
    sr = resistor(positive, ref, 10000, True)
    out = name + "_OK"
    rh = resistor(out, ref, 20e6)
    pull = resistor("V2V5_AUX", out, 10000)
    COMPARATORS.append(
        dict(
            name=name,
            positive=ref,
            negative=negative,
            output=out,
            sense_parts=rp,
            reference_series=sr,
            hysteresis=rh,
            pullup=pull,
        )
    )
comp_pins = [(5, 4, 2), (7, 6, 1), (9, 8, 14), (11, 10, 13)]
for i in range(2):
    ps = []
    for j, c in enumerate(COMPARATORS[4 * i : 4 * i + 4]):
        p, n, o = comp_pins[j]
        ps += [
            pin(p, f"{j + 1}+", "input", "L", c["positive"]),
            pin(n, f"{j + 1}-", "input", "L", c["negative"]),
            pin(o, f"{j + 1}OUT", "open_collector", "R", c["output"]),
        ]
    ps += [pin(3, "V+", "power_in", "R", "V2V5_AUX"), pin(12, "V-", "power_in", "R", "AGND")]
    component(
        f"U{9 + i}",
        "TLV1824IDR",
        "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
        ps,
        700 + 300 * i,
        420,
        TI + "tlv1824.pdf",
        "2.4V minimum supply fits declared AUX lower bound. Fail-safe positive sense inputs avoid backfeeding AUX. Offset/bias/brownout/timing qualification remains open.",
    )
    capacitor("V2V5_AUX", "AGND", "100nF 16V X7R")
gates = [
    ("P19_OV_OK", "N19_OV_OK", "OK_19"),
    ("P12_OV_OK", "N12_OV_OK", "OK_12"),
    ("V5_REG_OV_OK", "5V_DIG_OV_OK", "OK_5"),
    ("REF_LOW_OK", "REF_HIGH_OK", "OK_REF"),
    ("OK_19", "OK_12", "OK_ANALOG"),
    ("OK_5", "OK_REF", "OK_AUXILIARY"),
    ("OK_ANALOG", "OK_AUXILIARY", "OK_ALL_OV"),
    ("OK_ALL_OV", "POWER_RUN", "ALL_RAILS_ALLOW"),
]
logic_pins = [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]
for i in range(2):
    ps = []
    for j, (a, b, y) in enumerate(gates[4 * i : 4 * i + 4]):
        pa, pb, py = logic_pins[j]
        ps += [
            pin(pa, f"{j + 1}A", "input", "L", a),
            pin(pb, f"{j + 1}B", "input", "L", b),
            pin(py, f"{j + 1}Y", "output", "R", y),
        ]
    ps += [pin(7, "GND", "power_in", "L", "AGND"), pin(14, "VCC", "power_in", "R", "V2V5_AUX")]
    component(f"U{11 + i}", "SN74LVC08APWR", TSS14, ps, 100 + 300 * i, 540, TI + "sn74lvc08a.pdf")
    capacitor("V2V5_AUX", "AGND", "100nF 16V X7R")
resistor(
    "POWER_RUN",
    "AGND",
    100000,
    note="Missing run harness defaults OFF under5uA LVC input-leakage bound; include this load in E16 SHDN high/low calculations",
)
resistor(
    "PROTECT_REF",
    "AGND",
    10000,
    True,
    "Discharges reference on an open source; defeats feedback-resistor phantom bias in the settled open-reference model",
)
capacitor(
    "V2V5_AUX",
    "AGND",
    "10uF 16V X7R",
    note="Effective>=4.7uF; AUX bulk and driver RF decoupling,not a separate3V3 supply",
)
headers = [
    ("J1", [r + "_SRC" for r in ["P19"]] + ["AGND", "N19_SRC", "P12_SRC", "N12_SRC", "V5_REG_SRC"]),
    ("J2", ["5V_DIG_SRC", "AGND"]),
    ("J3", ["P19", "AGND", "N19", "P12", "N12", "V5_REG"]),
    ("J4", ["5V_DIG", "AGND"]),
    ("J5", ["V2V5_AUX", "AGND", "POWER_RUN"]),
    ("J6", ["AGND", "ALL_RAILS_ALLOW", "PROTECT_REF"]),
]
for i, (ref, nets) in enumerate(headers):
    component(
        ref,
        "Header" + str(len(nets)),
        "Connector_PinHeader_2.54mm:PinHeader_1x" + f"{len(nets):02d}" + "_P2.54mm_Vertical",
        [pin(j + 1, n, "passive", "L", n) for j, n in enumerate(nets)],
        1100,
        80 + i * 75,
        note="Engineering interface; production keying/current ratings not selected. J5 goes to E16 J6.",
    )
# Spread equal-size active blocks to avoid overlaps; this is a review sheet,not PCB placement.
for i, c in enumerate([c for c in COMPONENTS if c["ref"].startswith("Q")]):
    c["x"] = 70 + (i % 6) * 175
    c["y"] = 70 + (i // 6) * 80
for i in range(1, 7):
    c = next(c for c in COMPONENTS if c["ref"] == f"U{i}")
    c["x"] = 180 + (i - 1) % 3 * 300
    c["y"] = 240 + (i - 1) // 3 * 90
for ref, x, y in [
    ("U7", 100, 450),
    ("U8", 400, 450),
    ("U9", 700, 450),
    ("U10", 1000, 450),
    ("U11", 100, 560),
    ("U12", 400, 560),
]:
    c = next(c for c in COMPONENTS if c["ref"] == ref)
    c["x"] = x
    c["y"] = y
for c in COMPONENTS:
    if c["ref"].startswith("J"):
        c["x"] = 1180
passives = [c for c in COMPONENTS if c["ref"].startswith(("R", "C"))]
for i, c in enumerate(passives):
    c["x"] = 45 + (i % 12) * 100
    c["y"] = 650 + (i // 12) * 40
for c in COMPONENTS:
    c["x"] = round(round(c["x"] / 1.27) * 1.27, 4)
    c["y"] = round(round(c["y"] / 1.27) * 1.27, 4)
NOTES = [
    (
        20.32,
        20.32,
        "E17: six common-source FET rail disconnects; AUX-powered precision OV sensing and all-rail interlock. Source rails and protected outputs are distinct nets.",
    ),
    (
        20.32,
        30.48,
        "Candidate schematic only. No routed board,complete enclosure fit,manufacturer transient/stability model or physical protection proof.",
    ),
    (
        20.32,
        1160.78,
        "Any source OV/reference-window fault or POWER_RUN low disables all six drivers. Zero source voltage is allowed during startup; no protected-rail supply dependency.",
    ),
    (
        20.32,
        1170.94,
        "VSONP grouped pads1=S(physical1..3),2=G(physical4),3=D(physical5..8/EP). Body diodes oppose. Gate/source reference floats with each common node.",
    ),
    (
        20.32,
        1181.10,
        "Si8751 timing maxima use100pF load. Actual FET charge,bulk capacitors,MCAP currents,inrush,leakage,partial-power and fault-energy limits require qualification.",
    ),
]
