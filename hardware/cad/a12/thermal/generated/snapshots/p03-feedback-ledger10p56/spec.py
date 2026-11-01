"""P03 circuit intent. Earlier native sources are imported read-only then changed explicitly.

The exported KiCad netlist is independently checked; this is not a release record.
"""

import copy
import json
from pathlib import Path

from ...input_protection.spec import COMPONENTS as GUARD

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
LEGACY = REPO / "hardware/electronics/power_supply/components.json"
TI = "https://www.ti.com/lit/ds/symlink/"
ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"
SIZE = (160, 45)
OUTLINE = [(0, 0), (160, 0), (160, 35), (152, 35), (152, 45), (6, 45), (6, 35), (0, 35)]
MOUNTS = [(4, 4), (156, 4), (12, 41), (144, 41), (41, 22), (62, 22), (96, 41), (121, 41), (91, 4), (117, 4)]
THERMAL_NODES = {
    "U1": "AGND",
    "U13": "AGND",
    "U20": "AGND",
    "U23": "AGND",
    "U101": "AGND",
    "U102": "AGND",
    "U22": "AGND",
    "U11": "RAW_N17",
    "U8": "P12_SRC",
    "U7": "P19_SRC",
}
THERMAL_REGIONS = {
    "U1": [84.5, 8, 89, 12.5],
    "U101": [23.25, 10, 28.25, 15],
    "U102": [24.25, 18.5, 28.25, 21.5],
    "U22": [54, 34, 58, 38],
    "U23": [132.5, 25.5, 137.5, 30.5],
    "U20": [42, 9, 52, 17],
    "U13": [100, 1.2, 118, 15.2],
    "U11": [118, 22, 128, 33],
    "U8": [97, 24, 117, 38],
    "U7": [73.5, 29, 81.5, 35],
}
# Only these quiet reference/feedback nets may cross the U13 contact field on
# In2.Cu. Their actual clearance voids must be omitted from thermal extraction.
U13_QUIET_FIELD_NETS = frozenset({"LO_N_FB", "LO_REF_1V"})

# Old buck, preregulator, analog LDO and associated passives are removed,
# rather than paralleled with the new sources. Original reference/U5/U6 and
# all four bipolar source circuits remain, with U5's third channel repurposed.
REMOVED = {
    "U2",
    "U3",
    "U9",
    "L4",
    "L5",
    "J1",
    "J4",
    "J5",
    *[f"R{n}" for n in range(8, 17)],
    *[f"R{n}" for n in range(30, 34)],
    "R51",
    *[f"C{n}" for n in range(16, 30)],
    *[f"C{n}" for n in range(44, 49)],
}


def pin(n, name, net, kind="passive", side="L"):
    return dict(number=str(n), name=name, net=net, kind=kind, side=side)


