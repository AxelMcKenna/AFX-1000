"""Independent E12-R2 circuitry and explicitly conditional tolerance contracts."""

import copy
import itertools
from pathlib import Path

from ..spec import COMPONENTS as ORIGINAL
from ..spec import pin

ROOT = Path(__file__).resolve().parent
COMPARATOR = "https://www.ti.com/lit/gpn/tlv9024"
SUPERVISOR = "https://www.ti.com/lit/ds/symlink/tps3808.pdf"
PRECISION = "https://www.vishay.com/docs/60030/plt.pdf"
COMPONENTS = copy.deepcopy(ORIGINAL)
BY_REF = {c["ref"]: c for c in COMPONENTS}


def change(ref, *, value=None, footprint=None, nets=None, note=None):
    c = BY_REF[ref]
    if value:
        c["part"] = value
    if footprint:
        c["footprint"] = footprint
    if note:
        c["note"] = note
    if nets:
        for p in c["pins"]:
            if p["number"] in nets:
                p["net"] = nets[p["number"]]


def add(ref, value, footprint, nets, x, y, source="", note="", kinds=None):
    c = dict(
        ref=ref,
        part=value,
        footprint=footprint,
        pins=[
            pin(n, n, (kinds or {}).get(n, "passive"), "L" if int(n) % 2 else "R", net)
            for n, net in nets.items()
        ],
        x=round(round(x / 1.27) * 1.27, 4),
        y=round(round(y / 1.27) * 1.27, 4),
        source=source,
        note=note,
    )
    COMPONENTS.append(c)
    BY_REF[ref] = c


def passive(ref, value, a, b, x, y, footprint=None, source="", note=""):
    add(
        ref,
        value,
        footprint
        or ("Resistor_SMD:R_0603_1608Metric" if ref[0] == "R" else "Capacitor_SMD:C_0603_1608Metric"),
        {"1": a, "2": b},
        x,
        y,
        source,
        note,
    )


for ci, ch in enumerate(("L", "R")):

    def r(n):
        return "R" + str(n + ci * 16)

    def c(n):
        return "C" + str(n + ci * 14)

    for n in (1, 2, 3, 4):
        change(r(n), footprint="Resistor_SMD:R_0402_1005Metric")
    for n in (1, 2):
        change(
            c(n),
            footprint="Capacitor_SMD:C_0402_1005Metric",
            note="KEMET C0402C109B5GACTU: 1pF +/-0.1pF, C0G,50V; separate local HF feedback",
        )
    for n in (13, 14):
        change(
            c(n),
            footprint="Capacitor_SMD:C_0402_1005Metric",
            note="Local 100nF bypass; direct same-surface power-pad connection, adjacent ground via",
        )
    # Force nets terminate separately from feedback sense conductors.
    for n in (3, 4, 10, 11):
        for p in BY_REF[r(n)]["pins"]:
            if p["net"].startswith("ADC_"):
                p["net"] = p["net"].replace("ADC_", "SENSE_")
    # Lower divider impedance, and lower finite DC servo gain/leakage sensitivity.
    for n in (8, 9):
        change(
            r(n),
            value="100k 0.01%",
            note="PLT0805Z1003LST1; 50k Thevenin,10x lower than E12; reference loading must be qualified",
        )
    change(
        r(12),
        value="10M 1%",
        note="Lower DC servo feedback resistance by10x; finite DC error allocated explicitly",
    )
    # Reduce sense-node leakage sensitivity10x; common-mode integral crossover rises to31.83Hz.
    for n in (10, 11):
        change(
            r(n),
            value="10k 0.1%",
            note="Lower servo summing impedance10x; actual coupled common-mode loop must be qualified",
        )
    change(
        r(16),
        value="0.1R 1%",
        note="Reduce negative-rail load drop; ripple rejection now requires measurement, not assumed E12 filter",
    )
    for n in (14, 15):
        change(r(n), nets={"1": "PD_GATED"} if n == 14 else None)
    change(r(14), value="47k 1%")
    change(
        r(15),
        value="68k 1%",
        nets={"2": "NBIAS_" + ch},
        note="PD pull to its own negative supply; guaranteed reset low attenuated relative to VS-, not ground",
    )

