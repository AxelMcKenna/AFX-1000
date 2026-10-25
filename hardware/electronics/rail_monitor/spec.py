"""E13 independent window qualification for all analog/digital/bias supplies.

This is a monitor, not a supply generator or an overvoltage disconnect/clamp.
Persist circuit edits here; condition/part allocations require qualification.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
WINDOWS = [
    dict(
        name="P19",
        rail="P19",
        kind="positive",
        sense_top=91000,
        sense_bottom=10000,
        uv_top=3570,
        ov_top=3010,
        normal=[18.81, 19.19],
        valid=[18.392, 19.608],
    ),
    dict(
        name="N19",
        rail="N19",
        kind="inverted",
        amp_in=100000,
        amp_fb=10000,
        uv_top=3400,
        ov_top=2870,
        normal=[18.81, 19.19],
        valid=[18.392, 19.608],
    ),
    dict(
        name="P12",
        rail="P12",
        kind="positive",
        sense_top=91000,
        sense_bottom=10000,
        uv_top=11500,
        ov_top=10604,
        normal=[11.88, 12.12],
        valid=[11.616, 12.384],
    ),
    dict(
        name="N12",
        rail="N12",
        kind="inverted",
        amp_in=100000,
        amp_fb=10000,
        uv_top=11300,
        ov_top=10412,
        normal=[11.88, 12.12],
        valid=[11.616, 12.384],
    ),
    dict(
        name="NBIAS_L",
        rail="NBIAS_L",
        kind="inverted",
        amp_in=10000,
        amp_fb=80600,
        uv_top=8200,
        ov_top=1780,
        normal=[0.1838, 0.256],
        valid=[0.16, 0.27],
    ),
    dict(
        name="NBIAS_R",
        rail="NBIAS_R",
        kind="inverted",
        amp_in=10000,
        amp_fb=80600,
        uv_top=8200,
        ov_top=1780,
        normal=[0.1838, 0.256],
        valid=[0.16, 0.27],
    ),
    dict(
        name="V5_REG",
        rail="V5_REG",
        kind="positive",
        sense_top=10499,
        sense_bottom=10000,
        uv_top=374,
        ov_top=127,
        normal=[4.975, 5.025],
        valid=[4.90, 5.10],
    ),
    dict(
        name="5V_DIG",
        rail="5V_DIG",
        kind="positive",
        sense_top=10499,
        sense_bottom=10000,
        ov_sense_top=11500,
        uv_top=768,
        ov_top=270,
        normal=[4.90, 5.10],
        valid=[4.70, 5.30],
    ),
]


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


def resistor(a, b, r, precision=True, note=""):
    global r_count
    r_count += 1
    ref = "R" + str(r_count)
    component(
        ref,
        value(r) + (" 0.01% 5ppm" if precision else " 1%"),
        "Resistor_SMD:R_0805_2012Metric",
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        note=note,
    )
    return ref


def capacitor(a, b, v, note=""):
    global c_count
    c_count += 1
    ref = "C" + str(c_count)
    component(
        ref,
        v,
        "Capacitor_SMD:C_0805_2012Metric",
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        note=note,
    )
    return ref


# Each output has its own pull-up and hysteresis feedback; never wire these
# outputs together, which would couple sixteen independent trip thresholds.
comparator_pins = [("5", "4", "2"), ("7", "6", "1"), ("9", "8", "14"), ("11", "10", "13")]
all_comparators = []
for wi, w in enumerate(WINDOWS):
    for mode in ("UV", "OV"):
        name = w["name"] + "_" + mode
        out = name + "_OK"
        sense = name + "_SENSE"
        threshold = name + "_REF"
        sense_parts = []
        if w["kind"] == "positive":
            top = w.get("ov_sense_top", w["sense_top"]) if mode == "OV" else w["sense_top"]
            if top == 10499:
                mid = name + "_RT_MID"
                sense_parts += [resistor(w["rail"], mid, 10000), resistor(mid, sense, 499)]
            else:
                sense_parts.append(resistor(w["rail"], sense, top))
            sense_parts.append(resistor(sense, "AGND", w["sense_bottom"]))
        else:
            sense_parts.append(resistor(w["name"] + "_INV", sense, 10000))
        top = w[mode.lower() + "_top"]
        threshold_parts = []
        base = threshold + "_BASE" if mode == "OV" else threshold
        # Selected exact sums use ordinary preferred precision resistor values.
        terms = {10604: (10000, 604), 10412: (10000, 412)}.get(top, (top,))
        if len(terms) == 2:
            mid = name + "_REF_MID"
            threshold_parts += [resistor("REF_2V5", mid, terms[0]), resistor(mid, base, terms[1])]
        else:
            threshold_parts.append(resistor("REF_2V5", base, top))
        threshold_parts.append(resistor(base, "AGND", 10000))
        threshold_series = resistor(base, threshold, 10000) if mode == "OV" else None
        positive = sense if mode == "UV" else threshold
        negative = threshold if mode == "UV" else sense
        feedback = resistor(
            out, positive, 20e6, False, "Individual positive feedback; allocate total value error <=5%"
        )
        pull = resistor(
            "V3V3_IO", out, 10000, False, "Individual open-drain status pull-up; one LVC input only"
        )
        capacitor(sense, "AGND", "100pF C0G 5%", "Sense RF filter; finite detection time must be measured")
        capacitor(threshold, "AGND", "100pF C0G 5%", "Local reference RF filter")
        all_comparators.append(
            dict(
                name=name,
                window=w["name"],
                mode=mode,
                positive=positive,
                negative=negative,
                output=out,
                sense_parts=sense_parts,
                threshold_parts=threshold_parts,
                threshold_series=threshold_series,
                feedback=feedback,
                pull=pull,
            )
        )

for ci in range(4):
    pins = []
    for j, entry in enumerate(all_comparators[ci * 4 : ci * 4 + 4]):
        p, n, y = comparator_pins[j]
        pins += [
            pin(p, str(j + 1) + "+", "input", "L", entry["positive"]),
            pin(n, str(j + 1) + "-", "input", "L", entry["negative"]),
            pin(y, str(j + 1) + "_OUT", "open_collector", "R", entry["output"]),
        ]
    pins += [pin(3, "V+", "power_in", "R", "V5_REG"), pin(12, "V-", "power_in", "R", "AGND")]
    component(
        "U" + str(ci + 1),
        "TLV1824IDR",
        "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
        pins,
        100 + 300 * ci,
        100,
        "https://www.ti.com/lit/ds/symlink/tlv1824.pdf",
        "Eight rail windows total; full-temperature5V offset allocation +/-5mV includes margin beyond12V table limit.",
    )

amp_pins = [("3", "2", "1"), ("5", "6", "7"), ("10", "9", "8"), ("12", "13", "14")]
amps = []
for i, w in enumerate([w for w in WINDOWS if w["kind"] == "inverted"]):
    node = w["name"] + "_FB"
    out = w["name"] + "_INV"
    p, n, o = amp_pins[i]
    rin = resistor(w["rail"], node, w["amp_in"])
    rf = resistor(out, node, w["amp_fb"])
    capacitor(
        out, node, "100pF C0G 5%", "Inverting sense-amplifier feedback; includes a finite response delay"
    )
    amps.append(
        dict(window=w["name"], input_ref=rin, feedback_ref=rf, positive_pin=p, negative_pin=n, output_pin=o)
    )
pins = []
for a in amps:
    name = a["window"]
    pins += [
        pin(a["positive_pin"], name + "+", "input", "L", "AGND"),
        pin(a["negative_pin"], name + "-", "input", "L", name + "_FB"),
        pin(a["output_pin"], name + "_OUT", "output", "R", name + "_INV"),
    ]
pins += [pin(4, "V+", "power_in", "R", "V5_REG"), pin(11, "V-", "power_in", "R", "AGND")]
component(
    "U5",
    "OPA4192ID",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    pins,
    100,
    250,
    "https://www.ti.com/lit/ds/symlink/opa4192.pdf",
    "Two0.1x negative-rail and two8.06x negative-bias sense amplifiers; no negative voltage on comparator inputs in valid operation.",
)

component(
    "U6",
    "REF5025EIDR",
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    [
        pin(1, "EN", "input", "L", "V5_REG"),
        pin(2, "VIN", "power_in", "L", "V5_REG"),
        pin(4, "GND", "power_in", "L", "AGND"),
        pin(3, "TEMP", "output", "R", None),
        pin(5, "NR", "passive", "R", None),
        pin(6, "VOUT", "power_out", "R", "REF_2V5"),
        pin(7, "DNC7", "passive", "R", None),
        pin(8, "DNC8", "passive", "R", None),
    ],
    400,
    250,
    "https://www.ti.com/lit/ds/symlink/ref50.pdf",
    "Enhanced E grade; allocate total reference error <=0.1%; NR left open for startup, reference load/settling needs qualification.",
)

resistor("V5_REG", "V5_COARSE_SENSE", 105000)
resistor("V5_COARSE_SENSE", "AGND", 10000)
resistor("V3V3_IO", "STARTUP_CT", 100000, False, "U7 fixed300ms release mode; min180ms,max420ms")
resistor("V3V3_IO", "LOCAL_RAIL_OK", 10000, False, "Wire-AND only the two coarse supervisor reset outputs")
for ref, part, sense, ct, x in [
    ("U7", "TPS3808G01DBVR", "V5_COARSE_SENSE", "STARTUP_CT", 700),
    ("U8", "TPS3808G33DBVR", "V3V3_IO", None, 1000),
]:
    component(
        ref,
        part,
        "Package_TO_SOT_SMD:SOT-23-6",
        [
            pin(6, "VDD", "power_in", "L", "V3V3_IO"),
            pin(5, "SENSE", "input", "L", sense),
            pin(3, "MR_N", "input", "L", "V3V3_IO"),
            pin(2, "GND", "power_in", "R", "AGND"),
            pin(1, "RESET_N", "open_collector", "R", "LOCAL_RAIL_OK"),
            pin(4, "CT", "passive", "R", ct),
        ],
        x,
        250,
        "https://www.ti.com/lit/ds/symlink/tps3808.pdf",
        "Coarse V5 and logic UV guards inhibit unpowered comparator/reference false-good states; not a rail clamp.",
    )

pair_outputs = [w["name"] + "_WINDOW_OK" for w in WINDOWS]
gate_groups = [
    [(w["name"] + "_UV_OK", w["name"] + "_OV_OK", w["name"] + "_WINDOW_OK") for w in WINDOWS[:4]],
    [(w["name"] + "_UV_OK", w["name"] + "_OV_OK", w["name"] + "_WINDOW_OK") for w in WINDOWS[4:]],
    [
        (pair_outputs[0], pair_outputs[1], "HV_OK"),
        (pair_outputs[2], pair_outputs[3], "LV_OK"),
        (pair_outputs[4], pair_outputs[5], "BIAS_OK"),
        (pair_outputs[6], pair_outputs[7], "FIVES_OK"),
    ],
    [
        ("HV_OK", "LV_OK", "ANALOG_WINDOWS_OK"),
        ("BIAS_OK", "FIVES_OK", "LOWV_WINDOWS_OK"),
        ("ANALOG_WINDOWS_OK", "LOWV_WINDOWS_OK", "WINDOWS_OK"),
        ("WINDOWS_OK", "LOCAL_RAIL_OK", "PRE_ANALOG_OK"),
    ],
]
for i, group in enumerate(gate_groups):
    pins = []
    for (a, b, y), (pa, pb, py) in zip(group, [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]):
        pins += [pin(pa, "A", "input", "L", a), pin(pb, "B", "input", "L", b), pin(py, "Y", "output", "R", y)]
    pins += [pin(14, "VCC", "power_in", "R", "V3V3_IO"), pin(7, "GND", "power_in", "R", "AGND")]
    component(
        "U" + str(i + 9),
        "SN74LVC08APWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        pins,
        100 + 300 * i,
        375,
        "https://www.ti.com/lit/ds/symlink/sn74lvc08a.pdf",
        "2V VIH/0.8V VIL at3.3V; all16 gates used. Final output requires coarse rails AND all16 window outputs.",
    )
resistor(
    "PRE_ANALOG_OK",
    "AGND",
    330000,
    False,
    "Source default low; keeps total final-output load below100uA including E09 receiving pull-down",
)

for ref in range(1, 13):
    rail = "V3V3_IO" if ref >= 7 else "V5_REG"
    capacitor(rail, "AGND", "100nF 16V X7R", "Local bypass for U" + str(ref))
capacitor(
    "REF_2V5",
    "AGND",
    "2.2uF 16V X7R",
    "Require effective >=1uF; reference output stability/load and startup unverified",
)
capacitor("V5_REG", "AGND", "10uF 16V X7R", "Local bulk; require effective >=4.7uF")
capacitor("V3V3_IO", "AGND", "1uF 16V X7R", "Local logic bulk")

for ref, nets, y, note in [
    (
        "J1",
        ["5V_DIG", "V3V3_IO", "AGND"],
        80,
        "Logic power and digital5V sense; V3V3_IO common Seed3/E09 domain",
    ),
    (
        "J2",
        ["P19", "AGND", "N19", "P12", "N12", "V5_REG"],
        175,
        "Main power rail sense and analog5V power input",
    ),
    (
        "J3",
        ["AGND", "NBIAS_L", "NBIAS_R"],
        275,
        "Same filtered bias sense nets as E12 J4.3/4; missing sense wire fails window low",
    ),
    ("J4", ["AGND", "PRE_ANALOG_OK"], 375, "PRE_ANALOG_OK -> E09 J5.5; E09 J5.1 common AGND"),
]:
    component(
        ref,
        "Conn_01x" + str(len(nets)).zfill(2),
        f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
        [pin(i + 1, str(i + 1), "passive", "L", net) for i, net in enumerate(nets)],
        1400,
        y,
        note=note,
    )

index = 0
for c in COMPONENTS:
    if c["ref"].startswith(("R", "C")):
        c["x"] = 60 + (index % 12) * 130
        c["y"] = 480 + (index // 12) * 40
        index += 1
    c["x"] = round(round(c["x"] / 1.27) * 1.27, 4)
    c["y"] = round(round(c["y"] / 1.27) * 1.27, 4)

NOTES = [
    (
        20.32,
        17.78,
        "E13: eight independent UV/OV windows + coarse5V/3.3V guard. PRE_ANALOG_OK is generated in hardware, independent of MCU firmware.",
    ),
    (
        20.32,
        25.4,
        "Monitor only: no power generation, rail disconnect/clamp, transient-fault or fabrication approval. Precision/offset/reference allocations require qualification.",
    ),
    (
        20.32,
        1038.86,
        "Each open-drain comparator has its own pull-up and hysteresis. Do NOT wire comparator outputs together; use the shown AND tree.",
    ),
    (
        20.32,
        1046.48,
        "Coarse guard holds qualification low while reference/sense amplifiers start. E09/E11/F02 retain settling and fresh-permit requirements.",
    ),
    (
        20.32,
        1054.1,
        "Main-rail fault envelope extends to +/-3.2% with a conditional headroom review; normal generation remains +/-1%. Analog5V generation must be tighter than its4.90..5.10V accepted envelope.",
    ),
]
