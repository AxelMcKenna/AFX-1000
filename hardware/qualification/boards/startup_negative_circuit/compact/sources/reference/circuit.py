"""Actual NF03 component/pin topology. Package/cap/process acceptance is separate."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TI = "https://www.ti.com/lit/ds/symlink/"
ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"


def components():
    parts = []
    serial = {}

    def add(prefix, part, fp, terminals, source, note=""):
        serial[prefix] = serial.get(prefix, 0) + 1
        ref = prefix + str(serial[prefix])
        pins = []
        for i, (num, name, net, kind) in enumerate(terminals):
            pins.append(
                dict(
                    number=str(num),
                    name=name,
                    net=net,
                    kind=kind,
                    side="R" if kind in ("output", "open_collector", "power_out") else "L",
                )
            )
        index = len(parts)
        parts.append(
            dict(
                ref=ref,
                part=part,
                footprint=fp,
                pins=pins,
                source=source,
                note=note,
                x=round(round((80 + (index % 7) * 145) / 2.54) * 2.54, 4),
                y=round(round((90 + (index // 7) * 100) / 2.54) * 2.54, 4),
            )
        )
        return ref

    def r(v, a, b, note="", fp="Resistor_SMD:R_0805_2012Metric"):
        return add("R", v, fp, [(1, "1", a, "passive"), (2, "2", b, "passive")], "", note)

    def c(v, a, b, fp="Capacitor_SMD:C_0805_2012Metric", note=""):
        return add("C", v, fp, [(1, "1", a, "passive"), (2, "2", b, "passive")], "", note)

    def ic(part, fp, pmap, source, power=(), out=(), oc=(), nc=()):
        terminals = [
            (
                n,
                name,
                net,
                "power_in"
                if n in power
                else "output"
                if n in out
                else "open_collector"
                if n in oc
                else "no_connect"
                if n in nc
                else "input",
            )
            for n, (name, net) in pmap.items()
        ]
        u = add("U", part, fp, terminals, source)
        return u

    def gate(func, a, b, y, supply="AUX2V6", gnd="AGND"):
        family = "SN74AUP" if supply == "AUX2V6" else "SN74LVC"
        code = {"AND": "1G08", "OR": "1G32", "INV": "1G04"}[func]
        p = {1: ("A", a), 2: ("B", b), 3: ("GND", gnd), 4: ("Y", y), 5: ("VCC", supply)}
        if func == "INV":
            p = {1: ("NC", None), 2: ("A", a), 3: ("GND", gnd), 4: ("Y", y), 5: ("VCC", supply)}
        u = ic(
            family + code + "DBVR",
            "Package_TO_SOT_SMD:SOT-23-5",
            p,
            TI + (family + code).lower() + ".pdf",
            power=(3, 5),
            out=(4,),
            nc=(1,) if func == "INV" else (),
        )
        c("100nF 25V C0G C1206C104J3GACTU", supply, gnd, "Capacitor_SMD:C_1206_3216Metric")
        return u

    def ff(clk, d, qn, q, clear, preset):
        u = ic(
            "SN74AUP1G74DCUR",
            "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
            {
                1: ("CLK", clk),
                2: ("D", d),
                3: ("NOT_Q", qn),
                4: ("GND", "AGND"),
                5: ("Q", q),
                6: ("CLR_N", clear),
                7: ("PRE_N", preset),
                8: ("VCC", "AUX2V6"),
            },
            TI + "sn74aup1g74.pdf",
            power=(4, 8),
            out=(3, 5),
        )
        c("100nF 25V C0G C1206C104J3GACTU", "AUX2V6", "AGND", "Capacitor_SMD:C_1206_3216Metric")
        return u

    def translator1(a, b, va, vb, gnd):
        ic(
            "SN74LVC1T45DBVR",
            "Package_TO_SOT_SMD:SOT-23-6",
            {1: ("VCCA", va), 2: ("GND", gnd), 3: ("A", a), 4: ("B", b), 5: ("DIR", va), 6: ("VCCB", vb)},
            TI + "sn74lvc1t45.pdf",
            power=(1, 2, 6),
            out=(4,),
        )
        c("100nF 25V C0G C1206C104J3GACTU", va, gnd, "Capacitor_SMD:C_1206_3216Metric")
        c("100nF 25V C0G C1206C104J3GACTU", vb, gnd, "Capacitor_SMD:C_1206_3216Metric")
        r("47k", a, gnd)
        r("47k", b, gnd)

    # Real operating interfaces are proposals, not claims that a spare header exists.
    main = [
        "GUARDED_12V_FORCE",
        "DIG5_FORCE",
        "AUX2V6",
        "AGND",
        "AUX_VALID",
        "GLOBAL_MASTER",
        "RESET_REQUEST",
        "N19_ARM",
        "N19_START",
        "N12_ARM",
        "N12_START",
        "N19_FAULT",
        "N12_FAULT",
        "N19_COMPLETE",
        "N12_COMPLETE",
    ]
    add(
        "J",
        "NEW NF03 OPERATING FORCE/CONTROL INTERFACE - NOT P03J3",
        "Connector_PinHeader_2.54mm:PinHeader_1x15_P2.54mm_Vertical",
        [(i + 1, n, n, "passive") for i, n in enumerate(main)],
        "",
        "Physical force+return connector/harness unimplemented; no new pin rating or J3 bypass credited",
    )
    gate("AND", "AUX_VALID", "GLOBAL_MASTER", "GLOBAL_VALID")
    gate("INV", "GLOBAL_VALID", None, "NOT_GLOBAL_VALID")
    for name in ("N19", "N12"):
        n = lambda s: name + "_" + s
        gnd = n("BANK_OUT")
        local = n("LOCAL5")
        integer = n("INTVCC")
        # Isolated power is independent of the missing-source/common-mode state.
        ic(
            "TMR 1-1213",
            "Converter_DCDC:Converter_DCDC_TRACO_TMR-1-xxxx_Single_THT",
            {
                1: ("-VIN", "AGND"),
                2: ("+VIN", "GUARDED_12V_FORCE"),
                4: ("+VOUT", n("ISO15")),
                6: ("-VOUT", gnd),
            },
            "https://www.tracopower.com/tmr1-datasheet",
            power=(1, 2),
            out=(4, 6),
        )
        c("10uF 25V X7R - effective and module filter HOLD", "GUARDED_12V_FORCE", "AGND")
        c("1uF 25V X7R - effective HOLD", n("ISO15"), gnd)
        ic(
            "TPS7A1650DGNR",
            "Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm",
            {
                1: ("OUT", local),
                2: ("DNC", None),
                3: ("PG", None),
                4: ("GND", gnd),
                5: ("EN", n("ISO15")),
                6: ("NC", None),
                7: ("DELAY", n("LDO_DELAY")),
                8: ("IN", n("ISO15")),
                9: ("EP", gnd),
            },
            TI + "tps7a16.pdf",
            power=(4, 8, 9),
            out=(1,),
            nc=(2, 3, 6),
        )
        c("10uF 25V X7R - front local CIN effective>=0.1uF", n("ISO15"), gnd)
        c("10uF 25V X7R - front local COUT effective>=2.2uF", local, gnd)
        c("10nF 50V C0G5%", n("LDO_DELAY"), gnd)
        # Actual 4.646V local validity, rather than95%/85% LDO PG transfer.
        ic(
            "TPS389001DSET",
            "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
            {
                1: ("SENSE", n("LOCAL5_SENSE")),
                2: ("GND", gnd),
                3: ("MR_N", local),
                4: ("VDD", local),
                5: ("CT", n("LOCAL5_CT")),
                6: ("RESET_N", n("LOCAL5_VALID")),
            },
            TI + "tps3890.pdf",
            power=(2, 4),
            oc=(6,),
        )
        r("30.4k 0.1% receiving", local, n("LOCAL5_SENSE"))
        r("10k 0.1% receiving", n("LOCAL5_SENSE"), gnd)
        r("10k", local, n("LOCAL5_VALID"))
        c("10nF 50V C0G5%", n("LOCAL5_CT"), gnd)
        c("100nF 25V C0G C1206C104J3GACTU", local, gnd, "Capacitor_SMD:C_1206_3216Metric")
        ic(
            "OPA2192IDR",
            "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            {
                1: ("OUTA", n("SOURCE_SENSE")),
                2: ("INA-", n("SOURCE_MINUS")),
                3: ("INA+", n("SOURCE_PLUS")),
                4: ("V-", gnd),
                5: ("INB+", n("OUTPUT_PLUS")),
                6: ("INB-", n("OUTPUT_MINUS")),
                7: ("OUTB", n("OUTPUT_SENSE")),
                8: ("V+", local),
            },
            TI + "opa2192.pdf",
            power=(4, 8),
            out=(1, 7),
        )
        c("100nF 25V C0G C1206C104J3GACTU", local, gnd, "Capacitor_SMD:C_1206_3216Metric")
        for role, negative in [("SOURCE", name + "_SRC"), ("OUTPUT", name + "_PROTECTED")]:
            # R1=R4=100k, R2=R3=10k, exactly the -3 option.
            add(
                "U",
                "LT5400AIMS8E-3#PBF",
                "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm",
                [
                    (1, "R1A", negative, "passive"),
                    (8, "R1B", n(role + "_MINUS"), "passive"),
                    (2, "R2A", n(role + "_MINUS"), "passive"),
                    (7, "R2B", n(role + "_SENSE"), "passive"),
                    (3, "R3A", n(role + "_PLUS"), "passive"),
                    (6, "R3B", gnd, "passive"),
                    (4, "R4A", "AGND", "passive"),
                    (5, "R4B", n(role + "_PLUS"), "passive"),
                    (9, "EP", gnd, "passive"),
                ],
                ADI + "5400fc.pdf",
                "Actual0.1*(AGND-negative) difference amplifier; matching/life/dynamic error receiving proof pending",
            )
            ic(
                "LTC2914IGN-2#PBF",
                "Package_SO:SSOP-16_3.9x4.9mm_P0.635mm",
                {
                    1: ("VH1", n(role + "_UV_DIV")),
                    2: ("VL1", n(role + "_OV_DIV")),
                    3: ("VH2", local),
                    4: ("VL2", gnd),
                    5: ("VH3", local),
                    6: ("VL3", gnd),
                    7: ("VH4", local),
                    8: ("VL4", gnd),
                    9: ("GND", gnd),
                    10: ("REF", None),
                    11: ("OV_N", n(role + "_OV_GOOD")),
                    12: ("UV_N", n(role + "_UV_GOOD")),
                    13: ("DIS", gnd),
                    14: ("SEL", local),
                    15: ("TMR", local),
                    16: ("VCC", local),
                },
                ADI + "2914fc.pdf",
                power=(9, 16),
                oc=(11, 12),
                nc=(10,),
            )
            w = json.loads((ROOT / "design.json").read_text())["absolute_monitors_per_rail"]["windows"][name]
            for kind in ("UV", "OV"):
                r(
                    str(w[kind.lower() + "_top_ohm"]) + "ohm 0.3% COMPLETE RECEIVING",
                    n(role + "_SENSE"),
                    n(role + "_" + kind + "_DIV"),
                )
                r("10k 0.3% COMPLETE RECEIVING", n(role + "_" + kind + "_DIV"), gnd)
                r("10k", local, n(role + "_" + kind + "_GOOD"))
            c("100nF 25V C0G C1206C104J3GACTU", local, gnd, "Capacitor_SMD:C_1206_3216Metric")
        # No PG latch or floating reference-offset negative-input shortcut.
        gate("AND", n("SOURCE_UV_GOOD"), n("SOURCE_OV_GOOD"), n("S0"), local, gnd)
        gate("AND", n("S0"), n("OUTPUT_OV_GOOD"), n("S1"), local, gnd)
        gate("AND", n("S1"), n("LOCAL5_VALID"), n("SAFE_FLOAT"), local, gnd)
        gate("AND", n("OUTPUT_UV_GOOD"), n("OUTPUT_OV_GOOD"), n("O0"), local, gnd)
        gate("AND", n("O0"), n("LOCAL5_VALID"), n("READY_FLOAT"), local, gnd)
        ic(
            "ISO7731FDWR",
            "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
            {
                1: ("VCC1", local),
                2: ("GND1", gnd),
                3: ("INA", n("SAFE_FLOAT")),
                4: ("INB", n("READY_FLOAT")),
                5: ("OUTC", n("RUN_FLOAT5")),
                6: ("NC", None),
                7: ("EN1", local),
                8: ("GND1", gnd),
                9: ("GND2", "AGND"),
                10: ("EN2", "DIG5_FORCE"),
                11: ("NC", None),
                12: ("INC", n("RUN_HOST5")),
                13: ("OUTB", n("READY_HOST5")),
                14: ("OUTA", n("SAFE_HOST5")),
                15: ("GND2", "AGND"),
                16: ("VCC2", "DIG5_FORCE"),
            },
            TI + "iso7731.pdf",
            power=(1, 2, 8, 9, 15, 16),
            out=(5, 13, 14),
            nc=(6, 11),
        )
        c("100nF 25V C0G C1206C104J3GACTU", local, gnd, "Capacitor_SMD:C_1206_3216Metric")
        c("100nF 25V C0G C1206C104J3GACTU", "DIG5_FORCE", "AGND", "Capacitor_SMD:C_1206_3216Metric")
        translator1(n("RUN_FLOAT5"), n("CONTROLLER_ON"), local, integer, gnd)
        translator1(n("SAFE_HOST5"), n("SAFE"), "DIG5_FORCE", "AUX2V6", "AGND")
        translator1(n("READY_HOST5"), n("READY"), "DIG5_FORCE", "AUX2V6", "AGND")
        translator1(n("PERMIT"), n("RUN_HOST5"), "AUX2V6", "DIG5_FORCE", "AGND")
        # Hardware latches: direct START clock; asynchronous safety clear.
        gate("INV", n("SAFE"), None, n("NOT_SAFE"))
        gate("INV", n("READY"), None, n("NOT_READY"))
        gate("INV", n("WDO"), None, n("NOT_WDO"))
        gate("INV", n("ARM"), None, n("NOT_ARM"))
        gate("AND", n("ARM"), "GLOBAL_VALID", n("WD_ENABLE"))
        gate("AND", n("ARM"), n("NOT_SAFE"), n("F_SOURCE"))
        gate("AND", n("ARM"), n("WD_ARMED"), n("F_WD_ARM"))
        gate("AND", n("F_WD_ARM"), n("NOT_WDO"), n("F_TIMEOUT"))
        gate("AND", n("COMPLETE"), n("NOT_READY"), n("F_OUTPUT"))
        gate("OR", n("F_SOURCE"), n("F_TIMEOUT"), n("F0"))
        gate("OR", n("F0"), n("F_OUTPUT"), n("FAULT_CONDITION"))
        gate("AND", "RESET_REQUEST", n("NOT_ARM"), n("RESET_ALLOWED"))
        gate("INV", n("RESET_ALLOWED"), None, n("NOT_RESET_ALLOWED"))
        gate("AND", "GLOBAL_VALID", n("NOT_RESET_ALLOWED"), n("FAULT_CLR_N"))
        # Fault edges are latched on the CLOCK, PRE remains inactive. This avoids
        # the old draft's independently delayed active-low PRE/CLR overlap.
        # RESET is permitted only while ARM is LOW; source failures also clear
        # PERMIT directly. Pulse width/recovery/glitch behavior still needs the
        # actual AC/power-state test, not a quasistatic simulation claim.
        ff(n("FAULT_CONDITION"), "AUX2V6", n("NOT_FAULT"), n("FAULT"), n("FAULT_CLR_N"), "AUX2V6")
        gate("AND", n("WD_ARMED"), n("WDO"), n("START_ARMED"))
        gate("AND", n("START_ARMED"), n("SAFE"), n("START_SAFE"))
        gate("AND", n("START_SAFE"), n("NOT_FAULT"), n("PERMIT_D"))
        gate("AND", "GLOBAL_VALID", n("ARM"), n("PCLR0"))
        gate("AND", n("PCLR0"), n("NOT_FAULT"), n("PCLR1"))
        gate("AND", n("PCLR1"), n("SAFE"), n("PERMIT_CLR_N"))
        ff(n("START"), n("PERMIT_D"), n("NOT_PERMIT"), n("PERMIT"), n("PERMIT_CLR_N"), "AUX2V6")
        gate("AND", n("PERMIT"), n("READY"), n("COMPLETE_CLK"))
        gate("AND", n("PERMIT"), "AUX_VALID", n("COMPLETE_CLR_N"))
        ff(n("COMPLETE_CLK"), "AUX2V6", n("NOT_COMPLETE"), n("COMPLETE"), n("COMPLETE_CLR_N"), "AUX2V6")
        ic(
            "TPS3431SDRBR",
            "Package_SON:VSON-8-1EP_3x3mm_P0.65mm_EP1.65x2.4mm",
            {
                1: ("VDD", "AUX2V6"),
                2: ("CWD", n("CWD")),
                3: ("EN", n("WD_ENABLE")),
                4: ("GND", "AGND"),
                5: ("SET1", n("NOT_COMPLETE")),
                6: ("WDI", n("NOT_PERMIT")),
                7: ("WDO", n("WDO")),
                8: ("ENOUT", n("WD_ARMED")),
                9: ("EP", "AGND"),
            },
            TI + "tps3431.pdf",
            power=(1, 4, 9),
            oc=(7, 8),
        )
        c(
            "56nF C0G COMPLETE +/-10% RECEIVING" if name == "N19" else "33nF C0G COMPLETE +/-10% RECEIVING",
            n("CWD"),
            "AGND",
        )
        for net in (n("WDO"), n("WD_ARMED")):
            r("10k", "AUX2V6", net)
        c("100nF 25V C0G C1206C104J3GACTU", "AUX2V6", "AGND", "Capacitor_SMD:C_1206_3216Metric")
        # Both clamps release during ARM; translated ON remains LOW until PERMIT.
        gate("AND", n("PCLR0"), n("NOT_FAULT"), n("CLAMPS_RELEASE"))
        ic(
            "SN74LVC1G06DBVR",
            "Package_TO_SOT_SMD:SOT-23-5",
            {
                1: ("NC", None),
                2: ("A", n("CLAMPS_RELEASE")),
                3: ("GND", "AGND"),
                4: ("Y", n("CLAMP_LED_K")),
                5: ("VCC", "DIG5_FORCE"),
            },
            TI + "sn74lvc1g06.pdf",
            power=(3, 5),
            oc=(4,),
            nc=(1,),
        )
        r("47k", n("CLAMPS_RELEASE"), "AGND")
        r("383ohm COMPLETE +/-3% RECEIVING", "DIG5_FORCE", n("CLAMP_LED_A"))
        r("10k COMPLETE +/-3% RECEIVING", n("CLAMP_LED_A"), n("CLAMP_LED_K"))
        for label, led_a, led_k, gate_node, source_node in [
            ("PASS", n("CLAMP_LED_A"), n("CLAMP_LED_MID"), n("PASS_GATE"), n("PASS_SOURCE")),
            ("BANK", n("CLAMP_LED_MID"), n("CLAMP_LED_K"), n("BANK_GATE"), n("BANK_COMMON")),
        ]:
            r("220ohm COMPLETE +/-3% RECEIVING", gate_node, n(label + "_CLAMP_GATE"))
            add(
                "U",
                "TLP4590AF(F",
                "Package_DIP:DIP-6_W10.16mm",
                [
                    (1, "LED_A", led_a, "passive"),
                    (2, "LED_K", led_k, "passive"),
                    (4, "D1", n(label + "_CLAMP_GATE"), "passive"),
                    (5, "S_COMMON_NC", None, "no_connect"),
                    (6, "D2", source_node, "passive"),
                ],
                "https://toshiba.semicon-storage.com/info/docget.jsp?did=70530&prodName=TLP4590AF",
                "FormB normally CLOSED at LED0. A-connection4/6; gate-current/time/hot leakage are RECEIVING requirements, not qualified",
            )
        # Explicit interfaces to the unimplemented NF02 pass/power stage and E28 gate nodes.
        ports = [
            name + "_SRC",
            gnd,
            name + "_PROTECTED",
            n("PASS_SOURCE"),
            n("PASS_GATE"),
            n("BANK_GATE"),
            n("BANK_COMMON"),
            integer,
            n("CONTROLLER_ON"),
            "AGND",
        ]
        add(
            "J",
            name + " NEGATIVE POWER/CONTROLLER/GATE INTERFACE - REAL IMPLEMENTATION REQUIRED",
            "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical",
            [(i + 1, v, v, "passive") for i, v in enumerate(ports)],
            "",
            "Pin contract only: series power connector/force current/loaded gate wiring not selected; original protected bulk stays downstream",
        )
        for request in (n("ARM"), n("START")):
            r("47k", request, "AGND")
    return parts


if __name__ == "__main__":
    p = components()
    (ROOT / "components.json").write_text(json.dumps(p, indent=2) + "\n")
    print("NF03 actual component/pin rows", len(p))