# Connector supports separate routed force/sense per converter pin.
interface = [
    "ADC_LP",
    "SENSE_LP",
    "AGND",
    "ADC_LN",
    "SENSE_LN",
    "AGND",
    "REF_ADC1",
    "AGND",
    "ADC_RP",
    "SENSE_RP",
    "AGND",
    "ADC_RN",
    "SENSE_RN",
    "AGND",
    "REF_ADC2",
    "AGND",
    "PD_GATED",
    "BIAS_OK",
    "DRV_ENABLE",
    "AGND",
]
change(
    "J2",
    value="Conn_02x10_Odd_Even",
    footprint="Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical",
    note="Intermediate only; final codec co-location preferred. No cable is approved until loading/extraction is complete.",
)
BY_REF["J2"]["pins"] = [
    pin(i + 1, str(i + 1), "passive", "L" if i % 2 == 0 else "R", n) for i, n in enumerate(interface)
]
# Comparators are powered from V5/ground, not +/-12: fault output low must be ground referenced.
add(
    "U7",
    "TLV9024DR",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    {
        "1": "BIAS_OK",
        "2": "BIAS_OK",
        "3": "V5_REG",
        "4": "BIAS_SHIFT_L",
        "5": "THRESH_UPPER",
        "6": "THRESH_LOWER",
        "7": "BIAS_SHIFT_L",
        "8": "BIAS_SHIFT_R",
        "9": "THRESH_UPPER",
        "10": "THRESH_LOWER",
        "11": "BIAS_SHIFT_R",
        "12": "AGND",
        "13": "BIAS_OK",
        "14": "BIAS_OK",
    },
    520,
    420,
    COMPARATOR,
    "Four comparators: both upper/lower monitors on each negative rail. No assumed POR: current RevH removed POR claim.",
    {
        str(n): ("power_in" if n in (3, 12) else "open_collector" if n in (1, 2, 13, 14) else "input")
        for n in range(1, 15)
    },
)
add(
    "U8",
    "TPS3808G50DBVR",
    "Package_TO_SOT_SMD:SOT-23-6",
    {"1": "PD_GATED", "2": "AGND", "3": "BIAS_OK", "4": None, "5": "V5_REG", "6": "V5_REG"},
    650,
    420,
    SUPERVISOR,
    "Actual V5 supervisor; default20ms release delay. MR held low by either bias fault; physical dynamic timing unverified.",
    {"1": "open_collector", "2": "power_in", "3": "input", "4": "input", "5": "input", "6": "power_in"},
)
for ci, ch in enumerate(("L", "R")):
    for k, value, a, b in [
        (34 + ci * 2, "100k 0.01%", "V5_REG", "BIAS_SHIFT_" + ch),
        (35 + ci * 2, "10k 0.01%", "BIAS_SHIFT_" + ch, "NBIAS_" + ch),
    ]:
        passive(
            "R" + str(k),
            value,
            a,
            b,
            430 + ci * 100,
            470 + (k % 2) * 25,
            source=PRECISION,
            note="PLT0805Z1003LST1 / PLT0603Z1002LST1; 5ppm/C. Tolerance budget includes temperature/aging allocation.",
        )