def components():
    parts = [c for c in json.loads(LEGACY.read_text()) if c["ref"] not in REMOVED]
    lt3471_names = {
        "1": "FB1N",
        "2": "FB1P",
        "3": "VREF",
        "4": "FB2P",
        "5": "FB2N",
        "6": "SW2",
        "7": "SHDN_SS2",
        "8": "VIN",
        "9": "SHDN_SS1",
        "10": "SW1",
        "11": "GND_EP",
    }
    for c in parts:
        if c["ref"] in {"U1", "U13"}:
            for p in c["pins"]:
                p["name"] = lt3471_names[p["number"]]
                if p["number"] == "5":
                    p["kind"] = "input"
            c["note"] += (
                " P03 symbol erratum per LT3471 RevC page4:pin5 is quiet FB2N, not PGND; EP11 is the sole power ground. Native pin/net mapping preserved."
            )
    # Lower only the inverting low preregulator; the positive boost retains
    # 17 V to avoid its minimum-duty limitation at maximum input.
    r48 = next(c for c in parts if c["ref"] == "R48")
    r48["part"] = "10k 0.01% 5ppm"
    r48["note"] += (
        " P03: RAW_N17 historical net name now denotes nominal -14 V; only N12 LDO/caps/feedback consume it."
    )
    u5 = next(c for c in parts if c["ref"] == "U5")
    for p in u5["pins"]:
        p["net"] = {"10": "AGND", "9": "P03_SPARE_C", "8": "P03_SPARE_C"}.get(p["number"], p["net"])
    u5["note"] += " P03: removed analog-LDO channel is parked as a ground follower."

    # Native guard variant: same reverse/OV/auxiliary circuit, a real new ILIM
    # value and a wired inlet. No current traverses the old E23 guard.
    for original in GUARD:
        if original["ref"] in {"S1", "J2", "J5", "F1"}:
            # Physical panel switch is on the rear inlet assembly, reached by
            # J104's logic-only cable. Redundant internal/test headers omitted.
            continue
        c = copy.deepcopy(original)
        c["ref"] = c["ref"][0] + str(100 + int(c["ref"][1:]))
        for p in c["pins"]:
            if p["net"] == "VIN_SYS":
                p["net"] = "DC_IN"
        if c["ref"] == "J101":
            c.update(
                part="JST B2PS-VH (VHR-2N/SVH-41T-P1.1 AWG16)",
                footprint="Connector_JST:JST_VH_B2PS-VH_1x02_P3.96mm_Horizontal",
            )
            c["pins"] = [pin(1, "DC_IN", "DC_IN"), pin(2, "AGND", "AGND")]
            c["source"] = "https://www.jst.com/wp-content/uploads/2025/06/eVH.pdf"
            c["note"] = (
                "New wired inlet from rear passive jack assembly; >=4 A normal profile. VH10A catalog rating requiresAWG16;20mOhm environmental contact bound,notquietreturnstrap. Assembledside-entryheight10.5mm,depth20.5mm needsA12harnessaccess. No originalE23seriesguard."
            )
        if c["ref"] == "F101":
            c["part"] = "0451006.MRL 6A 125V"
            c["note"] = (
                "Backup fuse changed to 6 A. The 4 A normal profile is not a fuse/adapter/TVS fault-energy coordination proof."
            )
        if c["ref"] == "Q101":
            c["part"] = "PSMN012-100YL,115"
            c["source"] = "https://assets.nexperia.com/documents/data-sheet/PSMN012-100YL.pdf"
            c["note"] = (
                "P03 logic-level100V FET:33.1mOhmmax atVGS5V/Tj175C; originalYS needed10V butTPS2663BGATEclampmin8.3V. Startup/hotgateleakage/faultenergy still require qualification."
            )
        if c["ref"] == "R105":
            c["part"] = "68.1k 0.1% 10ppm"
            c["note"] = (
                "P03 PG threshold reduced after full-tolerance review to assert before 9.8 V protected-input operating floor."
            )
        if c["ref"] == "R107":
            c["part"] = "4.02k 0.1% 10ppm"
            c["note"] = (
                "Explicit datasheet full-temperature4.185..4.815A test point; with0.3%totalR error4.172..4.830A, below5Ainlet normal rating."
            )
        if c["ref"] == "R108":
            c["part"] = "11.7k 0.1% 10ppm"
            c["note"] += (
                " P03 AUX recentered for conditional E28 2.50..2.70V receiver contract; overshoot/path/partial-power validation remains required."
            )
            c["pins"][1]["net"] = "P03_AUX_TRIM"
        if c["ref"] == "R109":
            c["part"] = "10k 0.1% 10ppm"
        if c["ref"] == "J103":
            c["exclude_from_bom"] = True
            c.update(
                part="Bare POWER_READY probe pads, no fitted header", footprint="RMX_P03:Probe2_P2.54_D1"
            )
            c["note"] = (
                "Unfitted bare copper probing only; zero mated height. Production control usesJ104/J106; no header may be fitted in the A12 analog-bar lane."
            )
        if c["ref"] == "J104":
            c.update(
                part="JST B3B-XH-A (XHP-3/SXH-001T-P0.6)",
                footprint="Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical",
            )
        if c["ref"] == "J106":
            c.update(
                part="JST B4B-XH-A (XHP-4/SXH-001T-P0.6)",
                footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
            )
            c["pins"].append(pin(4, "SOURCE_READY", "P03_ALL_SOURCES_READY"))
            c["note"] = (
                "Mandatory new4wireE28controlinterface:2.5VAUX,AGND,POWER_RUN,debouncedall-sixsourceREADY."
            )
        if c["ref"] == "C105":
            c["part"] = "1uF 50V X7R"
            c["note"] = (
                "Slower protected 12 V bus start; effective 0.6..1.2uF construction bound, not nominal-only arithmetic."
            )
        parts.append(c)

    def add(ref, part, fp, pins, source="", note=""):
        parts.append(dict(ref=ref, part=part, footprint=fp, pins=pins, source=source, note=note))

    def r(ref, value, a, b, precision=False):
        add(
            ref,
            value + (" 0.01% 5ppm" if precision else " 1%"),
            "Resistor_SMD:R_0805_2012Metric",
            [pin(1, "1", a), pin(2, "2", b, side="R")],
        )

    def cap(ref, value, a, b, fp="Capacitor_SMD:C_1210_3225Metric", note=""):
        add(ref, value, fp, [pin(1, "+", a), pin(2, "-", b, side="R")], note=note)

    r("R130", "49.9", "P03_AUX_TRIM", "AUX_FB", True)

    for ref, prefix, output in (("U20", "D", "5V_DIG_SRC"), ("U23", "A", "P03_PRE6V")):
        add(
            ref,
            "TPS543620RPYR",
            "RMX_P03:TPS543620_RPY0014A",
            [
                pin(1, "SYNC_FSEL", f"P03_{prefix}_FSEL", "input"),
                pin(2, "MODE", f"P03_{prefix}_MODE", "input"),
                pin(3, "PGOOD", "P03_SOURCES_READY", "open_collector", "R"),
                pin(4, "FB", f"P03_{prefix}_FB", "input"),
                pin(5, "AGND", "AGND", "power_in"),
                pin(6, "BP5", f"P03_{prefix}_BP5", "power_out", "R"),
                pin(7, "EN", f"P03_{prefix}_ENABLE", "input"),
                pin(8, "VIN", "VIN_PROTECTED", "power_in"),
                pin(9, "PGND", "AGND", "power_in"),
                pin(10, "SW", f"P03_{prefix}_SW", "output", "R"),
                pin(11, "PGND", "AGND", "power_in"),
                pin(12, "VIN", "VIN_PROTECTED", "power_in"),
                pin(13, "SW_BOOT_RETURN", f"P03_{prefix}_SW", "passive", "R"),
                pin(14, "BOOT", f"P03_{prefix}_BOOT", "passive"),
            ],
            TI + "tps543620.pdf",
            "500kHz, high current limit, 4ms nominal soft start. Exact RPY0014A metal/mask/paste, no invented exposed pad.",
        )
        n = 200 if prefix == "D" else 220
        r(
            f"R{n}",
            "9k" if prefix == "D" else "11k",
            output,
            "P03_D_FB_TRIM" if prefix == "D" else f"P03_{prefix}_FB",
            True,
        )
        if prefix == "D":
            r("R206", "54.9", "P03_D_FB_TRIM", "P03_D_FB", True)
        r(f"R{n + 1}", "1k", f"P03_{prefix}_FB", "AGND", True)
        r(f"R{n + 2}", "24.3k", f"P03_{prefix}_FSEL", "AGND")
        r(f"R{n + 3}", "3.32k", f"P03_{prefix}_MODE", "AGND")
        r(f"R{n + 4}", "10k", "POWER_READY", f"P03_{prefix}_ENABLE")
        r(f"R{n + 5}", "22k", f"P03_{prefix}_ENABLE", "AGND")
        cap(
            f"C{n}",
            "4.7uF 16V X7R",
            f"P03_{prefix}_BP5",
            "AGND",
            note="Effective>=2.2uF at4.5V; nominal increased to allow tolerance/DC-bias/temperature derating.",
        )
        cap(
            f"C{n + 1}",
            "100nF 50V X7R",
            f"P03_{prefix}_BOOT",
            f"P03_{prefix}_SW",
            "Capacitor_SMD:C_0603_1608Metric",
        )
        for k in (2, 3):
            cap(f"C{n + k}", "100nF 50V X7R", "VIN_PROTECTED", "AGND", "Capacitor_SMD:C_0603_1608Metric")
        for k in (4, 5):
            cap(
                f"C{n + k}",
                "22uF 25V X7R",
                "VIN_PROTECTED",
                "AGND",
                note="Effective minimum5uF per device at13.2V; actual MPN curve required.",
            )
        for k in (6, 7, 8, 9):
            cap(
                f"C{n + k}",
                "47uF 16V X7R",
                output,
                "AGND",
                note="Effective minimum20uF per part at6V; maximum56.4uF. Source local only, downstream startup is separately controlled.",
            )
        add(
            "L20" if prefix == "D" else "L23",
            "4.7uH 20% Coilcraft XAL7030-472MEC",
            "Inductor_SMD:L_Coilcraft_XAL7030-472",
            [pin(1, "SW", f"P03_{prefix}_SW"), pin(2, "OUT", output, side="R")],
            "https://www.coilcraft.com/getmedia/0d05a05e-d55d-4a0c-911d-46bd73686633/xal7030.pdf",
            "Manufacturer current/temperature/DC-resistance and core-loss envelope checked separately.",
        )

    add(
        "U21",
        "ADR4550BRZ",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        [
            pin(1, "NIC", None, "no_connect"),
            pin(2, "VIN", "P03_PRE6V", "power_in"),
            pin(3, "NIC", None, "no_connect"),
            pin(4, "GND", "AGND", "power_in"),
            pin(5, "NIC", None, "no_connect"),
            pin(6, "VOUT", "P03_REF5", "power_out", "R"),
            pin(7, "NIC", None, "no_connect"),
            pin(8, "DNC", None, "no_connect"),
        ],
        ADI + "adr4520_4525_4530_4533_4540_4550.pdf",
    )
    add(
        "U22",
        "LT3045IDD#PBF",
        "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm",
        [
            pin(1, "IN", "P03_PRE6V", "power_in"),
            pin(2, "IN", "P03_PRE6V", "power_in"),
            pin(3, "EN_UV", "P03_PRE6V", "input"),
            pin(4, "PG", None, "no_connect"),
            pin(5, "ILIM", "AGND"),
            pin(6, "PGFB", "P03_PRE6V", "input"),
            pin(7, "SET", "P03_ANA_SET", "input"),
            pin(8, "GND", "AGND", "power_in"),
            pin(9, "OUTS", "V5_REG_SRC", "input", "R"),
            pin(10, "OUT", "V5_REG_SRC", "power_out", "R"),
            pin(11, "EP_GND", "AGND", "power_in"),
        ],
        ADI + "3045fa.pdf",
        "PGFB tied to IN disables fast-start; large disconnected bulk is not a directly attached source capacitor.",
    )
    add(
        "U24",
        "OPA2192ID",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        [
            pin(1, "OUT_A", "P03_ANA_DRIVE", "output", "R"),
            pin(2, "IN_A_N", "P03_ANA_FB", "input"),
            pin(3, "IN_A_P", "P03_REF_FILTER", "input"),
            pin(4, "V_N", "AGND", "power_in"),
            pin(5, "IN_B_P", "AGND", "input"),
            pin(6, "IN_B_N", "P03_SPARE_24", "input"),
            pin(7, "OUT_B", "P03_SPARE_24", "output", "R"),
            pin(8, "V_P", "VIN_PROTECTED", "power_in"),
        ],
        TI + "opa2192.pdf",
        "Powered directly from protected12V BEFORE buck enable; no dependence on delayed RAW_P22 for analog SET control.",
    )
    r("R240", "100", "P03_REF5", "P03_REF_FILTER", True)
    r("R241", "6.8k", "P03_ANA_DRIVE", "P03_ANA_SET")
    r("R242", "120", "P03_ANA_SET", "P03_ANA_DIV", True)
    r("R243", "100k", "P03_ANA_DIV", "AGND", True)
    r("R244", "100k", "P03_ANA_DIV", "P03_ANA_FB", True)
    r("R245", "2.21k", "V5_REG_SRC", "AGND")
    r("R246", "10k", "V2V5_AUX", "P03_SOURCES_READY")
    cap("C240", "47nF 50V C0G 5%", "P03_ANA_DRIVE", "P03_ANA_FB")
    cap(
        "C241",
        "1uF 25V X7R",
        "P03_ANA_SET",
        "AGND",
        note="Effective>=0.6uF; limits initial SET-current floor slew with local-only capacitor inventory.",
    )
    for n in range(242, 252):
        cap(
            f"C{n}",
            "100nF 25V C0G 5% KEMET C1206C104J3GACTU",
            "P03_REF_FILTER",
            "AGND",
            "Capacitor_SMD:C_1206_3216Metric",
            "Ten actual KEMET25V C0G parts (C1003 Rev2025-02-20 ordering example/Table1A) replace unsupported50V1206code;5Vfilter voltage; full hot/aged aggregate leakage and assembly still require qualification.",
        )
    cap("C252", "1uF 16V X7R", "P03_REF5", "AGND")
    cap("C253", "1uF 16V X7R", "P03_PRE6V", "AGND")
    cap("C254", "22uF 16V X7R", "V5_REG_SRC", "AGND", note="Local LT3045 effective output>=10uF.")
    cap("C255", "100nF 50V X7R", "VIN_PROTECTED", "AGND", "Capacitor_SMD:C_0603_1608Metric")
    for ref, name in (("J20", "analog quiet star"), ("J21", "digital quiet star")):
        add(
            ref,
            "Wurth 7466003R M3 SMT",
            "RMX_P03:Wurth_7466003R",
            [pin(1, "AGND", "AGND")],
            "https://www.we-online.com/components/products/datasheet/7466003R.pdf",
            name
            + "; top bolt/ring lug,4.2mm NPTH spigot,8.5mm copper,torque<=0.5Nm. Actual joint resistance unqualified.",
        )
    for ref, net in (("J23", "5V_DIG_SRC"), ("J24", "V5_REG_SRC")):
        add(
            ref,
            "Wurth 7466003R M3 SMT",
            "RMX_P03:Wurth_7466003R",
            [pin(1, "POWER", net)],
            "https://www.we-online.com/components/products/datasheet/7466003R.pdf",
            "Operating positive5V source stud. Qualified assembled link <=2mOhm includingbothterminalassemblies/crimps/wire/solder; no assumed contact resistance.",
        )
    add(
        "J22",
        "P03 READY test",
        "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        [
            pin(1, "ALL_SOURCES_READY", "P03_ALL_SOURCES_READY"),
            pin(2, "AGND", "AGND"),
            pin(3, "POWER_READY", "POWER_READY"),
        ],
        note="Hardware presence/staging prerequisite, not precision load-window/noise health or MCU authorization.",
    )
    add(
        "U25",
        "LTC2910HGN#PBF",
        "Package_SO:SSOP-16_3.9x4.9mm_P0.635mm",
        [
            *[
                pin(n, f"V{n}", net, "input")
                for n, net in enumerate(
                    [
                        "P03_MON_DIG",
                        "P03_MON_ANA",
                        "P03_MON_P19",
                        "P03_MON_P12",
                        "P03_MON_BUCK_OK",
                        "P03_MON_VIN",
                        "P03_MON_N19",
                        "P03_MON_N12",
                    ],
                    1,
                )
            ],
            pin(9, "GND", "AGND", "power_in"),
            pin(10, "REF", "P03_MON_REF", "power_out", "R"),
            pin(11, "RST_ACTIVE_HIGH", None, "no_connect"),
            pin(12, "RST_ACTIVE_LOW", "P03_ALL_SOURCES_READY", "open_collector", "R"),
            pin(13, "DIS", "AGND", "input"),
            pin(14, "SEL", "AGND", "input"),
            pin(15, "TMR", "P03_MON_TIMER"),
            pin(16, "VCC", "V2V5_AUX", "power_in"),
        ],
        ADI + "2910fc.pdf",
        "Hgrade -40..125C. SEL=GND enables both negative monitors; DIS=GND can never bypass monitoring. Presence/debounce only; no precision power-rail qualification.",
    )
    add(
        "U26",
        "SN74LVC1G08DBVR",
        "Package_TO_SOT_SMD:SOT-23-5",
        [
            pin(1, "A", "P03_SOURCES_READY", "input"),
            pin(2, "B", "POWER_READY", "input"),
            pin(3, "GND", "AGND", "power_in"),
            pin(4, "Y", "P03_MON_BUCK_OK", "output", "R"),
            pin(5, "VCC", "V2V5_AUX", "power_in"),
        ],
        TI + "sn74lvc1g08.pdf",
        "Real logic threshold buffer: buckPGVOL0.5V is belowLVC VIL0.7V; LVC outputLOW meetsLTC0.492V minimumthreshold.",
    )
    for n, rail, top, mon in [
        (300, "5V_DIG_SRC", "87.6k", "DIG"),
        (302, "V5_REG_SRC", "87.6k", "ANA"),
        (304, "P19_SRC", "324k", "P19"),
        (306, "P12_SRC", "200k", "P12"),
        (308, "VIN_PROTECTED", "180k", "VIN"),
    ]:
        r(f"R{n}", top, rail, f"P03_MON_{mon}", True)
        r(f"R{n + 1}", "10k", f"P03_MON_{mon}", "AGND", True)
    r("R310", "590", "P03_MON_REF", "P03_MON_NEG_BIAS", True)
    r("R311", "1k", "P03_MON_NEG_BIAS", "AGND", True)
    r("R312", "7.5k", "P03_MON_NEG_BIAS", "P03_MON_N19", True)
    r("R313", "1M", "P03_MON_N19", "N19_SRC", True)
    r("R314", "10k", "P03_MON_NEG_BIAS", "P03_MON_N12", True)
    r("R315", "750k", "P03_MON_N12", "N12_SRC", True)
    r("R316", "4.7k", "V2V5_AUX", "P03_ALL_SOURCES_READY")
    cap("C300", "10nF 50V C0G 5%", "P03_MON_TIMER", "AGND", "Capacitor_SMD:C_0805_2012Metric")
    cap("C301", "100nF 50V X7R", "V2V5_AUX", "AGND", "Capacitor_SMD:C_0603_1608Metric")
    cap("C302", "100nF 50V X7R", "V2V5_AUX", "AGND", "Capacitor_SMD:C_0603_1608Metric")

    # All schematic symbols remain separated on a labelled engineering sheet.
    for i, c in enumerate(parts):
        c["x"], c["y"] = 76.2 + (i % 8) * 152.4, 88.9 + (i // 8) * 101.6
    assert len({c["ref"] for c in parts}) == len(parts)
    for c in parts:
        if c["ref"] == "C72":
            c["part"] = "100nF 50V X7R 10% TDK C1005X7R1H104K050BB"
            c["footprint"] = "Capacitor_SMD:C_0402_1005Metric"
            c["source"] = (
                "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X7R1H104K050BB"
            )
            c["note"] += (
                " Actual0402 VREF bypass selected to fit beside U13; body maxima1.05x0.55x0.55mm. Required effective10nF..1uF and local-reference/noise performance still require verification by actual bias/assembly measurements, not reference-only plots."
            )
        if c["ref"].startswith("C") and c["part"].startswith("22uF "):
            c["part"] = "22uF 50V X7R 20% TDK C3225X7R1H226M250AC"
            c["source"] = (
                "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1H226M250AC"
            )
            c["note"] += (
                " Exact TDK bulk candidate:2.80mm maximum body +0.10mm seat; effective capacitance/ripple/aging and native IPC1210 land versus manufacturer recommendation require approval. Catalog plots are reference-only."
            )
        if c["ref"].startswith("C") and c["part"].startswith("47uF "):
            c["part"] = "47uF 25V X7S 20% TDK C3225X7S1E476M250AC"
            c["source"] = (
                "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7S1E476M250AC"
            )
            c["note"] = (
                "Actual25V X7S candidate replaces generic16V X7R:temperature±22%,initial±20%,not±15%. Effective20uF minimum at6V remains unverified; full initial-plus-positive-temperature maximum68.808uF before unbounded remaining effects. Maximum body2.80mm +0.10mm seat. Native IPC1210 land, ripple/DC-bias/aging and assembly require approval."
            )
        if c["ref"] in {"R200", "R201"}:
            resistance = "902" if c["ref"] == "R200" else "102"
            c["part"] = (
                "9k" if c["ref"] == "R200" else "1k"
            ) + f" 0.01% 2ppm Susumu RG2012L-{resistance}-L-T1"
            c["source"] = "https://www.susumu.co.jp/common/pdf/RG_LL_Data_Sheet.pdf"
            c["note"] = (
                "Total0.1%R error remains an explicit assembled/aging allocation, not manufacturer lifetime guarantee. No0.04% inference from marking."
            )
        if c["ref"] in {f"C{n}" for n in range(242, 252)}:
            c["source"] = "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf"
        if c["ref"] == "R206":
            c["part"] = "54.9 0.1% 25ppm Panasonic ERA6AEB549V"
            c["note"] = "Series trim;0.3%totalR allocation propagated with9k upperleg."
        if c["ref"] in {"J2", "J3"}:
            c["note"] += (
                " P03:5V pins are TEST ONLY; no operating5V harness may bypass J23/J24 power-stud links. Bipolar header remains separately specified."
            )
    return parts
