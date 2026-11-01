"""Explicit staged TPS259482L positive-rail circuit and hardware fault state.

Candidate adaptation of TI TPS25948 Rev D §8.6 from480x to482L/RCBCTRL=0.
No physical fault, startup, thermal or brownout qualification is inferred.
"""

import copy

from ..spec import COMPONENTS, pin
from .capacitor_patterns import CAPS
from .capacitor_patterns import SOURCE as CAP_SOURCE

TI = "https://www.ti.com/lit/ds/symlink/"
TSS14 = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"
REMOVED = {
    "J2",  # Optional engineering header; operating input is the real J11 stud.
    "U5",
    "U6",
    *(f"Q{i}" for i in range(9, 15)),
    *(f"R{i}" for i in range(33, 40)),
    *(f"R{i}" for i in range(41, 48)),
    "C18",
    "C19",
    "C22",
    "C23",
}
RETIRED_SUFFIXES = (
    "_COMMON",
    "_GATE",
    "_DRIVE",
    "_MCAP1",
    "_MCAP2",
    "_MCAP1_LIMIT",
    "_MCAP2_LIMIT",
    "_TT",
    "_ALLOW",
)


def components():
    parts = [copy.deepcopy(c) for c in COMPONENTS if c["ref"] not in REMOVED]
    for c in parts:
        if c["ref"] == "R93":
            c["part"] = "10k 1%"
            c["note"] = (
                "RAW POWER_RUN pulldown;2%total resistance envelope and20uA Schmitt input+2uA board leakage allocation. Actual external driver and partial-power capture remain unqualified."
            )
        if c["part"] == "TLV1824IDR":
            c["part"] = "TLV1824DR"
            c["note"] = (
                c.get("note", "")
                + " E28 ordering erratum: official TLV1824DR, not invalid IDR string; retained front SOIC14."
            )
    nres = 94
    ncap = 38
    owner = None

    def add(ref, part, fp, pins, source, note=""):
        nonlocal owner
        if ref.startswith("U"):
            owner = ref
        parts.append(
            dict(
                ref=ref,
                part=part,
                footprint=fp,
                pins=pins,
                source=source,
                note=note,
                x=0,
                y=0,
                owner_ref=owner,
            )
        )

    def r(a, b, value, note=""):
        nonlocal nres
        nres += 1
        add(
            f"R{nres}",
            value,
            "Resistor_SMD:R_0805_2012Metric",
            [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
            "",
            note,
        )
        return f"R{nres}"

    def c(a, b, value="100nF 16V X7R", note="", fp="Capacitor_SMD:C_0805_2012Metric"):
        nonlocal ncap
        ncap += 1
        add(f"C{ncap}", value, fp, [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)], "", note)
        return f"C{ncap}"

    def logic(ref, part, gates, gatepins):
        ps = []
        for (a, b, y), (pa, pb, py) in zip(gates, gatepins):
            ps.extend(
                [
                    pin(pa, "A", "input", "L", a),
                    pin(pb, "B", "input", "L", b),
                    pin(py, "Y", "output" if y else "no_connect", "R", y),
                ]
            )
        ps.extend([pin(7, "GND", "power_in", "L", "AGND"), pin(14, "VCC", "power_in", "R", "V2V5_AUX")])
        add(ref, part, TSS14, ps, TI + part.lower().split("apwr")[0] + "a.pdf")
        c("V2V5_AUX", "AGND")

    # Preserve the OV/reference network and make its final gate a true latched
    # request. All bipolar driver permits are further masked by the AUP master.
    u12 = next(c for c in parts if c["ref"] == "U12")
    next(p for p in u12["pins"] if p["number"] == "13")["net"] = "E28_SAFE_REQUEST"
    for channel_ref in ("R4", "R12", "R20", "R28"):
        item = next(c for c in parts if c["ref"] == channel_ref)
        next(p for p in item["pins"] if p["number"] == "1")["net"] = "E28_MASTER_ENABLE"
    j6 = next(c for c in parts if c["ref"] == "J6")
    next(p for p in j6["pins"] if p["number"] == "2")["net"] = "E28_MASTER_ENABLE"
    paths = [
        ("U13", "ANA", 0, "E28_ANA_ENABLE", "ANA_PG0"),
        ("U14", "ANA", 1, "E28_ANA_FOLLOW", "ANA_PG1"),
        ("U15", "DIG", 0, "E28_MASTER_ENABLE", "DIG_PG0"),
        ("U16", "DIG", 1, "E28_DIG_FOLLOW1", "DIG_PG1"),
        ("U17", "DIG", 2, "E28_DIG_FOLLOW2", "DIG_PG2"),
        ("U32", "ANA", 2, "E28_ANA_FOLLOW2", "ANA_PG2"),
        ("U33", "DIG", 3, "E28_DIG_FOLLOW3", "DIG_PG3"),
    ]
    for ref, domain, index, enable, pg in paths:
        source, output = ("V5_REG_SRC", "V5_REG") if domain == "ANA" else ("5V_DIG_SRC", "5V_DIG")
        prefix = f"E28_{domain}_{index}"
        ps = [
            pin(1, "EN_UVLO", "input", "L", enable),
            pin(2, "OVLO", "input", "L", "AGND"),
            pin(3, "SPLYGD", "open_collector", "R", pg),
            pin(4, "RCBCTRL", "input", "L", "AGND"),
            pin(5, "IN", "passive", "L", source),
            pin(6, "OUT", "passive", "R", output),
            pin(7, "DVDT", "passive", "L", prefix + "_DVDT"),
            pin(8, "GND", "power_in", "L", "AGND"),
            pin(9, "ILM", "passive", "L", prefix + "_ILM"),
            pin(10, "ITIMER", "no_connect", "R", None),
            pin(11, "OUT", "passive", "R", output),
            pin(12, "IN", "passive", "L", source),
        ]
        add(
            ref,
            "TPS259482LYWP",
            "RMX_E28:TPS259482L_YWP0012A",
            ps,
            TI + "tps25948.pdf",
            "RCBCTRL=0 disables steady-state reverse blocking; disabled/fault blocking remains. Local source UV and latch command every EN OFF. No equal-current assumption; each branch must carry full startup load.",
        )
        r(pg, "V2V5_AUX", "10k")
        r(enable, "AGND", "47k", "Ioff<=1.3uA gives<=61.1mV settled disabled gate.")
        r(
            prefix + "_ILM",
            "AGND",
            "2.43k 0.1%" if domain == "ANA" else "604 0.1%",
            "Manufacturer tabulated full-temp current range; upstream source limiting and output-UV latch still required.",
        )
        r(
            prefix + "_DVDT",
            prefix + "_DVDT_CAP",
            "100 1%",
            "TI requires series resistor for dVdt capacitance>10nF.",
        )
        c(prefix + "_DVDT_CAP", "AGND", "100nF 50V C0G 5%" if domain == "ANA" else "47nF 50V C0G 5%")
        c(
            source,
            "AGND",
            "1uF 50V X7R",
            "TPS259488.8:sourcelead>inches;effective>=.47uF required overvoltage/temperature/tolerance; actualpart acceptance pending.",
        )
    # Four fail-safe-input comparators: source presence and protected-output health.
    comparisons = [
        ("ANA_SRC", "V5_REG_SRC", "ANA_SOURCE_OK"),
        ("DIG_SRC", "5V_DIG_SRC", "DIG_SOURCE_OK"),
        ("ANA_OUT", "V5_REG", "ANA_OUTPUT_OK"),
        ("DIG_OUT", "5V_DIG", "DIG_OUTPUT_OK"),
    ]
    ps = []
    comp_pins = [(5, 4, 2), (7, 6, 1), (9, 8, 14), (11, 10, 13)]
    for (name, net, output), (plus, minus, out) in zip(comparisons, comp_pins):
        sense = "E28_" + name + "_SENSE"
        r(net, sense, "28.7k 0.01% 5ppm")
        r(sense, "AGND", "10k 0.01% 5ppm")
        r("V2V5_AUX", output, "10k")
        c(sense, "AGND", "100pF 50V C0G 5%")
        ps.extend(
            [
                pin(plus, "SENSE+", "input", "L", sense),
                pin(minus, "REF-", "input", "L", "PROTECT_REF"),
                pin(out, "UV_OK", "open_collector", "R", output),
            ]
        )
    ps.extend([pin(3, "V+", "power_in", "R", "V2V5_AUX"), pin(12, "V-", "power_in", "R", "AGND")])
    add(
        "U18",
        "TLV1824PWR",
        "RMX_E28:TLV1824_PW0014A",
        ps,
        TI + "tlv1824.pdf",
        "Nominal UV4.8375V. Source UV disables immediately; output UV is armed only after initial valid startup. Full offset/reference/resistor/leakage corners required.",
    )
    c("V2V5_AUX", "AGND")
    # AUX supervisor and independent startup deadline, both source-powered.
    for ref, sense, mr, out, ct in (
        ("U19", "E28_AUX_SENSE", "V2V5_AUX", "E28_AUX_RESET_N", "E28_AUX_CT"),
        ("U20", "E28_MASTER_ENABLE", "E28_MASTER_ENABLE", "E28_TIMEOUT", "E28_TIMEOUT_CT"),
    ):
        add(
            ref,
            "TPS389001DSET",
            "RMX_E28:TPS389001_DSE0006A",
            [
                pin(1, "SENSE", "input", "L", sense),
                pin(2, "GND", "power_in", "L", "AGND"),
                pin(3, "MR_N", "input", "L", mr),
                pin(4, "VDD", "power_in", "R", "V2V5_AUX"),
                pin(5, "CT", "passive", "L", ct),
                pin(6, "RESET_N", "open_collector", "R", out),
            ],
            TI + "tps3890.pdf",
        )
        c("V2V5_AUX", "AGND")
        r(out, "V2V5_AUX", "100k" if ref == "U19" else "10k")
    r("V2V5_AUX", "E28_AUX_DIV", "11.1k 0.1%")
    r("E28_AUX_DIV", "E28_AUX_SENSE", "39.2 0.1%")
    r("E28_AUX_SENSE", "AGND", "10k 0.1%")
    c("E28_AUX_CT", "AGND", "10nF 50V C0G 5%")
    for _ in range(5):
        c(
            "E28_TIMEOUT_CT",
            "AGND",
            "100nF 50V C0G 5%",
            "Five parallel C0G parts; cap/board leakage included in deadline bounds.",
        )
    gp = [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]
    np = [(2, 3, 1), (5, 6, 4), (8, 9, 10), (11, 12, 13)]
    logic(
        "U21",
        "SN74LVC02APWR",
        [
            ("ALL_RAILS_ALLOW", "E28_ARMED", "E28_ARM_BAR"),
            ("E28_RESET", "E28_ARM_BAR", "E28_ARMED"),
            ("E28_FAULT_SET", "E28_FAULT", "E28_FAULT_BAR"),
            ("E28_RESET", "E28_FAULT_BAR", "E28_FAULT"),
        ],
        np,
    )
    logic(
        "U22",
        "SN74LVC02APWR",
        [
            ("E28_OUT_VALID_ACTIVE", "E28_OUT_ARMED", "E28_OUT_ARM_BAR"),
            ("E28_RESET_OUT", "E28_OUT_ARM_BAR", "E28_OUT_ARMED"),
            ("E28_NORMAL_OK", "AGND", "E28_NOT_NORMAL_OK"),
            ("E28_OUT_READY", "AGND", "E28_NOT_OUT_READY"),
        ],
        np,
    )
    logic(
        "U23",
        "SN74LVC32APWR",
        [
            ("E28_NOT_RUN", "E28_NOT_AUX", "E28_RESET"),
            ("E28_RESET", "E28_FAULT", "E28_RESET_OUT"),
            ("E28_NOT_NORMAL_OK", "E28_OUT_UV_FAULT", "E28_FAULT_A"),
            ("E28_FAULT_A", "E28_TIMEOUT_FAULT", "E28_FAULT_ANY"),
        ],
        gp,
    )
    logic(
        "U24",
        "SN74LVC08APWR",
        [
            ("ANA_SOURCE_OK", "DIG_SOURCE_OK", "E28_SOURCE_READY"),
            ("ANA_OUTPUT_OK", "DIG_OUTPUT_OK", "E28_OUT_READY"),
            ("E28_SOURCE_READY", "OK_ALL_OV", "E28_NORMAL_OK"),
            ("POWER_RUN", "E28_AUX_VALID", "E28_USER_AUX"),
        ],
        gp,
    )
    logic(
        "U25",
        "SN74LVC08APWR",
        [
            ("E28_USER_AUX", "E28_SOURCE_READY", "E28_SAFE_STAGE"),
            ("E28_SAFE_STAGE", "E28_NOT_FAULT", "E28_SAFE_REQUEST"),
            ("E28_ARMED", "E28_FAULT_ANY", "E28_FAULT_SET"),
            ("E28_OUT_READY", "E28_MASTER_ENABLE", "E28_OUT_VALID_ACTIVE"),
        ],
        gp,
    )
    logic(
        "U26",
        "SN74LVC08APWR",
        [
            ("E28_OUT_ARMED", "E28_NOT_OUT_READY", "E28_OUT_UV_FAULT"),
            ("E28_TIMEOUT", "E28_NOT_OUT_READY", "E28_TIMEOUT_FAULT"),
            ("DIG_PG3", "ANA_PG2", "E28_ALL_CHANNELS_READY"),
            ("E28_ALL_CHANNELS_READY", "E28_OUT_READY", "E28_OUTPUT_PERMISSION"),
        ],
        gp,
    )
    logic(
        "U27",
        "SN74LVC08APWR",
        [
            ("E28_OUTPUT_PERMISSION", "E28_MASTER_ENABLE", "E28_OUTPUT_READY"),
            ("AGND", "AGND", None),
            ("AGND", "AGND", None),
            ("AGND", "AGND", None),
        ],
        gp,
    )
    # Inverters: source input references stay within AUX or are fail-safe pins.
    inv = []
    for (inp, out), (pa, py) in zip(
        (
            ("POWER_RUN", "E28_NOT_RUN"),
            ("E28_AUX_VALID", "E28_NOT_AUX"),
            ("E28_FAULT", "E28_NOT_FAULT"),
            ("E28_NOT_RUN", "E28_RUN_LOGIC"),
            ("P03_SOURCES_READY", "E28_NOT_SOURCE_READY"),
            ("E28_NOT_SOURCE_READY", "E28_SOURCE_READY_LOGIC"),
        ),
        ((1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12)),
    ):
        inv.extend(
            [pin(pa, "A", "input", "L", inp), pin(py, "Y", "output" if out else "no_connect", "R", out)]
        )
    inv.extend([pin(7, "GND", "power_in", "L", "AGND"), pin(14, "VCC", "power_in", "R", "V2V5_AUX")])
    add(
        "U28",
        "SN74LVC14APWR",
        "RMX_E28:SN74LVC14A_PW0014A",
        inv,
        TI + "sn74lvc14a.pdf",
        "Pin-compatible Schmitt receiver;three spare gates now buffer raw RUN/READY. No Ioff guarantee is claimed;do not externally drive outputs. Partial-AUX/hot input leakage remains a qualification hold.",
    )
    c("V2V5_AUX", "AGND")
    # AUP0.8V operation covers the range in which ordinary LVC/comparators are
    # undefined but eFuse EN could exceed1.17V. Every actual enable passes here.
    for ref, gates in (
        (
            "U29",
            [
                ("ALL_RAILS_ALLOW", "E28_AUX_VALID", "E28_MASTER_ENABLE"),
                ("E28_MASTER_ENABLE", "DIG_PG0", "E28_DIG_FOLLOW1"),
            ],
        ),
        (
            "U30",
            [
                ("E28_MASTER_ENABLE", "DIG_PG1", "E28_DIG_FOLLOW2"),
                ("E28_MASTER_ENABLE", "DIG_PG3", "E28_ANA_ENABLE"),
            ],
        ),
        (
            "U31",
            [
                ("E28_MASTER_ENABLE", "ANA_PG0", "E28_ANA_FOLLOW"),
                ("E28_AUX_RESET_N", "V2V5_AUX", "E28_AUX_VALID"),
            ],
        ),
        (
            "U34",
            [
                ("E28_MASTER_ENABLE", "DIG_PG2", "E28_DIG_FOLLOW3"),
                ("E28_MASTER_ENABLE", "ANA_PG1", "E28_ANA_FOLLOW2"),
            ],
        ),
    ):
        ps = []
        for (a, b, y), (pa, pb, py) in zip(gates, ((1, 2, 7), (5, 6, 3))):
            ps.extend(
                [
                    pin(pa, "A", "input", "L", a),
                    pin(pb, "B", "input", "L", b),
                    pin(py, "Y", "output" if y else "no_connect", "R", y),
                ]
            )
        ps.extend([pin(4, "GND", "power_in", "L", "AGND"), pin(8, "VCC", "power_in", "R", "V2V5_AUX")])
        add(
            ref,
            "SN74AUP2G08DCUR",
            "RMX_E28:SN74AUP2G08_DCU0008A",
            ps,
            TI + "sn74aup2g08.pdf",
            "Every actual eFuse enable is source/AUX masked. Settled partial-power truth and dynamic brownout capture are separate checks.",
        )
        c("V2V5_AUX", "AGND")
    r(
        "E28_SAFE_REQUEST",
        "AGND",
        "47k",
        "Keep the full-125C HIGH load below the100uA LVC VOH test point;2%total resistor envelope remains a construction requirement.",
    )
    r("E28_MASTER_ENABLE", "AGND", "10k")
    r(
        "P03_SOURCES_READY",
        "AGND",
        "15k",
        "Open-harness settled LOW corner assumes<=40uA aggregate LVC input leakage and2%total resistor error;source3.3kRESETpullup. Partial-AUX/dynamic/leakage acceptance remains open.",
    )
    # Combine P03 all-source presence with the user request at the latch input.
    u24 = next(c for c in parts if c["ref"] == "U24")
    next(p for p in u24["pins"] if p["number"] == "12")["net"] = "E28_RUN_AND_SOURCE"
    u27 = next(c for c in parts if c["ref"] == "U27")
    for number, net in (("4", "POWER_RUN"), ("5", "P03_SOURCES_READY"), ("6", "E28_RUN_AND_SOURCE")):
        pp = next(p for p in u27["pins"] if p["number"] == number)
        pp["net"] = net
        if number == "6":
            pp["kind"] = "output"
    u24 = next(c for c in parts if c["ref"] == "U24")
    next(p for p in u24["pins"] if p["number"] == "8")["net"] = "E28_NORMAL_PRE"
    for number, net in (("9", "E28_NORMAL_PRE"), ("10", "P03_SOURCES_READY"), ("8", "E28_NORMAL_OK")):
        pp = next(p for p in u27["pins"] if p["number"] == number)
        pp["net"] = net
        if number == "8":
            pp["kind"] = "output"
    # Allocate the second safety AND to the spare U27 gate. This preserves
    # Boolean behavior while allowing the U25 lower edge to share the nearby
    # source-bypass ground rather than routing NOT_FAULT into a via cage.
    for ref, mapping in (
        ("U25", {"4": "AGND", "5": "AGND", "6": None}),
        ("U27", {"12": "E28_SAFE_STAGE", "13": "E28_NOT_FAULT", "11": "E28_SAFE_REQUEST"}),
    ):
        part = next(c for c in parts if c["ref"] == ref)
        for terminal in part["pins"]:
            if terminal["number"] in mapping:
                terminal["net"] = mapping[terminal["number"]]
                if terminal["number"] in ("6", "11"):
                    terminal["kind"] = "output" if terminal["net"] else "no_connect"
    add(
        "J9",
        "E28 CONTROL",
        "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
        [
            pin(i + 1, name, "passive", "L", name)
            for i, name in enumerate(
                ("AGND", "P03_SOURCES_READY", "E28_OUTPUT_READY", "E28_FAULT", "E28_MASTER_ENABLE")
            )
        ],
        "",
        "P03 all-source-ready input; output-ready is independent of SPLYGD alone. Current/keying/capture physical qualification pending.",
    )
    for item in parts:
        if item["ref"] != "U28" and item["part"].startswith("SN74LVC"):
            for pp in item["pins"]:
                if pp["kind"] == "input" and pp["net"] in ("POWER_RUN", "P03_SOURCES_READY"):
                    pp["net"] = {"POWER_RUN": "E28_RUN_LOGIC", "P03_SOURCES_READY": "E28_SOURCE_READY_LOGIC"}[
                        pp["net"]
                    ]
    for item in parts:
        if item["part"] in CAPS:
            selected = CAPS[item["part"]]
            item.update(
                manufacturer_part=selected["mpn"],
                footprint="RMX_E28:" + selected["footprint"],
                source=CAP_SOURCE,
                maximum_package_height_mm=selected["max_height_mm"],
            )
            item["part"] += " " + selected["mpn"]
            item["note"] += (
                " ExactC0Gcase/voltage perKEMET2025Table1;LevelBlandTable3;heightTable2;procurement/assembly notaccepted."
            )
    for index, item in enumerate(parts):
        item["x"] = 76.2 + (index % 10) * 139.7
        item["y"] = 88.9 + (index // 10) * 88.9
    assert len({c["ref"] for c in parts}) == len(parts)
    return parts


def retired(net):
    return any(net == prefix + suffix for prefix in ("V5_REG", "5V_DIG") for suffix in RETIRED_SUFFIXES)
