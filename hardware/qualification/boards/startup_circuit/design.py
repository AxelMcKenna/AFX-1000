"""Positive-rail LM5069 draft after the retained B2B bank; no operating PCB changes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
TI = "https://www.ti.com/lit/ds/symlink/"
RELAY = (
    "https://toshiba.semicon-storage.com/info/TLP170GM_datasheet_en_20230522.pdf?did=69102&prodName=TLP170GM"
)
DIODE = "https://www.diodes.com/datasheet/download/1N4148W.pdf"
DRIVER = "https://assets.nexperia.com/documents/data-sheet/BSS138BK.pdf"
PNP = "https://www.onsemi.com/download/data-sheet/pdf/mmbt5401lt1-d.pdf"
SHUNT = "https://www.vishay.com/docs/30100/wsl.pdf"
STAGES = {
    "P19": dict(
        offset=0,
        cdv=4.7e-6,
        cdv_text="4.7uF film >=100V effective +/-10% REQUIREMENT",
        rpwr=20000,
        uvtop=49900,
        ovtop=75000,
        rled=7500,
        bulk="1500uF 35V 20% EEUFR1V152S",
        bulk_ref="C4",
        bulk_footprint="Capacitor_THT:CP_Radial_D16.0mm_P7.50mm",
    ),
    "P12": dict(
        offset=100,
        cdv=0.68e-6,
        cdv_text="680nF film >=100V effective +/-10% REQUIREMENT",
        rpwr=39200,
        uvtop=30100,
        ovtop=43200,
        rled=4700,
        bulk="220uF 35V 20% EEUFR1V221",
        bulk_ref="C12",
        bulk_footprint="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
    ),
}


def pin(n, name, net, kind="passive", side="L"):
    return dict(number=str(n), name=name, net=net, kind=kind, side=side)


def components():
    out = []
    for rail, d in STAGES.items():
        stage = []
        off = d["offset"]

        def net(name):
            return rail + "_" + name

        def add(ref, part, footprint, pins, source, note=""):
            ref = ref[0] + str(int(ref[1:]) + off)
            stage.append(
                dict(ref=ref, part=part, footprint=footprint, pins=pins, source=source, note=note, rail=rail)
            )

        def resistor(
            ref,
            value,
            a,
            b,
            note="",
            footprint="Resistor_SMD:R_0805_2012Metric",
            source="https://www.vishay.com/docs/28758/tnpw_e3.pdf",
        ):
            add(ref, value, footprint, [pin(1, "1", a), pin(2, "2", b, side="R")], source, note)

        def cap(ref, value, a, b, note="", footprint="Capacitor_SMD:C_1206_3216Metric", source=""):
            add(ref, value, footprint, [pin(1, "+", a), pin(2, "-", b, side="R")], source, note)

        add(
            "U1",
            "LM5069MM-1/NOPB",
            "Package_SO:TSSOP-10_3x3mm_P0.5mm",
            [
                pin(1, "SENSE", net("SENSE"), "input"),
                pin(2, "VIN", net("BANK_OUT"), "power_in"),
                pin(3, "UVLO_EN", net("UV"), "input"),
                pin(4, "OVLO", net("OV"), "input"),
                pin(5, "GND", "AGND", "power_in"),
                pin(6, "TIMER", net("TIMER"), "bidirectional", "R"),
                pin(7, "PWR", net("PWR"), "input", "R"),
                pin(8, "PGD", net("PG_RAW"), "open_collector", "R"),
                pin(9, "OUT", net("PROTECTED"), "input", "R"),
                pin(10, "GATE", net("GATE"), "output", "R"),
            ],
            TI + "lm5069.pdf",
            "Latch-off variant. Limits mostly at VIN48V; 12/19V trajectory not bounded. Kelvin shunt/OUT paths required.",
        )
        resistor(
            "R1",
            "91m 1% WSL2512R0910FTA",
            net("BANK_OUT"),
            net("SENSE"),
            "Kelvin sense; all-in tolerance includes TCR and separate life/assembly allowances, not just1%.",
            "Resistor_SMD:R_2512_6332Metric",
            SHUNT,
        )
        add(
            "Q1",
            "CSD19536KTT",
            "Package_TO_SOT_SMD:TO-263-2",
            [
                pin(1, "G", net("GATE"), "input"),
                pin(2, "D_TAB", net("SENSE")),
                pin(3, "S", net("PROTECTED"), side="R"),
            ],
            TI + "csd19536ktt.pdf",
            "Body diode conducts PROTECTED→SENSE. Charged-load reverse/partial-power behavior unresolved; not reverse blocking.",
        )
        add(
            "Q2",
            "MMBT5401LT1G",
            "Package_TO_SOT_SMD:SOT-23",
            [
                pin(1, "B", net("RAMP_BASE"), "input"),
                pin(2, "E", net("RAMP_CAP"), side="R"),
                pin(3, "C", "AGND", side="R"),
            ],
            PNP,
            "Exact PNP topology from TIDA-010070Figure13. Low-current beta/leakage effects remain unresolved.",
        )
        add(
            "D2",
            "1N4148W-7-F",
            "Diode_SMD:D_SOD-123",
            [pin(1, "K", net("RAMP_CAP")), pin(2, "A", net("GATE"), side="R")],
            DIODE,
            "Gate→Cdv charging diode; Q2 discharges capacitor when GATE falls.",
        )
        resistor("R2", "1.02k 0.1%", net("GATE"), net("RAMP_BASE"), "TIDA reference1.02k base resistor.")
        cap(
            "C1",
            d["cdv_text"],
            net("RAMP_CAP"),
            "AGND",
            "Exact film MPN, hot/aged effectiveC and leakage not selected; do not procure from this draft.",
            "StartupDraft:UNSELECTED_FILM_CDV",
            TI + "lm5069.pdf",
        )
        cap(
            "C2",
            "470nF >=16V film effective +/-10%",
            net("TIMER"),
            "AGND",
            "Exact timing-cap MPN/leakage unresolved; initial±10%scenario only.",
            "StartupDraft:UNSELECTED_FILM_CTIMER",
            TI + "lm5069.pdf",
        )
        resistor(
            "R3",
            f"{d['rpwr']} 0.1%",
            net("PWR"),
            "AGND",
            "Power limit uses typical equation; full12/19V lower/upper transfer accuracy not specified.",
        )
        cap(
            "C3",
            "100nF 100V X7R",
            net("BANK_OUT"),
            "AGND",
            "Small controller bypass only; ALL protected reservoir bulk stays after Q1. Exact MPN/effectiveC open.",
        )
        cap(
            "C4",
            d["bulk"],
            net("PROTECTED"),
            "AGND",
            "Represents retained E28"
            + d["bulk_ref"]
            + " relocated electrically after new limiter; canonical board is unchanged.",
            d["bulk_footprint"],
            "https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models",
        )
        resistor(
            "R4",
            "47k 1%",
            net("PROTECTED"),
            "AGND",
            "Retained rail bleed; no guaranteed rapid discharge or safe precharge detector.",
        )
        resistor(
            "R5",
            f"{d['uvtop']} 0.1%",
            net("BANK_OUT"),
            net("UV_SW_IN"),
            "Upper UV-divider branch is normally disconnected by U2.",
        )
        resistor("R6", "10k 0.1%", net("UV"), "AGND", "Default pull-down remains connected when U2 is open.")
        add(
            "U2",
            "TLP170GM(TPL,E",
            "StartupDraft:TLP170GM_11-4M1S_UNREVIEWED",
            [
                pin(1, "LED_A", net("LED_A")),
                pin(3, "LED_K", net("LED_K")),
                pin(4, "SW", net("UV_SW_IN"), side="R"),
                pin(6, "SW", net("UV"), side="R"),
            ],
            RELAY,
            "Normally-open1FormA, current manufacturerRev3.0.A; pins1/3/4/6. Footprint not reviewed. Offleak/onres/trigger table25C; full-temp proof open.",
        )
        resistor("R7", f"{d['ovtop']} 0.1%", net("BANK_OUT"), net("OV"))
        resistor("R8", "10k 0.1%", net("OV"), "AGND")
        resistor(
            "R9",
            f"{d['rled']} 1%",
            net("BANK_OUT"),
            net("LED_A"),
            "LED power comes from local after-bank rail, never V2V5_AUX. Add this source current to P03 budget.",
        )
        resistor(
            "R10",
            "10k 1%",
            net("LED_A"),
            net("LED_K"),
            "Diverts small driver off-state leakage around LED; hot defaultOFF still unverified.",
        )
        add(
            "Q3",
            "BSS138BK,215",
            "Package_TO_SOT_SMD:SOT-23",
            [
                pin(1, "G", net("ENABLE_GATE"), "input"),
                pin(2, "S", "AGND"),
                pin(3, "D", net("LED_K"), side="R"),
            ],
            DRIVER,
            "60V selected driver. 6.5Ohm at2.5V/10mA specified25C; full-temp drive and leakage still open.",
        )
        resistor(
            "R11",
            "100 1%",
            net("ENABLE_3V3"),
            net("ENABLE_GATE"),
            "External source3.0..3.6V high;0..0.1V low requirement. Not an AUX net.",
        )
        resistor(
            "R12",
            "10k 1%",
            net("ENABLE_GATE"),
            "AGND",
            "Passive defaultOFF request; external unpowered/fault leakage must be bounded.",
        )
        resistor(
            "R13",
            "100k 1%",
            net("PROTECTED"),
            net("PG_RAW"),
            "PG_RAW is positive-rail voltage, NOT GPIO. Independent receiver/absolute-voltage-valid check missing.",
        )
        add(
            "D1",
            "STPS1H100A",
            "Diode_SMD:D_SMA",
            [pin(1, "K", net("PROTECTED")), pin(2, "A", "AGND", side="R")],
            "https://www.st.com/resource/en/datasheet/stps1h100.pdf",
            "Exact waveform/negative clamp and inductive energy coordination unresolved.",
        )
        add(
            "D3",
            "SMAJ24A" if rail == "P19" else "SMAJ15A",
            "Diode_SMD:D_SMA",
            [pin(1, "K", net("BANK_OUT")), pin(2, "A", "AGND", side="R")],
            "https://www.littelfuse.com/assetdocs/littelfuse_tvs_diode_smaj_datasheet?assetguid=13c2a823-03b8-4d1f-9ddc-9b44670aed9d",
            "Candidate input TVS only; exact pulse/source coordination and primary current drawing required.",
        )
        add(
            "J1",
            "AFTER_RETAINED_B2B_BANK input / AGND",
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
            [pin(1, "BANK_OUT", net("BANK_OUT")), pin(2, "GND", "AGND")],
            TI + "lm5069.pdf",
            "Engineering net port only, operating connector unspecified. Do not put retained bulk ahead of Q1.",
        )
        add(
            "J2",
            "PROTECTED_BULK_AND_LOAD / AGND",
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
            [pin(1, "PROTECTED", net("PROTECTED")), pin(2, "GND", "AGND")],
            TI + "lm5069.pdf",
            "Additional downstream capacitance remains unbounded; canonical net rewiring has not been performed.",
        )
        add(
            "J3",
            "ENABLE3V3 / AGND / PG_RAW",
            "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
            [
                pin(1, "ENABLE", net("ENABLE_3V3")),
                pin(2, "GND", "AGND"),
                pin(3, "HIGH_VOLTAGE_PG", net("PG_RAW")),
            ],
            TI + "lm5069.pdf",
            "Engineering port only. PG is not logic-level safe; no receiver or ready state-machine implemented.",
        )
        for i, c in enumerate(stage):
            c.update(
                x=round((85 + (i % 4) * 160) / 1.27) * 1.27,
                y=round((75 + (i // 4) * 54 + (440 if rail == "P12" else 0)) / 1.27) * 1.27,
            )
        out += stage
    return out
