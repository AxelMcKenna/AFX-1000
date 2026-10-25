"""New native P02 source module. Existing PSU/E25 sources remain unchanged."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
TI = "https://www.ti.com/lit/ds/symlink/"
ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"
REF_URL = ADI + "adr4520_4525_4530_4533_4540_4550.pdf"


def pin(number, name, net, kind="passive", side="L"):
    return dict(number=str(number), name=name, kind=kind, side=side, net=net)


def components():
    result = []

    def add(ref, part, footprint, pins, source="", note=""):
        i = len(result)
        result.append(
            dict(
                ref=ref,
                part=part,
                footprint=footprint,
                pins=pins,
                x=76.2 + (i % 5) * 152.4,
                y=88.9 + (i // 5) * 88.9,
                source=source,
                note=note,
            )
        )

    add(
        "U1",
        "TPSM63606RDLR",
        "",
        [
            pin(1, "VIN2", "VIN_PROTECTED", "power_in"),
            pin(2, "SW", None, "no_connect"),
            pin(3, "CBOOT", None, "no_connect"),
            pin(4, "RBOOT", None, "no_connect"),
            pin(5, "VLDOIN", "P02_PRE6V", "power_in"),
            pin(6, "AGND", "AGND", "power_in"),
            pin(7, "VCC", None, "no_connect"),
            pin(8, "VOUT1", "P02_PRE6V", "power_out", "R"),
            pin(9, "VOUT2", "P02_PRE6V", "passive", "R"),
            pin(10, "FB", "P02_PRE_FB", "input"),
            pin(11, "AGND", "AGND", "power_in"),
            pin(12, "RT", "P02_RT", "input"),
            pin(13, "PG", None, "no_connect"),
            pin(14, "EN_SYNC", "P02_ENABLE", "input"),
            pin(15, "NC", None, "no_connect"),
            pin(16, "VIN1", "VIN_PROTECTED", "power_in"),
            *[pin(n, "PGND", "AGND", "power_in") for n in (17, 18, 19, 20)],
        ],
        TI + "tpsm63606.pdf",
        "Integrated 6 A module. RDL20 manufacturer land pattern must be authored/reviewed; empty footprint is an explicit fabrication hold.",
    )
    add(
        "U2",
        "LT3083IQ#PBF",
        "Package_TO_SOT_SMD:TO-263-5_TabPin3",
        [
            pin(1, "NC", None, "no_connect"),
            pin(2, "SET", "P02_DIG_SET", "input"),
            pin(3, "OUT_TAB", "5V_DIG_SRC", "power_out", "R"),
            pin(4, "VCONTROL", "VIN_PROTECTED", "power_in"),
            pin(5, "IN", "P02_PRE6V", "power_in"),
        ],
        ADI + "LT3083.pdf",
        "DD-PAK tab is 5V_DIG_SRC, never chassis/ground. Separate 10uF IN/2.2uF CONTROL/10uF OUT effective minima; thermal interface required.",
    )
    add(
        "U3",
        "LT3045IDD#PBF",
        "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm",
        [
            pin(1, "IN", "P02_PRE6V", "power_in"),
            pin(2, "IN", "P02_PRE6V", "power_in"),
            pin(3, "EN_UV", "P02_PRE6V", "input"),
            pin(4, "PG", None, "no_connect"),
            pin(5, "ILIM", "AGND", "passive"),
            pin(6, "PGFB", "P02_PRE6V", "input"),
            pin(7, "SET", "P02_ANA_SET", "input"),
            pin(8, "GND", "AGND", "power_in"),
            pin(9, "OUTS", "V5_REG_SRC", "input", "R"),
            pin(10, "OUT", "V5_REG_SRC", "power_out", "R"),
            pin(11, "EP_GND", "AGND", "power_in"),
        ],
        ADI + "3045fa.pdf",
        "OUTS stays at local output capacitor, upstream of E26. Ground EP differs from old LT3080 output EP.",
    )
    add(
        "U4",
        "ADR4550BRZ",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        [
            pin(1, "NIC", None, "no_connect"),
            pin(2, "VIN", "P02_PRE6V", "power_in"),
            pin(3, "NIC", None, "no_connect"),
            pin(4, "GND", "AGND", "power_in"),
            pin(5, "NIC", None, "no_connect"),
            pin(6, "VOUT", "P02_REF5", "power_out", "R"),
            pin(7, "NIC", None, "no_connect"),
            pin(8, "DNC", None, "no_connect"),
        ],
        REF_URL,
        "B grade; reference drift/humidity/assembly limits require qualification beyond guaranteed initial/TC/line/load terms.",
    )
    add(
        "U5",
        "OPA2192ID",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        [
            pin(1, "OUT_A", "P02_DIG_DRIVE", "output", "R"),
            pin(2, "IN_A_N", "P02_DIG_FB", "input"),
            pin(3, "IN_A_P", "P02_REF_FILTER", "input"),
            pin(4, "V_N", "AGND", "power_in"),
            pin(5, "IN_B_P", "P02_REF_FILTER", "input"),
            pin(6, "IN_B_N", "P02_ANA_FB", "input"),
            pin(7, "OUT_B", "P02_ANA_DRIVE", "output", "R"),
            pin(8, "V_P", "VIN_PROTECTED", "power_in"),
        ],
        TI + "opa2192.pdf",
        "Independent local SET loops; gain1.008 digital/1.0012 analog. No load-side or E26 feedback sense wires.",
    )
    r = 0
    c = 0

    def resistor(value, a, b, precision=False, note=""):
        nonlocal r
        r += 1
        add(
            f"R{r}",
            value + (" 0.01% 5ppm" if precision else " 1%"),
            "Resistor_SMD:R_0805_2012Metric",
            [pin(1, "1", a), pin(2, "2", b, side="R")],
            note=note,
        )

    def cap(value, a, b, film=False, note=""):
        nonlocal c
        c += 1
        add(
            f"C{c}",
            value,
            "" if film else "Capacitor_SMD:C_1210_3225Metric",
            [pin(1, "1", a), pin(2, "2", b, side="R")],
            source="https://www.wima.de/wp-content/uploads/media/d_WIMA_MKS_2.pdf" if film else "",
            note=note,
        )

    resistor("50k", "P02_PRE6V", "P02_PRE_FB", True)
    resistor("10k", "P02_PRE_FB", "AGND", True)
    resistor("13k", "P02_RT", "AGND")
    resistor("10k", "POWER_READY", "P02_ENABLE")
    resistor(
        "22k",
        "P02_ENABLE",
        "AGND",
        note="Receiving pulldown; verify actual off-state leakage/noise. Module EN is not MCU power permission.",
    )
    resistor(
        "10k",
        "P02_REF5",
        "P02_REF_FILTER",
        True,
        "Filtered SET ramp; effective C>=12.69uF and aggregate capacitor leakage<=30nA are requirements.",
    )
    for rail, top in (("DIG", "800"), ("ANA", "120")):
        resistor(
            "6.8k",
            f"P02_{rail}_DRIVE",
            f"P02_{rail}_SET",
            note="Fault SET-current limit; amplifier can sink full regulator SET current.",
        )
        resistor(top, f"P02_{rail}_SET", f"P02_{rail}_DIV", True)
        resistor("100k", f"P02_{rail}_DIV", "AGND", True)
        resistor("100k", f"P02_{rail}_DIV", f"P02_{rail}_FB", True)
        cap(
            "47nF 50V C0G 5%",
            f"P02_{rail}_DRIVE",
            f"P02_{rail}_FB",
            note="Local high-frequency feedback; finite loop stability remains a qualification hold.",
        )
        cap("100nF 25V X7R", f"P02_{rail}_SET", "AGND")
    resistor(
        "909",
        "5V_DIG_SRC",
        "AGND",
        note="Source-side minimum-load bleed, >=5mA at normal corners; choose>=0.125W rating.",
    )
    resistor(
        "2.21k",
        "V5_REG_SRC",
        "AGND",
        note="Source-side analog bleed; own current added beyond the 0.251A protected budget.",
    )
    # Each module VIN pad has its own local input capacitor. Do not treat nominal
    # capacitance as effective over DC bias, temperature and tolerance.
    for _ in range(2):
        cap(
            "10uF 50V X7R",
            "VIN_PROTECTED",
            "AGND",
            note="TPSM63606 local CIN; candidate effective>=5uF each; MPN/DC bias qualification open.",
        )
    for _ in range(2):
        cap(
            "47uF 16V X7R",
            "P02_PRE6V",
            "AGND",
            note="Module local COUT; candidate effective>=15uF each, combined local/direct PRE bounds checked.",
        )
    cap("22uF 16V X7R", "P02_PRE6V", "AGND", note="LT3083 local IN; effective>=10uF.")
    cap("10uF 25V X7R", "VIN_PROTECTED", "AGND", note="LT3083 local VCONTROL; effective>=2.2uF.")
    cap("10uF 16V X7R", "P02_PRE6V", "AGND", note="LT3045 local IN; effective>=4.7uF.")
    cap("1uF 16V X7R", "P02_PRE6V", "AGND", note="ADR4550 local IN; effective>=0.1uF.")
    cap("1uF 16V X7R", "P02_REF5", "AGND", note="ADR4550 local output; effective0.1..100uF requirement.")
    for _ in range(3):
        cap(
            "4.7uF film 63V 10%",
            "P02_REF_FILTER",
            "AGND",
            True,
            "Combined effective>=12.69uF. Hot/aged leakage<=10nA per capacitor requires component qualification.",
        )
    cap(
        "22uF 16V X7R",
        "5V_DIG_SRC",
        "AGND",
        note="LT3083 local COUT; effective>=10uF, ESR<=0.5ohm; remote E26 bulk is beyond the postreg.",
    )
    cap(
        "22uF 16V X7R",
        "V5_REG_SRC",
        "AGND",
        note="LT3045 local COUT; effective>=10uF and local OUTS Kelvin connection.",
    )
    cap("100nF 25V X7R", "VIN_PROTECTED", "AGND", note="OPA2192 local supply bypass.")
    cap("100nF 25V X7R", "P02_PRE6V", "AGND", note="VLDOIN bypass at module pin5.")
    cap(
        "18pF 50V C0G 5%",
        "P02_PRE6V",
        "P02_PRE_FB",
        note="Feedforward candidate, 50k x 18pF = 0.9us; validate TI compensation and actual effective capacitors.",
    )
    for ref, nets in (
        ("J1", ["VIN_PROTECTED", "AGND", "POWER_READY"]),
        ("J2", ["5V_DIG_SRC", "AGND"]),
        ("J3", ["V5_REG_SRC", "AGND"]),
        ("J4", ["P02_PRE6V", "AGND"]),
    ):
        add(
            ref,
            "Header" + str(len(nets)),
            "Connector_PinHeader_2.54mm:PinHeader_1x" + f"{len(nets):02d}" + "_P2.54mm_Vertical",
            [pin(i + 1, n, n) for i, n in enumerate(nets)],
            note="Logical engineering boundary only; production current/contact/retention interface must replace/review these headers.",
        )
    for ref, destination in (("J5", "E26 analog AGND star"), ("J6", "E26 digital AGND star")):
        add(
            ref,
            "AGND_TOP_STRAP_ATTACHMENT",
            "",
            [pin(1, "AGND", "AGND")],
            note="Separate source quiet-star top attachment to "
            + destination
            + "; <=2mohm full connection; contact/stud/support/land not fabrication released.",
        )
    return result