# Shared threshold dividers, explicitly ratio-based to V5.
for k, value, a, b in [
    (38, "161k 0.01%", "V5_REG", "THRESH_UPPER"),
    (39, "10k 0.01%", "THRESH_UPPER", "AGND"),
    (40, "240k 0.01%", "V5_REG", "THRESH_LOWER"),
    (41, "10k 0.01%", "THRESH_LOWER", "AGND"),
]:
    passive(
        "R" + str(k),
        value,
        a,
        b,
        620 + (k % 2) * 65,
        475 + (k // 2 - 19) * 35,
        footprint="Resistor_SMD:R_0805_2012Metric" if k in (38, 40) else None,
        source=PRECISION,
        note="Selected PLT 5ppm/C,0.01%; 161k/240k require0805 per manufacturer130k maximum0603",
    )
passive(
    "R42",
    "10k 1%",
    "V5_REG",
    "BIAS_OK",
    770,
    440,
    note="Pull-up plus TPS3808 internal MR pull-up; four open drains wired to inhibit",
)
passive(
    "R43",
    "10k 1%",
    "DRV_ENABLE",
    "PD_GATED",
    770,
    470,
    note="External request cannot override supervisor low; DRV_ENABLE must be low until +/-12 and ESS health valid",
)
passive("R44", "100k 1%", "PD_GATED", "AGND", 770, 500, note="Default PD low if enable connector open")
passive("C35", "100nF 16V X7R", "V5_REG", "AGND", 520, 550)
passive("C36", "100nF 16V X7R", "V5_REG", "AGND", 650, 550)
# Select realizable passive technologies before freezing the R2 value contract.
for ci in (0, 1):
    for n in (1, 2):
        change("R" + str(n + ci * 16), value="2.49k 0.05%")
    for n in (3, 4):
        change("R" + str(n + ci * 16), value="1.21k 0.05%")
    for n in (5, 6):
        change(
            "R" + str(n + ci * 16),
            value="3.3R 1%",
            note="CRCW08053R30FKEA; realistic standard low-ohm resistor; inside resistive feedback. Hot resistance must enter headroom/current screen.",
        )
    change(
        "C" + str(9 + ci * 14),
        value="47uF 25V X7S",
        note="TDK C3225X7S1E476M250AC; +/-20%,X7S +/-22%; effective reserve at5V/temperature/age must be measured >=22uF",
    )
    for n in (10, 11):
        change(
            "C" + str(n + ci * 14),
            value="47uF 6.3V X7S",
            note="TDK C3216X7S0J476M160AC; +/-20%,X7S +/-22%; effective capacitance atactualbias must be measured >=22uF",
        )
    for n in (13, 14):
        change(
            "C" + str(n + ci * 14),
            note="GRM155R71C104KA88D; backside local100nF bypass, one short supply via underFDA body; local ground-plane return",
        )
for ref in ("C33", "C34"):
    change(
        ref,
        footprint="Capacitor_SMD:C_1206_3216Metric",
        note="TDK C3216X7R1H106K160AC; actual10uF50V1206; effective capacitance under12V remains a physical gate",
    )

# Manufacturer ordering-code selections are engineering candidates, not approved procurement or effective-C evidence.
for component in COMPONENTS:
    ref = component["ref"]
    component["mpn"] = component["part"] if ref.startswith(("U", "D")) else None
    if ref.startswith("R"):
        index = int(ref[1:])
        local = (index - 1) % 16 + 1 if index <= 32 else index
        if index <= 32 and local in (1, 2, 3, 4):
            component["mpn"] = "TNPU0402" + ("2K49" if local in (1, 2) else "1K21") + "AZEP00"
            component["source"] = "https://www.vishay.com/docs/28779/tnpue3.pdf"
        elif index <= 32 and local in (10, 11):
            component["mpn"] = "TNPW080510K0BEEA"
            component["source"] = "https://www.vishay.com/docs/28758/tnpwe3.pdf"
        elif index <= 32 and local in (8, 9):
            component["mpn"] = "PLT0805Z1003LST1"
            component["source"] = PRECISION
        elif index in (34, 36):
            component["mpn"] = "PLT0603Z1003LST1"
        elif index in (35, 37, 39, 41):
            component["mpn"] = "PLT0603Z1002LST1"
        elif index in (38, 40):
            component["mpn"] = "PLT0805Z" + ("1613" if index == 38 else "2403") + "LST1"
        elif index <= 32 and local == 16:
            component["mpn"] = "WSL0805R1000FEA"
            component["source"] = "https://www.vishay.com/docs/30108/wsl.pdf"
        else:
            codes = {
                "3.3R": "3R30",
                "1M": "1M00",
                "100k": "100K",
                "10M": "10M0",
                "10k": "10K0",
                "1k": "1K00",
                "47k": "47K0",
                "68k": "68K0",
            }
            token = component["part"].split()[0]
            package = "0603" if "R_0603" in component["footprint"] else "0805"
            component["mpn"] = "CRCW" + package + codes[token] + "FKEA"
            component["source"] = "https://www.vishay.com/docs/20035/dcrcwe3.pdf"
    elif ref.startswith("C"):
        index = int(ref[1:])
        local = (index - 1) % 14 + 1 if index <= 28 else index
        if index <= 28:
            component["mpn"] = {
                1: "C0402C109B5GACTU",
                2: "C0402C109B5GACTU",
                3: "C0805C470J5GACTU",
                4: "C0805C220J5GACTU",
                5: "C0805C220J5GACTU",
                6: "GRM21BR71H104KA01L",
                7: "MKS2C041001F00KSSD",
                8: "GRM31CR71C106KAC7",
                9: "C3225X7S1E476M250AC",
                10: "C3216X7S0J476M160AC",
                11: "C3216X7S0J476M160AC",
                12: "GRM21BR71C225KA12L",
                13: "GRM155R71C104KA88D",
                14: "GRM155R71C104KA88D",
            }[local]
        elif index in (33, 34):
            component["mpn"] = "C3216X7R1H106K160AC"
        else:
            component["mpn"] = "C0603C104K5RACTU" if index in (35, 36) else "GRM21BR71H104KA01L"
        if component["mpn"].startswith("C3"):
            component["source"] = (
                "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=" + component["mpn"]
            )
        elif component["mpn"].startswith("C0"):
            component["source"] = (
                "https://search.kemet.com/component-documentation/download/specsheet/" + component["mpn"]
            )
        elif component["mpn"].startswith("GRM"):
            component["source"] = (
                "https://www.murata.com/en-global/products/productdetail?partno=" + component["mpn"]
            )
        else:
            component["source"] = "https://www.wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf"
for index, component in enumerate(COMPONENTS[len(ORIGINAL) :]):
    component["x"] = round(round((60 + (index % 7) * 110) / 1.27) * 1.27, 4)
    component["y"] = round(round((850 + (index // 7) * 40) / 1.27) * 1.27, 4)
BY_REF["U7"]["x"], BY_REF["U7"]["y"] = 149.86, 720.09
BY_REF["U8"]["x"], BY_REF["U8"]["y"] = 450.85, 720.09
CONTRACT = {
    c["ref"]: {
        p["number"]: (
            p["net"] if p["net"] is not None else "unconnected-(" + c["ref"] + "-Pad" + p["number"] + ")"
        )
        for p in c["pins"]
    }
    for c in COMPONENTS
}
VALUES = {c["ref"]: c["part"] for c in COMPONENTS}


def thresholds(v5=(4.975, 5.025), resistor_error=0.0012, offset_v=0.002, common_supply_error_v=0.0006):
    """Exact resistor corners; error is a declared post-assembly lifetime allocation."""
    assert 0 < resistor_error < 0.01 and offset_v >= 0 and len(v5) == 2
    result = {}
    for name, top in [("upper", 161000), ("lower", 240000)]:
        values = []
        for v, sa, sb, sc, sd, vo in itertools.product(v5, *([(-1, 1)] * 5)):
            # Vsense=(V5*Rb+NBIAS*Ra)/(Ra+Rb); compare to V5*Rd/(Rc+Rd)+Vos.
            ra = 100000 * (1 + sa * resistor_error)
            rb = 10000 * (1 + sb * resistor_error)
            rc = top * (1 + sc * resistor_error)
            rd = 10000 * (1 + sd * resistor_error)
            reference = v * rd / (rc + rd) + vo * (offset_v + common_supply_error_v)
            values.append((reference * (ra + rb) - v * rb) / ra)
        result[name + "_trip_v"] = [min(values), max(values)]
    result.update(
        resistor_total_error_fraction=resistor_error,
        full_temperature_offset_v=offset_v,
        declared_cmr_psr_leakage_allocation_v=common_supply_error_v,
        physical_thresholds_measured=False,
        component_lifetime_allocation_guaranteed=False,
        note="0.12% resistance budget:0.01% initial +0.05% temperature +0.04% aging +0.02% assembly allocation. Aging/assembly qualification remains required; IB is typical, not a guaranteed leakage bound.",
    )
    return result
