"""SC02: native negative after-bank startup DRAFT, never an operating-board edit."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
TI = "https://www.ti.com/lit/ds/symlink/"
RELAY = (
    "https://toshiba.semicon-storage.com/info/TLP170GM_datasheet_en_20230522.pdf?did=69102&prodName=TLP170GM"
)
DRIVER = "https://assets.nexperia.com/documents/data-sheet/BSS138BK.pdf"
SHUNT = "https://www.vishay.com/docs/30100/wsl.pdf"
MILLER = "https://www.analog.com/media/en/technical-documentation/data-sheets/4250lhfa.pdf"
STAGES = {
    "N19": dict(
        offset=0,
        cdv=1.5e-6,
        cgs=22e-6,
        rfb=82,
        rin=2000,
        uvtop=49900,
        ovtop=75000,
        rpwr=68100,
        bulk="1500uF 35V 20% EEUFR1V152S",
        bulk_ref="C8",
        bulk_footprint="Capacitor_THT:CP_Radial_D16.0mm_P7.50mm",
    ),
    "N12": dict(
        offset=100,
        cdv=1e-6,
        cgs=10e-6,
        rfb=100,
        rin=330,
        uvtop=30100,
        ovtop=43200,
        rpwr=49900,
        bulk="220uF 35V 20% EEUFR1V221",
        bulk_ref="C16",
        bulk_footprint="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
    ),
}


def pin(n, name, net, kind="passive", side="L"):
    return dict(number=str(n), name=name, net=net, kind=kind, side=side)


def components():
    out = []
    for rail, d in STAGES.items():
        stage = []

        def net(name):
            return rail + "_" + name

        def add(ref, part, footprint, pins, source=TI + "lm5067.pdf", note=""):
            ref = ref[0] + str(int(ref[1:]) + d["offset"])
            stage.append(
                dict(ref=ref, part=part, footprint=footprint, pins=pins, source=source, note=note, rail=rail)
            )

        def r(
            ref,
            value,
            a,
            b,
            note="",
            fp="Resistor_SMD:R_0805_2012Metric",
            source="https://www.vishay.com/docs/28758/tnpw_e3.pdf",
        ):
            add(ref, value, fp, [pin(1, "1", a), pin(2, "2", b, side="R")], source, note)

        def c(ref, value, a, b, note="", fp="Capacitor_SMD:C_1206_3216Metric", source=TI + "lm5067.pdf"):
            add(ref, value, fp, [pin(1, "+/1", a), pin(2, "-/2", b, side="R")], source, note)

        vee = net("BANK_OUT")
        add(
            "U1",
            "LM5067MM-1/NOPB",
            "Package_SO:TSSOP-10_3x3mm_P0.5mm",
            [
                pin(1, "VCC", net("VCC"), "power_in"),
                pin(2, "UVLO_EN", net("UV"), "input"),
                pin(3, "OVLO", net("OV"), "input"),
                pin(4, "PWR", net("PWR"), "input"),
                pin(5, "VEE", vee, "power_in"),
                pin(6, "TIMER", net("TIMER"), "bidirectional", "R"),
                pin(7, "SENSE", net("SENSE"), "input", "R"),
                pin(8, "GATE", net("GATE_CTRL"), "output", "R"),
                pin(9, "OUT", net("PROTECTED"), "input", "R"),
                pin(10, "PGD", net("PG_RAW"), "open_collector", "R"),
            ],
            note="All internal thresholds relative to VEE, NOT AGND. -1 latch-off. Table ICC2mA/OUT48V above VEE conditions not established at -12/-19V.",
        )
        r(
            "R1",
            "91m 1% WSL2512R0910FTA",
            net("SENSE"),
            vee,
            "Kelvin shunt. Negative-rail current enters SENSE and exits VEE.",
            "Resistor_SMD:R_2512_6332Metric",
            SHUNT,
        )
        add(
            "Q1",
            "CSD19536KTT",
            "Package_TO_SOT_SMD:TO-263-2",
            [
                pin(1, "G", net("GATE_FET"), "input"),
                pin(2, "D_TAB", net("PROTECTED")),
                pin(3, "S", net("SENSE"), side="R"),
            ],
            TI + "csd19536ktt.pdf",
            "Body diode SENSE -> PROTECTED; charged output can reverse-discharge into a collapsed bank. No reverse blocking.",
        )
        r(
            "R2",
            "10 1%",
            net("GATE_CTRL"),
            net("GATE_FET"),
            "Gate stopper; external RC interoperability with LM5067 unverified.",
        )
        r(
            "R3",
            f"{d['rfb']} 1%",
            net("GATE_CTRL"),
            net("MILLER"),
            "Experimental drain-feedback RC inferred from LT4250 Fig6a, NOT a TI LM5067 reference/guarantee.",
        )
        c(
            "C1",
            f"{d['cdv'] * 1e6:g}uF bipolar film >=100V effective +/-10% REQUIREMENT",
            net("MILLER"),
            net("PROTECTED"),
            "Bipolar: voltage reverses from -VSYS to +VGS. MPN/leakage/temp/aging and loop compatibility unselected.",
            "StartupDraft:UNSELECTED_BIPOLAR_FILM_CDV",
            MILLER,
        )
        c(
            "C2",
            f"{d['cgs'] * 1e6:g}uF film >=25V effective +/-10% REQUIREMENT",
            net("GATE_FET"),
            net("SENSE"),
            "Anti-injection trial capacitor; hot minimum Vth and initial-state proof missing. Large added gate charge delays ON and OFF.",
            "StartupDraft:UNSELECTED_FILM_CGS",
            MILLER,
        )
        c(
            "C3",
            "470nF film >=16V effective +/-10% REQUIREMENT",
            net("TIMER"),
            vee,
            "Timer relative to VEE. Zero-start scenarios only; reset must actually bring TIMER <0.3V.",
            "StartupDraft:UNSELECTED_FILM_CTIMER",
        )
        r(
            "R4",
            f"{d['rpwr']} 0.1%",
            net("PWR"),
            vee,
            "LM5067 equation RPWR=1.42e5*RS*PFET. Transfer corners specified at24V/75k; actual selected values unbounded.",
        )
        r(
            "R5",
            f"{d['rin']} 0.1%",
            "AGND",
            net("VCC"),
            "Input feed resistor, NOT a bleed. N12 cannot establish2mA shunt regulation with VSYS<13.65V; vendor/measurement hold.",
        )
        c(
            "C4",
            "100nF 50V X7R REQUIREMENT",
            net("VCC"),
            vee,
            "Small VCC bypass; exact MPN/effective capacitance open. No upstream protected reservoir.",
        )
        c(
            "C5",
            d["bulk"],
            "AGND",
            net("PROTECTED"),
            "Retained E28"
            + d["bulk_ref"]
            + " is electrically AFTER limiter; polarity positive to AGND. Canonical E28 unchanged.",
            d["bulk_footprint"],
            "https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models",
        )
        r("R6", "47k 1%", "AGND", net("PROTECTED"), "Retained bleed, not a proven reset/discharge timer.")
        r(
            "R7",
            f"{d['uvtop']} 0.1%",
            "AGND",
            net("UV_SW_IN"),
            "Normally-open relay joins UV upper divider to AGND.",
        )
        r(
            "R8",
            "10k 0.1%",
            net("UV"),
            vee,
            "Passive default UV pull to VEE. Hot leakage/dynamic OFF not proven.",
        )
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
            "Normally-open1FormA pins1/3/4/6. LED host-powered. Hot trigger/leakage/RON and exact footprint remain open.",
        )
        r("R9", f"{d['ovtop']} 0.1%", "AGND", net("OV"))
        r("R10", "10k 0.1%", net("OV"), vee)
        r(
            "R11",
            "680 1%",
            "HOST_3V3",
            net("LED_A"),
            "Host3.0..3.6V supplies LED, NEVER AUX or negative rail. Explicit digital-current budget required.",
        )
        r("R12", "10k 1%", net("LED_A"), net("LED_K"), "LED leakage shunt; actual hot defaultOFF not proven.")
        add(
            "Q2",
            "BSS138BK,215",
            "Package_TO_SOT_SMD:SOT-23",
            [
                pin(1, "G", net("ENABLE_GATE"), "input"),
                pin(2, "S", "AGND"),
                pin(3, "D", net("LED_K"), side="R"),
            ],
            DRIVER,
            "Gate-source logic referenced to AGND; no direct negative-domain logic connection. Hot drive/leakage unverified.",
        )
        r(
            "R13",
            "100 1%",
            net("ENABLE_3V3"),
            net("ENABLE_GATE"),
            "Same3.0..3.6VHIGH/0..0.1VLOW requirement asSC01. E28J9 2.5V is incompatible.",
        )
        r(
            "R14",
            "10k 1%",
            net("ENABLE_GATE"),
            "AGND",
            "Missing host/high-Z requests OFF; receiver leakage/partialpower must be bounded.",
        )
        r(
            "R15",
            "100k 1%",
            "AGND",
            net("PG_RAW"),
            "PG_RAW ranges VEE..AGND, NEVER GPIO. PGD is high with VCC-VEE<2V; not a voltage-health proof.",
        )
        add(
            "D1",
            "STPS1H100A",
            "Diode_SMD:D_SMA",
            [pin(1, "K", "AGND"), pin(2, "A", net("PROTECTED"), side="R")],
            "https://www.st.com/resource/en/datasheet/stps1h100.pdf",
            "Clamp positive output excursion at interruption; inductive energy/current/negative-source overshoot still unbounded.",
        )
        add(
            "D2",
            "SMAJ24A" if rail == "N19" else "SMAJ15A",
            "Diode_SMD:D_SMA",
            [pin(1, "K", "AGND"), pin(2, "A", vee, side="R")],
            "https://www.littelfuse.com/assetdocs/littelfuse_tvs_diode_smaj_datasheet?assetguid=13c2a823-03b8-4d1f-9ddc-9b44670aed9d",
            "Input TVS negative polarity. Pulse/source/thermal coordination open, not a sustained fault clamp.",
        )
        for ref, title, pins in [
            ("J1", "AFTER_B2B_NEGATIVE / AGND", [pin(1, "BANK_OUT", vee), pin(2, "AGND", "AGND")]),
            (
                "J2",
                "PROTECTED_NEGATIVE_BULK_LOAD / AGND",
                [pin(1, "PROTECTED", net("PROTECTED")), pin(2, "AGND", "AGND")],
            ),
            (
                "J3",
                "HOST3V3 / ENABLE3V3 / AGND",
                [pin(1, "HOST_3V3", "HOST_3V3"), pin(2, "ENABLE", net("ENABLE_3V3")), pin(3, "AGND", "AGND")],
            ),
            (
                "J4",
                "PG_RAW_NEGATIVE / VEE / AGND - NOT LOGIC",
                [pin(1, "PG_RAW", net("PG_RAW")), pin(2, "VEE", vee), pin(3, "AGND", "AGND")],
            ),
        ]:
            add(
                ref,
                title,
                f"Connector_PinHeader_2.54mm:PinHeader_1x0{len(pins)}_P2.54mm_Vertical",
                pins,
                note="Engineering net port only; production connector, receiver, sequencing and power domain validation unselected.",
            )
        for i, component in enumerate(stage):
            component.update(
                x=round((85 + i % 4 * 160) / 1.27) * 1.27,
                y=round((75 + i // 4 * 54 + (495 if rail == "N12" else 0)) / 1.27) * 1.27,
            )
        out += stage
    return out
